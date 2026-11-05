"""Index immutable test evidence, preserve predecessor receipts, build manifest."""
import hashlib
import json
from pathlib import Path
import re
import sys

package = Path(__file__).resolve().parent
root = package.parent.parent
task = package.name


def stamp(path):
    data = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if sys.argv[1] == "prepare":
    summary = []
    for result_file in sorted((package / "evidence").glob("*.result.json")):
        label = result_file.name.removesuffix(".result.json")
        result = json.loads(result_file.read_text(encoding="utf-8"))
        stdout = (package / "evidence" / (label + ".stdout.txt")).read_text(encoding="utf-8")
        stderr = (package / "evidence" / (label + ".stderr.txt")).read_text(encoding="utf-8")
        rows = re.findall(r"^(test_\S+) \(([^\n]+)\) \.\.\. (ok|ERROR|FAIL|skipped[^\n]*)$", stderr, re.M)
        guard_file = package / "evidence" / (label + ".guard.jsonl")
        denials = [json.loads(line) for line in guard_file.read_text(encoding="utf-8").splitlines()] if guard_file.exists() else []
        summary.append({"label": label, "exit_code": result["exit_code"],
                        "unittest_cases": [{"id": owner, "result": status} for name, owner, status in rows],
                        "pytest_cases": re.findall(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)", stdout, re.M),
                        "guard_denials": denials})
    final = {row["label"]: row for row in summary if row["label"] in
             {"unit_final", "model_regression", "accounting_regression", "stage3_after_guard"}}
    assert len(final) == 4 and all(row["exit_code"] == 0 for row in final.values())
    counts = {key: len(row["unittest_cases"]) + len(row["pytest_cases"]) for key, row in final.items()}
    assert counts == {"unit_final": 39, "model_regression": 38, "accounting_regression": 9, "stage3_after_guard": 30}, counts
    assert [r["boundary"] for r in final["unit_final"]["guard_denials"]] == ["physical_network", "dns", "credentials"]
    assert all(not row["guard_denials"] for key, row in final.items() if key != "unit_final")
    target = package / "evidence/test_summary.json"
    assert not target.exists()
    write(target, {"selected_final_pass": sum(counts.values()), "selected_final_skip": 0,
                   "counts": counts, "runs": summary})
    predecessors = []
    for task_id in ("CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001", "CODEX-WUA-S3-WS-WRITER-BUSY-CI-DIAG-001"):
        predecessors.extend(stamp(path) for path in sorted((root / "reports" / task_id).rglob("*")) if path.is_file())
    assert predecessors
    target = package / "evidence/predecessors.before.json"
    assert not target.exists()
    write(target, predecessors)

if sys.argv[1] == "receipt":
    result = json.loads((package / "evidence/finish.result.json").read_text(encoding="utf-8"))
    protocol = json.loads((package / "evidence/finish.stdout.txt").read_text(encoding="utf-8"))
    record = json.loads((package / "task_record.json").read_text(encoding="utf-8"))
    assert result["exit_code"] == 0
    old = json.loads((package / "evidence/predecessors.before.json").read_text(encoding="utf-8"))
    changed = [item["path"] for item in old if stamp(root / item["path"]) != item]
    assert not changed, changed
    card = root / "Документация/000_Задачи Codex.md"
    before = (package / "before/Документация/000_Задачи Codex.md.source.txt").read_bytes()
    after = card.read_bytes()
    marker = "# БЛОК 2 — ".encode()
    prefix = "# БЛОК 1 — ".encode()
    assert before.split(marker, 1)[1] == after.split(marker, 1)[1]
    assert before.split(prefix, 1)[0] == after.split(prefix, 1)[0]
    assert "**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**" in after.decode("utf-8").split("# БЛОК 1.1", 1)[0]
    assert record["id"] == task and record["status"] == "SUBMITTED / REVIEW PENDING"
    receipt = {"task_id": task, "history_id": record["history_id"], "exit_code": result["exit_code"],
               "protocol": protocol, "predecessor_files_verified": len(old),
               "predecessor_changes": changed, "blocks_2_4_unchanged": True,
               "package_tool_note": "First receipt assembler used an incorrect backup path and failed before writing a receipt. Corrected in this package only; native finish was not repeated. Original error: evidence/receipt_first_error.txt.",
               "card": stamp(card), "task_record": stamp(package / "task_record.json")}
    assert not (package / "finish_receipt.json").exists()
    write(package / "finish_receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("task_id", "history_id", "exit_code", "predecessor_files_verified", "blocks_2_4_unchanged")}))

paths = [root / "ordinary_chat_service.py", root / "test_ordinary_chat_service.py"]
paths.extend(path for path in sorted(package.rglob("*")) if path.is_file() and path.name != "manifest.json")
if (package / "finish_receipt.json").exists():
    paths.extend([root / "Документация/000_Задачи Codex.md", root / "reports/task_history_sequences.json"])
manifest = {"task_id": task, "status": "READY FOR INDEPENDENT VERIFICATION", "hash": "SHA-256 exact bytes",
            "manifest_excludes": ["manifest.json (self)"], "files": [stamp(path) for path in paths],
            "publication_allowlist": ["ordinary_chat_service.py", "test_ordinary_chat_service.py", f"reports/{task}/**",
                                      "Документация/000_Задачи Codex.md (native finish only)",
                                      "reports/task_history_sequences.json (native finish only)"],
            "publication_excludes": [".obsidian/**", ".ultra/**", "Чат_pro/**", "Чат_Pro_01/**", "unrelated local edits"],
            "selected_final_tests": {"pass": 116, "fail": 0, "error": 0, "skip": 0},
            "historical_failures_preserved": ["initial_red", "unit_first", "stage3_regression", "review_usage_red", "receipt_first_error.txt"],
            "independent_review": "PENDING", "stage4_full": "NOT COMPLETE", "live_provider_calls": 0}
write(package / "manifest.json", manifest)
for item in manifest["files"]:
    assert stamp(root / item["path"]) == item
print("Manifest verified:", len(manifest["files"]), "files")
