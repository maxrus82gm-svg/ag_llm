"""Addressed read-only source registry for the decision packet; no imports of inspected modules."""
import ast
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]

ITEMS = [
    ("S01", "Approved B2 graph and accounting owner", "Документация/20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md", ["## 5а.", "| **S3b**", "| **S9**", "## 14."]),
    ("S02", "Current journal: later S3a execution supersedes older OPEN", "Документация/21_Журнал качественного перехода - решения, метрики и аудит.md", ["independent GitHub Actions BOUNDED PASS", "S2 H-CODEX-000025"]),
    ("S03", "Stage6/7 and shared budget architecture", "Документация/37_Старт перехода - Web Alarm Ultra.md", ["### Этап 6", "### Этап 7", "## 4."]),
    ("S04", "Independent S1 69+23", "reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/review.md", ["**Verdict:", "## Actual independent"]),
    ("S05", "Independent S2 73 and bounded static import oracle", "reports/CHATGPT-WEB26-CODEX-RT002-S2-REVIEW-20261108/review.md", ["**VERDICT:", "## Инженерный"]),
    ("S06", "Independent OFFLINE S3a/Run Store/guards", "reports/CHATGPT-WEB26-RT002-S3A-REVIEW-20261108/review.md", ["**Verdict:", "## Executable", "## Engineering"]),
    ("S07", "Durable independent CI summary, artifact provenance", "reports/CHATGPT-WEB26-RT002-S3A-REVIEW-20261108/independent_runs.json", ["\"run_id\"", "\"artifact_expires\"", "\"offline_guard\""]),
    ("S08", "Current pure policy implementation", "ultra_budget_policy.py", ["ROUTES:", "class ScopeLimits", "class PolicySnapshot", "def validate_policy", "def estimate_input_tokens", "def calibrate_profiles", "class AttemptRecord", "def budget_view", "def evaluate_request"]),
    ("S09", "342-row derived calibration and legacy A/B/C proposals", "test_rt002_s2_budget_policy.py", ["DATASET_SHA256 =", "ROWS =", "CANDIDATES =", "def test_calibrated_lower_envelopes", "def test_leave_one_out", "def test_candidate_reserves_cover"]),
    ("S10", "S3a durable storage, engine/scope pins, marker", "ultra_budget_ledger.py", ["MAX_EVENTS =", "def _replay", "pin = (", "def _load", "def initialize", "def reserve", "def mark_not_sent"]),
    ("S11", "Shared index lock/atomic write/capacity", "run_store.py", ["_MAX_AUDIT_BYTES =", "def _index_lock", "def _atomic_json", "def _save_index"]),
    ("S12", "Ordinary shared text core and injection boundary", "ordinary_chat_service.py", ["class RequestLimits", "class PreparedRequest", "class ChatTransport", "async def execute_request"]),
    ("S13", "Existing fake-only shared adapter", "web_alarm/ordinary_chat_test_adapter.py", ["class _FixtureTransport", "class OfflineTestAdapter", "def execute"]),
    ("S14", "Current OFFLINE Web request caps, Turn integration", "web_alarm/ultra_chat.py", ["def _fixture_turns", "limits=RequestLimits", "def _context"]),
    ("S15", "Model aliases and effective provider identities", "model_registry.py", ["_MODEL_REGISTRY =", "def get_model_spec"]),
    ("S16", "H23 historical Ordinary proposal, not current acceptance status", "reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/ordinary_chat_contract.md", ["## Что требует", "## Узлы", "## Отмена"]),
    ("S17", "Current reviewed S1 physical/potential boundaries", "reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/route_reconciliation.md", ["## Launcher", "## Ordinary", "## Metadata"]),
    ("S18", "Saved H25 author calibration observations; not rerun here", "reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/evidence/s2.result.json", ["\"calibration_report_margin_0\"", "\"leave_one_out\""]),
    ("S19", "Coordination and freezes, latest S3a status", "Документация/40_Оперативная координация направлений.md", ["**CURRENT WEB26", "Colibri"]),
    ("S20", "Tactical context and precedence", "Документация/34_TACTICAL_CONTEXT.md", ["CURRENT", "S3a"]),
    ("S21", "Open decisions and risks index", "Документация/05_Реестр задач.md", ["`ORDINARY-CHAT-POLICY`", "`S2-STATIC-IMPORT-COVERAGE`"]),
    ("S22", "Testing/evidence rules", "Документация/36.1_Обязательный регламент тестирования для LLM.md", ["## TEST-ENG-01", "## TEST-EVID-01", "## TEST-SCOPE-01"]),
    ("S23", "Exact profile selectors, no need for regression on doc-only task", "Документация/36.3_Профиль тестирования Ultra.md", ["## 2.", "## 3."]),
    ("S24", "Entry/scope/finish rules", "Документация/08_Старт.md", ["## Две постоянные", "## Как теперь", "## Обязательные границы"]),
    ("S25", "H23 author architecture/limits", "reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/report.md", ["## MANUAL", "## NOT RUN"]),
    ("S26", "H24 author scope/negative evidence", "reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/report.md", ["## Причина", "## Оставшийся"]),
    ("S27", "H25 author scope/negative evidence", "reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/report.md", ["## Причина", "### MANUAL"]),
]


def main():
    rows = []
    for ident, title, name, needles in ITEMS:
        path = ROOT / name
        raw = path.read_bytes(); lines = raw.decode("utf-8").splitlines()
        rows.append({"id": ident, "title": title, "path": name, "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw),
            "locators": [{"needle": query, "line": next((i+1 for i,s in enumerate(lines) if query in s), None)} for query in needles]})
    out = {"task_id": P.name, "method": "local addressed source reads, no Git/GitHub/network", "sources": rows}
    (P / "evidence/source_registry.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    baseline_file = P / "evidence/baseline.json"
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
    known = {row["path"] for row in baseline["files"]}
    for row in rows:
        if row["path"] not in known:
            baseline["files"].append({k: row[k] for k in ["path", "sha256", "size"]});known.add(row["path"])
    baseline_file.write_text(json.dumps(baseline, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"sources": len(rows), "baseline_files": len(baseline["files"]),
                      "missing_locators": [{"id": row["id"],"needle":loc["needle"]} for row in rows for loc in row["locators"] if loc["line"] is None]}))


if __name__ == "__main__": main()
