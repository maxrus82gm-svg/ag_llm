"""Syntax gate for the changed Python files: compile() in memory (no .pyc), plus a byte scan for U+0085/U+2028/U+2029
and mixed line endings. Usage: compile_check.py <out.json>
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FILES = ("context_storage.py", "web_alarm/ultra_chat.py", "web_alarm/server.py", "web_alarm/ui.py",
         "test_ultra_chat_read.py", "test_web_alarm_ultra_chat.py")
rows = {}
for rel in FILES:
    raw = (REPO / rel).read_bytes()
    text = raw.decode("utf-8")
    try:
        compile(text, rel, "exec")
        compiled = True
    except SyntaxError as exc:
        compiled = f"SyntaxError line {exc.lineno}"
    crlf = raw.count(b"\r\n")
    rows[rel] = {"compiled": compiled, "unsafe_separators": sum(text.count(chr(c)) for c in (0x85, 0x2028, 0x2029)),
                 "line_endings": "CRLF" if crlf and crlf == raw.count(b"\n") else ("LF" if not crlf else "MIXED")}
for rel in ("test_web_alarm_ultra_chat_ui.js", "test_web_alarm_evm_ui.js"):
    raw = (REPO / rel).read_bytes()
    text = raw.decode("utf-8")
    rows[rel] = {"compiled": "n/a (node --test parses it)", "unsafe_separators": sum(text.count(chr(c)) for c in (0x85, 0x2028, 0x2029)),
                 "line_endings": "CRLF" if raw.count(b"\r\n") else "LF"}
ok = all(r["compiled"] in (True, "n/a (node --test parses it)") and not r["unsafe_separators"] and r["line_endings"] != "MIXED"
         for r in rows.values())
record = {"task": "CLAUDE-WUA-CHAT-S1-READONLY-UI-001", "files": rows, "all_ok": ok}
Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"all_ok": ok}))
