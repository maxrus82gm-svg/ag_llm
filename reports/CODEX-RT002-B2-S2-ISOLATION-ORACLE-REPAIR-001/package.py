"""Task-local exact-byte preparation/verification. No production imports or Git."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import platform
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = P / "evidence"
SOURCE = "test_rt002_s2_budget_policy.py"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def value(text, name):
    return ast.literal_eval(next(n.value for n in ast.parse(text).body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)))


def prepare():
    before = (P / "before" / SOURCE).read_text(encoding="utf-8")
    final = (ROOT / SOURCE).read_text(encoding="utf-8")
    (P / "final").mkdir(exist_ok=True)
    (P / "final" / (SOURCE + ".txt")).write_bytes((ROOT / SOURCE).read_bytes())
    (P / "source.diff.patch").write_text("".join(difflib.unified_diff(before.splitlines(keepends=True), final.splitlines(keepends=True),
        fromfile="before/" + SOURCE, tofile=SOURCE)), encoding="utf-8")
    write(E / "source_final.json", {"path": SOURCE, "before_sha256": sha((P / "before" / SOURCE).read_bytes()),
        "after_sha256": sha((ROOT / SOURCE).read_bytes()), "snapshot": "final/" + SOURCE + ".txt",
        "assigned_base": "main@0ee846a1159c690d2bc29eab46fca807e4027541", "Git_GitHub": "NOT USED"})
    checked = []
    for f in [ROOT / SOURCE, *sorted(P.glob("*.py"))]:
        source = f.read_text(encoding="utf-8"); ast.parse(source); compile(source, str(f), "exec")
        checked.append(f.relative_to(ROOT).as_posix())
    write(E / "syntax.json", {"result": "PASS", "python": platform.python_version(), "platform": platform.platform(),
        "method": "AST parse + compile without execution/bytecode", "files": checked})
    result = read(E / "s2.result.json")
    audit = result["observations"]["policy_import_isolation"]
    write(E / "import_graph.json", audit)
    baseline = {row["path"]: row for row in read(E / "baseline.json")["files"]}
    graph_sources = []
    for module in audit["graph"]:
        candidate = ROOT.joinpath(*module.split("."))
        path = candidate.with_suffix(".py") if candidate.with_suffix(".py").is_file() else candidate / "__init__.py"
        relative = path.relative_to(ROOT).as_posix()
        assert relative in baseline and sha(path.read_bytes()) == baseline[relative]["sha256"], relative
        graph_sources.append({"module": module, "path": relative, "sha256": sha(path.read_bytes())})
    write(E / "import_graph_sources.json", {"files": graph_sources, "all_matched_before_baseline": True})
    quality = read(E / "quality.result.json")
    write(E / "negative_matrix.json", [{"case": k, "expected": v["expected"], "actual": v["actual"],
        "inner_tests": v["tests_run"], "issues": v["audit"]["issues"], "policy_paths": v["audit"]["policy_paths"],
        "collected_nested_child": v.get("collected_nested_child", False)} for k, v in sorted(quality["observations"].items())])
    write(E / "test_summary.json", {"task_status": "AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING",
        "original_red": {"run": 73, "pass": 72, "fail": 1, "error": 0, "skip": 0, "exit": 1},
        "s2": {"run": 73, "pass": 73, "fail": 0, "error": 0, "skip": 0, "exit": 0, "guard": 0},
        "s1": {"run": 69, "pass": 69, "exit": 0, "guard": 0}, "s1_extra": {"run": 23, "pass": 23, "exit": 0, "guard": 0},
        "s3a": {"run": 35, "pass": 35, "exit": 0, "guard": 0},
        "quality": {"run": 47, "pass": 47, "expected_inner_RED": 43, "expected_inner_PASS": 4, "exit": 0, "guard": 0},
        "weakening": {"modes": ["disable", "transitive", "capsule_hash"], "exit": [1, 1, 1], "fail": [43, 1, 1], "expected": "RED"},
        "graph": {"local_modules": 82, "conservative_production_roots": 80, "capsules": ["ultra_budget_ledger"], "incoming_ledger": 0},
        "live_provider_calls": 0, "Git_GitHub": "NOT USED"})
    previous = ROOT / "reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/handoff_task.md"
    write(E / "closeout_before.json", {"card_sha256": sha((P / "before/card.md").read_bytes()), "previous_snapshot_sha256": sha(previous.read_bytes())})
    private = Path(tempfile.gettempdir()) / (P.name + "_private_logs")
    marker = E / "sanitization.json"
    mapping = read(marker)["files"] if marker.exists() else []
    home = str(Path.home()); patterns = [home.replace("\\", "\\\\"), home.replace("\\", "/"), home]
    for f in sorted(E.rglob("*")):
        if not f.is_file() or f == marker or f.suffix not in {".json", ".txt", ".jsonl", ".xml"}: continue
        raw = f.read_bytes(); text = raw.decode("utf-8")
        for pattern in patterns: text = text.replace(pattern, "<USER_HOME>")
        cleaned = text.encode("utf-8")
        if cleaned != raw:
            private.mkdir(exist_ok=True)
            name = f.name + "." + sha(raw) + ".raw"
            destination = private / name
            if not destination.exists(): destination.write_bytes(raw)
            assert sha(destination.read_bytes()) == sha(raw)
            f.write_bytes(cleaned)
            mapping.append({"path": f.relative_to(ROOT).as_posix(), "original_sha256": sha(raw), "sanitized_sha256": sha(cleaned),
                "original": "private TEMP / " + P.name + "_private_logs / " + name, "change": "home paths only"})
    write(marker, {"files": mapping, "RAW_prompts_published": False, "credential_values_published": False})


def manifest():
    files = [ROOT / SOURCE] + [f for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"]
    write(P / "manifest.json", {"task_id": P.name, "status": "LOCAL ONLY / AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING",
        "hash": "SHA-256 exact bytes", "self_excluded": True, "files": [{"path": f.relative_to(ROOT).as_posix(),
        "size": f.stat().st_size, "sha256": sha(f.read_bytes())} for f in sorted(files)]})


def check(post):
    data = read(P / "manifest.json")
    expected = {SOURCE} | {f.relative_to(ROOT).as_posix() for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"}
    assert expected == {r["path"] for r in data["files"]}
    for row in data["files"]:
        f = ROOT / row["path"]
        assert f.resolve().is_relative_to(P) or row["path"] == SOURCE
        assert f.stat().st_size == row["size"] and sha(f.read_bytes()) == row["sha256"], row["path"]
    baseline = read(E / "baseline.json")["files"]
    for row in baseline:
        if row["path"] != SOURCE: assert sha((ROOT / row["path"]).read_bytes()) == row["sha256"], row["path"]
    original, final = (P / "before" / SOURCE).read_text(encoding="utf-8"), (ROOT / SOURCE).read_text(encoding="utf-8")
    for name in ["MANIFEST", "ROWS", "DATASET_SHA256", "PRODUCTION_FILES", "ROUTE_SEND_SITES", "ROUTE_MAX_TOKENS"]:
        assert value(original, name) == value(final, name), name
    assert len(value(final, "MANIFEST")) == 73
    assert (P / "final" / (SOURCE + ".txt")).read_bytes() == (ROOT / SOURCE).read_bytes()
    for mode in ["s2", "quality", "weaken_disable", "weaken_transitive", "weaken_capsule_hash"]:
        assert read(E / (mode + ".execution.json"))["s2_source_sha256"] == sha((ROOT / SOURCE).read_bytes()), mode
    red = read(E / "red.result.json")
    assert red["counts"]["run"] == 73 and red["counts"]["failures"] == 1 and red["failures"] == ["__main__.IsolationTests.test_no_production_module_imports_the_policy_yet"]
    for mode, count in [("s2", 73), ("s1", 69)]:
        result = read(E / (mode + ".result.json"))
        assert result["gate"] == {"status": "PASS", "exit_code": 0, "reasons": []} and result["counts"]["run"] == count
        assert not result["isolation_violations"] and not result.get("problems", result.get("evidence_problems")) and result["selected"] is None
    for mode, count in [("quality", 47), ("s1_extra", 23)]:
        result = read(E / (mode + ".result.json"))
        assert result["counts"] == {"run": count, "fail": 0, "error": 0, "skip": 0} and not result["isolation_violations"]
    matrix = read(E / "negative_matrix.json")
    assert len(matrix) == 47 and sum(row["expected"] == "RED" for row in matrix) == 43
    assert all(row["actual"] == row["expected"] and row["inner_tests"] == 1 for row in matrix)
    for mode, failures in [("weaken_disable", 43), ("weaken_transitive", 1), ("weaken_capsule_hash", 1)]:
        result = read(E / (mode + ".result.json"))
        assert result["counts"] == {"run": 47, "fail": failures, "error": 0, "skip": 0} and not result["isolation_violations"]
        assert read(E / (mode + ".execution.json"))["exit_code"] == 1
    for mode in ["s1", "s2", "quality", "s1_extra"]:
        text = (E / (mode + ".stdout.txt")).read_text(encoding="utf-8")
        assert not json.loads(text[text.rfind('{"secret_guard":'):])["secret_guard"]["denials"]
    xml = ET.parse(E / "s3a.xml").getroot()
    assert len(list(xml.iter("testcase"))) == 35 and not any(list(xml.iter(tag)) for tag in ["error", "failure", "skipped"])
    assert not (E / "s3a.guard.jsonl").exists() or not (E / "s3a.guard.jsonl").read_text().strip()
    assert read(E / "controls.result.json")["expected_blocked_before_io"] == ["socket", "dns", "credentials", "credential_file"]
    graph = read(E / "import_graph.json")
    assert not graph["issues"] and not graph["policy_paths"] and graph["offline_capsules"] == ["ultra_budget_ledger"]
    assert len(graph["graph"]) == 82 and not any("ultra_budget_ledger" in edges for edges in graph["graph"].values())
    private = Path(tempfile.gettempdir()) / (P.name + "_private_logs")
    for row in read(E / "sanitization.json")["files"]:
        raw = private / (Path(row["path"]).name + "." + row["original_sha256"] + ".raw")
        assert sha(raw.read_bytes()) == row["original_sha256"]
    report = (P / "report.md").read_text(encoding="utf-8")
    assert "AUTHOR RESULT READY" in "\n".join(report.splitlines()[:12]) and "MANUAL ENGINEERING REVIEW" in report
    for link in re.findall(r"\]\(([^)]+)\)", report): assert (P / link).is_file(), link
    result = {"result": "AUTHOR_PACKAGE_CHECK_PASS", "phase": "post-finish" if post else "pre-finish",
        "task_status": "AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING", "manifest_files": len(data["files"]),
        "source_changes": [SOURCE], "read_only_unchanged": len(baseline) - 1, "s2": "73 PASS", "s1": "69 PASS", "s1_extra": "23 PASS",
        "s3a": "35 PASS", "quality": "47 PASS / 43 expected RED detected", "weakening": "3/3 expected exit1"}
    if post:
        receipt, record = read(P / "finish_protocol.json"), read(P / "task_record.json")
        assert receipt["result"] in {"ROTATED", "ALREADY_ROTATED"} and receipt["steps"][-1]["block1"]["state"] == "WAITING"
        assert receipt["steps"][-1]["block1_1"]["task_id"] == P.name
        assert record["sources"]["report"]["sha256"] == sha((P / "report.md").read_bytes())
        assert record["sources"]["assignment"]["sha256"] == sha((P / "handoff_task.md").read_bytes())
        old, new = (P / "before/card.md").read_bytes(), (ROOT / "Документация/000_Задачи Codex.md").read_bytes()
        begin = "###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN".encode()
        end = "###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END".encode()
        assert old.split(begin)[0] == new.split(begin)[0] and old.split(end)[1] == new.split(end)[1]
        assert sha((ROOT / "reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/handoff_task.md").read_bytes()) == read(E / "closeout_before.json")["previous_snapshot_sha256"]
        result.update(history_id=record["history_id"], block1="WAITING", block1_1="SUBMITTED / REVIEW PENDING", blocks2_to4_and_previous_snapshot="PRESERVED")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1] == "prepare": prepare()
    elif sys.argv[1] == "manifest": manifest()
    else: check(sys.argv[1] == "post")
