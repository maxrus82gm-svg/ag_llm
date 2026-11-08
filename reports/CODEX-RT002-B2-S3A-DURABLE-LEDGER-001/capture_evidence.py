"""Save exact synthetic committed index bytes; no real provider or live workspace."""
import json
import hashlib
import tempfile
from pathlib import Path
import runpy
import os
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
os.environ.update(ORDINARY_GUARD_ROOT=str(ROOT), ORDINARY_GUARD_NETWORK="none",
                  ORDINARY_GUARD_LOG=str(PACKAGE / "evidence/guard_capture.jsonl"))
runpy.run_path(str(ROOT / "reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/guard/sitecustomize.py"))
sys.path.insert(0, str(ROOT))
import context_storage as core
import run_store as store
from ultra_budget_ledger import BudgetLedger, LedgerDenied
from test_rt002_s3a_ledger import reserve

out = PACKAGE / "evidence/committed"
out.mkdir(exist_ok=True)
rows = []
with tempfile.TemporaryDirectory(prefix="s3a_evidence_") as directory:
    root = Path(directory)
    ws = core.ensure_workspace_storage(root)["workspace_id"]
    ledger = BudgetLedger(root, ws)
    ledger.initialize()
    (out / "workspace_identity.json").write_bytes((root / ".ultra/workspace.json").read_bytes())
    (out / "enrollment.json").write_bytes((root / ".ultra/audit/budget.enrollment.json").read_bytes())
    def snapshot(label):
        raw = store.workspace_index_path(root).read_bytes()
        (out / (label + ".json")).write_bytes(raw)
        view = BudgetLedger(root, ws).recover()
        rows.append({"phase": label, "sha256": hashlib.sha256(raw).hexdigest(), "revision": view.revision,
                     "events": view.event_count, "attempts": [{"provider_attempt_id": r.attempt_id, "state": r.state, "liability_tokens": r.liability_tokens} for r in view.attempts]})
    reserve(ledger);snapshot("01_reserved")
    ledger.mark_sent("pa_1");snapshot("02_sent")
    ledger.terminal("pa_1", "timeout", None);snapshot("03_unknown")
    usage = {"prompt_tokens": 20, "precached_prompt_tokens": 0, "completion_tokens": 5}
    ledger.terminal("pa_1", "completed", usage);snapshot("04_late_reconciled")
    before = store.workspace_index_path(root).read_bytes()
    duplicate = ledger.terminal("pa_1", "completed", usage)
    assert duplicate.replayed and store.workspace_index_path(root).read_bytes() == before
    ledger.terminal("pa_1", "completed", {"prompt_tokens": 1, "precached_prompt_tokens": 0, "completion_tokens": 0});snapshot("05_anomaly")
    try:
        reserve(ledger, "new_after_anomaly")
    except LedgerDenied:
        denied = True
    else:
        denied = False
    assert denied
    (out / "trace.json").write_text(json.dumps({"workspace_id": ws, "ledger_source_sha256": hashlib.sha256((ROOT / "ultra_budget_ledger.py").read_bytes()).hexdigest(), "rows": rows, "duplicate_terminal_no_write": True,
                    "new_attempt_after_anomaly_denied": denied, "physical_network_calls": 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"snapshots": len(rows), "guarded_synthetic_only": True}))
