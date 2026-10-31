"""Change inventory of CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001 without Git: the two changed files against the copies
taken before the first edit (a private TEMP folder, passed as an argument, never published), and every other file
of the Stage2 package against that package's manifest (must be unchanged: server.py, ui.py, ultra_ui.py, ...).
Published: SHA-256 before/after (raw and LF-normalised), line ending, added/removed line counts.
Usage: change_inventory.py <baseline-folder> <out.json>
"""
import difflib
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHANGED = ("context_storage.py", "test_ultra_chat_storage.py")
UNCHANGED_IN_SCOPE = ("test_message_context.py",)
sha = lambda data: hashlib.sha256(data).hexdigest()


def row(data: bytes) -> dict:
    lf = data.replace(b"\r\n", b"\n")
    return {"sha256": sha(data), "sha256_lf": sha(lf), "eol": "CRLF" if b"\r\n" in data else "LF", "lines": lf.count(b"\n")}


def main():
    base, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = {}
    for rel in CHANGED + UNCHANGED_IN_SCOPE:
        before, after = (base / rel).read_bytes(), (REPO / rel).read_bytes()
        diff = list(difflib.unified_diff(before.decode("utf-8").splitlines(), after.decode("utf-8").splitlines(), lineterm="", n=0))
        files[rel] = {"before": row(before), "after": row(after), "changed": before != after,
                      "added": sum(1 for d in diff if d.startswith("+") and not d.startswith("+++")),
                      "removed": sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))}
    s2 = json.loads((REPO / "reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/manifest.json").read_text(encoding="utf-8"))
    others = {}
    for group in ("changed_files", "new_files"):
        for rel, pinned in s2[group].items():
            if rel in CHANGED:
                continue
            data = (REPO / rel).read_bytes()
            lf = data.replace(b"\r\n", b"\n")
            others[rel] = pinned["sha256"] in {sha(data), sha(lf), sha(lf.replace(b"\n", b"\r\n"))}
    record = {"task": "CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", "method": "byte comparison with the pre-edit copies; no Git",
              "files": files, "stage2_files_outside_scope_unchanged": others,
              "all_outside_scope_unchanged": all(others.values())}
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: (v["added"], v["removed"], v["changed"]) for k, v in files.items()}))
    print(json.dumps(others))


if __name__ == "__main__":
    main()
