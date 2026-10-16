"""Exact candidate-only rollback. Dry run by default; refuses any later drift."""
import argparse,hashlib,json,os
from pathlib import Path
import shutil,tempfile
D=Path(__file__).resolve().parent;candidate=D.parent/'plugin'
parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
before=json.loads((D/'baseline.json').read_bytes())['candidate_before']
expected=json.loads((D/'candidate_manifest.json').read_bytes())['files']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
current={p.relative_to(candidate).as_posix():sha(p) for p in sorted(candidate.rglob('*')) if p.is_file()}
assert current==expected,'Candidate changed after verification; refuse rollback'
snapshot=D/'rollback/plugin'
assert all(sha(snapshot/n)==h for n,h in before.items())
added=set(expected)-set(before)
assert all(n.startswith('runtime/') for n in added),'Unexpected added path'
target=(candidate/'runtime').resolve()
assert target.parent==candidate.resolve() and target.name=='runtime'
assert not (candidate/'runtime').is_symlink()
if not args.apply:
    print(json.dumps({'rollback_ready':True,'mutated':False,'restore_changed_files':[n for n in before if before[n]!=expected[n]],'remove_only_added_runtime_files':len(added)}));raise SystemExit(0)
for name in before:
    if before[name]==expected[name]:continue
    fd,path=tempfile.mkstemp(prefix='restore-',dir=D)
    with os.fdopen(fd,'wb') as f:f.write((snapshot/name).read_bytes());f.flush();os.fsync(f.fileno())
    os.replace(path,candidate/name)
shutil.rmtree(target)
assert {p.relative_to(candidate).as_posix():sha(p) for p in candidate.rglob('*') if p.is_file()}==before
print(json.dumps({'restored_exact_candidate_before':True,'global_config_or_cache_touched':False}))
