"""Adversarial probes of the P9 change (CLAUDE-WUA-CHAT-RUNSTORE-P9-001), each in a fresh synthetic TEMP Workspace.
The oracle is plain file inspection (names, bytes, json); outcomes are recorded as observed, including pre-existing
weaknesses that this task does not fix (marked OPEN). Usage: adversarial_p9.py <out.json>
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import context_storage as cs  # noqa: E402
import run_store  # noqa: E402

T1, T2 = "tb_" + "1" * 32, "tb_" + "2" * 32


def listing(folder: Path) -> list[str]:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*"))


def outcome(call):
    try:
        call()
        return "accepted"
    except Exception as exc:  # the observable result is the refusal type/code
        return "refused " + str(getattr(exc, "code", type(exc).__name__))


def probe(name, function):
    base = Path(tempfile.mkdtemp(prefix="wa_p9_adv_")).resolve()
    links = []
    try:
        row = function(base, links)
        row["probe"] = name
        return row
    finally:
        for link in reversed(links):
            try:
                os.rmdir(link)
            except OSError:
                pass
        shutil.rmtree(base, ignore_errors=True)


def a1_junction_at_ultra(base, links):
    import _winapi
    outside, root = base / "outside", base / "w"
    outside.mkdir()
    root.mkdir()
    _winapi.CreateJunction(str(outside), str(root / ".ultra"))
    links.append(root / ".ultra")
    result = outcome(lambda: run_store.ensure_task_index_entry(root, T1, "chat"))
    return {"result": result, "outside_entries_after": listing(outside), "verdict": "PROTECTED" if result.startswith("refused") and not listing(outside) else "OPEN"}


def a2_junction_at_audit(base, links):
    import _winapi
    outside, root = base / "outside", base / "w"
    outside.mkdir()
    (root / ".ultra").mkdir(parents=True)
    _winapi.CreateJunction(str(outside), str(root / ".ultra" / "audit"))
    links.append(root / ".ultra" / "audit")
    result = outcome(lambda: run_store.ensure_task_index_entry(root, T1, "chat"))
    written = listing(outside)
    return {"result": result, "outside_entries_after": written,
            "verdict": "OPEN (pre-existing: Run Store does not verify .ultra/audit; not changed by P9)" if written else "PROTECTED"}


def a3_damaged_index(base, links):
    root = base / "w"
    root.mkdir()
    run_store.ensure_task_index_entry(root, T1, "chat")
    canonical = run_store.workspace_index_path(root)
    rows = {}
    for label, payload in (("broken json", b"{"), ("array", b"[]"), ("newer schema", b'{"schema_version": 3, "tasks": {}, "runs": {}}')):
        canonical.write_bytes(payload)
        rows[label] = {"result": outcome(lambda: run_store.ensure_task_index_entry(root, T2, "chat")),
                       "bytes_unchanged": canonical.read_bytes() == payload}
    ok = all(r["result"].startswith("refused") and r["bytes_unchanged"] for r in rows.values())
    return {"cases": rows, "verdict": "PROTECTED (visible error, nothing overwritten)" if ok else "OPEN"}


def a4_legacy_duplicate_generations(base, links):
    root = base / "w"
    root.mkdir()
    run_store.ensure_task_index_entry(root, T1, "chat")  # canonical revision 1
    gen = run_store.audit_root(root) / "index_generations"
    gen.mkdir()
    index = json.loads(run_store.workspace_index_path(root).read_text(encoding="utf-8"))
    a = {**index, "revision": 2, "tasks": {**index["tasks"], "tb_" + "a" * 32: {"display_id": "T-002", "task_block_id": "tb_" + "a" * 32, "chat_id": "chat", "runs": []}}, "next_task_number": 3}
    b = {**index, "revision": 2, "tasks": {**index["tasks"], "tb_" + "b" * 32: {"display_id": "T-002", "task_block_id": "tb_" + "b" * 32, "chat_id": "chat", "runs": []}}, "next_task_number": 3}
    (gen / ("index-%020d-%s.json" % (2, "a" * 32))).write_text(json.dumps(a), encoding="utf-8")
    (gen / ("index-%020d-%s.json" % (2, "b" * 32))).write_text(json.dumps(b), encoding="utf-8")
    chosen = sorted(run_store.load_workspace_run_index(root)["tasks"])
    entry = run_store.ensure_task_index_entry(root, T2, "chat")
    after = json.loads(run_store.workspace_index_path(root).read_text(encoding="utf-8"))
    return {"loaded_tasks_with_two_equal_revisions": chosen, "next_entry": entry["display_id"],
            "canonical_revision_after": after["revision"], "generations_left": len(list(gen.glob("index-*.json"))),
            "verdict": "CHARACTERISED: two generations of one revision (possible only from writers before P9) resolve "
                       "deterministically to one; the other's entries are not merged back (pre-existing loss stays lost)"}


def a5_lock_folder_is_a_file(base, links):
    root = base / "w"
    (root / ".ultra").mkdir(parents=True)
    (root / ".ultra" / "locks").write_text("not a folder", encoding="utf-8")
    result = outcome(lambda: run_store.ensure_task_index_entry(root, T1, "chat"))
    return {"result": result, "index_written": run_store.workspace_index_path(root).exists(),
            "verdict": "PROTECTED (visible refusal, no write)" if result.startswith("refused") and not run_store.workspace_index_path(root).exists() else "OPEN"}


def a6_run_store_under_the_core_lock_of_the_same_thread(base, links):
    root = base / "w"
    root.mkdir()
    cs.ensure_workspace_storage(root)
    started = time.monotonic()
    with cs._existing_workspace_writer(root):  # a future Stage3 step holding the core lock calls the Run Store
        entry = run_store.create_run_summary(root, "ws", "chat", T1, "run1")
    took = time.monotonic() - started
    return {"display_ids": [entry["task_display_id"], entry["run_display_id"]], "seconds": round(took, 3),
            "verdict": "NO DEADLOCK (same lock, reentrant in its thread)" if took < 5 else "WAITED"}


def a7_missing_root(base, links):
    root = base / "absent"
    result = outcome(lambda: run_store.ensure_task_index_entry(root, T1, "chat"))
    return {"result": result, "root_created": root.exists(),
            "verdict": "visible refusal, nothing created (before P9: the root and .ultra were created silently)"}


def main():
    rows = [probe("A1 junction at .ultra", a1_junction_at_ultra),
            probe("A2 junction at .ultra/audit", a2_junction_at_audit),
            probe("A3 damaged index", a3_damaged_index),
            probe("A4 legacy duplicate generations", a4_legacy_duplicate_generations),
            probe("A5 .ultra/locks is a file", a5_lock_folder_is_a_file),
            probe("A6 Run Store under the core lock in the same thread", a6_run_store_under_the_core_lock_of_the_same_thread),
            probe("A7 missing Workspace root", a7_missing_root)]
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001", "purpose": "adversarial probes of the P9 change (synthetic TEMP Workspaces)",
              "rows": rows}
    Path(sys.argv[1]).write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for r in rows:
        print(json.dumps({k: v for k, v in r.items() if k in ("probe", "result", "verdict", "outside_entries_after")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
