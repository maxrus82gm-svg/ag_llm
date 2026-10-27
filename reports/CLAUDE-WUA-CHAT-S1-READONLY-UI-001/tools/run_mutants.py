"""TEST-QA for stage 1: each mutant weakens one production rule in a disposable TEMP mirror of the code; the stage-1
tests must kill it. The unmodified mirror is the control and must pass every target.

Mirror = top-level *.py and *.js plus web_alarm/*.py of the working tree (no Git metadata, no data). Python targets
run through run_gate.py with CLAUDE_RUNNER_ROOT pointing at the mirror (guarded runner, TEMP isolation); JS targets
run with node --test inside the mirror. Only names, verdicts and counters are published.
Usage: run_mutants.py <python> <out.json> [mutant-name ...]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
CS, AD, SV, UI = "context_storage.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py"
READ, HTTP, JS = ("py", ("test_ultra_chat_read",)), ("py", ("test_web_alarm_ultra_chat",)), ("js", ("test_web_alarm_ultra_chat_ui.js",))

MUTANTS = {
    # core: identity, links, limits, read-only
    "C01 file final path not compared": (CS, [("        if os.path.normcase(_final_path_of_fd(fd)) != anchor.expected(parts):\n"
                                               "            raise StorageReadError(\"unsafe_storage_link\")\n", "")], READ),
    "C02 hard links accepted": (CS, [(" or st.st_nlink != 1:", ":")], READ),
    "C03 directory checks removed": (CS, [("    if _is_link_or_reparse(st):\n        raise StorageReadError(\"unsafe_storage_link\")\n"
                                           "    if not stat.S_ISDIR(st.st_mode):", "    if not stat.S_ISDIR(st.st_mode):"),
                                          ("    if os.path.normcase(final) != anchor.expected(parts):\n"
                                           "        raise StorageReadError(\"unsafe_storage_link\")\n", "")], READ),
    "C04 message workspace not checked": (CS, [("    if data.get(\"chat_id\") != chat_id or data.get(\"workspace_id\") != workspace_id:",
                                                "    if data.get(\"chat_id\") != chat_id:")], READ),
    "C05 file name not compared with id": (CS, [("    if data.get(\"message_id\") != message_id:\n        return \"name_mismatch\"\n", "")], READ),
    "C06 oversized file read anyway": (CS, [("        if size > limits.max_message_bytes:\n            exclude(\"too_large\", message_id)\n"
                                             "            continue\n", "")], READ),
    "C07 physical read not capped": (CS, [("        data = _read_up_to(fd, limit + 1)", "        data = _read_up_to(fd, 1 << 40)")], READ),
    "C08 history size checked only after reading": (CS, [("    if listed_bytes > limits.max_history_bytes:\n", "    if False:\n")], READ),
    "C09 byte budget not enforced": (CS, [("        cap = min(limits.max_message_bytes, budget)", "        cap = limits.max_message_bytes")], READ),
    "C10 listing count unbounded": (CS, [("                if len(entries) >= max_entries:", "                if False:")], READ),
    "C11 chat workspace not checked": (CS, [("    if data.get(\"workspace_id\") != workspace_id:\n        return \"foreign_identity\"\n", "")], READ),
    "C12 one damaged chat aborts the list": (CS, [("        except StorageReadError as exc:\n            status = \"unsafe_storage_link\" if exc.code == "
                                                   "\"unsafe_storage_link\" else \"damaged\"\n",
                                                   "        except StorageReadError as exc:\n            raise\n")], READ),
    "C13 reading creates storage": (CS, [("    anchor = _StorageAnchor(workspace_root)\n    try:\n        _verify_directory(anchor, (ULTRA_DIRNAME,))",
                                          "    ensure_workspace_storage(workspace_root)\n    anchor = _StorageAnchor(workspace_root)\n"
                                          "    try:\n        _verify_directory(anchor, (ULTRA_DIRNAME,))")], READ),
    # HTTP boundary and adapter
    "H01 capability tied to the folder picker": (SV, [("        enabled=enable_ultra_chat, loopback=host in LOOPBACK_HOSTS)",
                                                       "        enabled=enable_ultra_chat and enable_folder_picker, loopback=host in LOOPBACK_HOSTS)")], HTTP),
    "H02 history without token": (SV, [("            access.require(self.headers)\n", "")], HTTP),
    "H03 Host not checked": (SV, [("        if (not peer.is_loopback or not bound.is_loopback or len(hosts) != 1\n"
                                   "                or hosts[0] not in {f'127.0.0.1:{port}', f'localhost:{port}'}):",
                                   "        if (not peer.is_loopback or not bound.is_loopback):")], HTTP),
    "H04 Origin not compared": (SV, [("(origins and origins[0] != 'http://' + hosts[0])", "False")], HTTP),
    "H05 query not validated": (AD, [("        if not separator or key not in allowed or key in values:", "        if False:")], HTTP),
    "H06 capability on non-loopback bind": (AD, [("None if enabled and loopback else", "None if enabled else")], HTTP),
    "H07 legacy Tk marker ignored": (AD, [("            if message[\"text\"].startswith(LEGACY_FAILURE_PREFIX) or \"FAILED\" in statuses:",
                                          "            if \"FAILED\" in statuses:")], HTTP),
    "H08 Workspace path in the answer": (AD, [("        base = {\"wa_workspace_id\": wa_workspace_id, \"display_name\": record.display_name}",
                                               "        base = {\"wa_workspace_id\": wa_workspace_id, \"display_name\": record.display_name, "
                                               "\"root\": str(record.workspace_root)}")], HTTP),
    "H09 page byte limit ignored": (AD, [("        if used + size > MAX_PAGE_BYTES and selected:", "        if False:")], HTTP),
    "H10 cursor ignored": (AD, [("    if before is not None:\n        end = next(", "    if False:\n        end = next(")], HTTP),
    "H11 folder token accepted for history": (AD, [("        values = headers.get_all(ULTRA_CHAT_TOKEN_HEADER, [])",
                                                    "        values = headers.get_all(ULTRA_CHAT_TOKEN_HEADER, []) or "
                                                    "headers.get_all(\"X-WebAlarm-Folder-Token\", [])")], HTTP),
    "H12 index generations ignored": (AD, [("    if generations:\n        sources.append(", "    if False:\n        sources.append(")], HTTP),
    "H13 broken run index breaks the history": (AD, [("            if exc.code == \"missing\":\n                continue\n"
                                                      "            return {}, {}, \"run_index_unavailable\"\n",
                                                      "            if exc.code == \"missing\":\n                continue\n            raise\n")], HTTP),
    # page
    "U01 token sent to the EVM badge request": (UI, [("const s=(await api('/ultra/connections/selection?role=chat'))?.selection;",
                                                      "const s=(await chatGet('/ultra/connections/selection?role=chat'))?.selection;")], JS),
    "U02 token stored in localStorage": (UI, [("  chat.token=c.available&&typeof c.token==='string'&&c.token.length>=32?c.token:null;",
                                               "  chat.token=c.available&&typeof c.token==='string'&&c.token.length>=32?c.token:null;"
                                               "try{localStorage.setItem('ultraChatToken',String(chat.token))}catch(_){}")], JS),
    "U03 history rendered as markup": (UI, [("element('div',m.text,'msg-text')",
                                             "(()=>{const d=element('div',null,'msg-text');d.innerHTML=m.text;return d})()")], JS),
    "U04 old failure shown as an answer": (UI, [("m.role==='assistant'?(failed?'Ошибка выполнения':'Ultra')", "m.role==='assistant'?'Ultra'")], JS),
    "U05 no new capability after a restart": (UI, [("    if(e.code!=='ultra_chat_token_invalid')throw e;\n    chat.token=null;", "    throw e;\n    chat.token=null;")], JS),
    "U06 operator panel stays the default": (UI, [("showView(initialView(),true);", "showView('operator',true);")], JS),
    "U07 late answers not ignored": (UI, [("    const data=await chatGet('/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats');\n"
                                           "    if(epoch!==chat.epoch)return;",
                                           "    const data=await chatGet('/ultra/chat/workspaces/'+encodeURIComponent(chat.workspace)+'/chats');")], JS),
    "U08 double click loads a page twice": (UI, [("(older&&(chat.olderBusy||!chat.page?.next_before))", "(older&&!chat.page?.next_before)")], JS),
    "U09 partial history not told": (UI, [("  else if(data.history_state==='partial')notes.push(", "  else if(false)notes.push(")], JS),
    "U10 composer enabled": (UI, [('<textarea id="chatInput" disabled ', '<textarea id="chatInput" ')], JS),
}


def mirror(edits, file_name) -> Path:
    dest = Path(tempfile.mkdtemp(prefix="claude-s1-mirror-"))
    for path in list(REPO.glob("*.py")) + list(REPO.glob("*.js")):
        shutil.copy2(path, dest / path.name)
    (dest / "web_alarm").mkdir()
    for path in (REPO / "web_alarm").glob("*.py"):
        shutil.copy2(path, dest / "web_alarm" / path.name)
    if file_name:
        target = dest / file_name
        raw = target.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n") if crlf else raw.decode("utf-8")
        for old, new in edits:
            if text.count(old) != 1:
                shutil.rmtree(dest)
                sys.exit(f"pattern occurs {text.count(old)} times in {file_name}: {old[:60]!r}")
            text = text.replace(old, new)
        target.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return dest


def run(python, dest, kind, targets):
    if kind == "js":
        done = subprocess.run(["node", "--test", *targets], cwd=dest, capture_output=True, text=True, encoding="utf-8")
        failed = sorted({line.split(" - ", 1)[1].split(" ")[0] for line in done.stdout.splitlines() if line.startswith("not ok")})
        return done.returncode, failed, None
    # PYTHONIOENCODING: run_gate.py prints its summary (with Russian error text) in UTF-8, not the console code page.
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s1", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S1-READONLY-UI-001",
               CLAUDE_RUNNER_ROOT=str(dest), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_EXTRA_PATH", None)
    done = subprocess.run([python, str(GATE), python, "mutant", *targets], cwd=dest, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    summary = json.loads(done.stdout)
    failed = sorted({t[0].split(".")[-1].split(" ")[0] for t in summary.get("non_pass", []) if t[1] != "SKIP"})
    return summary["exit"], failed, summary.get("isolation_violations")


python, target = sys.argv[1], Path(sys.argv[2])
chosen = sys.argv[3:] or list(MUTANTS)
rows = []
controls = {}
for kind, targets in {READ, HTTP, JS}:
    dest = mirror([], None)
    try:
        code, failed, isolation = run(python, dest, kind, targets)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    controls[" ".join(targets)] = {"exit": code, "failing": failed, "isolation_violations": isolation,
                                   "verdict": "PASS" if code == 0 and not failed else "FAIL"}
    print(json.dumps({"control": targets, "verdict": controls[" ".join(targets)]["verdict"]}), flush=True)
for name in chosen:
    file_name, edits, (kind, targets) = MUTANTS[name]
    dest = mirror(edits, file_name)
    try:
        code, failed, isolation = run(python, dest, kind, targets)
    finally:
        shutil.rmtree(dest, ignore_errors=True)
    verdict = "KILLED" if code != 0 and failed else "SURVIVED"
    rows.append({"mutant": name, "file": file_name, "targets": targets, "exit": code, "failing_tests": failed,
                 "isolation_violations": isolation, "verdict": verdict})
    print(json.dumps({"mutant": name, "verdict": verdict, "failing": len(failed)}, ensure_ascii=False), flush=True)
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "controls": controls, "results": rows,
          "killed": sum(r["verdict"] == "KILLED" for r in rows), "mutants": len(rows)}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
