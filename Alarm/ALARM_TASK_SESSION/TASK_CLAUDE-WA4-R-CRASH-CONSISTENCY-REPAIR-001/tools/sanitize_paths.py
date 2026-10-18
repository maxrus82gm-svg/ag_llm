"""Replace machine paths (<TEMP>, <USER>) in this TASK folder's own run summaries; JSON stays valid.
Usage: sanitize_paths.py <file> [...]"""
import json
import sys
import tempfile
from pathlib import Path

TEMP = str(Path(tempfile.gettempdir()).resolve())
HOME = str(Path.home())
for name in sys.argv[1:]:
    path = Path(name)
    text = path.read_text(encoding="utf-8-sig")
    for raw, token in ((TEMP, "<TEMP>"), (HOME, "<USER>")):
        for form in (raw, raw.replace("\\", "\\\\"), raw.replace("\\", "/")):
            text = text.replace(form, token)
    json.loads(text)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))
    print("sanitized", path.name)
