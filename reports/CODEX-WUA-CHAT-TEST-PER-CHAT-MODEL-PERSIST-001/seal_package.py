"""Verify backup/source scope, results and registered report; no Git/imports."""
from pathlib import Path
import ast,hashlib,json

PKG=Path(__file__).resolve().parent;ROOT=PKG.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

if __name__=='__main__':
    before=json.loads((PKG/'preservation.json').read_text(encoding='utf-8'))
    backup=Path(before['backup'])
    copies={n:sha(backup/n)==v for n,v in before['before'].items()}
    protected={n:sha(ROOT/n)==v for n,v in before['protected'].items()}
    assert all(copies.values()) and all(protected.values())
    card='Документация/000_Задачи Codex.md'
    tail=lambda p:Path(p).read_bytes().split(b'TASK-SLOT:BLOCK-1.1:END',1)[1]
    assert tail(ROOT/card)==tail(backup/card)
    tree=ast.parse((ROOT/'test_rt002_s2_budget_policy.py').read_text(encoding='utf-8'))
    gates=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='OFFLINE_ADMISSION_GATES' for t in n.targets)))
    pin=hashlib.sha256(ast.dump(ast.parse((ROOT/'web_alarm/ultra_chat.py').read_text(encoding='utf-8')),
        include_attributes=False).encode('utf-8')).hexdigest()
    assert gates['web_alarm.ultra_chat']==pin
    attempts={p.name:json.loads(p.read_text(encoding='utf-8')) for p in (PKG/'evidence').glob('*.result.json')}
    for stage in ('regression_final','final_new_tests','ui_reviewed_final','s1_final','s2_final','quality_final','profile_entry_final'):
        r=attempts[stage+'.result.json'];assert r['exit_code']==0 and not r.get('unexpected_guard_denials',0),stage
    assert attempts['baseline_reviewed_final.result.json']['exit_code']==1
    assert attempts['baseline_reviewed_final.result.json']['counts']['fail']==2
    assert sha(PKG/'before_ui.py.txt')==before['before']['web_alarm/ui.py']
    history=None
    if (PKG/'task_record.json').exists():
        history=json.loads((PKG/'task_record.json').read_text(encoding='utf-8'))
        for ref in history['sources'].values():assert sha(ROOT/ref['path'])==ref['sha256']
    sources={n:dict(before=v,after=sha(ROOT/n),changed=sha(ROOT/n)!=v) for n,v in before['before'].items()}
    sources['test_web_alarm_test_model_persist.py']=dict(before=None,after=sha(ROOT/'test_web_alarm_test_model_persist.py'),changed=True)
    result=dict(task_id=PKG.name,status='AUTHOR RESULT READY / TECHNICAL PASS OFFLINE / REVIEW PENDING',
        history_id=history['history_id'] if history else None,user_ux='PENDING',
        physical_gui='NOT RUN',independent_ci='NOT RUN',real='HOLD / NOT RUN',git='NOT RUN',
        backup=str(backup),backup_verified=copies,protected_unchanged=protected,
        blocks_2_to_4_unchanged=True,base_source_matches=before['base_match'],sources=sources,
        attempts=attempts,original_failures_retained=True,
        artifacts={p.relative_to(PKG).as_posix():sha(p) for p in sorted(PKG.rglob('*'))
                   if p.is_file() and p.name!='manifest.json'})
    (PKG/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(task_id=PKG.name,history_id=result['history_id'],backup=len(copies),
        protected=len(protected),artifacts=len(result['artifacts']),status=result['status'])))
