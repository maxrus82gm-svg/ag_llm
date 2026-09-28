from pathlib import Path
from audit_storage import AuditThreadRecorder
from run_store import load_stream_records, reconstruct_executor_context, run_component_path


def event(n,messages,stage='s1'):
    return {'event':'executor_diagnostic_context','timestamp':n,'api_request_number':n,
      'stage_id':stage,'model_id':'m','provider_model_id':'p','messages':messages}


def test_executor_base_delta_and_reconstruction(tmp_path: Path):
    task='tb_'+'c'*32
    r=AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task)
    first=[{'role':'system','content':'GLOBAL BASE'},{'role':'user','content':'one'}]
    second=first+[{'role':'assistant','content':'two'}]
    reset=[first[0],{'role':'user','content':'new stage'}]
    r.observe(event(1,first)); r.observe(event(2,second)); r.observe(event(3,reset,'s2'))
    assert reconstruct_executor_context(tmp_path,'run',1)==first
    assert reconstruct_executor_context(tmp_path,'run',2)==second
    assert reconstruct_executor_context(tmp_path,'run',3)==reset
    records=load_stream_records(tmp_path,'run','EXECUTOR')
    assert 'context_base' in records[0]['payload'] and 'messages' not in records[0]['payload']
    assert records[1]['payload']['context_delta']['added_messages']==[second[-1]]
    assert records[2]['payload']['context_delta']['removed_suffix_count']==2
    assert run_component_path(tmp_path,'run','executor.jsonl').read_text(encoding='utf-8').count('GLOBAL BASE')==0
