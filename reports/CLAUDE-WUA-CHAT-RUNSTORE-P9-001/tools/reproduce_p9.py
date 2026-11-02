"""Standalone reproduction of P9 (Run Store v2 index, concurrent writers), independent of the unit tests.

Every scenario runs in a fresh TEMP folder (a synthetic Workspace) with N real child processes released together by
a file barrier. Each child imports run_store from <code root> and performs its share of index mutations. The
oracle reads the index files afterwards with plain json (canonical index.json and index_generations/*.json, the
highest revision wins as in run_store) - no run_store code is used to judge the result.
Scenarios:
  S1  2 processes x 40: new task + new run each (distinct ids)
  S2  4 processes x 20: the same
  S3  2 processes x 20 while index.json is held open by a reader (forces the generation fallback)
  S4  2 processes x 20: status updates of pre-created runs (update_run_summary_index)
  S5  2 processes x 20: both register the SAME 20 task ids (repeat registration must not duplicate)
Published: per scenario expected/actual counts, lost entries, duplicate display ids, child errors (type names only).
Usage: reproduce_p9.py <code root> <label> <out.json>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

CHILD = r"""
import json, sys, time
from pathlib import Path
code_root, root, prefix, count, ready, go, mode = sys.argv[1:8]
sys.path.insert(0, code_root)
import run_store
count = int(count)
Path(ready).write_text("1")
while not Path(go).exists():
    time.sleep(0.001)
errors, returned = [], {}
for k in range(count):
    task = "tb_" + (prefix + "%030d" % k)[-32:] if mode != "same" else "tb_" + "%032d" % k
    try:
        if mode in ("new", "same"):
            returned[task] = run_store.ensure_task_index_entry(root, task, "chat")["display_id"]
            if mode == "new":
                run = "run_%s_%03d" % (prefix, k)
                returned[run] = run_store.ensure_run_index_entry(root, run, task, "chat")["display_id"]
        elif mode == "status":
            run_store.update_run_summary_index(root, "run_%s_%03d" % (prefix, k), {"run_status": "DONE_" + prefix})
    except Exception as exc:
        errors.append(type(exc).__name__)
print(json.dumps({"errors": errors, "returned": returned}))
"""


def final_index(root: Path) -> dict:
    audit = root / ".ultra" / "audit"
    candidates = []
    canonical = audit / "index.json"
    if canonical.is_file():
        value = json.loads(canonical.read_text(encoding="utf-8"))
        candidates.append((value.get("revision", 0), 1, value))
    gen = audit / "index_generations"
    generations = sorted(gen.glob("index-*.json")) if gen.is_dir() else []
    revisions = []
    for path in generations:
        value = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((value.get("revision", 0), 0, value))
        revisions.append(value.get("revision", 0))
    best = max(candidates, key=lambda c: (c[0], c[1]))[2] if candidates else {"tasks": {}, "runs": {}}
    return {"index": best, "generations": len(generations),
            "duplicate_generation_revisions": sum(n - 1 for n in Counter(revisions).values() if n > 1)}


def run_children(code_root: Path, root: Path, prefixes, count, mode, hold_index=False):
    base = root.parent
    go = base / "go"
    children = []
    for prefix in prefixes:
        ready = base / f"ready_{prefix}"
        children.append(subprocess.Popen([sys.executable, "-B", "-c", CHILD, str(code_root), str(root), prefix, str(count),
                                          str(ready), str(go), mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, encoding="utf-8"))
    for prefix in prefixes:
        deadline = time.monotonic() + 60
        while not (base / f"ready_{prefix}").exists():
            if time.monotonic() > deadline:
                raise RuntimeError("child did not start")
            time.sleep(0.01)
    holder = open(root / ".ultra" / "audit" / "index.json", "rb") if hold_index else None
    go.write_text("1")
    errors, crashed, returned = [], 0, []
    try:
        for child in children:
            out, err = child.communicate(timeout=600)
            if child.returncode != 0:
                crashed += 1
                errors.append("CRASH:" + (err.strip().splitlines() or ["?"])[-1].split(":")[0][:60])
            else:
                answer = json.loads(out.strip().splitlines()[-1])
                errors.extend(answer["errors"])
                returned.append(answer["returned"])
    finally:
        if holder is not None:
            holder.close()
        go.unlink(missing_ok=True)
        for prefix in prefixes:
            (base / f"ready_{prefix}").unlink(missing_ok=True)
    return errors, crashed, returned


def returned_checks(returned, index):
    """Display ids the callers were given: one id handed out for two different entries, or no longer true."""
    owners = {}
    for answer in returned:
        for key, display in answer.items():
            owners.setdefault(display, set()).add(key)
    reused = sum(1 for keys in owners.values() if len(keys) > 1)
    final = {**{k: v["display_id"] for k, v in index.get("tasks", {}).items()},
             **{k: v["display_id"] for k, v in index.get("runs", {}).items()}}
    differs = sum(1 for answer in returned for key, display in answer.items() if final.get(key) != display)
    return reused, differs


def scenario(code_root: Path, name: str, prefixes, count, mode, hold_index=False):
    base = Path(tempfile.mkdtemp(prefix="wa_p9_repro_")).resolve()
    try:
        root = base / "w"
        root.mkdir()
        sys.path.insert(0, str(code_root))
        import run_store  # the code under test only prepares the fixture (sequentially)
        if mode == "status" or hold_index:
            # one sequential entry so index.json exists (needed to hold it open) and, for S4, runs to update
            seed = "tb_" + "f" * 32
            run_store.ensure_task_index_entry(root, seed, "chat")
        if mode == "status":
            for prefix in prefixes:
                for k in range(count):
                    task = "tb_" + (prefix + "%030d" % k)[-32:]
                    run_store.create_run_summary(root, "ws", "chat", task, "run_%s_%03d" % (prefix, k))
        before = final_index(root)["index"]
        errors, crashed, returned = run_children(code_root, root, prefixes, count, mode, hold_index)
        after = final_index(root)
        index = after["index"]
        reused, differs = returned_checks(returned, index)
        result = {"scenario": name, "processes": len(prefixes), "per_process": count, "mode": mode,
                  "index_held_open": hold_index, "child_errors": dict(Counter(errors)), "crashed_children": crashed,
                  "generation_files": after["generations"],
                  "duplicate_generation_revisions": after["duplicate_generation_revisions"],
                  "display_ids_handed_out_twice": reused, "returned_ids_not_in_final_index": differs}
        tasks, runs = index.get("tasks", {}), index.get("runs", {})
        if mode == "new":
            expected = len(prefixes) * count + len(before.get("tasks", {}))
            result.update(expected_tasks=expected, actual_tasks=len(tasks),
                          expected_runs=len(prefixes) * count, actual_runs=len(runs))
            ids_t = [t["display_id"] for t in tasks.values()]
            ids_r = [r["display_id"] for r in runs.values()]
            result.update(duplicate_task_display_ids=len(ids_t) - len(set(ids_t)),
                          duplicate_run_display_ids=len(ids_r) - len(set(ids_r)),
                          runs_missing_from_their_task=sum(1 for r in runs.values()
                                                           if r["run_id"] not in tasks.get(r["task_block_id"], {}).get("runs", [])),
                          next_task_number=index.get("next_task_number"), next_run_number=index.get("next_run_number"))
            result["lost"] = (result["expected_tasks"] - result["actual_tasks"]) + (result["expected_runs"] - result["actual_runs"])
        elif mode == "same":
            result.update(expected_tasks=count + len(before.get("tasks", {})), actual_tasks=len(tasks),
                          next_task_number=index.get("next_task_number"))
            ids_t = [t["display_id"] for t in tasks.values()]
            result["duplicate_task_display_ids"] = len(ids_t) - len(set(ids_t))
            result["numbers_consumed_beyond_entries"] = int(index.get("next_task_number", 1)) - 1 - len(tasks)
            result["lost"] = result["expected_tasks"] - result["actual_tasks"]
        else:
            done = sum(1 for r in runs.values() if str(r.get("run_status", "")).startswith("DONE_"))
            result.update(expected_updates=len(prefixes) * count, applied_in_index=done)
            result["lost"] = result["expected_updates"] - done
        result["defect_observed"] = bool(result["lost"] or crashed or errors or reused or differs
                                         or result["duplicate_generation_revisions"] or result.get("duplicate_task_display_ids")
                                         or result.get("duplicate_run_display_ids") or result.get("runs_missing_from_their_task"))
        return result
    finally:
        sys.path.remove(str(code_root)) if str(code_root) in sys.path else None
        sys.modules.pop("run_store", None)
        shutil.rmtree(base, ignore_errors=True)


def main():
    code_root, label, target = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3])
    rows = [scenario(code_root, "S1", ["a", "b"], 40, "new"),
            scenario(code_root, "S2", ["a", "b", "c", "d"], 20, "new"),
            scenario(code_root, "S3", ["a", "b"], 20, "new", hold_index=True),
            scenario(code_root, "S4", ["a", "b"], 20, "status"),
            scenario(code_root, "S5", ["a", "b"], 20, "same")]
    record = {"task": "CLAUDE-WUA-CHAT-RUNSTORE-P9-001", "purpose": f"standalone P9 reproduction: {label}",
              "oracle": "final index read with plain json (canonical + generations, highest revision), not run_store code",
              "scenarios": len(rows), "defects_observed": sum(r["defect_observed"] for r in rows), "rows": rows}
    target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"scenarios": len(rows), "defects_observed": record["defects_observed"]}))
    for r in rows:
        print(json.dumps({k: v for k, v in r.items() if k not in ("mode",)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
