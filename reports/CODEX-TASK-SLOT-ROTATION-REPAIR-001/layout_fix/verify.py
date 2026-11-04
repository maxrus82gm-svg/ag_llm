"""Package readback only; no GUI input, restart, task assignment or network."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / 'before.json').read_text(encoding='utf-8-sig'))
card = ROOT / 'Документация/000_Задачи Codex.md'
card_sha = hashlib.sha256(card.read_bytes()).hexdigest()
assert card_sha == before['card_sha256']
assert not before['proposal_file_exists']
doc = ROOT / 'Документация/Скрипт выставления задачи и синхронизации задачи выполненной.md'
text = doc.read_text(encoding='utf-8')
assert 'Статус: предложение пользователя' in text
assert '[[' not in text and '](' not in text
ast.parse((ROOT / 'tools/task_slot_monitor.py').read_text(encoding='utf-8'))
tests = (HERE / 'final_101_tests.txt').read_text(encoding='utf-8-sig')
assert 'Ran 101 tests' in tests and tests.rstrip().endswith('OK')
result = {
    'date': '2026-11-04', 'status': 'CODE SAVED / LIVE WINDOW RESTART PENDING',
    'layout': 'Only editor grid row expands; footer reserved before main log; text requests one line',
    'manual_send_required': True, 'card_unchanged': True, 'card_sha256': card_sha,
    'existing_targeted_tests': {'run': 101, 'pass': 101, 'new_tests_added_for_layout': 0},
    'native_resize_after_fix': 'NOT RUN; preserve possible unsent text in existing user window',
    'user_next_step': 'Copy any needed unsent text, close the program, reopen the existing desktop shortcut',
    'design_document': {'path': doc.relative_to(ROOT).as_posix(), 'new_file': True,
                        'status': 'PROPOSAL ONLY', 'wikilinks_and_markdown_links': 0,
                        'index_or_card_links_added': 0, 'profiles_implemented': False},
    'core_configuration_and_permissions_changed': False, 'git_operations': 0, 'network_requests': 0
}
(HERE / 'readback.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'card_unchanged': True, 'syntax': 'OK', 'tests': '101/101', 'standalone_design_created': True}))
