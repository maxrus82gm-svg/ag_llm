"""TEST-QA for the access-gate prototype: each mutant weakens one rule in a TEMP copy of proto_ultra_chat_access.py and
must be killed (non-zero runner exit) by the prototype's own tests; the unmodified control must pass.
Every attempt goes through run_gate.py (guarded runner, TEMP). Only names, statuses and counters are published.
Usage: run_gate_mutants.py <python> <out.json>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]
GATE = REPO / "Alarm" / "ALARM_TASK_SESSION" / "TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001" / "tools" / "run_gate.py"
SOURCE = (TOOLS / "proto_ultra_chat_access.py").read_text(encoding="utf-8")
MUTANTS = {
    "M1 read capability follows the folder picker": [
        ('UltraChatAccess(enabled=ultra_chat, bound_host="127.0.0.1")',
         'UltraChatAccess(enabled=ultra_chat and picker, bound_host="127.0.0.1")')],
    "M2 one token shared with the folder picker": [
        ('            self.server.ultra_chat_access = UltraChatAccess(enabled=ultra_chat, bound_host="127.0.0.1")\n',
         '            self.server.ultra_chat_access = UltraChatAccess(enabled=ultra_chat, bound_host="127.0.0.1")\n'
         '            if ultra_chat:\n'
         '                self.server.ultra_chat_access._token = self.server.web_alarm_folder_picker.token\n')],
    "M3 history GET without token check": [("        access.require(self.headers)\n", "")],
    "M4 no exact Host check": [
        ('            or hosts[0] not in {f"127.0.0.1:{port}", f"localhost:{port}"}):', "            ):")],
    "M5 query parameters not validated": [
        ('        if set(query) - {"before", "limit"} or any(len(v) != 1 for v in query.values()):', "        if False:")],
    "M6 folder header accepted as chat token": [
        ("        values = headers.get_all(TOKEN_HEADER, [])\n",
         "        values = headers.get_all(TOKEN_HEADER, []) or headers.get_all(FOLDER_HEADER, [])\n")],
    "M7 Origin not compared": [('(origins and origins[0] != "http://" + hosts[0])', "False")],
    "M8 Sec-Fetch-Site not compared": [('(sites and sites[0] not in {"same-origin", "none"})', "False")],
    "M9 capability also on non-loopback bind": [
        ("enabled and bound_host in LOOPBACK_HOSTS else", "enabled else")],
    "M10 duplicate token headers tolerated": [("(len(values) != 1 or", "(len(values) < 1 or")],
}
python, target = sys.argv[1], Path(sys.argv[2])
rows = []
for name, edits in {"C0 control (unmodified)": [], **MUTANTS}.items():
    text = SOURCE
    for old, new in edits:
        if text.count(old) != 1:
            sys.exit(f"mutant {name}: pattern occurs {text.count(old)} times")
        text = text.replace(old, new)
    folder = Path(tempfile.mkdtemp(prefix="claude-s0-mutant-"))
    (folder / "proto_ultra_chat_access.py").write_text(text, encoding="utf-8", newline="\n")
    env = dict(os.environ, CLAUDE_RUN_PREFIX="claude-s0", CLAUDE_TASK_LABEL="CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001",
               CLAUDE_EXTRA_PATH=str(folder))
    done = subprocess.run([python, str(GATE), python, "mutant", "proto_ultra_chat_access"], cwd=REPO, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    summary = json.loads(done.stdout)
    failed = sorted({t[0].removeprefix("proto_ultra_chat_access.").split(" ")[0] for t in summary.get("non_pass", [])})
    control = name.startswith("C0")
    rows.append({"mutant": name, "runner_exit": summary["exit"], "tests_run": summary.get("tests_run"),
                 "isolation_violations": summary.get("isolation_violations"), "failing_tests": failed,
                 "verdict": ("PASS" if summary["exit"] == 0 else "FAIL") if control else
                            ("KILLED" if summary["exit"] != 0 and failed else "SURVIVED")})
    print(json.dumps({"mutant": name, "verdict": rows[-1]["verdict"], "failing": len(failed)}, ensure_ascii=False))
record = {"task": "CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001", "module": "tools/proto_ultra_chat_access.py",
          "runner": "wa4a_acceptance.py via run_gate.py (TEMP isolation)", "results": rows,
          "killed": sum(r["verdict"] == "KILLED" for r in rows), "mutants": len(MUTANTS),
          "control": rows[0]["verdict"]}
target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
