import json
from pathlib import Path

import run_store
from audit_storage import AuditThreadRecorder
from run_store import (
    append_run_record, create_run_summary, ensure_run_index_entry,
    ensure_task_index_entry, get_run_index_entry, get_task_index_entry,
    list_run_records, load_run_record, load_workspace_run_index, run_component_path,
    update_run_summary_index,
)


def test_ids_and_utf8_offsets_are_stable(tmp_path: Path):
    t1='tb_'+'1'*32; t2='tb_'+'2'*32
    assert ensure_task_index_entry(tmp_path,t1,'chat')["display_id"]=='T-001'
    assert ensure_task_index_entry(tmp_path,t1,'chat')["display_id"]=='T-001'
    assert ensure_task_index_entry(tmp_path,t2,'chat')["display_id"]=='T-002'
    assert ensure_run_index_entry(tmp_path,'run1',t1,'chat')["display_id"]=='R-001'
    assert ensure_run_index_entry(tmp_path,'run2',t2,'chat')["display_id"]=='R-002'
    create_run_summary(tmp_path,'ws','chat',t1,'run1')
    a=append_run_record(tmp_path,'run1',source='SERVER',event='один',payload={'text':'Кириллица'},timestamp=1)
    b=append_run_record(tmp_path,'run1',source='SERVER',event='два',payload={'text':'ещё'},timestamp=2)
    assert a['offset']==0 and b['offset']==a['length']
    assert load_run_record(tmp_path,'run1',a['record_id'])['payload']['text']=='Кириллица'
    assert len(list_run_records(tmp_path,'run1'))==2
    assert load_workspace_run_index(tmp_path)['next_run_number']==3
    assert not list((tmp_path/'.ultra/audit').glob('.*.tmp'))


def test_atomic_json_retries_transient_permission_error(tmp_path: Path, monkeypatch):
    real_replace = run_store.os.replace
    attempts = []
    sleeps = []

    def flaky_replace(source, destination):
        attempts.append((source, destination))
        if len(attempts) < 3:
            raise PermissionError("simulated sharing violation")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", flaky_replace)
    monkeypatch.setattr(run_store.time, "sleep", sleeps.append)

    task = "tb_" + "c" * 32
    entry = ensure_task_index_entry(tmp_path, task, "chat")

    assert entry["display_id"] == "T-001"
    assert len(attempts) == 3
    assert sleeps == [0.02, 0.05]
    assert load_workspace_run_index(tmp_path)["tasks"][task]["display_id"] == "T-001"
    assert not list((tmp_path / ".ultra/audit").glob(".*.tmp"))


def test_persistent_canonical_lock_falls_back_to_generation(tmp_path: Path, monkeypatch):
    real_replace = run_store.os.replace
    canonical = run_store.workspace_index_path(tmp_path).resolve()
    sleeps = []

    def locked_canonical(source, destination):
        if Path(destination).resolve() == canonical:
            raise PermissionError("persistent canonical lock")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", locked_canonical)
    monkeypatch.setattr(run_store.time, "sleep", sleeps.append)

    task = "tb_" + "e" * 32
    entry = ensure_task_index_entry(tmp_path, task, "chat")
    loaded = load_workspace_run_index(tmp_path)

    assert entry["display_id"] == "T-001"
    assert loaded["tasks"][task]["display_id"] == "T-001"
    assert loaded["revision"] == 1
    assert not run_store.workspace_index_path(tmp_path).exists()
    generations = list((tmp_path / ".ultra/audit/index_generations").glob("index-*.json"))
    assert len(generations) == 1
    assert sleeps == list(run_store._ATOMIC_REPLACE_RETRY_DELAYS)
    assert not list((tmp_path / ".ultra/audit").glob(".*.tmp"))


def test_generation_path_preserves_monotonic_task_and_run_ids(tmp_path: Path, monkeypatch):
    real_replace = run_store.os.replace
    canonical = run_store.workspace_index_path(tmp_path).resolve()

    def locked_canonical(source, destination):
        if Path(destination).resolve() == canonical:
            raise PermissionError("persistent canonical lock")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", locked_canonical)
    monkeypatch.setattr(run_store.time, "sleep", lambda _delay: None)

    t1 = "tb_" + "3" * 32
    t2 = "tb_" + "4" * 32
    assert ensure_task_index_entry(tmp_path, t1, "chat")["display_id"] == "T-001"
    assert ensure_task_index_entry(tmp_path, t2, "chat")["display_id"] == "T-002"
    assert ensure_run_index_entry(tmp_path, "run1", t1, "chat")["display_id"] == "R-001"
    assert ensure_run_index_entry(tmp_path, "run2", t2, "chat")["display_id"] == "R-002"

    loaded = load_workspace_run_index(tmp_path)
    assert loaded["next_task_number"] == 3
    assert loaded["next_run_number"] == 3
    assert loaded["revision"] == 4
    assert len(list((tmp_path / ".ultra/audit/index_generations").glob("index-*.json"))) == 4


def test_primary_index_recovers_and_compacts_generations_after_unlock(tmp_path: Path, monkeypatch):
    real_replace = run_store.os.replace
    canonical = run_store.workspace_index_path(tmp_path).resolve()
    locked = {"value": True}

    def sometimes_locked(source, destination):
        if locked["value"] and Path(destination).resolve() == canonical:
            raise PermissionError("persistent canonical lock")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", sometimes_locked)
    monkeypatch.setattr(run_store.time, "sleep", lambda _delay: None)

    t1 = "tb_" + "5" * 32
    t2 = "tb_" + "6" * 32
    ensure_task_index_entry(tmp_path, t1, "chat")
    assert list((tmp_path / ".ultra/audit/index_generations").glob("index-*.json"))

    locked["value"] = False
    ensure_task_index_entry(tmp_path, t2, "chat")

    primary = run_store._load_index_file(run_store.workspace_index_path(tmp_path))
    assert primary["revision"] == 2
    assert primary["tasks"][t1]["display_id"] == "T-001"
    assert primary["tasks"][t2]["display_id"] == "T-002"
    assert not list((tmp_path / ".ultra/audit/index_generations").glob("index-*.json"))


def test_generation_write_failure_remains_visible(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        run_store.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(PermissionError("everything locked")),
    )
    monkeypatch.setattr(run_store.time, "sleep", lambda _delay: None)

    task = "tb_" + "7" * 32
    try:
        ensure_task_index_entry(tmp_path, task, "chat")
    except PermissionError:
        pass
    else:
        raise AssertionError("fallback storage failure must remain visible")

    assert not list((tmp_path / ".ultra/audit").glob(".*.tmp"))
    assert not list((tmp_path / ".ultra/audit/index_generations").glob(".*.tmp"))


def test_summary_only_update_does_not_rewrite_workspace_index(tmp_path: Path):
    task = "tb_" + "8" * 32
    create_run_summary(tmp_path, "ws", "chat", task, "run1")
    before = load_workspace_run_index(tmp_path)["revision"]

    update_run_summary_index(tmp_path, "run1", {"api_requests": 7, "tool_calls": 3})

    after = load_workspace_run_index(tmp_path)["revision"]
    assert after == before
    assert run_store.load_run_summary(tmp_path, "run1")["api_requests"] == 7


def test_new_recorder_has_directory_not_monolith(tmp_path: Path):
    task='tb_'+'a'*32
    AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task,raw_task='raw')
    assert run_component_path(tmp_path,'run','summary.json').is_file()
    assert not (tmp_path/'.ultra/audit/chat/run.json').exists()


def test_event_sources_reflect_record_ownership(tmp_path: Path):
    task='tb_'+'b'*32
    recorder=AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task)
    expected = {
        'planner_diagnostic_response': 'PLANNER',
        'planner_session_message': 'PLANNER',
        'planner_dredd_review_completed': 'DREDD',
        'planner_dredd_review_failed': 'DREDD',
        'stage_status_changed': 'SERVER',
        'persistence_satisfied': 'SERVER',
        'mutation_preflight_rejected': 'SERVER',
        'final_audit_passed': 'DREDD',
        'executor_diagnostic_response': 'EXECUTOR',
    }
    for sequence, event in enumerate(expected, 1):
        recorder._persist_event({'event': event, 'timestamp': sequence})
    recorded = {item['event']: item['source'] for item in list_run_records(tmp_path, 'run')}
    assert recorded == expected
