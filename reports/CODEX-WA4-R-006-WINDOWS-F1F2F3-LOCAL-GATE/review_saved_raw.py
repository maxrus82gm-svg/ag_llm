"""Additional oracle over saved outputs; never imports production or reruns tests."""
from pathlib import Path
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def find(result, suffix):
    matches = [test for test in result["tests"] if test["test"].endswith("." + suffix)]
    assert len(matches) == 1, (suffix, len(matches))
    return matches[0]


def states(test):
    return {key: value for fact in test["facts"] for key, value in fact.items()
            if isinstance(value, dict) and ("locations" in value or "files_sha256" in value)}


def workers(test):
    return {fact["worker"]: fact for fact in test["facts"] if "worker" in fact}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--temp", type=Path, required=True)
    args = parser.parse_args()
    full = json.loads((args.temp / "full-release/results.json").read_bytes())
    quality = json.loads((args.temp / "quality-final/results.json").read_bytes())
    first = json.loads((args.temp / "adversarial-before/results.json").read_bytes())
    checks = []
    test = find(full, "test_fresh_recovery_can_fail_again_without_success_or_second_apply")
    raw = states(test); actors = workers(test)
    assert raw["first_status_pending"]["locations"] == {"active": False, "completed": True}
    assert raw["first_status_pending"]["task"]["status"] == "PLANNED"
    assert raw["first_status_pending"] == raw["second_status_pending"]
    for name in ("initial_fault", "recovery_fault"):
        actor = actors[name]
        phases = [event["phase"] for event in actor["trace"]]
        assert "status_write_with_native_reader" in phases
        assert actor["pid"] and actor["exit"] == 2
        error = json.loads(actor["stdout"])["error"]
        assert error[-1]["type"] == "PermissionError" and error[-1]["winerror"] in (5, 32)
    terminal = raw["terminal"]
    before = raw["F1_quiescent_PRE_with_receipt_checkpoint_snapshot"]
    for field in ("operations", "checkpoint", "claims", "restore_records", "snapshot_hex", "target_hex"):
        assert terminal[field] == before[field]
    assert bytes.fromhex(terminal["events_hex"]).startswith(bytes.fromhex(before["events_hex"]))
    assert sum(event["event_type"] == "TASK_COMPLETED" for event in terminal["events"]) == 1
    checks.append({"case": "native recovery refuses twice, then fresh completion", "status": "PASS",
                   "worker_pids": {name: actors[name]["pid"] for name in actors},
                   "winerrors": {name: json.loads(actors[name]["stdout"])["error"][-1]["winerror"]
                                 for name in ("initial_fault", "recovery_fault")},
                   "source_selector": test["test"]})

    test = find(full, "test_killed_started_worker_releases_locks_without_blind_repeat")
    raw = states(test); actors = workers(test); killed = actors["killed_writer"]
    phases = [event["phase"] for event in killed["trace"]]
    assert killed["exit"] != 0 and killed["stdout"] == ""
    assert "durable_STARTED" in phases and "before_apply" in phases
    assert "apply_exit" not in phases and "durable_DONE" not in phases
    assert raw["STARTED_before_physical_apply"] == raw["terminal_after_forced_death"]
    assert raw["terminal"]["target_hex"] == "5052450d0a00ff"
    assert raw["terminal"]["operations"]["op_diag"]["status"] == "STARTED"
    assert raw["terminal"]["operations"]["op_diag"]["receipt"] is None
    assert json.loads(actors["fresh_unknown_replay"]["stdout"])["result"] == "RECONCILIATION_REQUIRED"
    checks.append({"case": "forced death on STARTED/before_apply", "status": "PASS", "killed_pid": killed["pid"],
                   "exit": killed["exit"], "physical_target": raw["terminal"]["target_hex"],
                   "physical_effects": "No apply_exit; actual PRE unchanged; recorded apply_enter is not an effect count",
                   "source_selector": test["test"]})

    test = find(full, "test_exception_after_durable_done_replays_without_second_apply")
    raw = states(test); actors = workers(test); done = raw["DONE_without_response"]
    receipt = done["operations"]["op_diag"]["receipt"]
    assert done["operations"]["op_diag"]["status"] == "DONE"
    assert receipt["sha256"] == sha(bytes.fromhex(done["target_hex"]))
    reply = json.loads(actors["fresh_receipt_replay"]["stdout"])
    assert reply["result"] == "REPLAYED" and reply["receipt"] == receipt
    assert not any(event["phase"] == "apply_enter" for event in actors["fresh_receipt_replay"]["trace"])
    assert len(next(fact["parent_applies"] for fact in test["facts"] if "parent_applies" in fact)) == 1
    checks.append({"case": "post-DONE exception / fresh known-receipt replay", "status": "PASS",
                   "parent_pid": "NOT PRESENT IN SOURCE", "replay_pid": actors["fresh_receipt_replay"]["pid"],
                   "source_selector": test["test"]})

    for suffix in ("test_task_identity_mismatch_blocks_gated_and_direct_completion",
                   "test_plan_identity_mismatch_blocks_gated_completion",
                   "test_foreign_microtask_parent_refuses_before_intent_and_apply",
                   "test_microtask_record_id_mismatch_refuses_before_intent_and_apply",
                   "test_unterminated_event_read_and_append_fail_without_modifying_prefix",
                   "test_unterminated_events_block_closeout_and_known_receipt_replay"):
        old = find(first, suffix); new = find(full, suffix)
        assert old["status"] == "FAIL" and new["status"] == "PASS"
        checks.append({"case": "initial RED preserved / final PASS", "before": old["status"],
                       "after": new["status"], "source_selector": new["test"], "status": "PASS"})
    for test in quality["tests"]:
        fact = test["facts"][0]
        assert test["status"] == "PASS"
        assert (fact["inner_tests"], fact["inner_failures"], fact["inner_errors"], fact["inner_skips"]) == (1, 1, 0, 0)
        assert "AssertionError" in fact["failure"]
    checks.append({"case": "quality accounting", "status": "PASS", "outer_pass": len(quality["tests"]),
                   "intentional_inner_failures": len(quality["tests"]), "inner_errors": 0, "inner_skips": 0})
    output = {"task": HERE.name, "status": "PASS", "checks": checks,
              "scope": "Recalculation from saved RAW only; not a second runtime execution or independent acceptance"}
    (HERE / "raw-review.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "checks": len(checks)}))


if __name__ == "__main__":
    main()
