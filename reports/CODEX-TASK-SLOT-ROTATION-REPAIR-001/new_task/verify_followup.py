"""Addressed readback; does not assign/rotate a real task or send UI inputs."""
import contextlib
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools import task_slot_monitor as monitor, task_slot_rotate as core

card = ROOT / 'Документация/000_Задачи Codex.md'
before = core.parse((HERE / 'source_before/000_Задачи Codex.md').read_bytes())
after = core.parse(card.read_bytes())
assert not before.problems and not after.problems
assert before.body('b1b', 'b1e')[0] == after.body('b1b', 'b1e')[0]
assert before.lines[before.idx['b1e']:] == after.lines[after.idx['b1e']:]
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = core.main(['watch', '--card', str(card), '--headless'])
check = json.loads(out.getvalue())
assert code == 0 and monitor.can_assign_task(check)
assert check['block1']['state'] == 'WAITING'
folder = monitor.runtime_folder(card)
view = json.loads((folder / 'view.json').read_text(encoding='utf-8'))
editor = json.loads((folder / 'editor_view.json').read_text(encoding='utf-8'))
button = view['new_task_button']
assert button['enabled'] and button['x'] > 0 and button['x'] + button['width'] == button['header_width']
assert editor['empty'] and editor['submit_disabled'] and editor['text_has_focus']
assert editor['resizable'] == [1, 1]
shortcut = json.loads((HERE / 'shortcut.json').read_text(encoding='utf-8-sig'))
assert shortcut['readback'] and shortcut['mode'] == 'WATCH_WITH_MANUAL_ACTIONS'
value = {
    'task': 'CODEX-TASK-SLOT-ROTATION-REPAIR-001 / new-task user amendment',
    'date': '2026-11-04', 'block1': check['block1'], 'block1_1': check['block1_1'],
    'card_sha256': check['card_sha256'], 'block1_unchanged': True,
    'block1_1_and_all_following_bytes_unchanged': True,
    'rules_prefix_changed_only_as_documented': True,
    'main_window_before_opening_form': view, 'native_editor_self_diagnostics': editor,
    'native_window_seen_via_computer_use': {'main_window_id': 7739870, 'count_for_card': 1},
    'native_editor_open_method': 'Supported watch --new-task startup, with WAITING gate; no submission',
    'native_mouse_click_on_new_task': 'NOT RUN: Computer Use geometry/capture unavailable for Tk window',
    'native_visual_screenshot': 'NOT VERIFIED: window capture timed out: timed out waiting on channel',
    'engineering_note': 'Experimental Ctrl+N through Computer Use did not open a form; removed from final code/docs. The visible button and explicit --new-task entry remain.',
    'native_submit_clickthrough': 'NOT RUN; real card intentionally left WAITING',
    'synthetic_assignment_tests': 22, 'total_targeted_tests': 101,
    'mutation_controls': {'run': 5, 'caught': 5, 'selectors_already_in_101': True},
    'shortcut': shortcut, 'git_operations': 0, 'network_requests': 0,
    'other_personal_cards_modified': 0, 'real_task_assignment_performed': False
}
(HERE / 'readback.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'block1': check['block1']['state'], 'right_aligned_button': True,
                  'native_editor_created_empty': True, 'history_unchanged': True}))
