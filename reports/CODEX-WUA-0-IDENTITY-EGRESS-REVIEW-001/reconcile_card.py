"""One guarded completion of the already staged rotation after WinError 5.
No re-archival, in-place truncation, elevation, attribute/ACL change or blind retry.
Preserves the initial failure and pre-rotation manifest inside the final receipt.
"""
from pathlib import Path
import json
import hashlib
import os

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
CARD=ROOT/'Документация/000_Задачи Codex.md'
def sha(b):return hashlib.sha256(b).hexdigest()

def main():
    receipt=OUT/'card_rotation.json';first=json.loads(receipt.read_text())
    assert first['status']=='CARD ROTATION BLOCKED' and first['error']=='PermissionError'
    assert 'attempt01' not in first,'A recovery was already attempted; stop'
    before=(OUT/'card_before.md').read_bytes();stage=CARD.read_bytes()
    assert sha(before)==first['before_sha256'] and sha(stage)==first['staged_sha256']==first['actual_card_sha256']
    a=before.index('# БЛОК 1'.encode());z=before.index('# БЛОК 2'.encode(),a+1)
    assignment=before[a:z];history=before[z:];prefix=before[:a]
    sa=stage.index('# БЛОК 1'.encode());sz=stage.index('# БЛОК 2'.encode(),sa+1)
    assert stage[:sa]==prefix and stage[sa:sz]==assignment and stage.endswith(history)
    assert '# БЛОК 3'.encode() in stage[sz:]
    pending=OUT/'card_rotation.pending';final=pending.read_bytes()
    nl='\r\n' if b'\r\n' in before else '\n'
    slot='# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'.replace('\n',nl).encode()
    assert final==prefix+slot+stage[sz:] and final.endswith(history)
    old_manifest=json.loads((OUT/'manifest.json').read_text())
    result={**first,'attempt01':first,'manifest_before_rotation':old_manifest,
        'recovery_reason':'Readback proves unchanged staged B2/B3/history and exact prebuilt final candidate; file is not read-only. Single retry of remaining atomic commit only.',
        'desired_final_sha256':sha(final),'recovery_attempts':1}
    try:
        assert CARD.read_bytes()==stage,'External drift; do not commit'
        os.replace(pending,CARD)
        observed=CARD.read_bytes();assert observed==final and observed.endswith(history)
        fa=observed.index('# БЛОК 1'.encode());fz=observed.index('# БЛОК 2'.encode(),fa+1)
        assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in observed[fa:fz] and OUT.name.encode() not in observed[fa:fz]
        result.update(status='CARD ROTATION VERIFIED',final_sha256=sha(observed),
            full_assignment_preserved=True,previous_history_byte_exact=True,b1_waiting=True,
            prefix_rules_byte_exact=True,recovery_result='PASS',
            limitation='Local filesystem recovery; reason for original WinError 5 unestablished; no global editor lock')
    except Exception as exc:
        result.update(status='CARD ROTATION BLOCKED',recovery_result='BLOCKED',recovery_error=type(exc).__name__,recovery_error_text=str(exc))
        raise
    finally:
        receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Preserve the intermediate card hash and refresh only the authorized final readback.
    p=OUT/'integrity.json';integrity=json.loads(p.read_text())
    for row in integrity['files']:
        target=Path(row['path']);target=target if target.is_absolute() else ROOT/target
        actual=sha(target.read_bytes())
        if row['authorized_change']:
            row['staged_readback_sha256']=row['final_sha256'];row['final_sha256']=actual
            assert actual==result['final_sha256']
        else:assert actual==row['sha256']==row['final_sha256']
    p.write_text(json.dumps(integrity,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'final_sha256':result['final_sha256'],
        'history_bytes':len(history),'history_preserved':True,'first_failure_preserved':True,'noncard_unchanged':integrity['unchanged_noncard']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
