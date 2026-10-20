"""Offline handoff checks and two-phase rotation of this TASK's own card only.

No Windows provisioning, network, Git, subprocess or secret/config access.
Historic card bytes never enter the public TASK directory. Rotation requires
the exact pre-recorded card, freezes B2/B3 before clearing B1, and is one-shot.
"""
from pathlib import Path
import hashlib
import ipaddress
import json
import os
import re
import sys
import time

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[1]
CARD = ROOT / '\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f/000_\u0417\u0430\u0434\u0430\u0447\u0438 Codex.md'
TASK = OUT.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(ref):
    return json.loads((OUT / ref).read_text(encoding='utf-8-sig'))


def save(ref, data):
    with (OUT / ref).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def source_checks():
    suite = load('synthetic_evidence/attempt06_ps7/results.json')
    parser = load('synthetic_evidence/syntax_ps51_release.json')
    review = load('collector_source_review_release.json')
    checked = []
    for ref, expected in suite['sources'].items():
        assert sha((OUT / 'toolkit' / ref).read_bytes()) == expected
        checked.append(ref)
    for row in parser['files']:
        assert sha((OUT / 'toolkit' / row['file']).read_bytes()) == row['sha256']
        checked.append(row['file'])
    for row in review['files']:
        assert sha((OUT / row['path']).read_bytes()) == row['sha256']
    assert suite['total'] == suite['passed'] == 62 and suite['failed'] == 0
    assert len(parser['files']) == 8 and parser['error_count'] == 0
    assert parser['execution_policy_override'] is False
    return suite, parser, sorted(set(checked))


def checks():
    suite, parser, checked = source_checks()
    coverage = load('host_discovery_release/coverage.json')
    verification = load('verification_release.json')
    plan = load('release_plan_rebuilt/install-plan.json')
    original = load('host_discovery_release/install-plan.json')
    assert plan == original, 'Release plan rebuild mismatch'
    assert coverage['required'] == coverage['represented'] == 55
    assert coverage['verified_metadata'] == 14 and coverage['blocking_count'] == 42
    assert verification['static_plan_binding'] == 'PASS'
    assert verification['static_policy']['status'] == 'PASS'
    protected = load('protected_inputs.json')['files']
    ordinary = [row for row in protected if not row['authorized_card']]
    for row in ordinary:
        assert sha((ROOT / row['ref']).read_bytes()) == row['sha256'], 'Protected input drift'
    assert len(protected) == 209 and len(ordinary) == 208
    save('checks.json', {
        'task_id': TASK,
        'status': 'RESULT READY / AWAITING INDEPENDENT VERIFICATION',
        'toolkit_release': '0.1.0-offline',
        'source_pins_current': checked,
        'PS7_final': {'passed': 62, 'total': 62, 'failed': 0,
                      'source': 'synthetic_evidence/attempt06_ps7/results.json',
                      'protocol_port_model_points_in_one_case': 2048,
                      'not_os_native_tests': True},
        'PS51_final': {'parser_files': 8, 'parse_errors': 0,
                       'policy': parser['execution_policy'], 'override': False,
                       'runtime_suite': 'NOT RUN', 'collector': 'NOT RUN',
                       'source': 'synthetic_evidence/syntax_ps51_release.json'},
        'legacy_PS51_deviation': {
            'early_prototype_passed': 47,
            'process_only_ExecutionPolicy_Bypass': True,
            'persistent_policy_store_changed': False,
            'process_exited': True,
            'final_release_runtime_certification': False,
            'disposition': 'Disclosed; not repeated; no bypass in toolkit'},
        'discovery': {'required': 55, 'represented': 55, 'representation_percent': 100,
                      'metadata_verified': 14, 'blocking_requirements': 42,
                      'readiness': 'BLOCKED', 'bounded_metadata_runs': 3,
                      'source': 'host_discovery_release/'},
        'plan': {'rebuild_equal': True, 'static_binding': 'PASS',
                 'independent_static_predicates': 'PASS',
                 'security_verdict': 'NOT VERIFIED'},
        'operational_calls': {'native_subject_launches': 0, 'install_wrapper_invocations': 0,
                              'uninstall_wrapper_invocations': 0, 'network_probes': 0,
                              'account_rights_ACL_WFP_firewall_changes': 0,
                              'V2Ray_route_DNS_service_task_changes': 0, 'git_github_calls': 0,
                              'scope': 'Agent commands/source; no host-wide traffic claim'},
        'protected_inputs': {'total': 209, 'noncard_unchanged_before_rotation': 208,
                             'authorized_card_only': True, 'final': 'integrity.json'},
        'live_install': 'BLOCKED / NO EXECUTABLE SECURITY BACKEND',
        'live_rollback': 'BLOCKED / KEEP DENY',
        'OS_ENFORCED_EGRESS_ISOLATION': 'NOT VERIFIED',
        'NATIVE_CLIENT_FAIL_CLOSED': 'NOT VERIFIED',
        'V2RAY_REMOTE_ROUTE': 'NOT VERIFIED',
        'HOSTED_TUNNEL': 'NOT STARTED',
        'ORDINARY_CHAT_E2E': 'NOT VERIFIED',
        'independent_acceptance': 'PENDING WEB_10',
        'publication': 'LOCAL ONLY / USER PUBLICATION NOT VERIFIED'
    })
    print(json.dumps({'sources_current': len(checked), 'synthetic': '62/62',
                      'coverage': '55/55', 'pre_rotation_noncard_unchanged': len(ordinary)}))


def privacy(final=False):
    """Bounded pattern/schema review, not proof that arbitrary data is nonsecret."""
    findings, reviewed = [], []
    patterns = {
        'private_user_path': r'(?i)[A-Z]:[\\/]+Users[\\/]+(?!PRIVATE_PERSON(?:[\\/]|\b))[^\s\\/\"\']+',
        'machine_name_literal': r'\bDESKTOP-[A-Z0-9]{5,}\b',
        'real_account_sid_shape': r'\bS-1-5-21-\d+-\d+-\d+-\d+\b',
        'credential_token_shape': r'\b(?:sk-proj-|sk-)[A-Za-z0-9_-]{24,}\b|\bBearer\s+[A-Za-z0-9._-]{20,}'
    }
    ip_candidates = set()
    files = [p for p in OUT.rglob('*') if p.is_file() and p.suffix != '.pending']
    for path in files:
        content = path.read_bytes()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            findings.append({'ref': path.relative_to(OUT).as_posix(), 'code': 'NON_UTF8_REVIEW_REQUIRED'})
            continue
        for code, expression in patterns.items():
            if re.search(expression, text):
                findings.append({'ref': path.relative_to(OUT).as_posix(), 'code': code})
        for candidate in re.findall(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])', text):
            try:
                address = ipaddress.ip_address(candidate)
            except ValueError:  # Windows / PowerShell dotted version, not IPv4
                continue
            ip_candidates.add(str(address))
            allowed = address.is_loopback or address.is_unspecified or str(address) in (
                '224.0.0.1', '255.255.255.255') or any(address in ipaddress.ip_network(net)
                for net in ('192.0.2.0/24', '198.51.100.0/24', '203.0.113.0/24'))
            if not allowed:
                findings.append({'ref': path.relative_to(OUT).as_posix(), 'code': 'IP_LITERAL_REVIEW_REQUIRED'})
        reviewed.append(path.relative_to(OUT).as_posix())
    assert not findings, json.dumps(findings, ensure_ascii=True)
    save('privacy_review_final.json' if final else 'privacy_review.json', {
        'scope': 'Bounded UTF-8/schema and identifier/token-shape review plus manual public field walkthrough',
        'files_reviewed': len(reviewed), 'findings': [],
        'allowed_address_classes': 'loopback, unspecified and explicit synthetic RFC5737/multicast fixtures',
        'raw_historic_card_copied': False,
        'external_connection_config_or_secret_store_read': False,
        'limitations': 'Pattern review is not a universal secret detector. New private inputs/LocalPreview need a new privacy review.',
        'gitignore': 'Root .gitignore read only; TASK source/evidence names not matched by its visible patterns. Global Git excludes not inspected; Git not invoked.'
    })
    print(json.dumps({'privacy_review_files': len(reviewed), 'findings': len(findings)}))


def rotate():
    receipt_path = OUT / 'card_rotation.json'
    assert not receipt_path.exists(), 'One-shot receipt already exists'
    initial = load('card_initial.json')
    before = CARD.read_bytes()
    assert sha(before) == initial['before_sha256'], 'Card changed; preserve current work'
    a = before.index('# \u0411\u041b\u041e\u041a 1'.encode())
    z = before.index('# \u0411\u041b\u041e\u041a 2'.encode(), a + 1)
    prefix, assignment, history = before[:a], before[a:z], before[z:]
    assert sha(prefix) == initial['prefix_sha256']
    assert sha(assignment) == initial['assignment_sha256']
    assert assignment == (OUT / 'assignment.md').read_bytes()
    assert len(history) == initial['history_bytes'] and sha(history) == initial['history_sha256']
    assert (OUT / 'report.md').is_file() and (OUT / 'checks.json').is_file()
    assert (OUT / 'privacy_review.json').is_file()
    manifest_bytes = (OUT / 'manifest.json').read_bytes()
    premanifest = json.loads(manifest_bytes)
    for row in premanifest['files']:
        data = (OUT / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], 'Pre-rotation manifest stale'

    b2 = '# \u0411\u041b\u041e\u041a 2 \u2014 \u041f\u041e\u0421\u041b\u0415\u0414\u041d\u042f\u042f \u0412\u042b\u041f\u041e\u041b\u041d\u0415\u041d\u041d\u0410\u042f \u0417\u0410\u0414\u0410\u0427\u0410 \u2014 \u041f\u041e\u0421\u0422\u0410\u041d\u041e\u0412\u041a\u0410\n\n'
    b2 += '## ' + TASK + ' / 2026-10-20\n\n'
    b2 += '\u041f\u043e\u043b\u043d\u0430\u044f \u0438\u0441\u0445\u043e\u0434\u043d\u0430\u044f \u043f\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 \u043d\u0438\u0436\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430 \u0431\u0435\u0437 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439; AMENDMENT \u043a \u044d\u0442\u043e\u0439 TASK \u043d\u0435\u0442.\n\n'
    b3 = f'''\n# БЛОК 3 — FACTUAL RESULT / HANDOFF

## {TASK} / 2026-10-20 / Codex 007

RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_10).
Discovery / Plan / Contracts / static Verify / rollback planner implemented.
Install/Uninstall mutation backend is absent: APPLY BLOCKED; keep deny.
Permitted bounded fallback under assignment sections 6.3/12; no live deployment.

Release PS7 suite 62/62 PASS, 0 FAIL, source-pinned. One case includes 2048
symbolic protocol/port combinations; no OS-native security test implied.
Final PS5.1 AST 8/8 files, 0 parse errors, Restricted, override=false;
final PS5.1 runtime NOT RUN. Early 47-case prototype used process-only
ExecutionPolicy Bypass once; no persistent policy change, disclosed deviation,
not final-release certification, not repeated or recommended.

Real bounded metadata release: 55/55 fields represented, 14 metadata VERIFIED,
42 blocking requirements. Three metadata runs during source/contract refinement.
11-action plan rebuilt identically; binding and independent symbolic static
policy checks PASS. Unknown/negative security facts remain blockers.

No account/rights/ACL/WFP/firewall/startup/network/V2Ray changes, native subject
launches, hosted tunnel, Install/Uninstall invocation or Git/GitHub operations.
OS-enforced isolation / native fail-closed / V2Ray route / ordinary Chat E2E:
NOT VERIFIED. C# backend source-only scaffold, not compiled/loaded.
Windows11 synthetic only; no blanket Windows/PS5 runtime certification.

All artifacts: reports/{TASK}/
report.md; manifest.json; checks.json; toolkit/README.md; toolkit/tests/;
host_discovery_release/; verification_release.json;
synthetic_evidence/attempt06_ps7/results.json;
synthetic_evidence/syntax_ps51_release.json;
manual_engineering_review.md; known_limitations.md; next_stage_plan.md;
privacy_review.json; card_rotation.json; integrity.json.

Protected baseline: 209 project files; 208 noncard hashes checked before
rotation. Only own card authorized; final readback in integrity.json.
Rules prefix and full old history preserved byte-for-byte. Full assignment
saved above before clearing B1. No historical raw card copy in public bundle.
Report/evidence/manifest saved before rotation; receipt binds their hashes.
DOC IMPACT: new own TASK directory + own card rotation only. Shared 18/19/34,
Claude/LLM12, production and working launcher untouched. SHARED DOC DELTA for
19/34 supplied in report only. Source pin from assignment not Git-verified.
Publication and independent acceptance NOT VERIFIED; user handles handoff.
NEXT: independent WEB_10 source/manifest review, then separately authorized
isolated-lab backend implementation/proof. No live Apply from this evidence.

---

## Архив прежних БЛОКОВ 2–3 — без изменения байтов прежней истории

'''
    tail = b2.encode('utf-8') + assignment + b3.encode('utf-8') + history
    stage = prefix + assignment + tail
    waiting = '# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА\n\nОЖИДАНИЕ НОВОЙ ЗАДАЧИ\n\n---\n\n'.encode('utf-8')
    final = prefix + waiting + tail
    pending = OUT / '.card.pending'
    assert pending.parent.resolve() == OUT.resolve() and not pending.exists()
    errors = []

    def replace_exact(expected, desired, phase):
        assert CARD.read_bytes() == expected, 'Card changed; do not overwrite'
        with pending.open('xb') as stream:
            stream.write(desired)
            stream.flush()
            os.fsync(stream.fileno())
        assert pending.read_bytes() == desired
        for attempt in range(2):
            assert CARD.read_bytes() == expected, 'Concurrent card change'
            try:
                os.replace(pending, CARD)
                break
            except PermissionError as error:
                errors.append({'phase': phase, 'attempt': attempt + 1,
                               'error_class': type(error).__name__, 'winerror': error.winerror})
                if attempt == 1:
                    raise
                time.sleep(0.15)
        assert CARD.read_bytes() == desired, 'Card readback mismatch'

    try:
        replace_exact(before, stage, 'save_B2_B3_history')
        saved = CARD.read_bytes()
        assert saved == stage and saved.endswith(history) and assignment in saved[len(prefix)+len(assignment):]
        replace_exact(stage, final, 'clear_B1_after_readback')
        saved = CARD.read_bytes()
        assert saved == final and saved.endswith(history)
        assert saved[:len(prefix)] == prefix
        status = 'CARD ROTATION SAVED / B1 WAITING'
    except Exception as error:
        # Pending is the exact owned staging file, never the only copy of history.
        current = CARD.read_bytes()
        if pending.exists() and current in (before, stage, final):
            assert current.endswith(history)
            assert pending.read_bytes() in (stage, final)
            assert pending.resolve().parent == OUT.resolve()
            pending.unlink()  # one verified owned file, no recursive operation
        save('card_rotation.json', {
            'status': 'CARD ROTATION BLOCKED', 'error_class': type(error).__name__,
            'before_sha256': sha(before), 'current_sha256': sha(current),
            'history_preserved': current.endswith(history), 'retry_events': errors})
        raise
    save('card_rotation.json', {
        'status': status,
        'before_sha256': sha(before), 'stage_sha256': sha(stage), 'final_sha256': sha(final),
        'prefix_sha256': sha(prefix), 'prefix_bytes': len(prefix),
        'assignment_sha256': sha(assignment), 'assignment_bytes': len(assignment),
        'old_history_sha256': sha(history), 'old_history_bytes': len(history),
        'full_assignment_preserved': True, 'old_history_preserved': True,
        'B2_B3_readback_before_B1_clear': True, 'B1_waiting': True,
        'report_before_rotation_sha256': sha((OUT / 'report.md').read_bytes()),
        'premanifest_sha256': sha(manifest_bytes),
        'no_raw_card_backup_in_public_bundle': True, 'retry_events': errors,
        'rollback': 'Only with explicit authorization and matching final card SHA: use unchanged prefix + assignment.md + old-history suffix, validate reconstructed before SHA; stop on any concurrent change.'
    })
    print(json.dumps({'status': status, 'old_history_bytes': len(history),
                      'prefix_unchanged': True, 'retry_events': errors}))


def finalize():
    source_checks()
    receipt = load('card_rotation.json')
    initial = load('card_initial.json')
    integrity = load('integrity.json')
    data = CARD.read_bytes()
    assert sha(data) == receipt['final_sha256'], 'Concurrent card change; stop'
    prefix = data[:receipt['prefix_bytes']]
    history = data[-receipt['old_history_bytes']:]
    assignment = (OUT / 'assignment.md').read_bytes()
    assert sha(prefix) == receipt['prefix_sha256']
    assert sha(history) == receipt['old_history_sha256']
    assert sha(prefix + assignment + history) == initial['before_sha256']
    active = data[len(prefix):data.index('# БЛОК 2'.encode(), len(prefix))]
    assert 'ОЖИДАНИЕ НОВОЙ ЗАДАЧИ'.encode() in active
    assert TASK.encode() not in active
    assert assignment in data[len(prefix)+len(active):]
    assert integrity['unchanged_noncard'] == integrity['protected_noncard'] == 208
    assert len([r for r in integrity['files'] if r['authorized_card'] and not r['unchanged']]) == 1
    save('handoff_verification.json', {
        'status': 'LOCAL HANDOFF CHECKED / INDEPENDENT ACCEPTANCE PENDING',
        'final_card_sha256': sha(data), 'B1_waiting': True,
        'original_card_reconstructs_byte_exactly': True,
        'old_history_bytes': len(history), 'prefix_unchanged': True,
        'full_assignment_in_B2': True, 'protected_noncard_unchanged': 208,
        'runtime_source_pins_still_current': True,
        'handoff_helper_correction': {
            'initial_final_integrity_attempts': 2,
            'error': 'FileNotFoundError from locale-dependent JSON decoding of Cyrillic paths',
            'fix': 'Explicit utf-8-sig for authoring helper JSON reads',
            'final_check': 'PASS',
            'files_were_not_missing_or_recreated': True,
            'toolkit_runtime_or_test_results_changed': False},
        'card_retry': receipt['retry_events'],
        'independent_verifier': 'WEB_10 / PENDING'
    })
    checks_data = load('checks.json')
    checks_data['card_rotation'] = {
        'status': receipt['status'], 'old_history_bytes_preserved': len(history),
        'B1_waiting': True, 'rollback_reconstruction_hash_checked': True}
    checks_data['protected_inputs']['noncard_unchanged_final'] = 208
    (OUT / 'checks.json').write_text(json.dumps(checks_data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    closing = '''
## Фактическое закрытие локального исполнения

`card_rotation.json` и независимый readback `handoff_verification.json`
подтверждают: B2/B3 сохранены до очистки B1; B1 = **ОЖИДАНИЕ НОВОЙ ЗАДАЧИ**.
Rule prefix не изменён, все **463 833 bytes** прежней истории byte-exact;
из prefix + assignment.md + history suffix реконструируется исходный card SHA.
Публичная raw-копия исторической карточки не создавалась.

При втором atomic replace был WinError 5; один ограниченный retry после
повторной проверки expected card SHA завершился успешно. Права/атрибуты не
перенастраивались, процессы/Obsidian не останавливались. Финальная сверка
`integrity.json`: **208/208 noncard файлов неизменны**, own card — единственное
изменение защищённого baseline. Два первых вызова handoff integrity reader
показали ошибку locale-decoding кириллических JSON paths; исправлен только
authoring helper на явный UTF-8. Никакие исходные файлы не восстанавливались
и не переписывались для прохождения этой проверки.

Очищенный package дополнительно проверен на типичные private user paths,
machine/SID/token shapes и реальные IPv4 literals; итог —
`privacy_review_final.json`. Это bounded review, не универсальный detector
секретов; новые private inputs потребуют нового review. Root .gitignore
прочитан как обычный файл: видимые правила не исключают новые source/evidence
имена TASK. Global excludes и фактическая Git-публикация не проверялись.

Полный текущий список размеров/SHA-256 — финальный `manifest.json` (сам manifest
исключён из собственного списка). Предротационный manifest имел другой hash;
receipt сохраняет именно предротационный контрольный hash, не выдаёт его за
конечный. После добавления closing evidence final manifest сформирован заново.

Итог для копирования WEB_10 — `factual_result.txt`. Независимая приёмка,
реальная установка, OS/native fail-closed, V2Ray remote route и ordinary Chat
E2E этим локальным закрытием не подтверждены.
'''
    report = OUT / 'report.md'
    current_report = report.read_text(encoding='utf-8')
    assert '## Фактическое закрытие локального исполнения' not in current_report
    report.write_text(current_report + closing, encoding='utf-8', newline='\n')
    factual = f'''TASK: {TASK}
RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_10).
Готово: переносимые Discovery, Contracts, Plan, static Verify, rollback planner.
Реальные Install/Uninstall: BLOCKED — executable security backend отсутствует.
Проверки: финальные PS7 62/62 PASS, 0 FAIL; PS5.1 AST 8/8, 0 ошибок, runtime NOT RUN (Restricted).
Ранний PS5.1 prototype запускался с process-only Bypass; отклонение раскрыто, финальной сертификацией не считается.
Реальный read-only inventory: 55/55 полей представлены, 14 metadata VERIFIED, 42 блокирующих требования.
План: 11 действий, повторная сборка идентична; binding/static invariants PASS.
OS isolation / native fail-closed / V2Ray route / ordinary Chat E2E: NOT VERIFIED; hosted tunnel NOT STARTED.
Windows, учётные записи, сеть, WFP/firewall, V2Ray и Git/GitHub не изменялись.
DOC IMPACT: reports/{TASK}/ + ротация собственной карточки; 208/208 остальных protected файлов неизменны.
Карточка: полная постановка в БЛОКЕ 2, factual result в БЛОКЕ 3, БЛОК 1 — ОЖИДАНИЕ НОВОЙ ЗАДАЧИ; история сохранена.
Артефакты: report.md, manifest.json, toolkit/README.md, checks.json, evidence и manual_engineering_review.md в TASK-папке.
NEXT: независимая проверка WEB_10; затем отдельный USER GO на изолированный lab backend/proof. Реальный Apply сейчас запрещён.
'''
    with (OUT / 'factual_result.txt').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(factual)
    print(json.dumps({'card_reconstruction': 'PASS', 'history_bytes': len(history),
                      'protected_noncard': '208/208', 'finalization': 'READY FOR FINAL PRIVACY AND SEAL'}))


if __name__ == '__main__':
    {'checks': checks, 'privacy': privacy, 'privacy-final': lambda: privacy(True),
     'rotate': rotate, 'finalize': finalize}[sys.argv[1]]()
