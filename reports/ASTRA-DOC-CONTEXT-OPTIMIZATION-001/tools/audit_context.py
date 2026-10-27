"""Read-only document audit. Writes only this task's evidence directory. No Git/app imports."""
from pathlib import Path
import hashlib
import json
import re
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / 'evidence'
DOC = ROOT / 'Документация'
NEW_DOC = DOC / '41_Оптимизация контекста документов.md'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def protected_files():
    # A bounded baseline of all documentation/Obsidian files and project source areas.
    paths = list(DOC.rglob('*')) + list((ROOT / '.obsidian').rglob('*'))
    paths += list(ROOT.glob('*'))
    for folder in ('web_alarm', 'integrations', '.github'):
        paths += list((ROOT / folder).rglob('*'))
    return sorted({p for p in paths if p.is_file() and p != NEW_DOC and
                   '__pycache__' not in p.parts and '.git' not in p.parts})

def snapshot():
    return {p.relative_to(ROOT).as_posix(): {'bytes': p.stat().st_size,
            'sha256': digest(p.read_bytes())} for p in protected_files()}

def sections(text):
    lines = text.splitlines(keepends=True)
    starts = [(i, len(m[1]), m[2]) for i, line in enumerate(lines)
              if (m := re.match(r'^(#{1,6}) (.+?)\s*$', line))]
    result = []
    for j, (i, level, title) in enumerate(starts):
        end = next((k for k, lev, _ in starts[j+1:] if lev <= level), len(lines))
        result.append({'title': title, 'level': level, 'start_line': i+1,
                       'end_line': end, 'chars': len(''.join(lines[i:end]))})
    return result

def graph_tokens(text):
    # Conservative syntax inventory, including code samples; NOT an Obsidian parser.
    return {'wiki': re.findall(r'!?\[\[[^\]\n]+\]\]', text),
            'markdown_links': re.findall(r'!?\[[^\]\n]*\]\([^\n]*?\)', text),
            'reference_definitions': re.findall(r'^ {0,3}\[[^\]\n]+\]:[^\n]+', text, re.M),
            'tag_candidates': re.findall(r'(?<![\w\\])#[\w/-]+', text)}

def main():
    mode = sys.argv[1]
    if mode == 'baseline':
        assert not (OUT / 'baseline.json').exists(), 'Baseline is immutable'
        assert not NEW_DOC.exists(), 'Output document already exists'
        state = snapshot()
        save('baseline.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(),
             'scope': 'Документация recursively; .obsidian recursively; root files; web_alarm/integrations/.github recursively; excludes __pycache__; no .git access',
             'files': state})
        metrics, index, graphs = [], {}, {}
        for p in sorted(DOC.glob('*.md')):
            data = p.read_bytes()
            text = data.decode('utf-8-sig')
            rel = p.relative_to(ROOT).as_posix()
            metrics.append({'path': rel, 'bytes': len(data), 'unicode_chars': len(text),
                            'lines': len(text.splitlines()), 'sha256': digest(data)})
            # Archive bodies are never emitted into model context.
            if not p.name.startswith(('001_', '06_', '25_', '21_', '26_')):
                index[rel] = sections(text)
            graphs[rel] = graph_tokens(text)
        save('document_metrics.json', metrics)
        save('section_index.json', index)
        save('graph_syntax_baseline.json', graphs)
        print(json.dumps({'protected_files': len(state), 'markdown_documents': len(metrics),
                          'metrics': [x for x in metrics if Path(x['path']).name.startswith(('05_', '08_', '34_', '40_'))]}, ensure_ascii=False))
    elif mode == 'inventory':
        result = []
        for prefix in ('08_', '34_'):
            p = next(DOC.glob(prefix + '*.md'))
            data = p.read_bytes()
            text = data.decode('utf-8-sig')
            lines = text.splitlines(keepends=True)
            boundaries = [0] + [i for i, line in enumerate(lines)
                                if i and re.match(r'^#{1,6} ', line)] + [len(lines)]
            fragments = []
            for n, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
                value = ''.join(lines[start:end])
                title = lines[start].strip()
                if not title.startswith('# ' ) and not title.startswith('##'):
                    title = 'Преамбула / без заголовка'
                tokens = graph_tokens(value)
                fragments.append({'fragment_id': f'{prefix[:2]}-{n:03d}',
                    'start_line': start+1, 'end_line': end, 'heading': title,
                    'chars': len(value), 'utf8_sha256': digest(value.encode('utf-8')),
                    'syntax_counts': {k: len(v) for k, v in tokens.items()},
                    'existing_content': 'UNCHANGED',
                    'future_preservation_gate': 'OPEN: authorized exact canonical destination and semantic readback required',
                    'routing_matrix': '41, sections 3 and 10; prospective destination is not yet verified'})
            assert sum(f['chars'] for f in fragments) == len(text)
            result.append({'path': p.relative_to(ROOT).as_posix(), 'source_sha256': digest(data),
                           'total_chars': len(text), 'covered_chars': sum(f['chars'] for f in fragments),
                           'coverage': '100% structural only, not semantic preservation acceptance',
                           'fragments': fragments})
        save('migration_inventory.json', result)
        print(json.dumps([{'path': v['path'], 'fragments': len(v['fragments']),
                           'covered_chars': v['covered_chars']} for v in result], ensure_ascii=False))
    elif mode == 'compare':
        before = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))['files']
        after = snapshot()
        changed = [p for p in before if p in after and before[p] != after[p]]
        removed = sorted(set(before) - set(after))
        added = sorted(set(after) - set(before))
        graph_before = json.loads((OUT / 'graph_syntax_baseline.json').read_text(encoding='utf-8'))
        graph_changed = [p for p, v in graph_before.items()
                         if graph_tokens((ROOT / p).read_text(encoding='utf-8-sig')) != v]
        new_tokens = graph_tokens(NEW_DOC.read_text(encoding='utf-8-sig'))
        result = {'checked_files': len(before), 'changed': changed, 'removed': removed,
                  'added_in_protected_scope': added, 'graph_syntax_changed_sources': graph_changed,
                  'new_doc_syntax_counts': {k: len(v) for k, v in new_tokens.items()},
                  'scope_unchanged': not (changed or removed or added),
                  'limitations': 'Static byte and syntax checks, not a live Obsidian graph export. New authorized document may appear as an isolated node. No runtime/visual/CI/Git validation.'}
        save('verification.json', result)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['scope_unchanged'] and not graph_changed and not any(new_tokens.values()) else 1
    else:
        raise ValueError(mode)

if __name__ == '__main__':
    sys.exit(main())
