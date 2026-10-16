"""Normalize this TASK folder's own text files: LF only, U+0085/U+2028/U+2029 written as escape text.

JSON files are re-serialized from their parsed value (JSON-equivalent: same data, escaped separators,
LF). Markdown files get the three raw characters replaced by their backslash-u escape text (the editor
had decoded the escapes written in the report). Prints what changed. Usage: normalize_task_files.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SEP = {chr(code): chr(92) + "u" + format(code, "04x") for code in (0x85, 0x2028, 0x2029)}
TABLE = str.maketrans(SEP)
changed = []
for path in sorted(HERE.rglob("*")):
    if not path.is_file() or "baseline" in path.relative_to(HERE).parts or path.name == "manifest.json":
        continue
    if path.suffix not in (".json", ".md"):
        continue
    data = path.read_bytes()
    text = data.decode("utf-8-sig")  # PowerShell 5.1 writes a BOM; the normalized file has none
    if path.suffix == ".json":
        value = json.loads(text)
        new = json.dumps(value, ensure_ascii=False, indent=1).translate(TABLE) + "\n"
        assert json.loads(new) == value, path
    else:
        new = text.replace("\r\n", "\n").translate(TABLE)
    if new.encode("utf-8") != data:
        path.write_bytes(new.encode("utf-8"))
        changed.append(path.relative_to(HERE).as_posix())
print(json.dumps(changed, indent=1))
