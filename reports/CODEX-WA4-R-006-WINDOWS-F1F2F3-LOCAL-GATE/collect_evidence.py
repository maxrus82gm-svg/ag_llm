"""Collect only this TASK's finalized disposable outputs, preserving initial RED.

Existing R-003/R-004/R-005 archives are referenced, never copied or rewritten.
RAW JSON records are directly readable without opening the new bulk ZIP.
"""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TASK = HERE.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--temp", type=Path, required=True)
    args = parser.parse_args()
    base = args.temp.resolve()
    assert base.name.startswith("codex-wa4r006-")
    assert not (HERE / "manifest.json").exists(), "Sealed output must not be overwritten"
    assert (base / "full-release/results.json").exists(), "Final full output absent"
    collection = json.loads((base / "collection-release/collection.json").read_bytes())
    results = {}
    zip_path = HERE / "evidence.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for attempt in ("baseline-focused", "adversarial-before", "adversarial-after", "lock-identity-before",
                        "quality", "quality-final", "full-release", "bounded-release"):
            path = base / attempt / "results.json"
            if not path.exists():
                continue
            results[attempt] = json.loads(path.read_bytes())
            for source, member in ((path, f"attempts/{attempt}/results.json"),
                                   (base / attempt / "isolation.jsonl", f"attempts/{attempt}/isolation.jsonl"),
                                   (base / (attempt + ".log"), f"attempts/{attempt}/runner.log"),
                                   (base / (attempt + ".exit"), f"attempts/{attempt}/runner.exit")):
                if source.exists():
                    archive.writestr(member, source.read_bytes())
        for filename in ("full-final.log", "full-final.exit", "full-final-interrupted.json",
                         "focused-final.log", "focused-final-incomplete.json", "probe_lock_identity.py",
                         "first-red-test.py", "R005-readonly-validation.json", "transport-actual.json", "transport-lf.json"):
            source = base / filename
            if source.exists():
                archive.writestr("diagnostics/" + filename, source.read_bytes())
        for name in ("collection.json", "isolation.jsonl"):
            archive.writestr("collection/" + name, (base / "collection-release" / name).read_bytes())
        for name in ("web_alarm/task_store.py", "web_alarm/event_checkpoint_store.py", "web_alarm/operation_store.py"):
            archive.writestr("sources/before/" + name, (base / "before" / name).read_bytes())
            archive.writestr("sources/final/" + name, (ROOT / name).read_bytes())
        archive.writestr("sources/final/test_web_alarm_wa4r006_local_gate.py", (ROOT / "test_web_alarm_wa4r006_local_gate.py").read_bytes())
        archive.writestr("sources/final/quality_controls.py", (HERE / "quality_controls.py").read_bytes())
        archive.writestr("sources/control-inputs.json", (HERE / "control-inputs.json").read_bytes())

    full = results["full-release"]
    assert full["tests_run"] == collection["collected"] == len(set(t["test"] for t in full["tests"]))
    assert set(collection["test_ids"]) == {t["test"] for t in full["tests"]}
    assert full["source_sha256"] == collection["source_sha256"]
    for relative, digest in full["source_sha256"].items():
        assert sha((ROOT / relative).read_bytes()) == digest, "Source changed since final full: " + relative
    focused_modules = {"test_web_alarm_wa4r006_local_gate", "test_web_alarm_wa4r002_diagnostics",
                       "test_web_alarm_reliability_wa017", "test_web_alarm_projection_concurrency",
                       "test_web_alarm_mutation_executor", "test_web_alarm_task_store",
                       "test_web_alarm_operation_store_concurrency", "test_web_alarm_target_claims_concurrency"}
    focused = [t for t in full["tests"] if t["test"].split(".")[0] in focused_modules]
    assert len(focused) == 103
    selected_diagnostics = ("test_F1_", "test_F2_directory_probes", "test_F2_move_between_destination",
                            "test_F2_move_cannot_interleave", "test_F2_release_event_error",
                            "test_F2_preflight_lock", "test_F3_marked_post_move", "test_F3_writer_first")
    records = []
    with zipfile.ZipFile(zip_path) as archive:
        for attempt, result in results.items():
            member = f"attempts/{attempt}/results.json"
            member_bytes = archive.read(member)
            for i, test in enumerate(result["tests"]):
                red = test["status"] in ("FAIL", "ERROR")
                quality = attempt == "quality-final"
                final_case = attempt == "full-release" and (
                    test["test"].startswith("test_web_alarm_wa4r006_local_gate.") or
                    ("RaceEvidenceTests" in test["test"] and any(p in test["test"] for p in selected_diagnostics)) or
                    "CompletionCrashRaceTests" in test["test"])
                if not (red or quality or final_case or attempt == "bounded-release"):
                    continue
                rid = f"R{len(records) + 1:03d}"
                name = "records/" + rid + ".json"
                origin = {"id": rid, "attempt": attempt, "archive": "evidence.zip", "member": member,
                          "member_sha256": sha(member_bytes), "member_bytes": len(member_bytes),
                          "pointer": f"/tests/{i}", "selector": test["test"], "original_status": test["status"],
                          "canonical_record_sha256": sha(canonical(test)), "file": name,
                          "classification": "INTENTIONAL_INNER_RED_OUTER_PASS" if quality else "ORIGINAL_RED" if red else "FINAL_RUNTIME_RECORD"}
                dump(HERE / name, {"origin": origin, "raw": test})
                origin["text_sha256"] = sha((HERE / name).read_bytes())
                origin["text_bytes"] = (HERE / name).stat().st_size
                records.append(origin)
        assert archive.testzip() is None
        inventory = [{"member": item.filename, "bytes": item.file_size,
                      "sha256": sha(archive.read(item.filename))} for item in archive.infolist()]
    (HERE / "raw-index.jsonl").write_bytes(b"".join(canonical(item) + b"\n" for item in records))
    runs = []
    for attempt, result in results.items():
        exit_path = base / (attempt + ".exit")
        runs.append({"attempt": attempt, **{key: result[key] for key in (
            "tests_run", "passed", "failures", "errors", "skips", "elapsed_seconds", "python", "platform", "targets", "isolation_violations")},
            "exit": int(exit_path.read_text(encoding="utf-8-sig").strip()) if exit_path.exists() else "NOT PRESENT IN SOURCE",
            "member": f"attempts/{attempt}/results.json", "member_sha256": next(item["sha256"] for item in inventory if item["member"] == f"attempts/{attempt}/results.json"),
            "source_map_canonical_sha256": sha(canonical(result["source_sha256"])),
            "test_ids": [t["test"] for t in result["tests"]]})
    checks = {"task": TASK, "status": "RESULT READY / AWAITING INDEPENDENT VERIFICATION",
              "runs": runs, "collection": {"collected": collection["collected"], "unique": collection["unique"],
                                            "matches_full_execution": True, "isolation_violations": collection["isolation_violations"]},
              "final_full_source_sha256": full["source_sha256"],
              "focused_within_full": {"tests": len(focused), "passed": sum(t["status"] == "PASS" for t in focused),
                                      "basis": "Subset of full-release, not a separate completed focused run",
                                      "test_ids": [t["test"] for t in focused]},
              "full_skip_reasons": [{"test": t["test"], "reason": t.get("reason")} for t in full["tests"] if t["status"] == "SKIP"],
              "incomplete_attempts": ["full-final: explicitly interrupted before third repair; no final result",
                                      "focused-final: session/process absent, no results/exit marker; attribution unknown"],
              "raw_records": len(records), "raw_equality_checks": 0}
    # Compare every exported parsed RAW object with its original ZIP subtree.
    with zipfile.ZipFile(zip_path) as archive:
        for entry in records:
            raw = (HERE / entry["file"]).read_bytes()
            item = json.loads(raw)
            source = json.loads(archive.read(entry["member"]))["tests"][int(entry["pointer"].split("/")[-1])]
            assert canonical(item["raw"]) == canonical(source)
            assert sha(canonical(source)) == entry["canonical_record_sha256"]
            assert sha(raw) == entry["text_sha256"] and len(raw) == entry["text_bytes"]
            checks["raw_equality_checks"] += 1
    dump(HERE / "checks.json", checks)
    dump(HERE / "provenance.json", {"task": TASK, "archive": {"file": "evidence.zip", "bytes": zip_path.stat().st_size,
                                                               "sha256": sha(zip_path.read_bytes()), "inventory": inventory},
         "raw_index": "raw-index.jsonl", "canonical_json": "UTF-8 / sort_keys=True / compact separators / ensure_ascii=False",
         "historical_original_F3": {"file": "../CODEX-WA4-R-005-EVIDENCE-EXPORT-GITHUB-GATE/records/historical-red/E043.jsonl",
                                    "source_zip_sha256": "020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120",
                                    "classification": "Historical FAIL preserved; handle owner unknown"}})
    dump(HERE / "transport-check.json", {"actual": json.loads((base / "transport-actual.json").read_bytes()),
                                         "simulated_lf": json.loads((base / "transport-lf.json").read_bytes())})
    print(json.dumps({"records": len(records), "full": {k: full[k] for k in ("tests_run", "passed", "failures", "errors", "skips")},
                      "focused_subset": len(focused), "zip_bytes": zip_path.stat().st_size}))


if __name__ == "__main__":
    main()
