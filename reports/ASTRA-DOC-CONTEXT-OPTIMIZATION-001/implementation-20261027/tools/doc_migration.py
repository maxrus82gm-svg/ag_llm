"""Documentation-only migration; no Git, application imports, runtime or network."""
from pathlib import Path
import hashlib, json, re, sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DOC = ROOT / 'Документация'
PREFIXES = ['000_Задачи для агента', '000_Задачи ChatGPT', '000_Задачи Claude',
            '000_Задачи Codex', '000_Задачи Ultra Desktop', '05_', '06_', '07_',
            '08_', '18_', '34_', '36_Единая', '40_']

def h(b): return hashlib.sha256(b).hexdigest()
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def target_files():
    return [next(p for p in DOC.glob('*.md') if p.name.startswith(prefix)) for prefix in PREFIXES]
def headings(text):
    result=[]; fence=None
    for line in text.splitlines():
        m=re.match(r'^\s{0,3}(`{3,}|~{3,})',line)
        if m:
            if fence is None: fence=m[1][0]
            elif m[1][0]==fence: fence=None
            continue
        if not fence and re.match(r'^#{1,6} ',line): result.append(line)
    return result
def graph(text):
    # Conservative observed-syntax proof. Existing headings and file/alias identity are also held.
    raw_wiki=re.findall(r'!?\[\[[^\]\n]+\]\]',text)
    raw_md=re.findall(r'!?\[[^\]\n]*\]\(([^\n]*?)\)',text)
    internal=[v for v in raw_md if not re.match(r'[A-Za-z][A-Za-z0-9+.-]*:',v)]
    codefree=re.sub(r'(?ms)^\s{0,3}```.*?^\s{0,3}```[^\n]*','',text)
    codefree=re.sub(r'`[^`\n]*`','',codefree)
    wiki_active=re.findall(r'!?\[\[[^\]\n]+\]\]',codefree)
    tags=[v for v in re.findall(r'(?<![\w/\\])#([\w/-]+)',codefree)
          if any(c.isalpha() or c=='_' for c in v)]
    front=re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)',text,re.S)
    blocks=re.findall(r'(?m)\^[A-Za-z0-9-]+\s*$',text)
    refs=re.findall(r'(?m)^ {0,3}\[[^\]\n]+\]:[^\n]+',text)
    return {k:dict(Counter(v)) for k,v in {'raw_wiki':raw_wiki,'active_wiki':wiki_active,
            'internal_markdown_targets':internal,'tags':tags,'blocks':blocks,'reference_definitions':refs,
            'frontmatter':[front[0]] if front else []}.items()}

def baseline():
    destination=WORK/'evidence/baseline.json'
    assert not destination.exists(), 'Do not overwrite baseline'
    files=list(DOC.glob('*'))+list((ROOT/'.obsidian').rglob('*'))+list(ROOT.glob('*'))
    for folder in ['web_alarm','integrations','.github']: files+=list((ROOT/folder).rglob('*'))
    files=sorted({p for p in files if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts})
    state={p.relative_to(ROOT).as_posix():{'sha256':h(p.read_bytes()),'bytes':p.stat().st_size} for p in files}
    targets=[]; fragments=[]
    for p in target_files():
        data=p.read_bytes(); text=data.decode('utf-8-sig')
        dest=WORK/'preservation'/(p.name+'.source.txt')
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        item={'source':p.relative_to(ROOT).as_posix(),'snapshot':dest.relative_to(ROOT).as_posix(),
              'sha256':h(data),'bytes':len(data),'chars':len(text),'headings':headings(text),'graph':graph(text)}
        targets.append(item)
        lines=text.splitlines(keepends=True)
        bounds=[0]+[i for i,s in enumerate(lines) if i and re.match(r'^#{1,6} ',s)]+[len(lines)]
        parts=[]
        for n,(a,b) in enumerate(zip(bounds,bounds[1:]),1):
            value=''.join(lines[a:b])
            parts.append({'record_id':f'S{n:03d}','first_line':a+1,'last_line':b,
                          'heading':lines[a].strip() if re.match(r'^#{1,6} ',lines[a]) else 'Преамбула',
                          'chars':len(value),'sha256_utf8':h(value.encode('utf-8'))})
        assert sum(x['chars'] for x in parts)==len(text)
        fragments.append({'source':item['source'],'snapshot':item['snapshot'],'parts':parts})
    dump(destination,{'task':'ASTRA-DOC-CONTEXT-OPTIMIZATION-001 / direct user implementation amendment 2026-10-27',
                      'files':state,'targets':targets})
    dump(WORK/'evidence/preservation_index.json',fragments)
    print(json.dumps({'baseline_files':len(files),'snapshots':len(targets),'status':'saved'},ensure_ascii=False))

def verify(apply=False):
    base=json.loads((WORK/'evidence/baseline.json').read_text(encoding='utf-8'))
    result=[]
    for item in base['targets']:
        name=Path(item['source']).name; source=ROOT/item['source']; draft=WORK/'candidate'/(name+'.txt')
        assert draft.exists(),f'Missing candidate {name}'
        new=draft.read_text(encoding='utf-8'); old=(WORK/'preservation'/(name+'.source.txt')).read_text(encoding='utf-8')
        missing=list((Counter(headings(old))-Counter(headings(new))).elements())
        checks={'snapshot_hash':h((WORK/'preservation'/(name+'.source.txt')).read_bytes())==item['sha256'],
                'existing_headers_retained':not missing,'same_graph_syntax':graph(old)==graph(new)}
        if name.startswith(('000_Задачи ChatGPT','000_Задачи Claude','000_Задачи Codex','000_Задачи Ultra')):
            needle='# БЛОК 1'
            if needle in old:
                raw_old=(WORK/'preservation'/(name+'.source.txt')).read_bytes()
                raw_new=draft.read_bytes(); marker=needle.encode('utf-8')
                checks['personal_task_blocks_unchanged']=raw_old[raw_old.index(marker):]==raw_new[raw_new.index(marker):]
        if name.startswith(('05_','06_')):
            checks['original_registry_or_journal_untouched_suffix']=draft.read_bytes().endswith((WORK/'preservation'/(name+'.source.txt')).read_bytes())
        checks['source_still_matches_baseline']=h(source.read_bytes())==item['sha256'] if apply else True
        result.append({'file':name,'before_chars':item['chars'],'after_chars':len(draft.read_bytes().decode('utf-8-sig')),
                       'checks':checks,'missing_headers':missing})
    errors=[x for x in result if not all(x['checks'].values())]
    dump(WORK/'evidence/candidate_checks.json',{'files':result,'failed_files':len(errors)})
    print(json.dumps({'files':len(result),'failed_files':len(errors),'details':errors},ensure_ascii=False))
    if errors: return 1
    if apply:
        # All preconditions checked before the first mutation; original immutable bytes are retained.
        for item in base['targets']:
            draft=WORK/'candidate'/(Path(item['source']).name+'.txt')
            (ROOT/item['source']).write_bytes(draft.read_bytes())
        print('Applied documentation candidates. Independent acceptance pending.')
    return 0

if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='baseline': baseline()
    elif cmd in ('verify','apply'): sys.exit(verify(cmd=='apply'))
    else: raise ValueError(cmd)
