import json
from pathlib import Path

from audit_storage import AuditThreadRecorder
from run_store import (
    append_run_record, create_run_summary, ensure_run_index_entry,
    ensure_task_index_entry, get_run_index_entry, get_task_index_entry,
    list_run_records, load_run_record, load_workspace_run_index, run_component_path,
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


def test_new_recorder_has_directory_not_monolith(tmp_path: Path):
    task='tb_'+'a'*32
    AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task,raw_task='raw')
    assert run_component_path(tmp_path,'run','summary.json').is_file()
    assert not (tmp_path/'.ultra/audit/chat/run.json').exists()
