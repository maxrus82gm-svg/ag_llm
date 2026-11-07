"""Collect/verify only this task's artifacts; no Git, networking or product writes."""
import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
E = PACKAGE / "evidence"
TASK = PACKAGE.name
CHANGED = ["web_alarm/ui.py", "web_alarm/ultra_chat.py", "test_web_alarm_ultra_chat_ui.js", "test_web_alarm_ultra_chat_s5_recovery.py"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect():
    baseline = load(E / "baseline.json")
    final = PACKAGE / "final"
    final.mkdir(exist_ok=True)
    source_rows, changes = [], []
    for path in CHANGED:
        data = (ROOT / path).read_bytes()
        destination = final / (path.replace("/", "__") + ".txt")
        destination.write_bytes(data)
        source_rows.append({"path": path, "sha256": sha(data), "size": len(data), "snapshot": destination.relative_to(ROOT).as_posix()})
        before = PACKAGE / "before" / (path.replace("/", "__") + ".txt")
        old = before.read_text(encoding="utf-8").splitlines(keepends=True) if before.exists() else []
        changes.extend(difflib.unified_diff(old, data.decode("utf-8").splitlines(keepends=True), fromfile="before/"+path, tofile="final/"+path))
    (E / "changes.diff").write_text("".join(changes), encoding="utf-8")
    write(E / "source_final.json", {"task_id": TASK, "files": source_rows,
          "protected": [row for row in baseline["files"] if row["path"] not in CHANGED]})
    for path in CHANGED:
        if path.endswith(".py"):
            ast.parse((ROOT / path).read_text(encoding="utf-8"))
    source = (ROOT / "web_alarm/ui.py").read_text(encoding="utf-8")
    script = re.search(r"<script>(.*?)</script>", source, re.S)[1]
    result = subprocess.run(["node", "--check", "-"], input=script, text=True, capture_output=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    write(E / "syntax.json", {"python_ast": "PASS", "python_files": 3, "inline_js_node_check": "PASS", "node_exit_code": result.returncode})
    js = (E / "final_js_52.stdout.txt").read_text(encoding="utf-8")
    py = (E / "python_web_regression.stderr.txt").read_text(encoding="utf-8")
    assert re.search(r"# tests 52\s", js) and "# fail 0" in js and "# pass 52" in js
    assert re.search(r"Ran 63 tests", py) and py.rstrip().endswith("OK")
    for case in ("test_tk_cancel_control_and_reopen_unknown", "test_tk_controls_and_history_shared_with_web"):
        assert (E / (case + ".stderr.txt")).read_text(encoding="utf-8").rstrip().endswith("OK")
    assert (E / "final_recovery3.stderr.txt").read_text(encoding="utf-8").rstrip().endswith("OK")
    write(E / "test_summary.json", {"task_id": TASK, "js": {"cases": 52, "pass": 52, "fail": 0, "skip": 0},
          "web_python": {"cases": 63, "pass": 63, "fail": 0, "skip": 0},
          "separate_tk": {"cases": 2, "pass": 2, "fail": 0}, "final_recovery_subset": {"cases": 3, "pass": 3, "included_in_web_63": True},
          "red": {"f1_js_failures": 2, "f2_python_failure": 1, "history_selection_js_failures": 2, "cancel_badge_js_failure": 1},
          "initial_errors": ["system Python missing httpx", "combined Tk/HTTP process Tcl abort exit 2147483651"],
          "guard_deny_events": len((E / "guard.jsonl").read_text().splitlines()) if (E / "guard.jsonl").exists() else 0,
          "guard_events_explanation": "Intentional existing Stage5 negative controls in combined and web-only runs; no successful external transport or credential read",
          "not_run": ["full repository suite", "CI", "real providers/OAuth", "verified 480px", "historical user RAW-loss episode"],
          "author_verdict": "PARTIAL / RESULT READY; no independent PASS"})
    home = str(Path.home())
    private = Path(tempfile.gettempdir()) / (TASK + "_private_original_logs")
    mapped = []
    for path in sorted(E.rglob("*")):
        if not path.is_file() or path.suffix not in {".txt", ".json", ".jsonl"}:
            continue
        original = path.read_bytes()
        text = original.decode("utf-8")
        cleaned = text.replace(home, "<USER_HOME>").replace(home.replace("\\", "\\\\"), "<USER_HOME>")
        if cleaned != text:
            private.mkdir(exist_ok=True)
            raw = private / path.relative_to(E).as_posix().replace("/", "__")
            if not raw.exists():
                raw.write_bytes(original)
            path.write_bytes(cleaned.encode("utf-8"))
            mapped.append({"path": path.relative_to(ROOT).as_posix(), "original_sha256": sha(original), "safe_sha256": sha(path.read_bytes()), "replacement": "USER_HOME only", "private_original": "local TEMP / TASK-ID_private_original_logs / relative filename; not published"})
    write(E / "sanitization.json", {"files": mapped, "private_archive": "local TEMP task-named private_original_logs", "credentials_or_tokens_copied": False})


def manifest():
    write(PACKAGE / "manifest.json", {"task_id": TASK, "status": "FINAL AUTHOR PACKAGE / PARTIAL / LOCAL ONLY", "date": "2026-11-07",
          "hash": "SHA-256 exact bytes", "self_excluded": True,
          "files": [{"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size, "sha256": sha(p.read_bytes())}
                    for p in sorted(PACKAGE.rglob("*")) if p.is_file() and p.name != "manifest.json"]})


def verify(post):
    values = load(PACKAGE / "manifest.json")
    actual = {p.relative_to(ROOT).as_posix() for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"}
    listed = set()
    for row in values["files"]:
        p = ROOT / row["path"]
        assert p.resolve().is_relative_to(PACKAGE) and not p.is_symlink()
        assert p.is_file() and p.stat().st_size == row["size"] and sha(p.read_bytes()) == row["sha256"], row["path"]
        assert row["path"] not in listed
        listed.add(row["path"])
    assert actual == listed
    sources = load(E / "source_final.json")
    for row in sources["files"]:
        assert sha((ROOT / row["path"]).read_bytes()) == row["sha256"]
        assert sha((ROOT / row["snapshot"]).read_bytes()) == row["sha256"]
    for row in sources["protected"]:
        assert sha((ROOT / row["path"]).read_bytes()) == row["sha256"], row["path"]
    for name in ("cancel_before", "cancel_after"):
        record = load(E / "controlled" / (name + ".json"))
        assert record["raw_sha256_before"] == record["raw_sha256_after"] == sha(record["raw_utf8"].encode("utf-8"))
        assert record["next_context"][-1]["content"] == "S5_NEXT_ONLY"
        assert len(record["next_context"]) == 2
    final_browser = load(E / "browser_final/session.json")
    assert final_browser["ui_sha256"] == sha((ROOT / "web_alarm/ui.py").read_bytes())
    requests = load(E / "browser_final/fake_transport_requests.json")
    assert len(requests) == 1 and requests[0]["messages"][-1]["content"] == "S5_BROWSER_CANCEL_FINAL"
    assert (E / "browser_final/check_error_dom.txt").is_file()
    assert len(load(PACKAGE / "followups.json")["items"]) == 6
    report = (PACKAGE / "report.md").read_text(encoding="utf-8")
    assert "PARTIAL" in report.splitlines()[4] and "480px PASS не заявлен" in report
    for target in re.findall(r"\]\(([^)]+)\)", report):
        assert (PACKAGE / target).is_file(), target
    outcome = {"phase": "post-finish" if post else "pre-finish", "result": "AUTHOR_PACKAGE_CHECK_PASS", "product_status": "PARTIAL",
               "manifest_files": len(listed), "working_files_changed": len(sources["files"]), "protected_unchanged": len(sources["protected"]),
               "cancel_raw_hashes": "PASS", "browser_final_source_bound": True}
    if post:
        receipt = load(PACKAGE / "finish_protocol.json")
        assert receipt["result"] in {"ROTATED", "ALREADY_ROTATED"}
        readback = receipt["steps"][-1]
        assert readback["block1"]["state"] == "WAITING" and readback["block1_1"]["task_id"] == TASK
        record = load(PACKAGE / "task_record.json")
        assert record["sources"]["report"]["sha256"] == sha((PACKAGE / "report.md").read_bytes())
        assert record["sources"]["assignment"]["sha256"] == sha((PACKAGE / "handoff_task.md").read_bytes())
        assert record["review"] == "NOT VERIFIED"
        before = (PACKAGE / "before/card.md").read_bytes()
        after = (ROOT / "Документация/000_Задачи Codex.md").read_bytes()
        begin = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN".encode()
        end = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END".encode()
        assert before.split(begin)[0] == after.split(begin)[0]
        assert before.split(end)[1] == after.split(end)[1]
        previous = ROOT / "reports/CODEX-WUA-S5-TURN-CHECK-DIAG-001/handoff_task.md"
        expected = load(E / "closeout_before.json")
        assert sha(previous.read_bytes()) == expected["previous_snapshot_sha256"]
        outcome.update(history_id=record["history_id"], block1="WAITING", block1_1=TASK,
                       prior_snapshot_and_blocks2_to4_preserved=True)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["collect", "manifest", "pre", "post"])
    args = parser.parse_args()
    if args.action == "collect":
        collect()
    elif args.action == "manifest":
        manifest()
    else:
        verify(args.action == "post")
