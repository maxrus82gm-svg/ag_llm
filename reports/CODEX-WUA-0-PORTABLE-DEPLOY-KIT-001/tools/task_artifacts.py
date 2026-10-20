"""Project-local safe handoff. Does not copy historic cards or publish external paths."""
from pathlib import Path
import hashlib,json,sys,os,time

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
CARD=ROOT/'Документация/000_Задачи Codex.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,obj):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
    previous=ROOT/'reports/CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001'
    inputs=json.loads((previous/'inputs_before.json').read_text(encoding='utf-8-sig'))['inputs']
    paths=set()
    for row in inputs:
        p=Path(row['path'])
        if p.is_absolute():continue
        if p.suffix in ('.yaml','.toml'):continue
        paths.add(ROOT/p)
    paths.update(p for p in previous.rglob('*') if p.is_file())
    rows=[]
    for p in sorted(paths):
        b=p.read_bytes();rows.append({'ref':p.relative_to(ROOT).as_posix(),'bytes':len(b),'sha256':sha(b),'authorized_card':p==CARD})
    save('protected_inputs.json',{'files':rows,'external_runtime_configs_not_read':True,'historic_card_backups_not_copied':True})
    b=CARD.read_bytes();a=b.index('# БЛОК 1'.encode());z=b.index('# БЛОК 2'.encode(),a+1)
    with (OUT/'assignment.md').open('xb') as f:f.write(b[a:z])
    save('card_initial.json',{'before_sha256':sha(b),'prefix_sha256':sha(b[:a]),'assignment_sha256':sha(b[a:z]),'history_sha256':sha(b[z:]),'history_bytes':len(b[z:]),'privacy':'Full historic card retained only in its canonical file; reversible rotation, no raw public backup.'})
    print(json.dumps({'protected_project_files':len(rows),'card_recorded':True}))
def seal():
    files=[]
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p==OUT/'manifest.json':continue
        if p.suffix=='.pending':raise RuntimeError('Unresolved private staging file; do not publish')
        b=p.read_bytes()
        if p.suffix=='.json':json.loads(b.decode('utf-8-sig'))
        files.append({'path':p.relative_to(OUT).as_posix(),'bytes':len(b),'sha256':sha(b)})
    manifest={'task_id':OUT.name,'status':'RESULT READY / AWAITING INDEPENDENT VERIFICATION','files':files,'self_hash':'excluded','publication':'LOCAL ONLY / USER PUBLICATION NOT VERIFIED','runtime_toolkit':'toolkit/; PowerShell/.NET built-ins; live backend absent'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for row in files:
        b=(OUT/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    print(json.dumps({'manifest_entries':len(files),'total_files':len(files)+1,'manifest_sha256':sha((OUT/'manifest.json').read_bytes()),'report_sha256':sha((OUT/'report.md').read_bytes())}))
def integrity():
    rows=json.loads((OUT/'protected_inputs.json').read_text(encoding='utf-8-sig'))['files'];done=[]
    for row in rows:
        h=sha((ROOT/row['ref']).read_bytes());done.append({**row,'final_sha256':h,'unchanged':h==row['sha256']})
    ordinary=[x for x in done if not x['authorized_card']]
    assert all(x['unchanged'] for x in ordinary),'Project input drift; do not overwrite others'
    save('integrity.json',{'protected_noncard':len(ordinary),'unchanged_noncard':len(ordinary),'files':done})
    print(json.dumps({'unchanged_noncard':len(ordinary),'card_changes':sum(not x['unchanged'] for x in done if x['authorized_card'])}))
if __name__=='__main__':{'prepare':prepare,'seal':seal,'integrity':integrity}[sys.argv[1]]()
