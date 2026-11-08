"""Document package QA only: provenance, arithmetic, approval boundaries and exact-byte scope."""
import ast
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = P / "evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare():
    syntax = []
    for file in sorted(P.glob("*.py")):
        text = file.read_text(encoding="utf-8"); ast.parse(text); compile(text, str(file), "exec")
        syntax.append({"path": file.relative_to(ROOT).as_posix(), "sha256": sha(file.read_bytes())})
    write(E / "syntax.json", {"result": "PASS", "method": "own documentation helpers AST + compile; no code/test imports or bytecode", "files": syntax})
    before = (P / "before/card.md").read_bytes()
    previous = ROOT / "reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/handoff_task.md"
    write(E / "closeout_before.json", {"card_sha256": sha(before), "previous_snapshot_sha256": sha(previous.read_bytes()),
        "chat_amendments": [{"path": "chat_amendment_01.md", "sha256": sha((P / "chat_amendment_01.md").read_bytes())}]})


def manifest():
    files = [f for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"]
    write(P / "manifest.json", {"task_id": P.name, "status": "RESULT READY / DECISION PACKET / NOT ACTIVE / WEB26 REVIEW PENDING",
        "hash": "SHA-256 exact bytes", "self_excluded": True, "runtime_source_changes": [], "files": [
            {"path": f.relative_to(ROOT).as_posix(), "size": f.stat().st_size, "sha256": sha(f.read_bytes())} for f in sorted(files)]})


def check(post):
    manifest = read(P / "manifest.json")
    expected = {f.relative_to(ROOT).as_posix() for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"}
    assert expected == {row["path"] for row in manifest["files"]}
    for row in manifest["files"]:
        file = ROOT / row["path"]
        assert file.resolve().is_relative_to(P) and not file.is_symlink()
        assert file.stat().st_size == row["size"] and sha(file.read_bytes()) == row["sha256"], row["path"]
    baseline = read(E / "baseline.json")["files"]
    for row in baseline:
        file = ROOT / row["path"]
        assert sha(file.read_bytes()) == row["sha256"], row["path"]
    registry = read(E / "source_registry.json")["sources"]
    assert len(registry) == 27
    for source in registry:
        file = ROOT / source["path"]
        assert sha(file.read_bytes()) == source["sha256"]
        lines = file.read_text(encoding="utf-8").splitlines()
        assert all(loc["line"] and loc["needle"] in lines[loc["line"]-1] for loc in source["locators"])
    assert read(E / "source_preflight.json")["result"] == "MATCH"
    facts, proposal, followups = [read(file) for file in [E / "calibration_facts.json", P / "policy_candidates.json", P / "followups.json"]]
    assert facts["rows"] == 342 and facts["known_prompt_rows"] == 340 and facts["ordinary_chat_rows"] == 0
    assert facts["dataset_sha256"] == "8a3ea10b75280ece550138af9a912b161997e17f5f3f17c894686961babf90ce"
    assert sum(group["samples"] for group in facts["groups"]) == 340
    assert not proposal["active"] and not proposal["user_approved"] and proposal["accepted_by_current_policy_schema"] is False
    assert proposal["route_proposed"] == proposal["role_proposed"] == "ordinary_chat" and proposal["scope_proposed"] == "ORDINARY_CHAT_SESSION"
    assert proposal["calibration_proposed"]["bytes_per_token"] is None and proposal["calibration_proposed"]["missing_profile"] == "DENY"
    approved = proposal["approved_design_constraints"]
    assert len(approved) == 1 and approved[0]["id"] == "CHAT-A01" and not approved[0]["implementation_authorized"]
    assert followups["user_approval_events"][0]["absolute_numeric_candidate_approved"] is False
    assert not followups["new_tasks_assigned"] and not followups["runtime_changes_authorized"]
    amendment = (P / "chat_amendment_01.md").read_text(encoding="utf-8")
    assert "Я не против" in amendment and "не выбрал A/B/C" in amendment
    expected_limits = {"A": (65536, 16000, 1024, 80000, 12), "B": (131072, 32000, 2048, 120000, 16), "C": (262144, 64000, 4096, 240000, 24)}
    for label, numbers in expected_limits.items():
        candidate = proposal["candidates"][label]; limits = candidate["limits_proposed"]; illustration = candidate["illustrations_only"]
        assert tuple(limits[key] for key in ["max_request_bytes", "max_request_input_tokens_est", "max_output_tokens", "max_session_liability_tokens", "max_session_attempts"]) == numbers
        legacy = facts["legacy_candidates_NOT_DEFAULTS"][label]
        assert numbers[0] == legacy["max_request_bytes"]//4 and numbers[3] == legacy["max_run_liability_tokens"]//2 and numbers[4] == legacy["max_run_attempts"]//2
        assert limits["max_workspace_ordinary_liability_tokens"] == numbers[3] and limits["max_workspace_ordinary_attempts"] == numbers[4]
        reserve = numbers[1] + numbers[2]
        assert illustration["reserve_at_full_input_and_output"] == reserve
        assert illustration["worst_full_UNKNOWNs_fitting_session_liability"] == numbers[3]//reserve
        assert illustration["typical_events_at_attempt_cap"] == 3*numbers[4] and illustration["sum_raw_wire_bytes_at_attempt_cap"] == numbers[0]*numbers[4]
        for row in illustration["divisor_scenarios"]:
            ratio = Fraction.from_float(row["illustrative_divisor_NOT_PROFILE"])
            estimate = (numbers[0]*ratio.denominator + ratio.numerator - 1)//ratio.numerator
            assert row["input_estimate_at_bytes_cap"] == estimate
    packet = (P / "policy_decision_packet.md").read_text(encoding="utf-8")
    assert [int(n) for n in re.findall(r"^## (\d+)\.", packet, re.M)] == list(range(1,10))
    assert "31910" in packet and "75559 / 78211" in packet and "4096" in packet and "64 MiB" in packet
    assert "CHAT-A01" in packet and "0 Ordinary Chat samples" in (P / "report.md").read_text(encoding="utf-8")
    assert "A/B/C и абсолютные числа не утверждены" in packet
    for question in ["U1", "U2", "U3", "U4", "U5", "U6"]:
        assert re.search(r"\| " + question + r" \|.*PENDING", packet)
    for file in P.glob("*.md"):
        text = file.read_text(encoding="utf-8")
        assert text.count("```") % 2 == 0, file.name
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://")): continue
            target = target.strip("<>").split("#",1)[0]
            assert not target or (file.parent / target).is_file(), (file.name, target)
    report = (P / "report.md").read_text(encoding="utf-8")
    assert "RESULT READY" in "\n".join(report.splitlines()[:12]) and "MANUAL ENGINEERING REVIEW" in report and "NOT RUN" in report
    result = {"result": "DOCUMENT_PACKAGE_CHECK_PASS", "phase": "post-finish" if post else "pre-finish", "task_status": "RESULT READY / DECISION PACKET / WEB26 REVIEW PENDING",
        "manifest_files": len(manifest["files"]), "sources_verified": len(registry), "read_only_files_unchanged": len(baseline),
        "runtime_tests_run": 0, "active_policy": False, "numeric_choice_approved": False, "approved_design_constraint": "CHAT-A01 Workspace envelope equality", "candidates": ["A", "B", "C"]}
    if post:
        receipt, record = read(P / "finish_protocol.json"), read(P / "task_record.json")
        assert receipt["result"] in {"ROTATED", "ALREADY_ROTATED"} and receipt["steps"][-1]["block1"]["state"] == "WAITING"
        assert receipt["steps"][-1]["block1_1"]["task_id"] == P.name
        assert record["sources"]["report"]["sha256"] == sha((P / "report.md").read_bytes())
        assert record["sources"]["assignment"]["sha256"] == sha((P / "handoff_task.md").read_bytes())
        assert "Я не против" in (P / "handoff_task.md").read_text(encoding="utf-8")
        old, new = (P / "before/card.md").read_bytes(), (ROOT / "Документация/000_Задачи Codex.md").read_bytes()
        begin = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN".encode()
        end = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END".encode()
        assert old.split(begin)[0] == new.split(begin)[0] and old.split(end)[1] == new.split(end)[1]
        assert sha((ROOT / "reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/handoff_task.md").read_bytes()) == read(E / "closeout_before.json")["previous_snapshot_sha256"]
        result.update(history_id=record["history_id"], block1="WAITING", block1_1="SUBMITTED / REVIEW PENDING", blocks2_to4_and_H25_snapshot="PRESERVED", chat_amendment="PRESERVED")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1] == "prepare": prepare()
    elif sys.argv[1] == "manifest": manifest()
    else: check(sys.argv[1] == "post")
