import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from audit_storage import AuditThreadRecorder
from gigachat_transport import extract_usage
from run_store import create_run_summary, load_run_summary, record_usage, update_run_summary_index
import verifier_runtime


USAGE={'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,'raw':{}}


def test_extract_and_aggregate_usage(tmp_path: Path):
    usage=extract_usage({'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,'cached':3}})
    assert usage['total_tokens']==120 and usage['raw']['cached']==3
    assert extract_usage({'choices':[]})=={'prompt_tokens':None,'completion_tokens':None,'total_tokens':None,'raw':None}
    task='tb_'+'e'*32
    summary=create_run_summary(tmp_path,'ws','chat',task,'run')
    record_usage(summary,'planner',usage)
    record_usage(summary,'executor',None)
    record_usage(summary,'dredd',{'prompt_tokens':5,'completion_tokens':5,'total_tokens':10})
    update_run_summary_index(tmp_path,'run',summary)
    saved=load_run_summary(tmp_path,'run')
    assert saved['usage']['planner']['total_tokens']==120
    assert saved['usage']['executor']['calls']==1 and saved['usage']['executor']['complete'] is False
    assert saved['usage']['total']['total_tokens']==130
    assert saved['usage']['total']['complete'] is False


def test_recorder_accounts_each_provider_role_and_not_synthetic_dispatch(tmp_path: Path):
    task='tb_'+'f'*32
    recorder=AuditThreadRecorder(tmp_path,'ws','chat','run',task_block_id=task)
    recorder.observe({'event':'planner_diagnostic_response','timestamp':1,'usage':USAGE})
    recorder.observe({'event':'executor_diagnostic_response','timestamp':2,
                      'api_request_number':1,'usage':USAGE})
    recorder.observe({'event':'final_audit_passed','timestamp':3,'usage':USAGE})
    before=load_run_summary(tmp_path,'run')['usage']['total']['calls']
    recorder.observe({'event':'persistence_dispatch','timestamp':4})
    saved=load_run_summary(tmp_path,'run')['usage']
    assert [saved[r]['calls'] for r in ('planner','executor','dredd')]==[1,1,1]
    assert saved['total']['calls']==before==3


def test_verifier_result_preserves_provider_usage(tmp_path: Path):
    content=json.dumps({'result':'PASS','check_type':'FINAL','violations':[],
                        'reason':'ok','required_action':'none'})
    async def run():
        with patch.object(verifier_runtime,'VERIFIER_LOG_ROOT',tmp_path/'logs'), \
             patch.object(verifier_runtime,'_request_gigachat',AsyncMock(return_value=(content,USAGE))):
            return await verifier_runtime.run_verifier_check(
                verifier_model_id=verifier_runtime.DEFAULT_VERIFIER_MODEL_ID,
                check_type='FINAL',raw_task='task',verification_context='evidence')
    result=asyncio.run(run())
    assert result.usage['total_tokens']==120
