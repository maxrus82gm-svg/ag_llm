"""Local compile, conservation, test evidence and manifest checks."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

package = Path(__file__).resolve().parent
root = package.parent.parent
evidence = package / "evidence"
card = "Документация/000_Задачи Codex.md"
sources = ("web_alarm/turn_service.py", "web_alarm/ordinary_chat_test_adapter.py",
           "test_web_alarm_ultra_chat_turn_s4b.py")


def stamp(path):
    data = path.read_bytes()
    return [len(data), hashlib.sha256(data).hexdigest()]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def conservation(after_finish):
    baseline = read(evidence / "baseline.json")
    changed = [name for name, old in baseline["sources"].items() if stamp(root / name) != old]
    allowed = [sources[0]] + ([card] if after_finish else [])
    assert changed == allowed, changed
    current = {}
    for folder in (".ultra", "Чат_pro", "Чат_Pro_01", ".obsidian"):
        for directory, dirs, files in os.walk(root / folder, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(directory) / d).is_junction()
                       and not (Path(directory) / d).is_symlink()]
            for name in files:
                path = Path(directory) / name
                if not path.is_symlink():
                    current[path.relative_to(root).as_posix()] = stamp(path)
    previous = baseline["protected"]
    differences = sorted(name for name in previous.keys() | current.keys()
                         if previous.get(name) != current.get(name))
    assert all(name.startswith(".obsidian/") for name in differences), differences
    assert read(root / "web_alarm/launch_config.json")["active"] == "standard"
    if after_finish:
        old_card = (package / "before" / (card + ".source.txt")).read_bytes()
        new_card = (root / card).read_bytes()
        marker = "# БЛОК 2 — ".encode()
        assert old_card.split(marker, 1)[1] == new_card.split(marker, 1)[1]
    return dict(changed_baseline_sources=changed, launcher="standard",
                user_files_verified=sum(not name.startswith(".obsidian/") for name in previous),
                editor_deltas_preserved=differences, blocks_2_4_unchanged=after_finish)


def test_summary():
    labels = ("integration_final", "s4a_final", "stage3_final", "storage_final", "runstore_final")
    runs = {}
    for label in labels:
        result = read(evidence / (label + ".result.json"))
        assert result["exit_code"] == 0, label
        for name in sources:
            assert result["source_sha256"][str(Path(name))] == stamp(root / name)[1], (label, name)
        stdout = (evidence / (label + ".stdout.txt")).read_text(encoding="utf-8")
        stderr = (evidence / (label + ".stderr.txt")).read_text(encoding="utf-8")
        unittest_cases = re.findall(
            r"^test_\S+ \(([^\n]+)\) \.\.\. (?:Executing [^\n]*\n)*(ok|skipped[^\n]*)$", stderr, re.M
        )
        pytest_cases = re.findall(r"^(\S+::\S+)\s+(PASSED|SKIPPED)", stdout, re.M)
        cases = unittest_cases or pytest_cases
        total = re.search(r"^Ran (\d+) tests?", stderr, re.M) or re.search(r"^collecting \.\.\. collected (\d+) items?", stdout, re.M)
        assert total and len(cases) == int(total[1]), (label, len(cases))
        skips = sum(status.lower().startswith("skip") for _, status in cases)
        guard_file = evidence / (label + ".guard.jsonl")
        denials = [json.loads(line)["boundary"] for line in guard_file.read_text(encoding="utf-8").splitlines()] if guard_file.exists() else []
        expected = ["physical_network", "dns", "credentials"] if label in ("integration_final", "s4a_final") else []
        assert denials == expected, (label, denials)
        runs[label] = dict(pass_count=len(cases)-skips, skip=skips, fail=0, error=0, cases=cases,
                           expected_guard_controls=denials, elapsed_seconds=result["elapsed_seconds"])
    return runs


mode = sys.argv[1]
if mode == "compile":
    for name in sources:
        compile((root / name).read_bytes(), name, "exec")
    print(json.dumps({name: stamp(root / name) for name in sources}, indent=2))
elif mode == "before":
    save(evidence / "conservation_before_finish.json", conservation(False))
    runs = test_summary()
    save(evidence / "test_summary.json", runs)
    for name, value in runs.items():
        print(name, value["pass_count"], "PASS", value["skip"], "SKIP")
elif mode == "after":
    result = read(evidence / "finish.result.json")
    protocol = read(evidence / "finish.stdout.txt")
    record = read(package / "task_record.json")
    assert result["exit_code"] == 0 and protocol["result"] == "ROTATED"
    assert record["id"] == package.name and protocol["history"]["history_id"] == record["history_id"]
    for source in record["sources"].values():
        assert stamp(root / source["path"])[1] == source["sha256"]
    proof = conservation(True)
    save(package / "finish_receipt.json", {**proof, "history_id": record["history_id"],
                                          "native_result": protocol["result"], "exit_code": result["exit_code"],
                                          "card_sha256": stamp(root / card)[1]})
    print(record["history_id"], protocol["result"], proof)
elif mode == "manifest":
    paths = [root / name for name in sources]
    paths.extend(path for path in sorted(package.rglob("*")) if path.is_file() and path.name != "manifest.json")
    if (package / "finish_receipt.json").exists():
        paths.extend([root / card, root / "reports/task_history_sequences.json"])
    files = [{"path": p.relative_to(root).as_posix(), "size": size, "sha256": sha}
             for p in paths for size, sha in [stamp(p)]]
    manifest = dict(task_id=package.name, status="READY FOR INDEPENDENT VERIFICATION",
                    hash="SHA-256 exact bytes", files=files,
                    publication_allowlist=[*sources, f"reports/{package.name}/**", card,
                                           "reports/task_history_sequences.json (native finish only)"],
                    publication_excludes=[".obsidian/**", ".ultra/**", "Чат_pro/**", "Чат_Pro_01/**",
                                          "unrelated local changes"],
                    independent_review="PENDING", external_provider_calls=0)
    save(package / "manifest.json", manifest)
    assert all(stamp(root / row["path"]) == [row["size"], row["sha256"]] for row in files)
    print("Manifest verified", len(files))
else:
    raise ValueError(mode)
