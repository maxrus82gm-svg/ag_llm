"""Read-only real-card verification and local follow-up evidence; no UI inputs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools import task_slot_monitor as monitor, task_slot_rotate as core

card = ROOT / 'Документация/000_Задачи Codex.md'
before = json.loads((HERE / 'before.json').read_text(encoding='utf-8-sig'))
raw = card.read_bytes()
out = io.StringIO()
with contextlib.redirect_stdout(out):
    code = core.main(['watch', '--card', str(card), '--headless'])
check = json.loads(out.getvalue())
assert code == 0 and check['block1']['state'] == 'WAITING'
assert not monitor.can_manual_finish(check)
assert hashlib.sha256(raw).hexdigest() == before['card_sha256']
assert card.read_bytes() == raw
owner_path = monitor.runtime_folder(card) / 'owner.json'
owner = json.loads(owner_path.read_text()) if owner_path.exists() else None
shortcut = json.loads((HERE / 'shortcut.json').read_text(encoding='utf-8-sig'))
assert shortcut['readback'] and shortcut['mode'] == 'WATCH_WITH_MANUAL_FINISH'
value = {
    'real_card_unchanged': True, 'card_sha256': check['card_sha256'],
    'block1': check['block1'], 'block1_1': check['block1_1'],
    'manual_finish_enabled_for_current_card': False,
    'shortcut_readback': shortcut, 'watch_process_alive_at_readback': bool(owner and monitor.process_alive(owner['pid'])),
    'native_window_observation': {
        'method': 'Computer Use sky.list_windows',
        'old_window_closed_via': 'Alt_L+F4; old process exited',
        'new_window_count_for_card': 1, 'new_window_id': 15011740,
        'title': 'Ротация карточки — 000_Задачи Codex',
        'screenshot': 'NOT VERIFIED: window capture timed out: timed out waiting on channel',
        'manual_dialog_ui_clickthrough': 'NOT RUN; live card WAITING; no synthetic GUI claim'
    },
    'inspection_retry': 'First readback found no owner after prior window observation. No rotation occurred. Reopened exact shortcut target with diagnostic stdout/stderr; check OK, stderr empty, one window observed. Readback does not require a viewer to remain open.',
    'synthetic_workflow': '8 new tests; positive finish four phases and amendment bytes; negative waiting, declarations, missing package, same-ID/different-ID stale observation',
    'real_task_rotation_this_followup': 'NOT RUN; no task in BLOCK 1',
    'network_and_git_operations': 0
}
(HERE / 'readback.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(value, ensure_ascii=False))
