import json
from pathlib import Path
from audit_storage import AuditThreadRecorder, load_audit_thread, list_chat_audit_summaries
from run_store import audit_exists


def test_legacy_read_and_lightweight_lookup(tmp_path: Path, monkeypatch):
    path=tmp_path/'.ultra/audit/chat/legacy.json'; path.parent.mkdir(parents=True)
    data={'workspace_id':'ws','chat_id':'chat','run_id':'legacy','task_block_id':None,
          'issues':[],'final_audit':'PASS','run_status':'SUCCESS'}
    path.write_text(json.dumps(data),encoding='utf-8')
    assert audit_exists(tmp_path,'chat','legacy')
    assert list_chat_audit_summaries(tmp_path,'ws','chat')==[]
    assert load_audit_thread(tmp_path,'ws','chat','legacy')['run_id']=='legacy'
    assert path.is_file()


def test_v2_compatibility_is_explicit(tmp_path: Path):
    task='tb_'+'d'*32
    recorder=AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task)
    recorder.observe({'event':'run_started','timestamp':1,'task_block_id':task})
    assert load_audit_thread(tmp_path,'ws','chat','run')['task_block_id']==task
    assert not (tmp_path/'.ultra/audit/chat/run.json').exists()
