"""Local packet readback/manifest. No Git, UI, process mutation or network."""
import ast
import hashlib
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UI = ROOT / 'reports/CODEX-WUA-CHAT-UI-INTEGRATION-001'
CORE = runpy.run_path(str(ROOT / 'tools/task_slot_rotate.py'))


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def put(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def record(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def packet(folder, extra):
    paths = [p for p in folder.rglob('*') if p.is_file() and p != folder / 'manifest.json'] + extra
    return {'task': folder.name, 'status': 'LOCAL ONLY / AWAITING INDEPENDENT VERIFICATION',
            'self_excluded': 'manifest.json', 'files': [record(p) for p in sorted(set(paths))]}


def verify_manifest(path):
    data = read(path)
    for row in data['files']:
        assert record(ROOT / row['path']) == row, row['path']
    return len(data['files'])


def readback():
    old = CORE['parse']((HERE / 'card_before.md').read_bytes())
    path = ROOT / 'Документация/000_Задачи Codex.md'
    new = CORE['parse'](path.read_bytes())
    assert not old.problems and not new.problems
    before = b''.join(old.body('b1b', 'b1e')[0])
    new1 = CORE['classify_block1'](new.body('b1b', 'b1e')[1], 0)
    slot = CORE['classify_block11'](*new.body('b11b', 'b11e'))
    previous = CORE['classify_block11'](*old.body('b11b', 'b11e'))
    assert new1['state'] == 'WAITING'
    assert slot['copy'] == before and slot['task_id'] == 'CODEX-WUA-CHAT-UI-INTEGRATION-001'
    assert old.lines[old.idx['b11e']:] == new.lines[new.idx['b11e']:], 'B2-B4 changed'
    current_snapshot = UI / 'handoff_task.md'
    previous_snapshot = ROOT / 'reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001/handoff_task.md'
    assert CORE['snapshot_parts'](current_snapshot.read_bytes())[0] == before.replace(b'\r\n', b'\n')
    assert CORE['snapshot_parts'](previous_snapshot.read_bytes())[0] == previous['copy'].replace(b'\r\n', b'\n')
    assert record(previous_snapshot)['sha256'] == 'ff4eb2759ed6d5111ec137640cb2af77db1998d654fa881ba78f4646a654111d'
    shared = '000_Задачи для агента.md'
    marker = '## Сохранённые адреса прежней редакции'
    old_history = (HERE / 'source_before' / shared).read_bytes().decode('utf-8').split(marker, 1)[1]
    new_history = (ROOT / 'Документация' / shared).read_bytes().decode('utf-8').split(marker, 1)[1]
    assert old_history == new_history
    repeat = read(HERE / 'final_repeat.json')
    assert repeat['result'] == 'ALREADY_ROTATED'
    assert read(HERE / 'auto_close_result.json')['still_running'] is False
    assert read(HERE / 'shortcut.json')['readback'] is True
    for py in [ROOT / 'tools/task_slot_rotate.py', ROOT / 'tools/task_slot_monitor.py', ROOT / 'tools/test_task_slot_rotate.py', *HERE.glob('*.py'), *HERE.glob('new_task/*.py'), *HERE.glob('layout_fix/*.py')]:
        ast.parse(py.read_text(encoding='utf-8'), filename=py.name)
    for path in [*HERE.rglob('*.json'), *UI.glob('*.json')]:
        read(path)
    return {'block1': 'WAITING', 'block1_1': slot['task_id'], 'copied_exact': True,
            'block2_4_unchanged': True, 'previous_snapshot_sha256': record(previous_snapshot)['sha256'],
            'card_sha256': record(ROOT / 'Документация/000_Задачи Codex.md')['sha256'],
            'global_000_historical_tail_unchanged': True}


if __name__ == '__main__':
    extra = [ROOT / n for n in ['tools/task_slot_rotate.py', 'tools/test_task_slot_rotate.py',
             'tools/task_slot_monitor.py', 'tools/task_slot_debug.json', 'tools/create_task_slot_shortcut.ps1',
             'tools/TASK_SLOT_ROTATION.md', 'Документация/18_Регламент сопровождения документации.md',
             'Документация/08_Старт.md', 'Документация/000_Задачи для агента.md', 'Документация/000_Задачи Codex.md',
             'Документация/Скрипт выставления задачи и синхронизации задачи выполненной.md']]
    if sys.argv[1:] == ['--verify']:
        state = readback()
        print(json.dumps({'ui_manifest_files': verify_manifest(UI / 'manifest.json'),
                          'repair_manifest_files': verify_manifest(HERE / 'manifest.json'), 'readback': state}, ensure_ascii=False))
        raise SystemExit(0)
    assert not sys.argv[1:]
    state = readback()
    text = (HERE / 'layout_fix/final_101_tests.txt').read_text(encoding='utf-8-sig')
    assert 'Ran 101 tests' in text and text.rstrip().endswith('OK')
    followup = read(HERE / 'manual_finish/readback.json')
    assert followup['real_card_unchanged'] and not followup['manual_finish_enabled_for_current_card']
    editor = read(HERE / 'new_task/readback.json')
    assert editor['block1_unchanged'] and editor['block1_1_and_all_following_bytes_unchanged']
    mutants = read(HERE / 'mutants-new-task.json')
    assert len(mutants) == 5 and all(row['caught'] and row['exit_code'] == 1 for row in mutants)
    put(HERE / 'checks.json', {
        'task': HERE.name, 'date': '2026-11-04', 'status': 'RESULT READY / AWAITING INDEPENDENT VERIFICATION',
        'test_command': 'python -B -m unittest tools.test_task_slot_rotate.Rotation tools.test_task_slot_rotate.Refusals tools.test_task_slot_rotate.Markers tools.test_task_slot_rotate.Cli tools.test_task_slot_rotate.AutomaticArchive tools.test_task_slot_rotate.ManualFinish tools.test_task_slot_rotate.TaskAssignment',
        'tests': {'run': 101, 'pass': 101, 'fail': 0, 'error': 0, 'skip': 0, 'exit_code': 0},
        'new_task_followup': {'new_tests': 22, 'evidence': 'new_task/', 'readback': editor,
                              'prior_79_test_evidence_retained': True},
        'layout_and_design_followup': read(HERE / 'layout_fix/readback.json'),
        'manual_finish_followup': {'new_tests': 8, 'first_red_errors': 8,
                                 'evidence': 'manual_finish/', 'real_readback': followup,
                                 'prior_71_test_evidence_retained': True},
        'initial_baseline': {'run': 43, 'fail': 1, 'exit_code': 1, 'finding': 'Existing unrelated Claude card INVALID in RealCards; not edited'},
        'new_tests_old_source': {'run': 16, 'pass': 1, 'fail': 11, 'error': 4, 'exit_code': 1, 'evidence': 'new_tests_old_source_retry.txt'},
        'first_green_attempt': {'run': 58, 'pass': 53, 'fail': 5, 'error': 0, 'exit_code': 1},
        'mutant_command': 'python -B reports/CODEX-TASK-SLOT-ROTATION-REPAIR-001/verify_mutants.py mutants-new-task',
        'mutants': {'executed': 5, 'caught': 5, 'outer_exit_code': 0, 'selectors_overlap_101_tests': True},
        'real_workflow': 'finish --card Документация/000_Задачи Codex.md --task-id CODEX-WUA-CHAT-UI-INTEGRATION-001 --no-chat-amendment --date 2026-11-04 --apply --monitor',
        'workflow_result': 'ROTATED; later ALREADY_ROTATED',
        'window': {'dark_theme': True, 'default_debug_enabled': False, 'font_default': 12, 'font_maximum': 16,
                   'refresh_minutes': 30, 'auto_close_seconds': 8, 'history_limit': 10,
                   'single_instance_observed': True, 'auto_close_process_exit_observed': True,
                   'user_visual_feedback': 'User reported window visible and satisfactory',
                   'native_capture': 'NOT VERIFIED: CUA screenshot timed out', 'full_30_minute_cycle': 'NOT RUN'},
        'shortcut': read(HERE / 'new_task/shortcut.json'), 'readback': state,
        'other_platforms_and_github': 'NOT RUN; actual headless entrypoint tested without Tkinter/monitor imports',
        'git_operations': 0, 'network_requests': 0, 'other_cards_modified': 0,
        'known_initial_issues': ['Windows os.kill(pid,0) interrupted own first test runner; replaced by process query and guarded by a19',
                               'Multiple pythonw commands in PATH caused first shortcut creation failure; select first by PATH priority',
                               'Raw monitor stdout contained multiple/truncated JSON objects; preserved as *_raw.txt. Full per-run JSON saved separately.'],
        'manifest_note': 'All report files plus addressed final code/docs; no recursive self-hash. Desktop .lnk and TEMP history are not published machine-independent artifacts.'})
    ui_extra = [ROOT / 'web_alarm/ui.py', ROOT / 'test_web_alarm_ultra_chat_ui.js']
    old_manifest = UI / 'manifest.json'
    backup = HERE / 'source_before/ui_manifest_before.json'
    if not backup.exists():
        backup.write_bytes(old_manifest.read_bytes())
    put(old_manifest, packet(UI, ui_extra))
    repair_extra = extra + [old_manifest, UI / 'report.md', UI / 'handoff_task.md', ROOT / 'reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001/handoff_task.md']
    put(HERE / 'manifest.json', packet(HERE, repair_extra))
    print(json.dumps({'repair_manifest_files': verify_manifest(HERE / 'manifest.json'),
                      'ui_manifest_files': verify_manifest(UI / 'manifest.json'), 'readback': state}, ensure_ascii=False))
