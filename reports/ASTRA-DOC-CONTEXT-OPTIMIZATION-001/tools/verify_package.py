"""Bounded documentation checks; no product imports, Git, runtime or network."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parents[1]
DOC = ROOT / 'Документация' / '41_Оптимизация контекста документов.md'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

checks = []
def check(name, passed, detail):
    checks.append({'name': name, 'pass': bool(passed), 'detail': detail})

baseline = json.loads((TASK / 'evidence/baseline.json').read_text(encoding='utf-8'))['files']
original_docs = [p for p in baseline if p.startswith('Документация/')]
changed_docs = [p for p in original_docs if not (ROOT / p).is_file() or sha(ROOT / p) != baseline[p]['sha256']]
check('Original documentation bytes unchanged', not changed_docs,
      {'checked': len(original_docs), 'changed': changed_docs})
graph = '.obsidian/graph.json'
check('Graph configuration unchanged', sha(ROOT / graph) == baseline[graph]['sha256'], graph)
source_paths = [p for p in baseline if not p.startswith(('Документация/', '.obsidian/'))]
changed_sources = [p for p in source_paths if not (ROOT / p).is_file() or sha(ROOT / p) != baseline[p]['sha256']]
check('Existing source/config/test files unchanged', not changed_sources,
      {'checked': len(source_paths), 'changed': changed_sources})
text = DOC.read_text(encoding='utf-8')
required = ['# 41. Оптимизация контекста документов — 27.10.2026',
            'ASTRA-DOC-CONTEXT-OPTIMIZATION-001', 'Astra / Codex 007',
            'PROPOSAL / AWAITING INDEPENDENT REVIEW']
check('Required identity and proposal status', all(x in text for x in required), required)
new_markdown = [DOC] + list(TASK.rglob('*.md'))
violations = []
for p in new_markdown:
    t = p.read_text(encoding='utf-8')
    patterns = [r'!?\[\[[^\]\n]+\]\]', r'!?\[[^\]\n]*\]\([^\n]*?\)',
                r'^ {0,3}\[[^\]\n]+\]:', r'(?<![\w\\])#[\w/-]+',
                r'\A---\s*\n']
    if any(re.search(pattern, t, re.M) for pattern in patterns):
        violations.append(p.relative_to(ROOT).as_posix())
check('New Markdown has no graph-link/tag/frontmatter syntax', not violations,
      {'checked': len(new_markdown), 'violations': violations})
inventory = json.loads((TASK / 'evidence/migration_inventory.json').read_text(encoding='utf-8'))
coverage = all(x['covered_chars'] == x['total_chars'] and
               sum(f['chars'] for f in x['fragments']) == x['total_chars'] for x in inventory)
check('Migration ledger covers complete source text structurally', coverage,
      {'fragments': sum(len(x['fragments']) for x in inventory),
       'chars': sum(x['total_chars'] for x in inventory), 'semantic_acceptance': 'NOT PERFORMED'})
syntax = json.loads((TASK / 'evidence/graph_syntax_baseline.json').read_text(encoding='utf-8'))
backlinks = [(p, t) for p, kinds in syntax.items() for items in kinds.values() for t in items
             if 'Оптимизация контекста документов' in t or re.search(r'(?<!\d)41_', t)]
check('No old references to document 41 in bounded syntax inventory', not backlinks,
      {'documents': len(syntax), 'matches': backlinks, 'whole_vault_resolver': 'NOT RUN'})
report = TASK / 'report.md'
check('Mandatory local report exists and retains pending review', report.is_file() and
      'AWAITING INDEPENDENT REVIEW' in report.read_text(encoding='utf-8'), 'report.md')
result = {'checks': checks, 'passed': sum(x['pass'] for x in checks),
          'failed': sum(not x['pass'] for x in checks),
          'note': 'Author checks only. All-file drift check is separate and must not be hidden by this bounded result.'}
(TASK / 'evidence/package_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if not result['failed'] else 1)
