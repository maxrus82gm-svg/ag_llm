"""Validate exported texts alone, or additionally compare original ZIP sources.

No runtime imports, network, Git, subprocesses, or writes outside disposable
TEMP. --checks writes only this report's checks.json. This is an evidence
validator, not a replay of production tests or an independent acceptance.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(data):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("Duplicate key: " + key)
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def resolve(value, pointer):
    if pointer == "":
        return value
    assert pointer.startswith("/")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def child(pointer, key):
    return pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")


def safe_path(base, name):
    path = (base / name).resolve()
    assert path.is_relative_to(base.resolve()), "Path escapes package"
    return path


def reconstruct(entry, data):
    rows = [load(line) for line in data.splitlines()]
    assert rows and rows[0]["kind"] == "ROOT"
    expected_header = {"kind": "ROOT", **{k: v for k, v in entry.items()
                                           if k not in ("text_bytes", "text_sha256")}}
    assert encode(rows[0]) == encode(expected_header), "Root header mismatch"
    by_pointer = {}
    for row in rows[1:]:
        pointer = row["pointer"]
        assert pointer not in by_pointer, "Duplicate pointer"
        assert pointer == entry["pointer"] or pointer.startswith(entry["pointer"] + "/"), "Foreign pointer"
        by_pointer[pointer] = row
    visited = set()

    def build(pointer):
        row = by_pointer[pointer]
        visited.add(pointer)
        if row["kind"] == "RAW":
            value = row["value"]
            assert digest(encode(value)) == row["canonical_sha256"], "RAW hash mismatch"
            return value
        assert row["kind"] == "STRUCTURE"
        keys = row["keys"]
        assert len(keys) == len(set(keys)), "Duplicate shape key"
        if row["container"] == "array":
            assert keys == list(range(len(keys))), "Missing/reordered array indexes"
            return [build(child(pointer, k)) for k in keys]
        assert row["container"] == "object"
        assert all(isinstance(k, str) for k in keys)
        return {k: build(child(pointer, k)) for k in keys}

    test = build(entry["pointer"])
    assert set(by_pointer) == visited, "Unvisited extra nodes"
    assert digest(encode(test)) == entry["root_canonical_sha256"], "Root canonical mismatch"
    assert test["test"] == entry["selector"] and test["status"] == entry["original_status"]
    return test, len(rows) - 1


def source_archives(provenance, root):
    opened = {}
    for aid, item in provenance["archives"].items():
        if "parent" in item:
            parent = item["parent"]
            data = opened[parent["archive"]].read(parent["member"])
        else:
            data = safe_path(root, item["path"]).read_bytes()
        assert len(data) == item["bytes"] and digest(data) == item["sha256"], "Archive identity mismatch"
        archive = zipfile.ZipFile(io.BytesIO(data))
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert archive.testzip() is None
        assert archive.namelist() == [r["member"] for r in item["inventory"]]
        for member in item["inventory"]:
            raw = archive.read(member["member"])
            assert len(raw) == member["bytes"] and digest(raw) == member["sha256"]
        opened[aid] = archive
    return opened


def validate(package, sources=None):
    provenance = load((package / "provenance.json").read_bytes())
    opened = source_archives(provenance, sources) if sources else None
    source_members = {}
    if opened:
        for key, item in provenance["members"].items():
            raw = opened[item["archive"]].read(item["member"])
            assert digest(raw) == item["member_sha256"] and len(raw) == item["member_bytes"]
            original = load(raw)
            assert encode(item["context"]) == encode({k: v for k, v in original.items() if k != "tests"})
            source_members[key] = original
        for item in provenance["inputs"]:
            raw = safe_path(sources, item["path"]).read_bytes()
            assert digest(raw) == item["sha256"] and len(raw) == item["bytes"], "Source report drift"

    root_ids = set()
    tests = {}
    node_count = 0
    for entry in provenance["roots"]:
        assert entry["id"] not in root_ids
        root_ids.add(entry["id"])
        data = safe_path(package, entry["file"]).read_bytes()
        assert digest(data) == entry["text_sha256"] and len(data) == entry["text_bytes"], "Text byte mismatch"
        test, count = reconstruct(entry, data)
        tests[entry["id"]] = test
        node_count += count
        if opened:
            original = resolve(source_members[entry["archive"] + ":" + entry["member"]], entry["pointer"])
            assert encode(test) == encode(original), "Original source mismatch"

    indexed = []
    for filename in ("f1-raw.jsonl", "f2f3-raw.jsonl", "negative-controls.jsonl", "historical-red.jsonl"):
        entries = [load(line) for line in (package / filename).read_bytes().splitlines()]
        indexed.extend(entries)
    assert len(indexed) == len(root_ids) and len({e["id"] for e in indexed}) == len(indexed)
    assert {e["id"]: e for e in indexed} == {e["id"]: e for e in provenance["roots"]}
    final_f1 = [e for e in indexed if e["role"] == "FINAL_F1"]
    controls = [e for e in indexed if e["role"] == "INTENTIONAL_INNER_RED_OUTER_PASS"]
    assert len(final_f1) == 4
    assert len(controls) == 12
    control_results = []
    for entry in controls:
        test = tests[entry["id"]]
        assert test["status"] == "PASS"
        fact = test["facts"][0]
        if entry["archive"] == "R004":
            assert (fact["inner_tests"], fact["inner_failures"], fact["inner_errors"], fact["inner_skips"]) == (1, 1, 0, 0)
            assert "AssertionError" in fact["failure"]
            result = {"inner_tests": 1, "inner_failures": 1, "inner_errors": 0, "inner_skips": 0,
                      "inner_trace": "/facts/0/failure"}
        else:
            assert fact["intentional_inner_red"].strip()
            result = {"inner_trace": "/facts/0/intentional_inner_red",
                      "inner_counters": "NOT PRESENT IN SOURCE",
                      "inner_raw_facts": "PRESENT" if "raw" in fact else "NOT PRESENT IN SOURCE"}
        control_results.append({"id": entry["id"], "archive": entry["archive"],
                                "outer": test["status"], **result})

    # Independently recompute navigation aids, rather than trust derived indexes.
    observations = load((package / "observations.json").read_bytes())
    for item in observations["records"]:
        test = tests[item["id"]]
        assert item["selector"] == test["test"]
        for state in item["raw_states"]:
            raw = resolve(test, state["pointer"])
            assert raw["locations"] == state["locations"]
            assert raw["task"]["status"] == state["status"]
            assert raw["target_hex"] == state["target_hex"]
            assert digest(bytes.fromhex(raw["target_hex"])) == state["computed_target_sha256"]
            assert state["recorded_target_sha256"] == raw["target_sha256"]
            assert state["target_sha256_matches"] is (state["computed_target_sha256"] == raw["target_sha256"])
            assert state["completion_event_count_from_parsed_records"] == sum(
                e.get("event_type") == "TASK_COMPLETED" for e in raw["events"])
            if "events_hex" in raw:
                event_bytes = bytes.fromhex(raw["events_hex"])
                assert digest(event_bytes) == state["computed_events_bytes_sha256"]
                assert encode([load(line) for line in event_bytes.splitlines() if line.strip()]) == encode(raw["events"])
            else:
                assert state["events_hex"] == "NOT PRESENT IN SOURCE"
        for worker in item["workers"]:
            raw = resolve(test, worker["pointer"])
            for key in ("worker", "pid", "exit", "stderr"):
                assert worker[key] == raw.get(key, "NOT PRESENT IN SOURCE")
        for sequence in item["phase_sequences"]:
            raw = resolve(test, sequence["pointer"])
            assert sequence["phases"] == [e.get("phase", "NOT PRESENT IN SOURCE") for e in raw]
        for pointer in item["apply_markers"]:
            assert resolve(test, pointer)["phase"] == "apply_enter"
        assert item["apply_enter_count_in_recorded_trace"] == len(item["apply_markers"])

    f1 = []
    for entry in final_f1:
        test = tests[entry["id"]]
        facts = test["facts"]
        labelled = {key: value for fact in facts for key, value in fact.items()
                    if isinstance(value, dict) and "locations" in value}
        pre = labelled["F1_quiescent_PRE_with_receipt_checkpoint_snapshot"]
        terminal = labelled["terminal"]
        workers = {fact["worker"]: fact for fact in facts if "worker" in fact}
        applied = sum(event.get("phase") == "apply_enter" for worker in workers.values()
                      for event in worker.get("trace", []))
        op = pre["operations"]["op_diag"]
        assert applied == 1
        assert encode(op) == encode(terminal["operations"]["op_diag"])
        assert op["receipt"]["sha256"] == digest(bytes.fromhex(terminal["target_hex"]))
        assert terminal["target_hex"] == pre["target_hex"]
        for key in ("claims", "snapshot_hex", "restore_records"):
            assert encode(pre[key]) == encode(terminal[key])
        assert all(hexbytes == labelled["PRE"]["target_hex"] for hexbytes in pre["snapshot_hex"].values())
        before = bytes.fromhex(pre["events_hex"])
        after = bytes.fromhex(terminal["events_hex"])
        assert after.startswith(before)
        close = load(workers["close"]["stdout"])
        variant = test["test"].split(".test_F1_")[1]
        if "admission_first" in variant:
            assert close["result"] == "REJECTED"
            assert encode(labelled["admission_committed_before_closeout_refusal"]) == encode(terminal)
            baseline_checkpoint = labelled["admission_committed_before_closeout_refusal"]["checkpoint"]
            fresh = workers["raw_rejected"]
        else:
            baseline_checkpoint = pre["checkpoint"]
            fresh = workers["raw_reopen"]
            assert terminal["locations"] == {"active": False, "completed": True}
            assert terminal["task"]["status"] == "COMPLETED"
        assert encode(baseline_checkpoint) == encode(terminal["checkpoint"])
        assert encode(load(fresh["stdout"])) == encode(terminal)
        if "native_pre" in variant:
            assert encode(pre) == encode(labelled["native_pre_move_refusal"])
            assert workers["close"]["exit"] == 2
            assert close["error"][-1]["winerror"] in (5, 32)
            assert not any(p["phase"] == "directory_moved" for p in workers["close"]["trace"])
        if "native_post" in variant:
            pending = labelled["status_pending_before_recovery"]
            assert pending["locations"] == {"active": False, "completed": True} and pending["task"]["status"] == "PLANNED"
            assert encode(pre["files_sha256"]) == encode(pending["files_sha256"])
            assert workers["close"]["exit"] == 2 and close["error"][-1]["winerror"] in (5, 32)
            assert load(workers["recover"]["stdout"])["resumed"] == "MOVED_STATUS_PENDING"
        for name in ("historical_replay", "pending_replay"):
            if name in workers:
                replay = load(workers[name]["stdout"])
                assert replay["result"] == "REPLAYED" and encode(replay["receipt"]) == encode(op["receipt"])
        f1.append({"id": entry["id"], "selector": entry["selector"],
            "observed_apply_enter": applied, "original_operation_unchanged": True,
            "receipt_matches_actual_target": True, "snapshot_matches_initial_target": True,
            "raw_event_prefix_exact": True, "checkpoint_preserved_from_applicable_barrier": True,
            "terminal_completion_events": sum(e.get("event_type") == "TASK_COMPLETED" for e in terminal["events"]),
            "fresh_process_raw_equals_terminal": True, "fresh_worker_pid": fresh["pid"],
            "native_winerror": close.get("error", [{}])[-1].get("winerror", "NOT PRESENT IN SOURCE"),
            "limit": "Analysis of saved synthetic fixtures only, not a new runtime test or historical closure."})

    parse_files = 0
    for path in package.rglob("*"):
        if path.suffix == ".json":
            load(path.read_bytes()); parse_files += 1
        elif path.suffix == ".jsonl":
            for line in path.read_bytes().splitlines():
                load(line)
            parse_files += 1
    manifest_checked = False
    if (package / "manifest.json").exists():
        manifest = load((package / "manifest.json").read_bytes())
        actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()
                  and p.name != "manifest.json" and "__pycache__" not in p.parts}
        assert actual == set(manifest["files"]), "Manifest coverage mismatch"
        for name, pin in manifest["files"].items():
            raw = safe_path(package, name).read_bytes()
            assert len(raw) == pin["bytes"] and digest(raw) == pin["sha256"], "Package file mismatch: " + name
        manifest_checked = True
    return {"mode": "ORIGINAL_ZIP_EQUALITY" if sources else "TEXT_ONLY_INTERNAL_INTEGRITY",
            "roots": len(tests), "nodes": node_count, "json_jsonl_files_parsed": parse_files,
            "F1_roots": len(final_f1), "controls": control_results,
            "F1_saved_raw_analysis": f1, "derived_observations_checked": len(observations["records"]),
            "original_red": sum(e["role"] == "ORIGINAL_RED_NOT_RECLASSIFIED" for e in indexed),
            "manifest_checked": manifest_checked,
            "replay": "NOT RUN; no runtime/test modules imported"}, provenance


def adversarial(package, provenance, sources):
    entry = copy.deepcopy(provenance["roots"][0])
    data = (package / entry["file"]).read_bytes()
    rows = [load(line) for line in data.splitlines()]
    status_row = next(row for row in rows if row.get("pointer") == entry["pointer"] + "/status")
    status_row["value"] = "FORGED_SUCCESS"
    status_row["canonical_sha256"] = digest(encode(status_row["value"]))
    corrupt = b"".join(encode(r) + b"\n" for r in rows)
    results = []
    with tempfile.TemporaryDirectory(prefix="wa4r005-adversarial-") as temporary:
        path = Path(temporary) / "corrupted.jsonl"
        path.write_bytes(corrupt)
        assert digest(path.read_bytes()) != entry["text_sha256"]
        results.append({"control": "changed raw status / unchanged text pin", "expected": "REJECT", "observed": "REJECT", "status": "PASS"})
        try:
            reconstruct(entry, path.read_bytes())
        except AssertionError as error:
            assert str(error) == "Root canonical mismatch"
            results.append({"control": "changed raw status / recalculated node hash", "expected": "REJECT", "observed": str(error), "status": "PASS"})
        else:
            raise AssertionError("Undetected adversarial raw change")
        missing = [r for r in rows if r is not status_row]
        try:
            reconstruct(entry, b"".join(encode(r) + b"\n" for r in missing))
        except KeyError:
            results.append({"control": "omitted RAW node", "observed": "REJECT missing shape child", "status": "PASS"})
        else:
            raise AssertionError("Undetected missing node")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, help="Original local repository root; no Git used")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--checks", action="store_true", help="Write report-local checks.json")
    args = parser.parse_args()
    if args.checks and (HERE / "manifest.json").exists():
        raise SystemExit("Refusing to overwrite checks.json of a sealed report.")
    result, provenance = validate(HERE, args.sources)
    if args.self_check:
        result["adversarial"] = adversarial(HERE, provenance, args.sources)
    result.update({"status": "PASS", "production_tests": "NOT RUN", "git_used": False})
    if args.checks:
        (HERE / "checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "controls"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
