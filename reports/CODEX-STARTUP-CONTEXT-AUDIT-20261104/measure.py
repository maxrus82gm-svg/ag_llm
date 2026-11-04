"""Read-only document-size audit. Only measurements, never archive bodies, are emitted."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import re
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--tokenizer-dir', required=True)
args = parser.parse_args()
sys.path.insert(0, args.tokenizer_dir)
import tiktoken

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'Документация'
ENC = tiktoken.get_encoding('o200k_base')

def measure(text):
    return {'chars': len(text), 'tokens': len(ENC.encode(text)),
            'lines': len(text.splitlines())}

texts = {p.name: p.read_text(encoding='utf-8-sig') for p in DOCS.glob('*.md')}
files = {name: {**measure(text), 'sha256_bytes': hashlib.sha256((DOCS/name).read_bytes()).hexdigest()}
         for name, text in texts.items()}
parts = {}

def part(key, name, first=1, last=None):
    lines = texts[name].splitlines(keepends=True)
    last = len(lines) if last is None else last
    body = ''.join(lines[first-1:last])
    parts[key] = {'file': name, 'first_line': first, 'last_line': last, **measure(body)}
    return body

for key, name in [('08_active','08_Старт.md'), ('000_active','000_Задачи для агента.md'),
                  ('34_active','34_TACTICAL_CONTEXT.md')]:
    marker = texts[name].splitlines().index('## Сохранённые адреса прежней редакции')
    part(key, name, last=marker)
part('40_full', '40_Оперативная координация направлений.md')
part('40_AB_only', '40_Оперативная координация направлений.md', 65, 81)
part('40_latest', '40_Оперативная координация направлений.md', 1, 3)
part('40_common', '40_Оперативная координация направлений.md', 82, 98)
followup = part('05_followup', '05_Реестр задач.md', 28, 60)
rows = [s for s in followup.splitlines(keepends=True) if s.startswith('| `FOLLOWUP-')]
closed = [s for s in rows if re.match(r'(?:ACCEPTED_BY_USER|CLOSED)', s.split('|')[-2].strip().replace('**',''))]
open_body = ''.join(s for s in followup.splitlines(keepends=True) if s not in closed)
parts['05_followup_open'] = {'file':'05_Реестр задач.md', 'first_line':28, 'last_line':60,
                             'omitted_closed_rows':len(closed), 'open_rows':len(rows)-len(closed), **measure(open_body)}
part('script_spec', 'Скрипт выставления задачи и синхронизации задачи выполненной.md')
part('01_map', '01_Архитектура и текущее состояние.md', 1, 115)
part('36_document_entry', '36_Единая архитектура тестирования.md', 157, 159)

name18 = '18_Регламент сопровождения документации.md'
lines = texts[name18].splitlines(keepends=True)
heads = []
fenced = False
for n, line in enumerate(lines):
    if line.startswith('```'):
        fenced = not fenced
    if not fenced and re.match(r'^#{1,2} ', line):
        heads.append(n)
rules = {}
for i, n in enumerate(heads):
    found = re.match(r'^## (DOC-[A-Z0-9-]+)', lines[n])
    if not found:
        continue
    end = heads[i+1] if i+1 < len(heads) else len(lines)
    body = ''.join(lines[n:end])
    meta = re.search(r'```rule-meta\n(.*?)```', body, re.S)
    metadata = meta.group(1) if meta else ''
    contract = re.search(r'^contract:\s*(\d+)', metadata, re.M)
    requires = re.search(r'^requires:(.*)', metadata, re.S | re.M)
    refs = re.findall(r'(DOC-[A-Z0-9-]+)@(\d+)', requires.group(1)) if requires else []
    rules[found.group(1)] = {'first_line':n+1, 'last_line':end, **measure(body),
                            'contract':int(contract.group(1)) if contract else None,
                            'requires':[{'id':rid,'contract':int(ver)} for rid,ver in refs]}

def closure(seeds):
    pending = list(seeds)
    seen = set()
    missing = set()
    mismatches = set()
    while pending:
        rid = pending.pop()
        if rid in seen:
            continue
        if rid not in rules:
            missing.add(rid)
            continue
        seen.add(rid)
        for ref in rules[rid]['requires']:
            actual = rules.get(ref['id'], {}).get('contract')
            if actual != ref['contract']:
                mismatches.add(f"{rid} -> {ref['id']}@{ref['contract']}; actual @{actual}")
            pending.append(ref['id'])
    return {'seeds':seeds, 'rule_ids':sorted(seen), 'count':len(seen),
            'tokens':sum(rules[rid]['tokens'] for rid in seen),
            'missing':sorted(missing), 'contract_mismatches':sorted(mismatches)}

closures = {
    'context_ops':closure(['DOC-CONTEXT-OPS-01']),
    'startup_explicit':closure(['DOC-CONTEXT-OPS-01','DOC-GIT-01','DOC-ENGINEERING-ROLES-01',
                                'DOC-PARALLEL-01','DOC-GITHUB-HANDOFF-01']),
    'reading_audit':closure(['DOC-CONTEXT-OPS-01','DOC-PLAN-TASK-INDEX-01']),
}
base = ['08_active','000_active','40_full','34_active','05_followup','script_spec']
base_tokens = sum(parts[key]['tokens'] for key in base)
trim = base_tokens - parts['40_full']['tokens'] + sum(parts[x]['tokens'] for x in ['40_AB_only','40_latest','40_common'])
full_route_files = ['08_Старт.md','000_Задачи для агента.md','40_Оперативная координация направлений.md',
                    '34_TACTICAL_CONTEXT.md','05_Реестр задач.md',name18,'01_Архитектура и текущее состояние.md',
                    '36_Единая архитектура тестирования.md','36.1_Обязательный регламент тестирования для LLM.md',
                    '36.2_Профиль тестирования Web Alarm Workspace.md','Скрипт выставления задачи и синхронизации задачи выполненной.md']
data = {'date':'2026-11-04', 'root':str(ROOT), 'encoding':'o200k_base',
        'tiktoken_version':importlib.metadata.version('tiktoken'),
        'method':'UTF-8 BOM removed, CRLF normalized to LF. Raw text only; no prompts, reasoning, repeated request input or billing.',
        'files':files, 'parts':parts, 'rules18':rules, 'closures18':closures,
        'scenarios':{'base_keys':base,'base_tokens':base_tokens,'base_with_only_current_AB_common40':trim,
                     'base_with_open_followup_only':base_tokens-parts['05_followup']['tokens']+parts['05_followup_open']['tokens'],
                     'base_plus_context_ops_closure':base_tokens+closures['context_ops']['tokens'],
                     'base_plus_explicit_startup_closure':base_tokens+closures['startup_explicit']['tokens'],
                     'whole_file_route_files':full_route_files,
                     'whole_file_route_tokens':sum(files[name]['tokens'] for name in full_route_files)},
        'task_record_markers':{name:len(re.findall(r'^<!-- TASK-RECORD .* BEGIN -->$', text, re.M))
                               for name,text in texts.items() if name.startswith(('05_','06_','001_','43.2_'))}}
output = Path(__file__).with_name('metrics.json')
output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'parts':parts,'closures':closures,'scenarios':data['scenarios'],
                  'task_record_markers':data['task_record_markers'], 'metrics_path':str(output)}, ensure_ascii=False, indent=2))
