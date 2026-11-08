"""Task-local artifact preparation/checking only. No Git or provider access."""
import ast
import hashlib
import json
from pathlib import Path
import re
import tempfile
import sys
import xml.etree.ElementTree as ET

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
E = PACKAGE / "evidence"
TASK = PACKAGE.name
SOURCES = ["ultra_budget_ledger.py", "test_rt002_s3a_ledger.py"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    final = PACKAGE / "final"
    final.mkdir(exist_ok=True)
    rows = []
    for name in SOURCES:
        raw = (ROOT / name).read_bytes()
        ast.parse(raw.decode("utf-8"))
        compile(raw.decode("utf-8"), name, "exec")
        dest = final / (name + ".txt")
        dest.write_bytes(raw)
        rows.append({"path": name, "sha256": sha(raw), "size": len(raw), "snapshot": dest.relative_to(ROOT).as_posix()})
    write(E / "source_final.json", {"files": rows, "Git": "NOT USED; assigned base only", "run_store_changed": False})
    write(E / "syntax.json", {"ast_parse": "PASS", "compile_without_execution_or_pycache": "PASS", "files": SOURCES})
    x = ET.parse(E / "final_s3a.xml").getroot()
    cases = list(x.iter("testcase"))
    assert len(cases) == 35 and not list(x.iter("failure")) and not list(x.iter("error")) and not list(x.iter("skipped"))
    previous = ET.parse(E / "final_tests.xml").getroot()
    runstore = [c for c in previous.iter("testcase") if c.attrib.get("classname", "").startswith("test_run_store_v2")]
    assert len(runstore) == 51 and all(c.find("failure") is None and c.find("error") is None and c.find("skipped") is None for c in runstore)
    s2, s1 = read(E / "s2_result.json"), read(E / "s1_result.json")
    assert s2["gate"]["exit_code"] == 0 and s2["counts"]["run"] == 73
    assert s1["gate"]["exit_code"] == 1 and s1["counts"]["run"] == 69 and s1["counts"]["failures"] == 2
    for mutant in ["ignore_policy_deny", "free_unknown", "ignore_checksum"]:
        assert "1 failed" in (E / ("final_mutant_" + mutant + ".stdout.txt")).read_text(encoding="utf-8")
    controls = json.loads((E / "guard_control.stdout.txt").read_text(encoding="utf-8"))
    assert controls["blocked_before_io"] == ["socket", "dns", "credentials"]
    denied_tests = len((E / "guard_tests.jsonl").read_text().splitlines()) if (E / "guard_tests.jsonl").exists() else 0
    denied_capture = len((E / "guard_capture.jsonl").read_text().splitlines()) if (E / "guard_capture.jsonl").exists() else 0
    assert denied_tests == denied_capture == 0
    write(E / "test_summary.json", {"s3a": {"cases": 35, "pass": 35, "fail": 0, "error": 0, "skip": 0},
          "run_store_regression": {"cases": 51, "pass": 51, "scope": "subset of 85-test combined run before final invalid-root test; Run Store unchanged"},
          "s2": {"cases": 73, "pass": 73, "exit": 0, "guard": len(s2["isolation_violations"])},
          "s1": {"cases": 69, "pass": 67, "fail": 2, "exit": 1, "guard": len(s1["isolation_violations"])},
          "negative_controls": {"cases": 3, "expected_nonzero": 3, "actual_exit": [1, 1, 1]},
          "network_guard": {"expected_denials_control": 3, "unexpected_test_denials": denied_tests, "unexpected_capture_denials": denied_capture},
          "initial_s3a_runs": [{"cases": 29, "pass": 13, "fail": 16, "exit": 1}, {"cases": 29, "pass": 25, "fail": 4, "exit": 1}],
          "product_verdict": "PARTIAL / no S3b enforcement / S1 drift OPEN", "python": s2["python"]})
    private = Path(tempfile.gettempdir()) / (TASK + "_private_original_logs")
    homes = [str(Path.home()), str(Path.home()).replace("\\", "/"), str(Path.home()).replace("\\", "\\\\")]
    mapping = []
    for path in sorted(E.rglob("*")):
        if not path.is_file() or path.suffix not in {".txt", ".json", ".jsonl", ".xml"}:
            continue
        raw = path.read_bytes()
        cleaned = raw.decode("utf-8")
        for home in homes:
            cleaned = cleaned.replace(home, "<USER_HOME>")
        if cleaned.encode("utf-8") != raw:
            private.mkdir(exist_ok=True)
            destination = private / path.relative_to(E).as_posix().replace("/", "__")
            if not destination.exists(): destination.write_bytes(raw)
            path.write_bytes(cleaned.encode("utf-8"))
            mapping.append({"path": path.relative_to(ROOT).as_posix(), "original_sha256": sha(raw), "sanitized_sha256": sha(path.read_bytes()), "change": "home path only", "original_locator": "private TEMP task archive, same relative filename"})
    write(E / "sanitization.json", {"files": mapping, "archive": "private TEMP / TASK-ID_private_original_logs", "secrets_published": False})
    before = (PACKAGE / "before/card.md").read_bytes()
    previous = ROOT / "reports/CODEX-WUA-S5-TURN-UX-RECOVERY-001/handoff_task.md"
    write(E / "closeout_before.json", {"card_sha256": sha(before), "previous_snapshot_sha256": sha(previous.read_bytes())})


def manifest():
    paths = [ROOT / name for name in SOURCES] + [p for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"]
    write(PACKAGE / "manifest.json", {"task_id": TASK, "status": "FINAL AUTHOR PACKAGE / PARTIAL / LOCAL ONLY", "date": "2026-11-08", "hash": "SHA-256 exact bytes", "self_excluded": True,
          "files": [{"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(paths)]})


def verify(post):
    data = read(PACKAGE / "manifest.json")
    for item in data["files"]:
        path = ROOT / item["path"]
        assert path.resolve().is_relative_to(PACKAGE) or path.relative_to(ROOT).as_posix() in SOURCES
        assert not path.is_symlink() and path.stat().st_size == item["size"] and sha(path.read_bytes()) == item["sha256"], item["path"]
    expected = {p.relative_to(ROOT).as_posix() for p in PACKAGE.rglob("*") if p.is_file() and p.name != "manifest.json"} | set(SOURCES)
    assert expected == {row["path"] for row in data["files"]}
    baseline = read(E / "baseline.json")
    for item in baseline["files"]:
        assert sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"]
    source = read(E / "source_final.json")["files"]
    for item in source:
        assert sha((ROOT / item["snapshot"]).read_bytes()) == item["sha256"]
    trace = read(E / "committed/trace.json")
    assert trace["ledger_source_sha256"] == sha((ROOT / "ultra_budget_ledger.py").read_bytes())
    expected_states = ["RESERVED", "SENT", "UNKNOWN_TERMINAL", "RECONCILED", "ANOMALY"]
    liability = []
    for row, state in zip(trace["rows"], expected_states, strict=True):
        raw = (E / "committed" / (row["phase"] + ".json")).read_bytes()
        assert sha(raw) == row["sha256"] and len(row["attempts"]) == 1 and row["attempts"][0]["state"] == state
        liability.append(row["attempts"][0]["liability_tokens"])
    assert liability[0] == liability[1] == liability[2] and liability[3] == 25 and liability[4] >= max(liability[:4])
    assert trace["duplicate_terminal_no_write"] and trace["new_attempt_after_anomaly_denied"]
    assert read(E / "test_summary.json")["s1"]["fail"] == 2
    report = (PACKAGE / "report.md").read_text(encoding="utf-8")
    assert "PARTIAL" in "\n".join(report.splitlines()[:12]) and "MANUAL ENGINEERING REVIEW" in report
    for target in re.findall(r"\]\(([^)]+)\)", report): assert (PACKAGE / target).is_file(), target
    result = {"phase": "post-finish" if post else "pre-finish", "result": "AUTHOR_PACKAGE_CHECK_PASS", "technical_status": "PARTIAL", "manifest_entries": len(data["files"]),
              "new_working_files": 2, "existing_files_unchanged": len(baseline["files"]), "committed_snapshots_verified": 5, "s1_open_failures": 2}
    if post:
        receipt = read(PACKAGE / "finish_protocol.json")
        assert receipt["result"] in {"ROTATED", "ALREADY_ROTATED"}
        assert receipt["steps"][-1]["block1"]["state"] == "WAITING"
        assert receipt["steps"][-1]["block1_1"]["task_id"] == TASK
        record = read(PACKAGE / "task_record.json")
        assert record["sources"]["report"]["sha256"] == sha((PACKAGE / "report.md").read_bytes())
        assert record["sources"]["assignment"]["sha256"] == sha((PACKAGE / "handoff_task.md").read_bytes())
        old = (PACKAGE / "before/card.md").read_bytes()
        new = (ROOT / "Документация/000_Задачи Codex.md").read_bytes()
        begin = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN".encode()
        end = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END".encode()
        assert old.split(begin)[0] == new.split(begin)[0] and old.split(end)[1] == new.split(end)[1]
        previous = ROOT / "reports/CODEX-WUA-S5-TURN-UX-RECOVERY-001/handoff_task.md"
        assert sha(previous.read_bytes()) == read(E / "closeout_before.json")["previous_snapshot_sha256"]
        result.update(history_id=record["history_id"], block1="WAITING", block1_1=TASK, previous_snapshot_and_blocks2_to4_preserved=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "prepare": prepare()
    elif action == "manifest": manifest()
    else: verify(action == "post")
