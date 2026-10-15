"""Offline, read-only source export. No project imports or subprocesses.

Only writes this report directory. All RAW nodes are exact JSON subtrees;
large containers have explicit shape nodes and ordered JSON pointers.
"""
from pathlib import Path
import hashlib
import io
import json
import platform
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASK = HERE.name
MISSING = "NOT PRESENT IN SOURCE"
LIMIT = 10000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_json(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False) + "\n", encoding="utf-8")


def pointer_child(pointer, key):
    return pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")


def nodes(value, pointer):
    if len(canonical(value)) <= LIMIT or not isinstance(value, (dict, list)):
        yield {"kind": "RAW", "pointer": pointer,
               "canonical_sha256": sha(canonical(value)), "value": value}
        return
    keys = list(value) if isinstance(value, dict) else list(range(len(value)))
    yield {"kind": "STRUCTURE", "pointer": pointer,
           "container": "object" if isinstance(value, dict) else "array", "keys": keys}
    for key in keys:
        yield from nodes(value[key], pointer_child(pointer, key))


def walk(value, pointer=""):
    yield pointer, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, pointer_child(pointer, key))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from walk(child, pointer_child(pointer, key))


def inspect_test(test):
    """Derived indexes only: every observation carries its source pointer."""
    observations = {"raw_states": [], "workers": [], "phase_sequences": [],
                    "apply_markers": [], "missing": []}
    for ptr, value in walk(test):
        if not isinstance(value, dict):
            continue
        if "locations" in value and "target_hex" in value:
            target = bytes.fromhex(value["target_hex"])
            events = value.get("events", [])
            event_hex = value.get("events_hex", MISSING)
            observations["raw_states"].append({
                "pointer": ptr, "locations": value["locations"],
                "status": value.get("task", {}).get("status", MISSING),
                "target_hex": value["target_hex"], "computed_target_sha256": sha(target),
                "recorded_target_sha256": value.get("target_sha256", MISSING),
                "target_sha256_matches": sha(target) == value.get("target_sha256"),
                "completion_event_count_from_parsed_records": sum(
                    e.get("event_type") == "TASK_COMPLETED" for e in events),
                "events_hex": "PRESENT" if event_hex != MISSING else MISSING,
                "computed_events_bytes_sha256": sha(bytes.fromhex(event_hex)) if event_hex != MISSING else MISSING,
                "operations": list(value.get("operations", {})),
                "checkpoint": "PRESENT" if "checkpoint" in value else MISSING,
                "snapshot_hex": "PRESENT" if "snapshot_hex" in value else MISSING,
                "restore_records": "PRESENT" if "restore_records" in value else MISSING,
                "claims": "PRESENT" if "claims" in value else MISSING,
                "task_json_original_bytes": MISSING,
            })
        if "worker" in value:
            observations["workers"].append({"pointer": ptr, "worker": value["worker"],
                **{k: value.get(k, MISSING) for k in ("pid", "exit", "stderr")},
                "stdout_pointer": pointer_child(ptr, "stdout") if "stdout" in value else MISSING})
            trace = value.get("trace")
            if isinstance(trace, list):
                observations["phase_sequences"].append({"pointer": pointer_child(ptr, "trace"),
                    "worker": value["worker"], "phases": [r.get("phase", MISSING) for r in trace]})
        if value.get("phase") == "apply_enter":
            observations["apply_markers"].append(ptr)
    observations["apply_enter_count_in_recorded_trace"] = len(observations["apply_markers"])
    observations["apply_count_limit"] = "Recorded instrumentation only; absence is not proof against uninstrumented effects."
    observations["missing"] = ["Global wall-clock ordering across workers: " + MISSING,
        "Historical handle owner: " + MISSING,
        "Raw TASK JSON bytes (parsed objects and file hashes are preserved where present): " + MISSING]
    return observations


def main():
    if (HERE / "manifest.json").exists():
        raise SystemExit("Sealed report exists; use a separately authorized new revision, not overwrite.")
    archives = {}
    inputs = []
    for aid, task in [("R003", "CODEX-WA4-R-003-F2F3-LOCAL-REPAIR"),
                      ("R004", "CODEX-WA4-R-004-F1-CLOSEOUT-GATE")]:
        directory = ROOT / "reports" / task
        for name in ("manifest.json", "checks.json", "versions.json", "report.md", "quality_controls.py"):
            path = directory / name
            if path.exists():
                inputs.append({"path": path.relative_to(ROOT).as_posix(),
                               "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())})
        manifest = strict((directory / "manifest.json").read_bytes())
        path = directory / "evidence.zip"
        data = path.read_bytes()
        entries = manifest.get("files", manifest.get("artifacts"))
        expected = next(v for k, v in entries.items() if k.endswith("evidence.zip"))
        assert sha(data) == expected["sha256"]
        assert len(data) == expected["bytes"]
        archive = zipfile.ZipFile(io.BytesIO(data))
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert archive.testzip() is None
        archives[aid] = {"zip": archive, "data": data, "path": path.relative_to(ROOT).as_posix(),
                         "manifest": manifest}
    historical_member = "historical/original-wa4r002-independent-38379575748-1.zip"
    data = archives["R004"]["zip"].read(historical_member)
    assert sha(data) == "020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120"
    archives["HIST-F3"] = {"zip": zipfile.ZipFile(io.BytesIO(data)), "data": data,
        "parent": {"archive": "R004", "member": historical_member},
        "path": MISSING, "manifest": {"source_sha256": {}}}

    provenance = {"task": TASK, "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
        "publication": "LOCAL ONLY / NOT SYNCED", "schema": 1,
        "canonical_json": "UTF-8; ensure_ascii=False; sort_keys=True; separators=(',', ':'); allow_nan=False",
        "meaning": "RAW is exact parsed JSON, not claimed to be original member byte serialization. Original member byte hashes are separate.",
        "supplied_baseline": {"commit": "38e7164b1ab3af6131d65cfc9dc8760ee426dd1e", "user_number": 336,
            "subsequent_docs_only": 337, "authority": "Approved Block 1 / coordinator handoff; no Git verification"},
        "historical_supplied_source": {"commit": "37123b176097c15c8d21e0040bdf7d7f3e8072a3",
            "run": "38379575748", "artifact": "wa4r002-independent-38379575748-1",
            "authority": "Coordinator handoff; archive source_sha256 file pins are independently available"},
        "export_environment": {"python": sys.version, "platform": platform.platform(), "git_used": False},
        "inputs": inputs, "archives": {}, "members": {}, "roots": [], "source_pins": {},
        "missing_historical_archives": {"F1 original CI artifact": MISSING, "F2 original 80-round artifact": MISSING}}
    for aid, archive in archives.items():
        provenance["archives"][aid] = {k: v for k, v in archive.items() if k in ("path", "parent")}
        provenance["archives"][aid].update({"sha256": sha(archive["data"]), "bytes": len(archive["data"]),
            "crc_check": "PASS", "manifest_match": True if aid != "HIST-F3" else "Pinned embedded original SHA"})
        provenance["archives"][aid]["inventory"] = [{"member": i.filename, "bytes": i.file_size,
            "sha256": sha(archive["zip"].read(i.filename))} for i in archive["zip"].infolist()]
        pins = archive["manifest"].get("source_sha256", {})
        provenance["source_pins"][aid] = {}
        for path, expected in pins.items():
            actual_path = ROOT / path
            current = sha(actual_path.read_bytes()) if actual_path.is_file() else MISSING
            provenance["source_pins"][aid][path] = {"recorded": expected, "local_current": current,
                                                   "byte_equal": expected == current}

    selections = []
    def select(aid, member, index, group, role):
        key = (aid, member, index)
        if key not in [(s[0], s[1], s[2]) for s in selections]:
            selections.append((aid, member, index, group, role))

    for aid, member in [("R004", "attempts/focused-final/results.json"),
                        ("R003", "focused-final-2/results.json")]:
        result = strict(archives[aid]["zip"].read(member))
        for i, test in enumerate(result["tests"]):
            name = test["test"]
            if aid == "R004" and ".test_F1_" in name:
                select(aid, member, i, "f1", "FINAL_F1")
            if aid == "R003" and (("RaceEvidenceTests.test_F2_" in name or "RaceEvidenceTests.test_F3_" in name)
                                  or "CompletionCrashRaceTests" in name or "test_execution_racing_the_task_closure" in name):
                select(aid, member, i, "f2f3", "FINAL_F2F3")
    for aid, member in [("R003", "quality-final/results.json"),
                        ("R004", "attempts/quality-byte-prefix/results.json")]:
        result = strict(archives[aid]["zip"].read(member))
        assert len(result["tests"]) == 6
        for i in range(6):
            select(aid, member, i, "negative-controls", "INTENTIONAL_INNER_RED_OUTER_PASS")
    for aid in ("R003", "R004", "HIST-F3"):
        for member in archives[aid]["zip"].namelist():
            if not member.endswith("results.json"):
                continue
            result = strict(archives[aid]["zip"].read(member))
            for i, test in enumerate(result["tests"]):
                if test["status"] not in ("PASS", "SKIP"):
                    select(aid, member, i, "historical-red", "ORIGINAL_RED_NOT_RECLASSIFIED")

    indexes = {group: [] for group in ("f1", "f2f3", "negative-controls", "historical-red")}
    observations = []
    for sequence, (aid, member, index, group, role) in enumerate(selections, 1):
        archive = archives[aid]["zip"]
        raw_member = archive.read(member)
        result = strict(raw_member)
        test = result["tests"][index]
        member_id = aid + ":" + member
        if member_id not in provenance["members"]:
            provenance["members"][member_id] = {"archive": aid, "member": member,
                "member_bytes": len(raw_member), "member_sha256": sha(raw_member),
                "context": {k: v for k, v in result.items() if k != "tests"}}
        rid = f"E{sequence:03d}"
        path = "records/" + group + "/" + rid + ".jsonl"
        entry = {"id": rid, "archive": aid, "member": member, "pointer": f"/tests/{index}",
            "selector": test["test"], "attempt": member.removesuffix("/results.json"),
            "original_status": test["status"], "role": role, "file": path,
            "root_canonical_sha256": sha(canonical(test)),
            "note": "Original assertion outcome; no new runtime execution or independent acceptance."}
        output = HERE / path
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical({"kind": "ROOT", **entry}).decode() + "\n")
            for node in nodes(test, entry["pointer"]):
                stream.write(canonical(node).decode() + "\n")
        entry["text_sha256"] = sha(output.read_bytes())
        entry["text_bytes"] = output.stat().st_size
        provenance["roots"].append(entry)
        indexes[group].append(entry)
        if group in ("f1", "f2f3") or "RAW_reader" in test["test"] or aid == "HIST-F3":
            observations.append({"id": rid, "selector": test["test"], **inspect_test(test)})

    for group, entries in indexes.items():
        filename = group + ("-raw" if group in ("f1", "f2f3") else "") + ".jsonl"
        (HERE / filename).write_bytes(b"".join(canonical(entry) + b"\n" for entry in entries))
    write_json("provenance.json", provenance)
    write_json("observations.json", {"task": TASK, "meaning": "DERIVED ONLY, never substitutes RAW; pointers relative to selected original test root.",
                                     "records": observations})
    print(json.dumps({"roots": len(provenance["roots"]), "groups": {k: len(v) for k, v in indexes.items()},
                      "record_bytes": sum(r["text_bytes"] for r in provenance["roots"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
