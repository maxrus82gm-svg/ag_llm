"""Read-only artifact validator. Does not execute collection/rotation/client scripts."""
from pathlib import Path
import hashlib
import json
import ast
from collections import Counter

OUT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()

def validate():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    expected={x['path']:x for x in manifest['files']}
    actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'}
    assert set(expected)==actual, {'missing':sorted(set(expected)-actual),'extra':sorted(actual-set(expected))}
    for name,row in expected.items():
        rel=Path(name)
        assert not rel.is_absolute() and '..' not in rel.parts
        p=OUT/rel;assert p.resolve().is_relative_to(OUT.resolve()) and not p.is_symlink()
        data=p.read_bytes()
        assert len(data)==row['bytes'] and sha(data)==row['sha256'],name
        if p.suffix=='.json':json.loads(data.decode('utf-8-sig'))
        if p.suffix=='.py':ast.parse(data.decode('utf-8-sig'),filename=name)
    checks=json.loads((OUT/'checks.json').read_text())
    counts=dict(Counter(x['status'] for x in checks['checks']))
    assert counts==checks['counts']
    rotation=json.loads((OUT/'card_rotation.json').read_text())
    assert sha((OUT/'card_before.md').read_bytes())==rotation['before_sha256']
    decision=json.loads((OUT/'preflight_decision.json').read_text())
    assert not decision['may_create_or_modify_vm'] and not decision['may_execute_native_client']
    assert decision['native_cases_executed']==0
    return {'artifact_hashes_verified':len(expected),'total_files_including_manifest':len(expected)+1,
            'checks_counts':counts,'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),
            'report_sha256':sha((OUT/'report.md').read_bytes()),
            'result':'PASS — PACKAGE INTEGRITY ONLY; NOT OS/NATIVE/INDEPENDENT ACCEPTANCE'}

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False,indent=2))
