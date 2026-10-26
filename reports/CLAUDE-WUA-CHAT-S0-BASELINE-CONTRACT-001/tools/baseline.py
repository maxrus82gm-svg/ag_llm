"""Stage 0 source baseline without Git: compare local bytes with the manifest of the accepted Astra rev2 analysis.

Astra rev2 (`Документация/Дополнительная аналитика Астры.md`, §2.2) lists 30 sources with byte length and SHA-256;
WEB_14 independently matched them with main@7924d765 (#436). This tool parses that table from the document on disk,
hashes the same local files, and additionally records every file the next stages are expected to read or change, so
the coordinator can compare them with the stage-0 base revision (main@d33056e6 per BLOCK 1) on GitHub.
Raw bytes, no line-ending normalisation; a LF-normalised hash is added for CRLF files. Read-only.
Usage: baseline.py <out.json>
"""
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ASTRA = REPO / "Документация" / "Дополнительная аналитика Астры.md"
EXTRA = ("context_registry.py", "server_context_messages.py", "agent_global_context.py", "web_alarm/context_pack.py",
         "web_alarm/models.py", "web_alarm/folder_picker.py", "web_alarm/store_lock.py", "web_alarm/operator_view.py",
         "test_web_alarm_operator_ui.js", "test_web_alarm_ui.py", "test_web_alarm_ui_ux.py", "test_web_alarm_server.py",
         "test_message_context.py", "test_chat_create_atomicity.py", "test_context_registry.py",
         "wa4a_acceptance.py", ".github/workflows/web-alarm-tests.yml", "chat_context.py")
sha = lambda data: hashlib.sha256(data).hexdigest()


def facts(rel: str) -> dict:
    path = REPO / rel
    if not path.is_file():
        return {"exists": False}
    data = path.read_bytes()
    row = {"exists": True, "bytes": len(data), "sha256": sha(data)}
    if b"\r\n" in data:
        row["sha256_lf_normalized"] = sha(data.replace(b"\r\n", b"\n"))
    return row


text = ASTRA.read_text(encoding="utf-8")
section = text[text.index("### 2.2."):text.index("### 2.3.")]
manifest = {m.group(1): (int(m.group(2)), m.group(3))
            for m in re.finditer(r"^\| ([\w./-]+\.(?:py|js)) \| (\d+) \| ([0-9a-f]{64}) \|$", section, re.M)}
compared = {}
for rel, (size, digest) in manifest.items():
    local = facts(rel)
    compared[rel] = {"astra_bytes": size, "astra_sha256": digest, **local,
                     "match": local.get("exists") and local["bytes"] == size and local["sha256"] == digest}
result = {
    "reference": "Дополнительная аналитика Астры.md §2.2 (rev2; matched by WEB_14 with main@7924d765 / #436)",
    "astra_document": facts("Документация/Дополнительная аналитика Астры.md"),
    "manifest_rows": len(manifest),
    "matched": sum(1 for r in compared.values() if r["match"]),
    "mismatched": sorted(rel for rel, r in compared.items() if not r["match"]),
    "compared": compared,
    "additional_files": {rel: facts(rel) for rel in EXTRA},
    "git_used": False,
}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"rows": result["manifest_rows"], "matched": result["matched"], "mismatched": result["mismatched"],
                  "missing_extra": [k for k, v in result["additional_files"].items() if not v["exists"]]}, ensure_ascii=False))
