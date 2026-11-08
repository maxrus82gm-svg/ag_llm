"""Exact-byte package verification. No Git, network or production imports."""
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
SOURCE = "test_rt002_s1_routes.py"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assignment(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.literal_eval(node.value)


def ast_hash(node): return sha(ast.dump(node, include_attributes=False).encode("utf-8"))


def prepare():
    original = (P / "before" / SOURCE).read_text(encoding="utf-8")
    current = (ROOT / SOURCE).read_text(encoding="utf-8")
    (P / "final").mkdir(exist_ok=True)
    (P / "final" / (SOURCE + ".txt")).write_bytes((ROOT / SOURCE).read_bytes())
    write(E / "source_final.json", {"path": SOURCE, "before_sha256": sha((P / "before" / SOURCE).read_bytes()),
        "after_sha256": sha((ROOT / SOURCE).read_bytes()), "snapshot": "final/" + SOURCE + ".txt",
        "assigned_base": "main@87edc6c1537722981b5016fa2c33b8bc59cc580c", "Git_GitHub": "NOT USED"})
    (P / "source.diff.patch").write_text("".join(difflib.unified_diff(original.splitlines(keepends=True),
        current.splitlines(keepends=True), fromfile="before/" + SOURCE, tofile=SOURCE)), encoding="utf-8")
    syntax = []
    for f in [ROOT / SOURCE, *sorted(P.glob("*.py"))]:
        text = f.read_text(encoding="utf-8"); ast.parse(text); compile(text, str(f), "exec")
        syntax.append(f.relative_to(ROOT).as_posix())
    write(E / "syntax.json", {"result": "PASS", "python": platform.python_version(), "no_execution_or_bytecode": True, "files": syntax})


def literal_pins(text):
    values = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"R031_DIR", "R026_DIR"}:
                values[name] = ast.literal_eval(node.value)
            elif name == "EVIDENCE_PINS":
                class Replace(ast.NodeTransformer):
                    def visit_Name(self, item): return ast.copy_location(ast.Constant(values[item.id]), item)
                    def visit_BinOp(self, item):
                        item = self.generic_visit(item)
                        assert isinstance(item.op, ast.Add)
                        return ast.copy_location(ast.Constant(ast.literal_eval(item.left) + ast.literal_eval(item.right)), item)
                return ast.literal_eval(Replace().visit(node.value))


def prepare_evidence():
    text = (ROOT / SOURCE).read_text(encoding="utf-8")
    rows = []
    for label, (locator, expected, size) in literal_pins(text).items():
        raw = (ROOT / locator).read_bytes()
        assert sha(raw) == expected and len(raw) == size
        rows.append({"label": label, "source": locator, "expected_sha256": expected, "actual_sha256": sha(raw), "bytes": len(raw)})
    write(E / "pinned_fixtures.json", {"result": "PASS", "files": rows, "RAW_copied_to_package": False})
    pin_rows = []
    for module, pins in assignment(text, "RECON_PINS").items():
        path = ROOT / module if (ROOT / module).is_file() else ROOT / "web_alarm" / module
        tree = ast.parse(path.read_text(encoding="utf-8")); nodes = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes[node.name] = node
                if isinstance(node, ast.ClassDef):
                    nodes.update({node.name + "." + child.name: child for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))})
            elif isinstance(node, ast.Assign):
                nodes.update({target.id: node for target in node.targets if isinstance(target, ast.Name)})
        for symbol, digest in pins.items():
            node = nodes[symbol]
            assert ast_hash(node) == digest, (module, symbol)
            pin_rows.append({"module": path.relative_to(ROOT).as_posix(), "symbol": symbol, "line": node.lineno,
                "ast_sha256": digest, "reviewed_source": ast.unparse(node)})
    write(E / "reconciliation_pins.json", {"python_ast": "3.12", "nodes": pin_rows,
        "reference_census_sha256": assignment(text, "RECON_REFERENCES"), "runtime_pin_refresh": False})
    result = read(E / "s1.result.json")
    write(E / "reconciled_sites.json", {"sites": result["observations"]["static_send_sites"], "approved_llm_posts": 7,
        "approved_oauth_posts": 1, "additional_constructions": 4, "dynamic_send": "POTENTIAL_LLM, not a safe exemption"})
    old = (P / "before" / SOURCE).read_text(encoding="utf-8")
    def func(value, name): return next(n for n in ast.parse(value).body if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast_hash(func(old, "_production_modules")) == ast_hash(func(text, "_production_modules"))
    write(E / "s2_preexisting_failure_analysis.json", {"test": "IsolationTests.test_no_production_module_imports_the_policy_yet",
        "predicate": "all s1._production_modules() except policy must not import ultra_budget_policy",
        "unchanged_scanner_ast_sha256": ast_hash(func(text, "_production_modules")),
        "unchanged_ledger_import": "ultra_budget_ledger.py:25 imports ultra_budget_policy as policy",
        "source_provenance": "ledger and S2 test are in before baseline and remain byte-identical",
        "proof": "source-level independence from changed S1 inventory; not a separate baseline S2 execution",
        "action": "STOP S2 oracle changes; separate AMENDMENT requested"})
    write(E / "test_summary.json", {"status": "PARTIAL overall; S1 AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING",
        "original_red": {"run": 69, "pass": 67, "fail": 2, "error": 0, "skip": 0, "exit": 1},
        "s1_final": {"run": 69, "pass": 69, "fail": 0, "error": 0, "skip": 0, "exit": 0, "guard": 0, "evidence": 0},
        "extra_checks": {"run": 23, "pass": 23, "fail": 0, "error": 0, "skip": 0, "source_mutations": 18, "positive_controls": 1, "fake_execution": 4},
        "weakened_oracles": {"processes": 3, "expected_exit": 1, "observed_exit": [1, 1, 1], "fail_counts": [1, 3, 1]},
        "s2_final": {"run": 73, "pass": 72, "fail": 1, "error": 0, "skip": 0, "exit": 1, "guard": 0},
        "s3a": {"run": 35, "pass": 35, "fail": 0, "error": 0, "skip": 0, "exit": 0},
        "scope": "one S1 source file; no runtime, policy, ledger, network settings or approved routes changed"})
    previous = ROOT / "reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/handoff_task.md"
    write(E / "closeout_before.json", {"card_sha256": sha((P / "before/card.md").read_bytes()), "previous_snapshot_sha256": sha(previous.read_bytes())})
    private = Path(tempfile.gettempdir()) / (P.name + "_private_logs")
    mapping_file = E / "sanitization.json"
    mapping = read(mapping_file)["files"] if mapping_file.exists() else []
    home = str(Path.home()); patterns = [home, home.replace("\\", "/"), home.replace("\\", "\\\\")]
    for f in sorted(E.rglob("*")):
        if not f.is_file() or f.suffix not in {".txt", ".json", ".jsonl", ".xml"} or f == mapping_file: continue
        raw = f.read_bytes(); cleaned = raw.decode("utf-8")
        for pattern in patterns: cleaned = cleaned.replace(pattern, "<USER_HOME>")
        if cleaned.encode("utf-8") != raw:
            private.mkdir(exist_ok=True)
            archive_name = f.name + "." + sha(raw) + ".raw"
            dest = private / archive_name
            if not dest.exists(): dest.write_bytes(raw)
            f.write_bytes(cleaned.encode("utf-8"))
            mapping.append({"path": f.relative_to(ROOT).as_posix(), "original_sha256": sha(raw), "sanitized_sha256": sha(f.read_bytes()),
                            "change": "home path only", "original": "private TEMP / " + P.name + "_private_logs / " + archive_name})
    write(mapping_file, {"files": mapping, "RAW_fixtures_published": False, "credential_values_published": False})


def manifest():
    paths = [ROOT / SOURCE] + [f for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"]
    write(P / "manifest.json", {"task_id": P.name, "status": "LOCAL ONLY / PARTIAL / INDEPENDENT REVIEW PENDING", "hash": "SHA-256 exact bytes", "self_excluded": True,
        "files": [{"path": f.relative_to(ROOT).as_posix(), "size": f.stat().st_size, "sha256": sha(f.read_bytes())} for f in sorted(paths)]})


def check(post):
    data = read(P / "manifest.json")
    expected = {SOURCE} | {f.relative_to(ROOT).as_posix() for f in P.rglob("*") if f.is_file() and f.name != "manifest.json"}
    assert expected == {r["path"] for r in data["files"]}
    for row in data["files"]:
        f = ROOT / row["path"]
        assert f.resolve().is_relative_to(P) or row["path"] == SOURCE
        assert f.stat().st_size == row["size"] and sha(f.read_bytes()) == row["sha256"], row["path"]
    baseline = read(E / "baseline.json")
    for row in baseline["files"]:
        if row["path"] != SOURCE: assert sha((ROOT / row["path"]).read_bytes()) == row["sha256"], row["path"]
    before, final = (P / "before" / SOURCE).read_text(encoding="utf-8"), (ROOT / SOURCE).read_text(encoding="utf-8")
    assert assignment(before, "MANIFEST") == assignment(final, "MANIFEST") and len(assignment(final, "MANIFEST")) == 69
    assert assignment(before, "EXPECTED_SEND_SITES") == assignment(final, "EXPECTED_SEND_SITES")
    assert (P / "final" / (SOURCE + ".txt")).read_bytes() == (ROOT / SOURCE).read_bytes()
    source_sha = sha((ROOT / SOURCE).read_bytes())
    for name in ["s1", "checks", "weaken_unknown", "weaken_local", "weaken_metadata"]:
        assert read(E / (name + ".execution.json"))["s1_source_sha256"] == source_sha, name
    s1, red, s2, extra = [read(E / name) for name in ["s1.result.json", "red.result.json", "s2.result.json", "checks.result.json"]]
    assert red["counts"]["run"] == 69 and red["counts"]["failures"] == 2
    assert s1["gate"] == {"status": "PASS", "exit_code": 0, "reasons": []} and s1["counts"]["run"] == 69
    assert s1["selected"] is None and not s1["isolation_violations"] and not s1["evidence_problems"]
    assert s2["counts"]["run"] == 73 and s2["counts"]["failures"] == 1 and s2["failures"] == ["__main__.IsolationTests.test_no_production_module_imports_the_policy_yet"]
    assert not s2["isolation_violations"] and not s2["problems"]
    assert extra["counts"] == {"run": 23, "fail": 0, "error": 0, "skip": 0} and not extra["isolation_violations"]
    negative = [k for k, v in extra["observations"].items() if isinstance(v, list)]
    assert len(negative) == 18 and all(extra["observations"][k] for k in negative)
    for name, failures in [("weaken_unknown", 1), ("weaken_local", 3), ("weaken_metadata", 1)]:
        result = read(E / (name + ".result.json"))
        assert result["counts"] == {"run": 23, "fail": failures, "error": 0, "skip": 0}
        assert read(E / (name + ".execution.json"))["exit_code"] == 1 and not result["isolation_violations"]
    for name in ["s1", "checks"]:
        raw = (E / (name + ".stdout.txt")).read_text(encoding="utf-8")
        secret = json.loads(raw[raw.rfind('{"secret_guard":'):])["secret_guard"]
        assert not secret["denials"]
    xml = ET.parse(E / "s3a.xml").getroot()
    assert len(list(xml.iter("testcase"))) == 35 and not any(list(xml.iter(k)) for k in ["failure", "error", "skipped"])
    assert not (E / "s3a.guard.jsonl").exists() or not (E / "s3a.guard.jsonl").read_text().strip()
    assert read(E / "controls.result.json")["expected_blocked_before_io"] == ["socket", "dns", "credentials", "credential_file"]
    report = (P / "report.md").read_text(encoding="utf-8")
    assert "PARTIAL" in "\n".join(report.splitlines()[:12]) and "MANUAL ENGINEERING REVIEW" in report
    for target in re.findall(r"\]\(([^)]+)\)", report): assert (P / target).is_file(), target
    result = {"result": "AUTHOR_PACKAGE_CHECK_PASS", "phase": "post-finish" if post else "pre-finish", "technical_status": "PARTIAL overall / S1 AUTHOR RESULT READY",
        "manifest_files": len(data["files"]), "working_source_changes": [SOURCE], "read_only_unchanged": len(baseline["files"]) - 1,
        "s1": "69 PASS", "extra": "23 PASS / 18 mutations detected", "s2": "72 PASS / 1 FAIL retained", "s3a": "35 PASS"}
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
        assert sha((ROOT / "reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/handoff_task.md").read_bytes()) == read(E / "closeout_before.json")["previous_snapshot_sha256"]
        result.update(history_id=record["history_id"], block1="WAITING", block1_1="SUBMITTED / REVIEW PENDING", previous_snapshot_and_blocks2_to4="PRESERVED")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "prepare":
        prepare(); prepare_evidence()
    elif action == "manifest": manifest()
    else: check(action == "post")
