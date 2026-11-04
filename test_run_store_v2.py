import json
from pathlib import Path

import run_store
import pytest
import contextlib
import hashlib
import os
import sys
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


def _gate_run(base):
    root = base / 'workspace'
    root.mkdir()
    create_run_summary(root, 'ws_gate', 'chat', 'tb_gate', 'run')
    return root


def _append_gate(root, text='пример'):
    return append_run_record(root, 'run', source='SERVER', event='gate', payload={'text': text}, timestamp=1.0)


def _files(base):
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in base.rglob('*') if p.is_file()}


@pytest.mark.parametrize('relative', ['.ultra/audit', '.ultra/audit/chat', '.ultra/audit/chat/run', '.ultra/audit/index_generations'])
def test_gate_existing_directory_junction_is_refused_without_external_writes(tmp_path, relative):
    if os.name != 'nt':
        pytest.skip('Windows junction oracle')
    import _winapi
    root = _gate_run(tmp_path)
    outside = tmp_path / 'outside'; outside.mkdir()
    (outside/'marker').write_bytes(b'preserve')
    link = root/relative
    if link.exists():
        backup = tmp_path/'original'
        assert link.resolve().is_relative_to(tmp_path.resolve()) and backup.resolve().is_relative_to(tmp_path.resolve())
        link.rename(backup)
    _winapi.CreateJunction(str(outside), str(link))
    before = _files(outside)
    try:
        with pytest.raises(run_store._ultra_core.StorageWriteError):
            _append_gate(root)
        assert _files(outside) == before
    finally:
        os.rmdir(link)


@pytest.mark.parametrize('component', ['index.json', 'summary.json', 'server.jsonl', 'records.idx.jsonl', 'append.pending.json'])
def test_gate_hardlinked_files_are_refused_without_touching_target(tmp_path, component):
    root = _gate_run(tmp_path)
    outside = tmp_path/'outside'; outside.mkdir()
    path = run_store.workspace_index_path(root) if component=='index.json' else root/'.ultra/audit/chat/run'/component
    target = outside/'target'
    target.write_bytes(path.read_bytes() if path.exists() else b'')
    path.unlink(missing_ok=True)
    os.link(target, path)
    before = _files(outside)
    with pytest.raises(run_store._ultra_core.StorageWriteError):
        if component=='summary.json':
            update_run_summary_index(root, 'run', {'run_status':'COMPLETED'})
        else:
            _append_gate(root)
    assert _files(outside) == before


@pytest.mark.parametrize('relative', [False, True])
def test_gate_index_summary_path_cannot_escape_workspace(tmp_path, relative):
    root = _gate_run(tmp_path)
    outside = tmp_path/'outside.json'; outside.write_bytes(b'{"untouched":true}')
    path = run_store.workspace_index_path(root)
    index = json.loads(path.read_bytes())
    index['runs']['run']['summary_path'] = '../../outside.json' if relative else str(outside)
    path.write_text(json.dumps(index), encoding='utf-8')
    with pytest.raises(ValueError, match='locator'):
        update_run_summary_index(root, 'run', {'run_status':'COMPLETED'})
    assert outside.read_bytes() == b'{"untouched":true}'


@pytest.mark.parametrize('partial_index', [False, True])
def test_gate_disk_error_requires_explicit_recovery_preserving_confirmed_prefix(tmp_path, monkeypatch, partial_index):
    root = _gate_run(tmp_path)
    confirmed = _append_gate(root, 'confirmed')
    index_path = run_component_path(root, 'run', 'records.idx.jsonl')
    stream_path = run_component_path(root, 'run', 'server.jsonl')
    before = (index_path.read_bytes(), stream_path.read_bytes())
    original = run_store._append_file
    class Partial:
        def __init__(self, stream): self.stream = stream
        def write(self, data):
            self.stream.write(data[:len(data)//2]); self.stream.flush(); os.fsync(self.stream.fileno())
            raise OSError('injected partial index')
    @contextlib.contextmanager
    def failing(path):
        if path.name=='records.idx.jsonl':
            if not partial_index: raise OSError('injected before index')
            with original(path) as stream: yield Partial(stream)
        else:
            with original(path) as stream: yield stream
    with monkeypatch.context() as scoped:
        scoped.setattr(run_store, '_append_file', failing)
        with pytest.raises(OSError): _append_gate(root, 'unconfirmed')
    with pytest.raises(run_store.RunStoreRecoveryRequired): _append_gate(root, 'do not replay')
    result = run_store.recover_run_records(root, 'run')
    assert result['committed'] is False and result['removed_bytes']['server.jsonl'] > 0
    assert (index_path.read_bytes(), stream_path.read_bytes()) == before
    assert load_run_record(root, 'run', confirmed['record_id'], expected_sha256=confirmed['sha256'])
    assert _append_gate(root, 'after recovery')['sequence'] == 2


@pytest.mark.parametrize('corruption', ['missing_index', 'torn_index', 'bad_checksum'])
def test_gate_unexplained_corruption_is_not_silently_repaired(tmp_path, corruption):
    root = _gate_run(tmp_path); _append_gate(root)
    index_path = run_component_path(root, 'run', 'records.idx.jsonl')
    if corruption=='missing_index': index_path.unlink()
    elif corruption=='torn_index': index_path.write_bytes(index_path.read_bytes()+b'{broken')
    else:
        value=json.loads(index_path.read_bytes()); value['sha256']='0'*64
        index_path.write_text(json.dumps(value)+'\n', encoding='utf-8')
    before = _files(root/'.ultra/audit')
    with pytest.raises(ValueError): run_store.recover_run_records(root, 'run')
    assert _files(root/'.ultra/audit') == before


def test_gate_corrupt_pending_intent_is_not_discarded(tmp_path, monkeypatch):
    root = _gate_run(tmp_path)
    with monkeypatch.context() as scoped:
        @contextlib.contextmanager
        def fail_before_stream(_path):
            raise OSError('before stream'); yield
        scoped.setattr(run_store, '_append_file', fail_before_stream)
        with pytest.raises(OSError): _append_gate(root)
    pending=root/'.ultra/audit/chat/run/append.pending.json'
    data=json.loads(pending.read_bytes()); del data['record']['sha256']
    pending.write_text(json.dumps(data), encoding='utf-8')
    before = _files(root/'.ultra/audit')
    with pytest.raises(ValueError): run_store.recover_run_records(root, 'run')
    assert _files(root/'.ultra/audit') == before


def test_gate_partial_stream_write_is_visible_and_recovery_preserves_prefix(tmp_path, monkeypatch):
    root = _gate_run(tmp_path); receipt = _append_gate(root, 'confirmed')
    stream_path = run_component_path(root, 'run', 'server.jsonl')
    index_path = run_component_path(root, 'run', 'records.idx.jsonl')
    before = (stream_path.read_bytes(), index_path.read_bytes())
    original = run_store._append_file
    @contextlib.contextmanager
    def partial(path):
        with original(path) as stream:
            if path.name == 'server.jsonl':
                class ShortWrite:
                    def tell(self): return stream.tell()
                    def write(self, data):
                        size = stream.write(data[:len(data)//2])
                        stream.flush(); os.fsync(stream.fileno())
                        return size
                yield ShortWrite()
            else:
                yield stream
    with monkeypatch.context() as scoped:
        scoped.setattr(run_store, '_append_file', partial)
        with pytest.raises(OSError, match='Partial'): _append_gate(root, 'incomplete')
    with pytest.raises(run_store.RunStoreRecoveryRequired): _append_gate(root, 'no replay')
    result = run_store.recover_run_records(root, 'run')
    assert result['committed'] is False and result['removed_bytes']['server.jsonl'] > 0
    assert (stream_path.read_bytes(), index_path.read_bytes()) == before
    assert load_run_record(root, 'run', receipt['record_id'], expected_sha256=receipt['sha256'])
    assert _append_gate(root)['sequence'] == 2


@pytest.mark.parametrize('corruption', ['changed_prefix', 'extra_index', 'foreign_stream', 'bad_tail_hash'])
def test_gate_pending_recovery_refuses_unexplained_changes_without_mutation(tmp_path, monkeypatch, corruption):
    root = _gate_run(tmp_path); _append_gate(root, 'confirmed')
    original = run_store._append_file
    @contextlib.contextmanager
    def before_index(path):
        if path.name == 'records.idx.jsonl': raise OSError('injected before index')
        with original(path) as stream: yield stream
    with monkeypatch.context() as scoped:
        scoped.setattr(run_store, '_append_file', before_index)
        with pytest.raises(OSError): _append_gate(root, 'pending')
    index_path = run_component_path(root, 'run', 'records.idx.jsonl')
    if corruption == 'changed_prefix':
        index_path.write_bytes(index_path.read_bytes().replace(b'gate', b'GATE', 1))
    elif corruption == 'extra_index':
        with index_path.open('ab') as stream: stream.write(b'not the planned receipt\n')
    elif corruption == 'foreign_stream':
        run_component_path(root, 'run', 'executor.jsonl').write_bytes(b'foreign\n')
    else:
        path = run_component_path(root, 'run', 'server.jsonl')
        data = path.read_bytes(); path.write_bytes(data[:-2] + b'x\n')
    before = _files(root/'.ultra/audit')
    with pytest.raises(ValueError): run_store.recover_run_records(root, 'run')
    assert _files(root/'.ultra/audit') == before


@pytest.mark.parametrize('phase', ['after_intent', 'after_stream', 'after_index'])
def test_gate_process_crash_recovery_never_loses_confirmed_records(tmp_path, phase):
    root = _gate_run(tmp_path); first = _append_gate(root, 'first')
    code = r'''
import sys,os,contextlib
sys.path.insert(0,sys.argv[1]); import run_store as rs
if sys.argv[3]=='after_index':
    rs._clear_pending=lambda p:os._exit(91)
else:
    original=rs._append_file
    @contextlib.contextmanager
    def stop(path):
        if sys.argv[3]=='after_intent': os._exit(93)
        if path.name=='records.idx.jsonl': os._exit(92)
        with original(path) as stream: yield stream
    rs._append_file=stop
rs.append_run_record(sys.argv[2],'run',source='SERVER',event='crash',payload={'synthetic':True},timestamp=2)
'''
    result=_subprocess.run([sys.executable,'-B','-c',code,str(Path(__file__).resolve().parent),str(root),phase],capture_output=True,timeout=30)
    assert result.returncode=={'after_index':91,'after_stream':92,'after_intent':93}[phase], result.stderr
    recovered=run_store.recover_run_records(root, 'run')
    assert recovered['committed'] is (phase=='after_index')
    assert load_run_record(root,'run',first['record_id'],expected_sha256=first['sha256'])
    records=list_run_records(root,'run')
    assert len(records)==(2 if phase=='after_index' else 1)
    assert _append_gate(root,'next')['sequence']==len(records)+1


def test_gate_append_lock_timeout_is_visible_and_does_not_write(tmp_path, monkeypatch):
    root = _gate_run(tmp_path)
    ready=tmp_path/'ready'; release=tmp_path/'release'
    code=r'''
import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]); import run_store as rs
with rs._index_lock(sys.argv[2]):
    Path(sys.argv[3]).write_text('ready')
    deadline=time.monotonic()+10
    while not Path(sys.argv[4]).exists():
        if time.monotonic()>deadline: raise RuntimeError('bounded timeout')
        time.sleep(.01)
'''
    child=_subprocess.Popen([sys.executable,'-B','-c',code,str(Path(__file__).resolve().parent),str(root),str(ready),str(release)])
    try:
        deadline=_time.monotonic()+5
        while not ready.exists():
            assert child.poll() is None and _time.monotonic()<deadline
            _time.sleep(.01)
        before=_files(root/'.ultra/audit')
        monkeypatch.setattr(run_store._ultra_core,'WRITER_LOCK_TIMEOUT_SECONDS',.05)
        with pytest.raises(run_store._ultra_core.WorkspaceBusyError): _append_gate(root)
        assert _files(root/'.ultra/audit')==before
    finally:
        release.write_text('go')
        try: child.wait(timeout=10)
        finally:
            if child.poll() is None: child.kill(); child.wait(timeout=10)
    assert child.returncode==0


def test_gate_generation_hardlink_is_refused(tmp_path):
    root=_gate_run(tmp_path)
    outside=tmp_path/'outside.json'; outside.write_bytes(run_store.workspace_index_path(root).read_bytes())
    folder=root/'.ultra/audit/index_generations'; folder.mkdir()
    os.link(outside,folder/('index-'+('1'*20)+'-'+('a'*32)+'.json'))
    before=outside.read_bytes()
    with pytest.raises(run_store._ultra_core.StorageWriteError):
        ensure_task_index_entry(root,'tb_other','chat')
    assert outside.read_bytes()==before


def test_gate_concurrent_run_offsets_hashes_and_restart(tmp_path):
    root = _gate_run(tmp_path)
    code = r'''
import sys,json
sys.path.insert(0,sys.argv[1]); import run_store as rs
for i in range(12):
    rs.append_run_record(sys.argv[2],'run',source=['SERVER','EXECUTOR','PLANNER'][int(sys.argv[3])],event='parallel',payload={'i':i,'writer':sys.argv[3],'text':'ёж 😀'},timestamp=i)
print('done')
'''
    children=[_subprocess.Popen([sys.executable,'-B','-c',code,str(Path(__file__).resolve().parent),str(root),str(n)],stdout=_subprocess.PIPE,stderr=_subprocess.PIPE) for n in range(3)]
    try:
        for child in children:
            out,err=child.communicate(timeout=60); assert child.returncode==0, err
    finally:
        for child in children:
            if child.poll() is None: child.kill()
            child.communicate(timeout=20)
    records=list_run_records(root,'run')
    assert [r['sequence'] for r in records]==list(range(1,37))
    ends={name:0 for name in run_store.STREAM_BY_SOURCE.values()}
    for receipt in records:
        assert receipt['offset']==ends[receipt['stream']]
        ends[receipt['stream']]+=receipt['length']
        assert load_run_record(root,'run',receipt['record_id'],expected_sha256=receipt['sha256'])
    assert run_store.recover_run_records(root,'run')=={'removed_bytes':{},'committed':False}


@pytest.mark.parametrize('large_payload', [False, True])
def test_gate_append_refuses_projected_read_limit_before_any_write(tmp_path, monkeypatch, large_payload):
    root = _gate_run(tmp_path)
    monkeypatch.setattr(run_store, '_MAX_AUDIT_BYTES', 8192)
    text = 'x' * 9000 if large_payload else 'small'
    for _ in range(80):
        before = _files(root/'.ultra/audit')
        try:
            _append_gate(root, text)
        except ValueError as exc:
            assert 'limit' in str(exc).lower()
            assert _files(root/'.ultra/audit') == before
            assert run_store.recover_run_records(root,'run') == {'removed_bytes':{},'committed':False}
            break
    else:
        pytest.fail('projected index or stream limit was not enforced')


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


# --- P9 (CLAUDE-WUA-CHAT-RUNSTORE-P9-001): concurrent writers of the Run Store v2 index -------------------------------
# Real child processes released together by a file barrier; the oracle reads the index files with plain json (canonical
# index.json and index_generations/*.json, highest revision wins) instead of run_store's own loader where it matters.

import hashlib as _hashlib
import os as _os
import subprocess as _subprocess
import sys as _sys
import threading as _threading
import time as _time

import context_storage as _core

_REPO = Path(run_store.__file__).resolve().parent
_CHILD = r"""
import json, sys, time
from pathlib import Path
repo, root, prefix, count, ready, go, mode = sys.argv[1:8]
sys.path.insert(0, repo)
import run_store
Path(ready).write_text("1")
while not Path(go).exists():
    time.sleep(0.001)
returned, errors = {}, []
for k in range(int(count)):
    task = "tb_" + ("%032d" % k if mode == "same" else (prefix + "%031d" % k)[-32:])
    try:
        if mode in ("new", "same"):
            returned[task] = run_store.ensure_task_index_entry(root, task, "chat")["display_id"]
            if mode == "new":
                run = "run_%s_%03d" % (prefix, k)
                returned[run] = run_store.ensure_run_index_entry(root, run, task, "chat")["display_id"]
        else:
            run_store.update_run_summary_index(root, "run_%s_%03d" % (prefix, k), {"run_status": "DONE_" + prefix})
    except Exception as exc:
        errors.append(type(exc).__name__)
print(json.dumps({"returned": returned, "errors": errors}))
"""


def _raw_index(root: Path) -> dict:
    audit = root / ".ultra" / "audit"
    found = []
    if (audit / "index.json").is_file():
        value = json.loads((audit / "index.json").read_text(encoding="utf-8"))
        found.append((value["revision"], 1, value))
    for path in sorted((audit / "index_generations").glob("index-*.json")) if (audit / "index_generations").is_dir() else []:
        value = json.loads(path.read_text(encoding="utf-8"))
        found.append((value["revision"], 0, value))
    return max(found, key=lambda item: (item[0], item[1]))[2]


def _together(root: Path, prefixes, count, mode, *, hold_index=False):
    base = root.parent
    go = base / "go"
    children = [_subprocess.Popen([_sys.executable, "-B", "-c", _CHILD, str(_REPO), str(root), p, str(count),
                                   str(base / f"ready_{p}"), str(go), mode],
                                  stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, text=True, encoding="utf-8")
                for p in prefixes]
    try:
        for p in prefixes:
            deadline = _time.monotonic() + 60
            while not (base / f"ready_{p}").exists():
                assert _time.monotonic() < deadline, "a child did not start"
                _time.sleep(0.01)
        holder = open(run_store.workspace_index_path(root), "rb") if hold_index else None
        go.write_text("1")
        answers = []
        try:
            for child in children:
                out, err = child.communicate(timeout=300)
                assert child.returncode == 0, err[-600:]
                answers.append(json.loads(out.strip().splitlines()[-1]))
        finally:
            if holder is not None:
                holder.close()
        return answers
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=30)


def _numbers(display_ids):
    return sorted(int(d.split("-")[1]) for d in display_ids)


def test_p9_concurrent_processes_create_tasks_and_runs_without_lost_updates(tmp_path: Path):
    root = tmp_path / "w"
    root.mkdir()
    for prefixes, count in ((["a", "b"], 25), (["c", "d", "e", "f"], 8)):
        before = len(_raw_index(root)["tasks"]) if run_store.workspace_index_path(root).is_file() else 0
        answers = _together(root, prefixes, count, "new")
        assert all(a["errors"] == [] for a in answers)
        index = _raw_index(root)
        added = len(prefixes) * count
        assert len(index["tasks"]) == before + added and len(index["runs"]) == before + added, "an entry was lost"
        assert _numbers(t["display_id"] for t in index["tasks"].values()) == list(range(1, before + added + 1))
        assert _numbers(r["display_id"] for r in index["runs"].values()) == list(range(1, before + added + 1))
        assert index["next_task_number"] == index["next_run_number"] == before + added + 1
        for run in index["runs"].values():
            assert run["run_id"] in index["tasks"][run["task_block_id"]]["runs"]
        handed = [(key, display) for a in answers for key, display in a["returned"].items()]
        final = {**{k: v["display_id"] for k, v in index["tasks"].items()}, **{k: v["display_id"] for k, v in index["runs"].items()}}
        assert all(final[key] == display for key, display in handed), "a caller was given a number that is not stored"
    assert index["revision"] == 2 * len(index["tasks"]), "one confirmed revision per new task and per new run"
    assert not (root / ".ultra/audit/index_generations").exists()
    assert not list((root / ".ultra/audit").glob(".*.tmp"))


def test_p9_repeat_registration_from_two_processes_creates_one_entry(tmp_path: Path):
    root = tmp_path / "w"
    root.mkdir()
    answers = _together(root, ["a", "b"], 15, "same")
    index = _raw_index(root)
    assert len(index["tasks"]) == 15 and index["next_task_number"] == 16
    assert answers[0]["returned"] == answers[1]["returned"], "both callers must get the same number for the same task"
    assert _numbers(t["display_id"] for t in index["tasks"].values()) == list(range(1, 16))


def test_p9_identity_conflicts_are_refused_without_any_write(tmp_path: Path):
    task, other = "tb_" + "1" * 32, "tb_" + "2" * 32
    create_run_summary(tmp_path, "ws", "chat", task, "run1")
    ensure_task_index_entry(tmp_path, other, "chat")
    canonical = run_store.workspace_index_path(tmp_path)
    before = canonical.read_bytes()
    for call in (lambda: ensure_task_index_entry(tmp_path, task, "other_chat"),
                 lambda: ensure_run_index_entry(tmp_path, "run1", other, "chat"),
                 lambda: ensure_run_index_entry(tmp_path, "run1", task, "other_chat")):
        try:
            call()
        except ValueError:
            pass
        else:
            raise AssertionError("a conflicting identity was accepted")
    assert canonical.read_bytes() == before
    assert ensure_run_index_entry(tmp_path, "run1", task, "chat")["display_id"] == "R-001"
    assert canonical.read_bytes() == before, "a repeated registration writes nothing"


def test_p9_nested_calls_reenter_and_another_thread_waits(tmp_path: Path):
    task = "tb_" + "3" * 32
    started = _time.monotonic()
    create_run_summary(tmp_path, "ws", "chat", task, "run1")  # create -> ensure_run -> ensure_task, one lock
    assert _time.monotonic() - started < 5, "a nested call waited for its own lock"
    anchor = _core._write_anchor(tmp_path.resolve())
    results = []
    with _core._workspace_writer_lock(anchor):
        worker = _threading.Thread(target=lambda: results.append(
            ensure_task_index_entry(tmp_path, "tb_" + "4" * 32, "chat")["display_id"]))
        worker.start()
        _time.sleep(0.3)
        assert results == [], "another thread wrote the index while the lock was held"
    worker.join(15)
    assert results == ["T-002"]
    assert _core._held_writer_locks() == {}


def test_p9_a_held_workspace_lock_is_a_bounded_visible_refusal(tmp_path: Path, monkeypatch):
    task = "tb_" + "5" * 32
    ensure_task_index_entry(tmp_path, task, "chat")
    canonical = run_store.workspace_index_path(tmp_path)
    before = canonical.read_bytes()
    held = tmp_path / "held"
    hold = ("import sys, time\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport context_storage as cs\n"
            "with cs._workspace_writer_lock(cs._write_anchor(Path(sys.argv[2]).resolve())):\n"
            "    open(sys.argv[3], 'w').close()\n    time.sleep(60)\n")
    holder = _subprocess.Popen([_sys.executable, "-B", "-c", hold, str(_REPO), str(tmp_path), str(held)])
    try:
        deadline = _time.monotonic() + 60
        while not held.exists():
            assert _time.monotonic() < deadline
            _time.sleep(0.01)
        monkeypatch.setattr(_core, "WRITER_LOCK_TIMEOUT_SECONDS", 0.4)
        for call in (lambda: ensure_task_index_entry(tmp_path, "tb_" + "6" * 32, "chat"),
                     lambda: create_run_summary(tmp_path, "ws", "chat", task, "run1")):
            started = _time.monotonic()
            try:
                call()
            except _core.WorkspaceBusyError as exc:
                assert exc.code == "workspace_busy"
            else:
                raise AssertionError("a busy Workspace must be refused visibly")
            assert 0.35 <= _time.monotonic() - started < 10, "the wait must be bounded"
        assert canonical.read_bytes() == before
    finally:
        holder.kill()
        holder.communicate(timeout=30)
    monkeypatch.setattr(_core, "WRITER_LOCK_TIMEOUT_SECONDS", 5)
    assert ensure_task_index_entry(tmp_path, "tb_" + "6" * 32, "chat")["display_id"] == "T-002", "after the holder died"


def test_p9_a_process_dying_at_publication_leaves_no_unconfirmed_success(tmp_path: Path):
    canonical = run_store.workspace_index_path(tmp_path)
    ensure_task_index_entry(tmp_path, "tb_" + "7" * 32, "chat")
    die = ("import os, sys\nsys.path.insert(0, sys.argv[1])\nimport run_store\nreal = os.replace\n"
           "def die(*a, **k):\n    if sys.argv[3] == 'after':\n        real(*a, **k)\n    os._exit(17)\n"
           "os.replace = die\nrun_store.ensure_run_index_entry(sys.argv[2], 'run_x', 'tb_' + '8' * 32, 'chat')\n")
    before = canonical.read_bytes()
    child = _subprocess.run([_sys.executable, "-B", "-c", die, str(_REPO), str(tmp_path), "before"], capture_output=True)
    assert child.returncode == 17
    assert canonical.read_bytes() == before, "nothing unconfirmed was published"
    child = _subprocess.run([_sys.executable, "-B", "-c", die, str(_REPO), str(tmp_path), "after"], capture_output=True)
    assert child.returncode == 17
    first = load_workspace_run_index(tmp_path)
    assert first["tasks"]["tb_" + "8" * 32]["display_id"] == "T-002", "the task step was published before the death"
    assert "run_x" not in first["runs"]
    entry = ensure_run_index_entry(tmp_path, "run_x", "tb_" + "8" * 32, "chat")  # the repeat after a restart
    again = load_workspace_run_index(tmp_path)
    assert (entry["display_id"], again["tasks"]["tb_" + "8" * 32]["display_id"], again["next_task_number"]) == ("R-001", "T-002", 3)


def test_p9_writers_with_a_held_index_use_generations_then_recover_the_canonical_index(tmp_path: Path):
    root = tmp_path / "w"
    root.mkdir()
    ensure_task_index_entry(root, "tb_" + "f" * 32, "chat")
    answers = _together(root, ["a", "b"], 8, "new", hold_index=True)
    assert all(a["errors"] == [] for a in answers)
    generations = sorted((root / ".ultra/audit/index_generations").glob("index-*.json"))
    revisions = [json.loads(p.read_text(encoding="utf-8"))["revision"] for p in generations]
    assert len(revisions) == len(set(revisions)) == 32, "every fallback write got its own revision"
    index = _raw_index(root)
    assert len(index["tasks"]) == 17 and len(index["runs"]) == 16
    ensure_task_index_entry(root, "tb_" + "e" * 32, "chat")  # the index is free again: canonical recovers
    canonical = json.loads(run_store.workspace_index_path(root).read_text(encoding="utf-8"))
    assert canonical["revision"] == max(revisions) + 1 and len(canonical["tasks"]) == 18
    assert not list((root / ".ultra/audit/index_generations").glob("index-*.json")), "generations compacted"


def test_p9_status_updates_from_two_processes_are_all_kept(tmp_path: Path):
    root = tmp_path / "w"
    root.mkdir()
    for prefix in ("a", "b"):
        for k in range(12):
            create_run_summary(root, "ws", "chat", "tb_" + (prefix + "%031d" % k)[-32:], "run_%s_%03d" % (prefix, k))
    _together(root, ["a", "b"], 12, "status")
    runs = _raw_index(root)["runs"]
    assert sorted(r["run_status"] for r in runs.values()) == ["DONE_a"] * 12 + ["DONE_b"] * 12


def test_p9_the_index_is_never_published_outside_the_lock(tmp_path: Path):
    ensure_task_index_entry(tmp_path, "tb_" + "9" * 32, "chat")
    index = load_workspace_run_index(tmp_path)
    before = run_store.workspace_index_path(tmp_path).read_bytes()
    try:
        run_store._save_index(tmp_path, index)
    except RuntimeError as exc:
        assert "lock" in str(exc)
    else:
        raise AssertionError("an index publication without the lock must be refused")
    assert run_store.workspace_index_path(tmp_path).read_bytes() == before


def test_p9_a_junction_at_ultra_is_refused_and_the_target_untouched(tmp_path: Path):
    import _winapi
    outside = tmp_path / "outside"
    (outside / ".ultra_target").mkdir(parents=True)
    root = tmp_path / "w"
    root.mkdir()
    _winapi.CreateJunction(str(outside / ".ultra_target"), str(root / ".ultra"))
    try:
        before = sorted(p.name for p in (outside / ".ultra_target").rglob("*"))
        try:
            ensure_task_index_entry(root, "tb_" + "a" * 32, "chat")
        except _core.StorageWriteError as exc:
            assert exc.code == "unsafe_storage_link"
        else:
            raise AssertionError("a junction at .ultra must be refused")
        assert sorted(p.name for p in (outside / ".ultra_target").rglob("*")) == before
    finally:
        _os.rmdir(root / ".ultra")


def test_p9_a_damaged_index_is_a_visible_error_and_is_not_overwritten(tmp_path: Path):
    ensure_task_index_entry(tmp_path, "tb_" + "b" * 32, "chat")
    canonical = run_store.workspace_index_path(tmp_path)
    for payload in (b"{", b"[]", json.dumps({"schema_version": 3, "tasks": {}, "runs": {}}).encode()):
        canonical.write_bytes(payload)
        try:
            ensure_task_index_entry(tmp_path, "tb_" + "c" * 32, "chat")
        except ValueError:  # json.JSONDecodeError is a ValueError
            pass
        else:
            raise AssertionError("a damaged index must not be replaced by a fresh one")
        assert canonical.read_bytes() == payload


def test_p9_a_reader_tolerates_a_generation_compacted_while_it_reads(tmp_path: Path, monkeypatch):
    real_replace = run_store.os.replace
    canonical = run_store.workspace_index_path(tmp_path).resolve()
    locked = {"value": True}

    def sometimes_locked(source, destination):
        if locked["value"] and Path(destination).resolve() == canonical:
            raise PermissionError("held by a reader")
        return real_replace(source, destination)
    monkeypatch.setattr(run_store.os, "replace", sometimes_locked)
    monkeypatch.setattr(run_store.time, "sleep", lambda _delay: None)
    ensure_task_index_entry(tmp_path, "tb_" + "d" * 32, "chat")  # canonical held: written as a generation
    generations = list((tmp_path / ".ultra/audit/index_generations").glob("index-*.json"))
    assert len(generations) == 1
    real_load = run_store._load_index_file

    def compacted_meanwhile(path):
        if path.parent.name == "index_generations":  # a writer published the canonical index and removed it
            raise FileNotFoundError(path)
        return real_load(path)
    monkeypatch.setattr(run_store, "_load_index_file", compacted_meanwhile)
    index = load_workspace_run_index(tmp_path)  # a lock-free reader: older but whole, never a crash
    assert index["revision"] == 0 and index["tasks"] == {}
