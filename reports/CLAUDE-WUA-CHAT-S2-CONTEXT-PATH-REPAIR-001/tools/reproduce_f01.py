"""Standalone reproduction of F-01 (FOLLOWUP-WUA-S2-CONTEXT-PATH-001), independent of the unit tests.

In a fresh TEMP folder: one synthetic Workspace with one RAW and one Context Variant, and one synthetic "outside"
folder. For each level of .ultra/chats/<chat>/message_context/<message_id>/variants the real folder is moved
outside and replaced by a Windows junction to it; then each public writer is called once. The oracle is a plain
listing of the outside folder (names and SHA-256) before and after - no code of context_storage is used for it.
Published: per level and writer, "refused <code>" or "WROTE OUTSIDE: <new names>"; never a path.
Usage: reproduce_f01.py <code root> <label> <out.json>
  <code root> - folder that holds the context_storage.py to test (the working tree, or a copy of the base bytes)
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def load(code_root: Path):
    spec = importlib.util.spec_from_file_location("context_storage_under_test", code_root / "context_storage.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def listing(folder: Path) -> dict:
    out = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "dir"
    return out


def main():
    code_root, label, target = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3])
    cs = load(code_root)
    import _winapi
    rows = []
    for level in ("message_context", "message", "variants"):
        for writer in ("create", "activate", "restore"):
            base = Path(tempfile.mkdtemp(prefix="wa_s2r_f01_")).resolve()
            junction = None
            try:
                root = base / "w"
                root.mkdir()
                cs.ensure_workspace_storage(root)
                chat = cs.create_chat(root, "Диалог")["chat_id"]
                message = "msg_" + "1" * 32
                cs.commit_raw_message(root, chat, message, "user", "текст")
                variant = cs.create_message_context_variant(root, chat, message, "сжато", source="manual_edit")["context_variant_id"]
                context = root / ".ultra" / "chats" / chat / "message_context"
                real = {"message_context": context, "message": context / message, "variants": context / message / "variants"}[level]
                outside = base / "outside"
                outside.mkdir()
                moved = outside / "moved"
                shutil.move(str(real), str(moved))
                _winapi.CreateJunction(str(moved), str(real))
                junction = real
                before = listing(outside)
                calls = {"create": lambda: cs.create_message_context_variant(root, chat, message, "новый", source="manual_edit"),
                         "activate": lambda: cs.activate_message_context_variant(root, chat, message, variant),
                         "restore": lambda: cs.restore_message_raw(root, chat, message)}
                try:
                    calls[writer]()
                    outcome = "accepted"
                except Exception as exc:  # the refusal code is the observable result
                    outcome = "refused " + str(getattr(exc, "code", type(exc).__name__))
                after = listing(outside)
                new = sorted(set(after) - set(before))
                changed = sorted(k for k in before if k in after and before[k] != after[k])
                rows.append({"junction_at": level, "writer": writer, "outcome": outcome,
                             "outside_new_entries": [n.replace(chat, "<chat>").replace(message, "<msg>") for n in new],
                             "outside_changed_files": [n.replace(chat, "<chat>").replace(message, "<msg>") for n in changed],
                             "wrote_outside": bool(new or changed)})
            finally:
                if junction is not None:
                    try:
                        os.rmdir(junction)
                    except OSError:
                        pass
                shutil.rmtree(base, ignore_errors=True)
    record = {"task": "CLAUDE-WUA-CHAT-S2-CONTEXT-PATH-REPAIR-001", "purpose": f"standalone F-01 reproduction: {label}",
              "oracle": "names and SHA-256 of the outside folder before/after, without context_storage code",
              "cases": len(rows), "wrote_outside": sum(r["wrote_outside"] for r in rows),
              "refused": sum(r["outcome"].startswith("refused") for r in rows), "rows": rows}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: record[k] for k in ("cases", "wrote_outside", "refused")}))
    for r in rows:
        print(r["junction_at"], r["writer"], r["outcome"], r["outside_new_entries"], r["outside_changed_files"])


if __name__ == "__main__":
    main()
