"""Build a disposable TEMP mirror of the repository code for red-final and quality-mutant runs.

Usage: build_mirror.py <variant> <dest>
  variant "baseline": the 8 scope files are replaced by the exact pre-repair bytes in baseline/web_alarm.
  variant "<mutant>": one exact, single-occurrence replacement on the repaired bytes (see MUTANTS).
Copies only top-level *.py and web_alarm/*.py (read-only use of the repository); refuses a dest
outside TEMP or an existing dest. Prints a JSON line with the changed files and their SHA-256.
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(r"M:\GitHub\ag_llm")
TASK = Path(__file__).resolve().parent.parent
BASELINE = TASK / "baseline" / "web_alarm"

MUTANTS = {
    # R-MT: the transition intent is not written before the compare-and-set
    "M1-no-intent": ("state_machine.py",
                     "                task_id, MICROTASK_INTENT, microtask_id=microtask_id, operation_id=operation_id,",
                     "                task_id, \"MUTANT_NOT_AN_INTENT\", microtask_id=microtask_id, operation_id=operation_id,"),
    # R-MT: a step does not reconcile open intents on entry
    "M2-no-entry-resolve": ("state_machine.py",
                            "        with self.tasks.mutation_lock(task_id):\n            self._resolve_locked(task_id, microtask_id, step)\n",
                            "        return None\n"),
    # AUD-02b: closeout ignores legacy VERIFIED without evidence
    "M3-closeout-ignores-unproven": ("projection.py",
                                     "        elif item[\"code\"] == \"MICROTASK_VERIFICATION_UNPROVEN\":",
                                     "        elif item[\"code\"] == \"MUTANT_NEVER_EMITTED\":"),
    # R-OP: the reconciling replay goes on to execute in the same call
    "M4-reconcile-then-execute": ("operation_store.py",
                                  "                    raise OperationIntentReconciled(task_id, chosen_id)",
                                  "                    pass"),
    # R-OP: progress events do not disqualify reconstruction
    "M5-no-progress-check": ("operation_store.py",
                             "            if event.event_type in _PROGRESS_EVENTS:",
                             "            if False:"),
    # R-MT: the recovery (RC-6) status writer does not close an open intent first
    "M6-rc6-no-resolve": ("recovery_coordinator.py",
                          "            self.operations.events.resolve_microtask_intents_locked(task_id, microtask_id)",
                          "            None"),
    # AUD-02b: the journal never reports legacy VERIFIED without evidence
    "M7-no-unproven": ("event_checkpoint_store.py",
                       "    unproven = sorted(",
                       "    unproven = [] and sorted("),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    variant, dest = sys.argv[1], Path(sys.argv[2]).resolve()
    temp = Path(os.environ["TEMP"]).resolve()
    if temp not in dest.parents or dest.exists():
        raise SystemExit(f"refused: {dest} must be a new directory under TEMP")
    (dest / "web_alarm").mkdir(parents=True)
    for src in REPO.glob("*.py"):
        shutil.copyfile(src, dest / src.name)
    for src in (REPO / "web_alarm").glob("*.py"):
        shutil.copyfile(src, dest / "web_alarm" / src.name)
    changed = []
    if variant == "baseline":
        for src in sorted(BASELINE.glob("*.py")):
            shutil.copyfile(src, dest / "web_alarm" / src.name)
            changed.append(src.name)
    else:
        name, old, new = MUTANTS[variant]
        path = dest / "web_alarm" / name
        text = path.read_bytes().decode("utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"refused: {variant} anchor occurs {text.count(old)} times in {name}")
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        changed.append(name)
    print(json.dumps({"variant": variant, "dest": str(dest),
                      "changed": {n: sha(dest / "web_alarm" / n) for n in changed}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
