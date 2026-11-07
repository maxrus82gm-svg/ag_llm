"""Read-only author-package integrity check. Does not run browser/product integration tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
TASK = PACKAGE.name


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pre-finish", "post-finish"], required=True)
    phase = parser.parse_args().phase
    manifest = load(PACKAGE / "manifest.json")
    assert manifest["task_id"] == TASK and "PARTIAL" in manifest["status"]
    seen = set()
    for item in manifest["files"]:
        rel = item["path"]
        path = ROOT / rel
        assert path.resolve().is_relative_to(PACKAGE) and not path.is_symlink()
        assert rel not in seen
        seen.add(rel)
        assert path.is_file() and path.stat().st_size == item["size"]
        assert digest(path) == item["sha256"], rel
    actual = {p.relative_to(ROOT).as_posix() for p in PACKAGE.rglob("*")
              if p.is_file() and p.name != "manifest.json"}
    assert actual == seen, {"unlisted": sorted(actual - seen), "missing": sorted(seen - actual)}
    sources = load(PACKAGE / "evidence/source_state_before_closeout.json")["files"]
    for source in sources:
        assert digest(ROOT / source["path"]) == source["sha256"], source["path"]
        assert digest(ROOT / source["snapshot"]) == source["sha256"], source["snapshot"]
    checks = load(PACKAGE / "evidence/diagnostic_checks.json")
    assert checks["counts"] == {"diagnostic_cases": 4, "passed": 4, "failed": 0}
    assert checks["product_verdict"].startswith("PARTIAL")
    assert load(PACKAGE / "evidence/checks_execution.json")["exit_code"] == 0
    delta = load(PACKAGE / "evidence/prior_ui_change.json")
    assert delta["baseline_exact_bytes_match"] is True and delta["changed_source_lines"] == 4
    assert delta["logic_changed_by_this_delta"] is False
    image = load(PACKAGE / "evidence/user_screenshot_provenance.json")
    assert digest(PACKAGE / "evidence" / image["copy"]) == image["sha256"]
    followups = load(PACKAGE / "followups.json")["items"]
    assert len(followups) == len({item["risk_id"] for item in followups}) == 6
    assert all(item["status"] == "OPEN" and item["successor_task_id"] is None for item in followups)
    report = (PACKAGE / "report.md").read_text(encoding="utf-8")
    assert TASK in report and "PARTIAL" in report and "USER_REPORTED" in report
    assert "не доказывает исчезновение из UI" in report or "а не объяснение исчезновения из UI" in report
    generated = {"closeout.json", "finish_protocol.json", "evidence/package_check_post_finish.json"}
    for target in re.findall(r"\]\(([^)]+)\)", report):
        assert "://" not in target
        file_target = target.split("#", 1)[0]
        path = (PACKAGE / file_target).resolve()
        assert path.is_relative_to(PACKAGE)
        # The caller saves this check's stdout, then rebuilds and rechecks the manifest.
        own_receipt = target == "evidence/package_check_post_finish.json"
        assert path.is_file() or phase == "pre-finish" and target in generated or own_receipt, target
    result = {"phase": phase, "result": "AUTHOR_PACKAGE_CHECK_PASS", "product_verdict": "PARTIAL",
              "manifest_entries_verified": len(seen), "source_files_unchanged": len(sources),
              "open_followups": len(followups), "new_task_created": False,
              "scope": "artifact hashes/links, source preservation, recorded checks and lifecycle readback; not independent product verification"}
    if phase == "post-finish":
        receipt = load(PACKAGE / "finish_protocol.json")
        assert receipt["result"] in {"ROTATED", "ALREADY_ROTATED"}
        assert receipt["task_id"] == TASK
        assert receipt["steps"][-1]["block1"]["state"] == "WAITING"
        assert receipt["steps"][-1]["block1_1"]["task_id"] == TASK
        record = load(PACKAGE / "task_record.json")
        assert record["id"] == TASK and record["review"] == "NOT VERIFIED"
        assert record["sources"]["report"]["sha256"] == digest(PACKAGE / "report.md")
        assert record["sources"]["assignment"]["sha256"] == digest(PACKAGE / "handoff_task.md")
        snapshot = (PACKAGE / "handoff_task.md").read_bytes().replace(b"\r\n", b"\n")
        assigned = (PACKAGE / "evidence/assignment_before_finish.md").read_bytes().replace(b"\r\n", b"\n").strip(b"\n")
        original = snapshot.split(b"<!-- TASK-SNAPSHOT:BEGIN -->", 1)[1].split(b"<!-- TASK-SNAPSHOT:END -->", 1)[0].strip(b"\n")
        assert original == assigned
        for name in ("amendment_01_ui_wording.md", "amendment_02_formal_closeout.md"):
            assert (PACKAGE / name).read_bytes().replace(b"\r\n", b"\n") in snapshot
        before = load(PACKAGE / "evidence/card_before_finish.json")
        card = (ROOT / before["card"]).read_bytes()
        begin = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN".encode()
        end = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END".encode()
        assert hashlib.sha256(card.split(begin, 1)[0]).hexdigest() == before["prefix_before_block1_sha256"]
        assert hashlib.sha256(card.split(end, 1)[1]).hexdigest() == before["suffix_after_block1_1_sha256"]
        previous = before["previous_slot_snapshot"]
        assert digest(ROOT / previous["path"]) == previous["sha256"]
        closeout = load(PACKAGE / "closeout.json")
        assert closeout["history_id"] == record["history_id"]
        assert closeout["block1"] == "WAITING" and closeout["block1_1_task_id"] == TASK
        result.update(history_id=record["history_id"], block1="WAITING", block1_1_task_id=TASK,
                      assignment_and_amendments_preserved=True, previous_snapshot_unchanged=True,
                      card_prefix_and_blocks2_to4_unchanged=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
