"""Offline final artifact validation/sealing. No subprocesses or sockets.

Rerunning refreshes only this folder's integrity/execution/validation/manifest.
Original artifact failure retained in validation_attempt01.txt.
"""
import ast
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def load(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    target = OUT / name
    assert target.parent == OUT
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    issues = []
    rows = []
    for row in load('inputs_before.json')['inputs']:
        path = Path(row['path'])
        path = path if path.is_absolute() else ROOT / path
        current = sha(path) if path.is_file() else None
        rows.append({'path': row['path'], 'before_sha256': row['sha256'],
                     'after_sha256': current, 'unchanged': current == row['sha256']})
    integrity = load('integrity.json')
    integrity.update(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     checks=rows, unchanged=sum(x['unchanged'] for x in rows),
                     drift=[x for x in rows if not x['unchanged']])
    save('integrity.json', integrity)
    assert integrity['unchanged'] == integrity['protected_files'] == 70, 'PROTECTED INPUT DRIFT'
    parsed_json, syntax, scanned = [], [], []
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path.is_symlink():
            issues.append('Unexpected directory/symlink:' + path.name)
            continue
        if path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8'))
            parsed_json.append(path.name)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            syntax.append({'path': path.name, 'sha256': sha(path), 'status': 'PASS'})
        if path.suffix not in ('.json', '.py', '.ps1', '.txt', '.md'):
            issues.append('Unexpected extension:' + path.name)
            continue
        text = path.read_text(encoding='utf-8-sig')
        scanned.append(path.name)
        for label, pattern in [
            ('API_KEY', r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}'),
            ('JWT', r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),
            ('PRIVATE_KEY', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
        ]:
            if re.search(pattern, text):
                issues.append(label + ':' + path.name)
    audit, symbols, excerpts = load('static_audit.json'), load('binary_symbols.json'), load('binary_excerpts.json')
    gate, checks, plan = load('native_gate_result.json'), load('checks.json'), load('native_test_plan.json')
    execution = load('execution.json')
    execution['syntax'] = syntax
    execution['artifact_validation_history'] = [
        {'attempt': 1, 'status': 'HARNESS DEFECT', 'evidence': 'validation_attempt01.txt'},
        {'attempt': 2, 'source': 'validate_artifacts.py', 'status': 'PASS IF THIS RUN SEALS SUCCESSFULLY'}
    ]
    save('execution.json', execution)
    report = (OUT / 'report.md').read_text(encoding='utf-8')
    source_request = (OUT / 'source_request.md').read_text(encoding='utf-8')
    assert checks['counts'] == dict(collections.Counter(x['status'] for x in checks['checks'])) == {'PASS': 17, 'BLOCKED': 5, 'NOT RUN': 4}
    assert len(plan['cases']) == 18 and all(c['status'] == 'BLOCKED' and c['executed'] is False for c in plan['cases'])
    assert gate['native_executed'] == execution['native_transport_tests']['executed'] == 0
    assert audit['exe_sha256'] in report and audit['exe_sha256'] in source_request
    assert str(excerpts[0]['offset']) in (OUT / 'proxy_path_audit.md').read_text(encoding='utf-8')
    assert len(symbols['project_file_paths']) == 177
    assert all(status in report for status in checks['statuses'])
    assert execution['parser_unit_tests']['pass'] == 5
    assert 'Ran 5 tests' in (OUT / 'static_parser_tests.txt').read_text(encoding='utf-8')
    assert len(syntax) == 4
    for check in checks['checks']:
        for name in check['evidence'].split(';'):
            assert (OUT / name).is_file(), 'Missing check evidence:' + name
    launcher = OUT.parent / 'secure_tunnel_preparation/start_tunnel.py'
    assert 'HOSTED_TUNNEL_ON_HOLD_BY_USER' in launcher.read_text(encoding='utf-8')
    assert not issues, issues
    validation = {
        'status': 'PASS', 'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'json_parse_files': parsed_json, 'syntax_files': syntax, 'text_secret_scan_files': len(scanned),
        'secret_patterns_detected': 0, 'secret_scan_limit': 'Bounded pattern scan plus manual review; not a general DLP guarantee.',
        'protected_files_unchanged': 70, 'evidence_rows': 26, 'evidence_counts': checks['counts'],
        'unit_tests': '5/5 parser only', 'native_tests': '0 executed;18 blocked specifications',
        'native_gate_exit': 3, 'evidence_locators_exist': True, 'report_identity_consistent': True,
        'hosted_hold_literal_preserved': True, 'issues': issues,
        'original_validator_failure': 'validation_attempt01.txt (codec name HARNESS DEFECT)',
        'manifest_note': 'Final manifest byte roundtrip checked after sealing; no subsequent file writes.'
    }
    save('artifact_validation.json', validation)
    files = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(OUT.iterdir()) if p.is_file() and p.name != 'manifest.json']
    manifest = {
        'task_id': 'CODEX-WUA-0-DESKTOP-MCP-E2E-001', 'amendment': '06',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/native_client_offline_20261017/',
        'status': 'PARTIAL / NATIVE EXECUTION BLOCKED / AWAITING INDEPENDENT REVIEW',
        'source_revision': 'local byte hashes;no Git read;coordinator main 5f91f7ec35b0a008e2d3a9e0730540731c197d01 not independently verified',
        'native_exe_sha256': audit['exe_sha256'], 'statuses': checks['statuses'], 'files': files,
        'manifest_self_hash': 'Excluded to avoid self-reference; handed off separately',
        'publication': 'LOCAL ONLY / NOT PUBLISHED BY CODEX'
    }
    save('manifest.json', manifest)
    sealed = load('manifest.json')
    assert {p.name for p in OUT.iterdir() if p.is_file() and p.name != 'manifest.json'} == {x['path'] for x in sealed['files']}
    for entry in sealed['files']:
        path = OUT / entry['path']
        assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
    print(json.dumps({'artifact_validation': 'PASS', 'manifest_roundtrip': 'PASS',
                      'files_covered': len(files), 'total_files': len(files) + 1,
                      'bytes_covered': sum(x['bytes'] for x in files),
                      'report_sha256': sha(OUT / 'report.md'), 'manifest_sha256': sha(OUT / 'manifest.json'),
                      'protected_unchanged': 70, 'parser_unit_tests': '5/5 PASS',
                      'native_executed': 0, 'blocked_native_contracts': 18}))


if __name__ == '__main__':
    main()
