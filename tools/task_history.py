"""Addressed task history. JSON records live beside existing reports, never in 001.

Read commands print a bounded result or nothing. Registration preserves old metadata;
it does not assert independent acceptance, publish files, or rotate a task card.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ID_RE = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)+\Z")
MAX_BYTES = 8 * 1024 * 1024
AGENTS = {"codex": "Codex", "claude": "Claude", "ultra": "Ultra Desktop"}
CARDS = {"codex": "001_История выполненных задач Codex.md",
         "claude": "001_История выполненных задач Claude.md",
         "ultra": "001_История выполнения задач Ultra Desktop.md"}
BEGIN = "<!-- TASK-HISTORY-INDEX:BEGIN -->"
END = "<!-- TASK-HISTORY-INDEX:END -->"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_id(value):
    if not ID_RE.fullmatch(value) or len(value) > 120:
        raise ValueError("Invalid TASK ID")
    return value


def safe_path(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Expected a repository-relative path without traversal")
    path = root / rel
    for node in (path, *path.parents):
        if node == root:
            break
        if node.exists() or node.is_symlink():
            st = node.lstat()
            if node.is_symlink() or getattr(st, "st_file_attributes", 0) & 0x400:
                raise ValueError("Links/reparse points are not history sources")
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path outside repository")
    return path


def bounded_bytes(path):
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing, non-file or oversized history source: " + str(path))
    return path.read_bytes()


def source_ref(root, path, first=None, last=None):
    p = safe_path(root, path)
    data = bounded_bytes(p)
    ref = {"path": Path(path).as_posix(), "sha256": digest(data)}
    if first is not None or last is not None:
        count = len(data.decode("utf-8-sig").splitlines())
        if first is None or last is None or not 1 <= first <= last <= count:
            raise ValueError("Invalid source range")
        ref.update(first_line=first, last_line=last)
    return ref


def source_text(root, ref):
    data = bounded_bytes(safe_path(root, ref["path"]))
    if digest(data) != ref["sha256"]:
        raise ValueError("Source changed: " + ref["path"])
    text = data.decode("utf-8-sig").replace("\r\n", "\n")
    if 'first_line' in ref or 'last_line' in ref:
        lines = text.splitlines(keepends=True)
        first, last = ref.get('first_line'), ref.get('last_line')
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
            raise ValueError('Invalid source line boundaries')
        text = ''.join(lines[first-1:last])
    return text


@contextlib.contextmanager
def locked(root):
    key = digest(str(Path(root).resolve()).casefold().encode())[:24]
    p = Path(tempfile.gettempdir()) / ("task-history-" + key + ".lock")
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError:
        raise ValueError("History is locked; retry after the other writer finishes")
    try:
        os.close(fd)
        yield
    finally:
        p.unlink(missing_ok=True)


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".history-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    if path.read_bytes() != data:
        raise ValueError("History readback failed")


def record_path(root, task):
    return safe_path(root, f"reports/{valid_id(task)}/task_record.json")


def load_record(root, task):
    if re.fullmatch(r"H-[A-Z0-9_]+-\d{6}", task):
        matches = []
        for p in safe_path(root, 'reports').glob('*/task_record.json'):
            value = json.loads(bounded_bytes(safe_path(root, p.relative_to(root))).decode('utf-8'))
            if value.get('history_id') == task:
                matches.append(value.get('id'))
        if len(matches) != 1:
            raise ValueError('Unknown or duplicate HISTORY ID')
        task = matches[0]
    value = json.loads(bounded_bytes(record_path(root, task)).decode("utf-8"))
    if value.get("schema") != 1 or value.get("id") != task or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',value.get('agent','')):
        raise ValueError("Invalid history record")
    return value


def save_record(root, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("Record too large")
    atomic(record_path(root, value["id"]), data)


def register(root, task, agent, title, date, sources, status="SUBMITTED / REVIEW PENDING"):
    valid_id(task)
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',agent) or not title.strip() or len(title) > 240 or "\n" in title:
        raise ValueError("Expected known agent and a one-line title of at most 240 characters")
    dt.date.fromisoformat(date)
    for ref in sources.values():
        source_text(root, ref)  # verify before metadata writes
    with locked(root):
        path = record_path(root, task)
        old = load_record(root, task) if path.exists() else None
        if old and old["agent"] != agent:
            raise ValueError("TASK ID belongs to another agent")
        if old and {k:v for k,v in old["sources"].items() if k != 'review'} == sources:
            return old  # repeated finish cannot erase a verifier's verdict
        value = {"schema": 1, "id": task, "history_id": old['history_id'] if old else next_history_id(root, agent), "agent": agent, "title": title,
                 "date": date, "status": status, "review": "NOT VERIFIED",
                 "sources": sources, "previous": []}
        if old:
            previous = dict(old)
            value["previous"] = previous.pop("previous", []) + [previous]
        else:
            counter_path = safe_path(root, 'reports/task_history_sequences.json')
            counters = json.loads(bounded_bytes(counter_path)) if counter_path.exists() else {}
            counters[agent] = int(value['history_id'].rsplit('-', 1)[1])
            atomic(counter_path, (json.dumps(counters, sort_keys=True) + '\n').encode())
        save_record(root, value)
        return value


def card_agent(card_path):
    agent_name = Path(card_path).stem.removeprefix("000_Задачи ").strip()
    agent = next((key for key, value in AGENTS.items() if value == agent_name), agent_name.lower().replace(' ','_'))
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',agent):
        raise ValueError('Unsupported card agent identifier')
    return agent


def next_history_id(root, agent):
    prefix = 'H-' + agent.upper() + '-'
    values = [v['history_id'] for v in all_records(root) if v.get('history_id','').startswith(prefix)]
    if len(values) != len(set(values)):
        raise ValueError('Duplicate HISTORY ID')
    number = 1 + max([int(v.removeprefix(prefix)) for v in values] or [0])
    counter_path = safe_path(root, 'reports/task_history_sequences.json')
    counters = json.loads(bounded_bytes(counter_path)) if counter_path.exists() else {}
    counter = counters.get(agent, 0)
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        raise ValueError('Invalid history sequence counter')
    number = max(number, counter + 1)
    if number > 999999:
        raise ValueError('History sequence exhausted')
    return prefix + f'{number:06d}'


def preview_history_id(root, task, card_path):
    p = record_path(root, task)
    return load_record(root, task)['history_id'] if p.exists() else next_history_id(root, card_agent(card_path))


def register_submission(root, card_path, task, snapshot, report, date):
    agent = card_agent(card_path)
    root = Path(root).resolve()
    assignment = Path(snapshot).relative_to(root).as_posix()
    report_rel = Path(report).relative_to(root).as_posix()
    text = bounded_bytes(Path(snapshot)).decode("utf-8-sig")
    # Search only inside the preserved assignment, not the snapshot's wrapper title.
    body = text.split("<!-- TASK-SNAPSHOT:BEGIN -->", 1)[-1]
    candidates = re.findall(r"^(?:#{1,3} (?:Задача:?\s*)?|\*\*Название:\*\*\s*)(.+)$", body, re.M)
    title = next((s.strip(" *#") for s in candidates if "БЛОК " not in s and len(s) > 15), task)
    sources = {"assignment": source_ref(root, assignment), "report": source_ref(root, report_rel)}
    value = register(root, task, agent, title[:240], date, sources)
    return {"id": task, "history_id": value['history_id'], "record": record_path(root, task).relative_to(root).as_posix(),
            "status": value["status"], "review": value["review"]}


def all_records(root, agent=None, query=None):
    reports = safe_path(root, "reports")
    records = []
    for p in reports.glob("*/task_record.json"):
        value = load_record(root, p.parent.name)
        if agent and value["agent"] != agent:
            continue
        if query and query.casefold() not in (value["id"] + " " + value["title"]).casefold():
            continue
        records.append(value)
    return sorted(records, key=lambda v: (v["date"], int(v['history_id'].rsplit('-',1)[1]), v["id"]), reverse=True)


def row(value):
    clean = lambda s: str(s).replace("|", "/").replace("\n", " ")
    task = value["id"]
    return (f"| {value['date']} | `{value['history_id']}` / `{task}` | {clean(value['title'])} | {clean(value['status'])}; "
            f"{clean(value['review'])} | `reports/{task}/task_record.json` |")


def table(records):
    return ("| Дата | ID | Задача | Статус / проверка | Адрес подробностей |\n"
            "| --- | --- | --- | --- | --- |\n" + "\n".join(row(v) for v in records) + "\n")


def render_indexes(root):
    """Coordinator action. Prepare all views, compare old bytes, then publish each atomically.

    Views are rebuildable. A crash may leave a stale view, never destroy a task record.
    """
    with locked(root):
        records = all_records(root)
        changes = []
        for agent, filename in CARDS.items():
            p = safe_path(root, "Документация/" + filename)
            old = bounded_bytes(p)
            text = old.decode("utf-8-sig")
            if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) >= text.index(END):
                raise ValueError("Missing/ambiguous generated index boundaries: " + filename)
            selected = [v for v in records if v["agent"] == agent][:10]
            body = table(selected) if selected else "Зарегистрированных задач пока нет.\n"
            a, tail = text.split(BEGIN)
            _, b = tail.split(END)
            new = (a + BEGIN + "\n" + body + END + b).encode("utf-8")
            changes.append((p, old, new))
        p = safe_path(root, "Документация/05_Реестр задач.md")
        old = bounded_bytes(p)
        text = old.decode("utf-8-sig")
        if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) >= text.index(END):
            raise ValueError("Missing/ambiguous index boundaries in 05")
        a, tail = text.split(BEGIN)
        _, b = tail.split(END)
        selected = [v for agent in AGENTS for v in [x for x in records if x['agent'] == agent][:10]]
        changes.append((p, old, (a + BEGIN + "\n" + table(selected) + END + b).encode("utf-8")))
        for p, old, new in changes:
            if p.read_bytes() != old:
                raise ValueError("Index changed concurrently")
        for p, old, new in changes:
            if p.read_bytes() != old:
                raise ValueError("Index changed concurrently; rerun render after reconciliation")
            if new != old:
                atomic(p, new)
        return [str(p.relative_to(root)) for p, _, _ in changes]


def bounded_output(text, budget):
    if not 1 <= budget <= 20000:
        raise ValueError("max-tokens must be 1..20000")
    try:
        import tiktoken
        units = len(tiktoken.get_encoding("o200k_base").encode(text))
        method = "o200k_base"
    except ImportError:
        units = len(text.encode("utf-8"))
        method = "UTF-8 bytes (conservative o200k_base upper bound)"
    if units > budget:
        raise ValueError(f"Output exceeds budget ({units} via {method}; limit {budget}). Select fewer records or a line range; nothing printed.")
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-tokens", type=int, default=8000)
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--agent", choices=AGENTS)
    ls.add_argument("--last", type=int, default=10)
    ls.add_argument("--query")
    read = sub.add_parser("read")
    read.add_argument("--id", required=True)
    read.add_argument("--part", default="record")
    read.add_argument("--start-line", type=int, default=1)
    read.add_argument("--lines", type=int)
    add = sub.add_parser('register')
    add.add_argument('--id', required=True)
    add.add_argument('--agent', required=True, choices=AGENTS)
    add.add_argument('--title', required=True)
    add.add_argument('--date', required=True)
    add.add_argument('--assignment', required=True)
    add.add_argument('--report', required=True)
    add.add_argument('--apply', action='store_true')
    review = sub.add_parser("review")
    review.add_argument("--id", required=True)
    review.add_argument("--verdict", required=True, choices=["PASS", "PARTIAL", "REVISE", "FAIL", "BLOCKED"])
    review.add_argument("--evidence", required=True)
    review.add_argument("--scope", required=True)
    review.add_argument("--apply", action="store_true")
    render = sub.add_parser("render")
    render.add_argument("--apply", action="store_true")
    sub.add_parser("validate")
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    try:
        if args.command == "list":
            if not 1 <= args.last <= 100:
                raise ValueError("last must be 1..100")
            records = all_records(root, args.agent, args.query)
            output = table(records[:args.last]) + f"\nПоказано {min(args.last, len(records))} из {len(records)}. Полные тексты не загружены.\n"
        elif args.command == "read":
            value = load_record(root, valid_id(args.id))
            if args.part == "record":
                text = json.dumps({k:v for k,v in value.items() if k != 'previous'}, ensure_ascii=False, indent=2) + "\n"
            else:
                if args.part not in value["sources"]:
                    raise ValueError("Unknown part; first read record metadata")
                text = source_text(root, value["sources"][args.part])
            lines = text.splitlines(keepends=True)
            if args.start_line < 1 or args.start_line > len(lines) or (args.lines is not None and args.lines < 1):
                raise ValueError("Invalid output line range")
            stop = len(lines) if args.lines is None else min(len(lines), args.start_line-1+args.lines)
            output = (f"ID {args.id}; part {args.part}; lines {args.start_line}-{stop}/{len(lines)}\n" +
                      "".join(lines[args.start_line-1:stop]))
        elif args.command == 'register':
            sources = {k:source_ref(root,getattr(args,k)) for k in ('assignment','report')}
            value = register(root,args.id,args.agent,args.title,args.date,sources) if args.apply else None
            output = json.dumps({'id':args.id,'history_id':value['history_id'] if value else None,'applied':args.apply},ensure_ascii=False)+'\n'
        elif args.command == "review":
            ref = source_ref(root, args.evidence)
            if not args.scope.strip() or len(args.scope) > 500 or "\n" in args.scope:
                raise ValueError("Expected a short explicit review scope")
            with locked(root):
                value = load_record(root, valid_id(args.id))
                previous = dict(value)
                old_history = previous.pop("previous", [])
                value.update(review=args.verdict + " / " + args.scope, sources={**value['sources'], 'review':ref})
                if value != {**previous, 'previous':old_history}:
                    value['previous'] = old_history + [previous]
                if args.apply:
                    save_record(root, value)
            output = json.dumps({'id':args.id,'review':value['review'],'applied':args.apply},ensure_ascii=False)+"\n"
        elif args.command == "render":
            output = json.dumps({'updated':render_indexes(root) if args.apply else [],'apply':args.apply},ensure_ascii=False)+"\n"
        else:
            records = all_records(root)
            for value in records:
                for ref in value['sources'].values():
                    source_text(root, ref)
            output = json.dumps({'records':len(records),'sources':'HASH VERIFIED'})+"\n"
        sys.stdout.write(bounded_output(output, args.max_tokens) if args.command in ('list','read','validate') else output)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("History refused: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
