"""Synthetic S3a contracts; run through the task OFFLINE guard, never a provider."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest
import context_storage as core
import run_store as store
import ultra_budget_policy as p
from ultra_budget_ledger import BudgetLedger, LedgerDenied

DRIVER = Path(__file__).parent / "reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/run_checks.py"


def policy(**overrides):
    run = dict(max_request_bytes=4096, max_request_input_tokens_est=1000,
               max_verification_request_bytes=4096, max_verification_request_input_tokens_est=1000,
               max_run_liability_tokens=2000, max_run_attempts=10,
               max_attempts_per_role={"planner": None, "executor": None, "dredd": None},
               verification_reserve_tokens=100, verification_reserve_attempts=0)
    run.update(overrides)
    return dict(schema_version=1, revision_label="S3a SYNTHETIC ONLY", run=run,
                estimation={"profiles": [dict(provider_model_id="SYNTHETIC", profile_key="executor",
                                              bytes_per_token=1.0, samples=10, source_sha256="a" * 64)], "missing_profile": "DENY"},
                output_reserve="MAX_TOKENS", compressor={"mode": "DENY"}, mcp={"mode": "DENY"},
                read={"max_full_read_bytes": 4096})


def reserve(ledger, attempt="pa_1", raw=None, text="synthetic", context=None, **kwargs):
    body = dict(model="SYNTHETIC", max_tokens=8, messages=[{"role": "user", "content": text}])
    return ledger.reserve(attempt, policy() if raw is None else raw, "executor", p.serialize_request_body(body),
                          context or p.RunContext("run_synthetic", False),
                          {"run_id": "run_synthetic", "chat_id": "chat_synthetic", "turn_id": "turn_synthetic", "logical_call_id": "lc_1"}, **kwargs)


def last_token_policy():
    body = dict(model="SYNTHETIC", max_tokens=8, messages=[{"role": "user", "content": "synthetic"}])
    exact = len(p.serialize_request_body(body)) + 8  # synthetic bytes/token=1, exact output reserve
    return policy(max_run_liability_tokens=exact, max_request_input_tokens_est=exact,
                  max_verification_request_input_tokens_est=exact, verification_reserve_tokens=0)


@pytest.fixture
def ledger(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    ws = core.ensure_workspace_storage(root)["workspace_id"]
    value = BudgetLedger(root, ws)
    value.initialize()
    return value


def worker(mode, root, ws, attempt="pa_worker", gate=""):
    ledger = BudgetLedger(root, ws)
    if mode == "read":
        view = ledger.recover()
        return {"count": len(view.attempts), "liability": sum(a.liability_tokens for a in view.attempts)}
    if mode in ("race", "race_tokens"):
        until = time.monotonic() + 8
        while not Path(gate).exists() and time.monotonic() < until:
            time.sleep(.01)
        try:
            reserve(ledger, attempt, last_token_policy() if mode == "race_tokens" else policy(max_run_attempts=1))
            return {"allowed": True}
        except LedgerDenied:
            return {"allowed": False}
    original = store._save_index
    def crash(*args, **kwargs):
        if mode == "crash_before":
            os._exit(79)
        original(*args, **kwargs)
        os._exit(79)
    with patch.object(store, "_save_index", crash):
        reserve(ledger, attempt, policy(max_run_attempts=1))
    raise AssertionError("crash seam not reached")


def child(ledger, *args, **kwargs):
    return subprocess.run([sys.executable, "-B", str(DRIVER), "--worker", *args,
                           str(ledger.root), ledger.workspace_id], capture_output=True, timeout=15, **kwargs)


def test_durable_reservation_new_process_and_idempotent_identity(ledger):
    first = reserve(ledger)
    index = store.workspace_index_path(ledger.root).read_bytes()
    assert first.record.reserved_liability_tokens > 8
    again = reserve(ledger)
    assert again.replayed and again.record == first.record
    assert index == store.workspace_index_path(ledger.root).read_bytes()
    result = child(ledger, "read")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"count": 1, "liability": first.record.reserved_liability_tokens}
    with pytest.raises(LedgerDenied, match="ATTEMPT_ID_CONFLICT"):
        reserve(ledger, text="different")
    assert len(ledger.recover().attempts) == 1


@pytest.mark.parametrize("mode", ["race", "race_tokens"])
def test_two_processes_compete_for_last_reservation(ledger, tmp_path, mode):
    gate = tmp_path / "start"
    commands = [[sys.executable, "-B", str(DRIVER), "--worker", mode, str(ledger.root), ledger.workspace_id, a, str(gate)] for a in ("pa_a", "pa_b")]
    children = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for cmd in commands]
    try:
        gate.write_text("go")
        outputs = [c.communicate(timeout=15) for c in children]
        assert [c.returncode for c in children] == [0, 0], outputs
        assert sorted(json.loads(out[0])["allowed"] for out in outputs) == [False, True]
        assert len(ledger.recover().attempts) == 1
    finally:
        for c in children:
            if c.poll() is None:
                c.kill()
                c.wait(5)


@pytest.mark.parametrize("mode,committed", [("crash_before", False), ("crash_after", True)])
def test_process_crash_no_false_zero_after_commit(ledger, mode, committed):
    result = child(ledger, mode)
    assert result.returncode == 79, result.stderr
    view = ledger.recover()
    assert len(view.attempts) == int(committed)
    if committed:
        with pytest.raises(LedgerDenied):
            reserve(ledger, "new_attempt", policy(max_run_attempts=1))
    else:
        reserve(ledger, "new_attempt", policy(max_run_attempts=1))


def test_sent_timeout_unknown_late_usage_and_duplicate(ledger):
    limited = policy(max_run_attempts=1)
    held = reserve(ledger, raw=limited).record.reserved_liability_tokens
    assert not ledger.mark_sent("pa_1").replayed
    assert ledger.mark_sent("pa_1").replayed
    assert ledger.terminal("pa_1", "timeout", None).record.liability_tokens == held
    restarted = BudgetLedger(ledger.root, ledger.workspace_id)
    assert restarted.recover().attempts[0].state == p.UNKNOWN_TERMINAL
    with pytest.raises(LedgerDenied, match="RUN_ATTEMPTS_EXCEEDED"):
        reserve(restarted, "no_free_retry", limited)
    usage = dict(prompt_tokens=20, precached_prompt_tokens=0, completion_tokens=5)
    settled = restarted.terminal("pa_1", "completed", usage)
    assert settled.record.state == p.RECONCILED and settled.record.liability_tokens == 25
    revision = settled.revision
    assert restarted.terminal("pa_1", "completed", usage).replayed
    assert restarted.recover().revision == revision
    conflicting = restarted.terminal("pa_1", "completed", dict(prompt_tokens=1, precached_prompt_tokens=0, completion_tokens=0))
    assert conflicting.record.state == p.ANOMALY
    assert conflicting.record.liability_tokens >= max(held, 25)
    with pytest.raises(LedgerDenied):
        reserve(restarted, "pa_blocked")


def test_not_sent_requires_proof_and_never_frees_sent_attempt(ledger):
    held = reserve(ledger).record.liability_tokens
    with pytest.raises(LedgerDenied):
        ledger.mark_not_sent("pa_1")
    assert ledger.recover().attempts[0].liability_tokens == held
    proof = {"kind": "PROVEN_PRE_SEND_NOT_SENT", "reference": "offline_no_dispatch_1"}
    released = ledger.mark_not_sent("pa_1", proof)
    assert released.record.state == p.NOT_SENT and released.record.liability_tokens == 0
    assert ledger.mark_not_sent("pa_1", proof).replayed
    reserve(ledger, "pa_2")
    ledger.mark_sent("pa_2")
    anomalous = ledger.mark_not_sent("pa_2", proof).record
    assert anomalous.state == p.ANOMALY and anomalous.liability_tokens == held


@pytest.mark.parametrize("change", ["bad_json", "ledger_version", "bool_version", "missing_state", "checksum", "bad_event", "missing_index", "missing_marker", "marker_version"])
def test_corrupt_or_missing_ledger_fails_closed(ledger, change):
    reserve(ledger)
    path = store.workspace_index_path(ledger.root)
    value = json.loads(path.read_bytes())
    state = value["budget_ledger"]
    if change == "missing_index":
        path.unlink()
    elif change in {"missing_marker", "marker_version"}:
        marker = ledger.root / ".ultra/audit/budget.enrollment.json"
        if change == "missing_marker": marker.unlink()
        else:
            data = json.loads(marker.read_bytes());data["schema_version"] = 99
            marker.write_text(json.dumps(data), encoding="utf-8")
    elif change == "bad_json":
        path.write_bytes(b'{"broken":')
    else:
        if change == "ledger_version": state["schema_version"] = 2
        elif change == "bool_version": state["schema_version"] = True
        elif change == "missing_state": del value["budget_ledger"]
        elif change == "checksum": state["events"][0]["provider_attempt_id"] = "changed"
        elif change == "bad_event":
            state["events"][0]["op"] = "new_unknown_op"
            from ultra_budget_ledger import _hash
            state["events_sha256"] = _hash(state["events"])
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(LedgerDenied): ledger.recover()
    with pytest.raises(LedgerDenied): reserve(ledger, "new")
    with pytest.raises(LedgerDenied): ledger.initialize()


@pytest.mark.parametrize("field", ["missing_profile", "invalid_policy", "missing_max_tokens", "unknown_route", "wire_changed", "policy_changed"])
def test_invalid_request_policy_and_scope_binding_deny_without_writes(ledger, field):
    raw = policy()
    if field == "policy_changed": reserve(ledger)
    before = store.workspace_index_path(ledger.root).read_bytes()
    if field == "missing_profile": raw["estimation"]["profiles"] = []
    if field == "invalid_policy": raw["run"]["max_run_attempts"] = True
    if field == "policy_changed": raw["revision_label"] = "different"
    body = dict(model="SYNTHETIC", max_tokens=8, messages=[])
    if field == "missing_max_tokens": del body["max_tokens"]
    wire = p.serialize_request_body(body)
    if field == "wire_changed": wire += b" "
    route = "ordinary_chat" if field == "unknown_route" else "executor"
    with pytest.raises(LedgerDenied):
        ledger.reserve("new", raw, route, wire, p.RunContext("run_synthetic", False),
                       dict(run_id="run_synthetic", chat_id="chat", turn_id="turn", logical_call_id="lc"))
    assert store.workspace_index_path(ledger.root).read_bytes() == before


@pytest.mark.parametrize("failure", ["fsync", "lock", "before_commit", "after_commit"])
def test_io_failure_never_returns_permit_and_keeps_committed_liability(ledger, failure):
    if failure == "fsync": target, replacement = "os.fsync", lambda *a: (_ for _ in ()).throw(OSError("injected fsync"))
    elif failure == "lock": target, replacement = "_index_lock", lambda *a: (_ for _ in ()).throw(core.WorkspaceBusyError())
    else:
        original = store._save_index
        def replacement(*args):
            if failure == "after_commit": original(*args)
            raise OSError("injected commit boundary")
        target = "_save_index"
    with patch("run_store." + target, replacement), pytest.raises(LedgerDenied) as refused: reserve(ledger)
    if failure == "lock": assert "WorkspaceBusyError" in str(refused.value)
    view = ledger.recover()
    assert len(view.attempts) == (1 if failure == "after_commit" else 0)


def test_generation_fallback_preserves_reserve(ledger):
    original = store._replace_with_retry
    def busy_canonical(source, destination):
        if destination.name == "index.json":
            raise PermissionError("shared index busy")
        return original(source, destination)
    with patch.object(store, "_replace_with_retry", busy_canonical):
        reserve(ledger)
    assert len(ledger.recover().attempts) == 1
    assert store._generation_paths(ledger.root)


def test_move_identity_and_existing_run_store_compatibility(ledger, tmp_path):
    first = reserve(ledger)
    store.create_run_summary(ledger.root, ledger.workspace_id, "chat", "task", "legacy_run")
    store.append_run_record(ledger.root, "legacy_run", source="SERVER", event="legacy", payload={"text": "unchanged"}, timestamp=1)
    summary = store.run_component_path(ledger.root, "legacy_run", "summary.json").read_bytes()
    reserve(ledger, "pa_2")
    assert store.run_component_path(ledger.root, "legacy_run", "summary.json").read_bytes() == summary
    assert store.load_stream_records(ledger.root, "legacy_run", "SERVER")[0]["payload"] == {"text": "unchanged"}
    destination = tmp_path / "moved_workspace"
    assert ledger.root.resolve().is_relative_to(tmp_path.resolve()) and destination.parent.resolve() == tmp_path.resolve()
    ledger.root.rename(destination)
    recovered = BudgetLedger(destination, ledger.workspace_id).recover()
    assert recovered.attempts[0] == first.record and len(recovered.attempts) == 2
    with pytest.raises(LedgerDenied): BudgetLedger(destination, "foreign_workspace").recover()


def test_missing_ledger_and_historical_audit_never_bootstrap_zero(tmp_path):
    root = tmp_path / "legacy";root.mkdir()
    ws = core.ensure_workspace_storage(root)["workspace_id"]
    store.create_run_summary(root, ws, "chat", "task", "legacy")
    before = store.run_component_path(root, "legacy", "summary.json").read_bytes()
    ledger = BudgetLedger(root, ws)
    with pytest.raises(LedgerDenied): ledger.recover()
    with pytest.raises(LedgerDenied): ledger.initialize()
    assert store.run_component_path(root, "legacy", "summary.json").read_bytes() == before


def test_marker_first_initialization_failure_cannot_reset(tmp_path):
    root = tmp_path / "new";root.mkdir();ws = core.ensure_workspace_storage(root)["workspace_id"]
    ledger = BudgetLedger(root, ws)
    with patch.object(store, "_save_index", side_effect=OSError("init interrupted")), pytest.raises(LedgerDenied): ledger.initialize()
    with pytest.raises(LedgerDenied): ledger.initialize()
    with pytest.raises(LedgerDenied): ledger.recover()


def test_policy_engine_upgrade_needs_migration_not_lower_replayed_reserve(ledger):
    held = reserve(ledger).record.liability_tokens
    with patch("ultra_budget_ledger._engine_id", return_value="f" * 64):
        with pytest.raises(LedgerDenied, match="INVALID_ENROLLMENT"): ledger.recover()
        with pytest.raises(LedgerDenied): reserve(ledger, "new")
    assert ledger.recover().attempts[0].liability_tokens == held


def test_invalid_or_missing_workspace_refused_without_creation(tmp_path):
    with pytest.raises(LedgerDenied): BudgetLedger(None, "ws")
    missing = tmp_path / "missing"
    with pytest.raises(LedgerDenied): BudgetLedger(missing, "ws").initialize()
    assert not missing.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction oracle")
@pytest.mark.parametrize("link_kind", ["audit", "marker", "root"])
def test_unsafe_path_refusal_without_external_write(ledger, tmp_path, link_kind):
    import _winapi
    outside = tmp_path / "outside";outside.mkdir();(outside / "preserve").write_bytes(b"same")
    if link_kind == "marker":
        path = ledger.root / ".ultra/audit/budget.enrollment.json"
        path.unlink()
        os.link(outside / "preserve", path)
    else:
        path = ledger.root / ".ultra/audit" if link_kind == "audit" else tmp_path / "alias"
        if path.exists():
            backup = tmp_path / "audit_backup"
            assert path.resolve().is_relative_to(tmp_path.resolve()) and backup.parent == tmp_path
            path.rename(backup)
        _winapi.CreateJunction(str(outside if link_kind == "audit" else ledger.root), str(path))
    before = {p.name: p.read_bytes() for p in outside.iterdir()}
    target = BudgetLedger(path, ledger.workspace_id) if link_kind == "root" else ledger
    with pytest.raises(LedgerDenied): target.recover()
    with pytest.raises(LedgerDenied): reserve(target)
    assert before == {p.name: p.read_bytes() for p in outside.iterdir()}
