"""Readback/hash the author package, without Git or importing application code."""
from pathlib import Path
import ast
import hashlib
import json

PKG=Path(__file__).resolve().parent
ROOT=PKG.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

if __name__=='__main__':
    saved=json.loads((PKG/'preservation.json').read_text(encoding='utf-8'))
    backup=Path(saved['backup'])
    backup_ok={n:sha(backup/n)==v for n,v in saved['before'].items()}
    protected={n:sha(ROOT/n)==v for n,v in saved['protected'].items()}
    assert all(backup_ok.values()) and all(protected.values())
    card='Документация/000_Задачи Codex.md'
    tail=lambda p:Path(p).read_bytes().split(b'TASK-SLOT:BLOCK-1.1:END',1)[1]
    assert tail(ROOT/card)==tail(backup/card), 'Blocks 2–4 changed'
    source={n:{'before':v,'after':sha(ROOT/n),'changed':sha(ROOT/n)!=v} for n,v in saved['before'].items()}
    source.update({n:{'before':None,'after':sha(ROOT/n),'changed':True} for n in (
        'web_alarm/ordinary_provider.py','test_web_alarm_ordinary_application.py')})
    gates=ast.literal_eval(next(n.value for n in ast.parse((ROOT/'test_rt002_s2_budget_policy.py').read_text(encoding='utf-8')).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OFFLINE_ADMISSION_GATES' for t in n.targets)))
    pin=hashlib.sha256(ast.dump(ast.parse((ROOT/'web_alarm/ordinary_provider.py').read_text(encoding='utf-8')),
        include_attributes=False).encode('utf-8')).hexdigest()
    assert gates['web_alarm.ordinary_provider']==pin
    attempts={p.name:json.loads(p.read_text(encoding='utf-8')) for p in (PKG/'evidence').glob('*.result.json')}
    for stage in ('core_reviewed','legacy_final','s1_final','s2_reviewed','quality_reviewed','ui_final',
                  'mutations_final','server_final','http_expectations_final','cancel_review','application_storage_final'):
        assert attempts[stage+'.result.json']['exit_code']==0,stage
    history=None
    if (PKG/'task_record.json').exists():
        history=json.loads((PKG/'task_record.json').read_text(encoding='utf-8'))
        for ref in history['sources'].values():
            assert sha(ROOT/ref['path'])==ref['sha256']
    report=(PKG/'report.md').read_text(encoding='utf-8')
    assert 'CORE_RESULT' not in report and '**PARTIAL**' in report
    result=dict(task_id=PKG.name,status='AUTHOR RESULT READY / PARTIAL',
        history_id=history['history_id'] if history else None,
        technical='NOT READY',provider_contract='PARTIAL',real_factory='BLOCKED',
        real_application_offline='PASS / SYNTHETIC ONLY',live='NOT RUN',user_ux='PENDING',release='HOLD',
        remote_main='NOT VERIFIED / no Git authority',backup=str(backup),backup_verified=backup_ok,
        protected_unchanged=protected,blocks_2_to_4_unchanged=True,sources=source,
        attempts=attempts,failed_attempts_retained=True,
        artifacts={p.relative_to(PKG).as_posix():sha(p) for p in sorted(PKG.rglob('*'))
                   if p.is_file() and p.name!='manifest.json'})
    (PKG/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(task_id=PKG.name,history_id=result['history_id'],backup_files=len(backup_ok),
        protected_files=len(protected),artifacts=len(result['artifacts']),status=result['status'])))
