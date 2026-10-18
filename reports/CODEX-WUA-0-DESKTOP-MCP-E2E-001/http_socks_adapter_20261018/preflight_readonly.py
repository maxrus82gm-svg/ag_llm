"""AM07 file/process/listener inventory, no live socket or external probes."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shlex
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
TASK = OUT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ps(command):
    script = '[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); @(' + command + ') | ConvertTo-Json -Depth 4'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                            capture_output=True, encoding='utf-8-sig', errors='replace', timeout=25)
    if result.returncode:
        raise RuntimeError('inventory command failed; private raw output withheld')
    data = json.loads(result.stdout or '[]')
    return data if isinstance(data, list) else [data] if data else []


def main():
    processes = ps("Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(v2rayN|sing-box)\\.exe$'} | Select-Object Name,ProcessId,ParentProcessId,ExecutablePath,CommandLine")
    listeners = ps('Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess')
    facts = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'processes': [], 'config_candidates': [], 'live_socket_probes': 0,
             'gui_settings_are_loaded_core_evidence': False,
             'http_inbound': 'NOT VERIFIED', 'remote_route': 'NOT VERIFIED'}
    private_hashes = []
    for proc in processes:
        exe = Path(proc['ExecutablePath']) if proc.get('ExecutablePath') else None
        facts['processes'].append({'name': proc['Name'], 'pid': proc['ProcessId'],
                                  'parent_pid': proc['ParentProcessId'],
                                  'executable_path_available': bool(proc.get('ExecutablePath')),
                                  'command_line_available': bool(proc.get('CommandLine')),
                                  'exe_sha256': sha(exe) if exe and exe.is_file() else None,
                                  'listeners': [{'address': x['LocalAddress'] if x['LocalAddress'] in ('127.0.0.1', '::1') else 'nonloopback-redacted',
                                                 'port': x['LocalPort']} for x in listeners if x['OwningProcess'] == proc['ProcessId']]})
        if proc['Name'].lower() == 'v2rayn.exe' and exe:
            for name in ('guiNConfig.json', 'guiNDB.db'):
                path = exe.parent / 'guiConfigs' / name
                if path.is_file():
                    private_hashes.append({'role': name, 'path': str(path), 'sha256': sha(path),
                                           'content_exported': False})
        if proc['Name'].lower() != 'sing-box.exe':
            continue
        tokens = shlex.split(proc.get('CommandLine') or '', posix=False)
        for index, token in enumerate(tokens[:-1]):
            if token not in ('-c', '--config'):
                continue
            path = Path(tokens[index + 1].strip('"'))
            absolute = path.is_absolute()
            candidates = [path] if absolute else []
            if not absolute and exe:
                manager = next((x for x in processes if x['ProcessId'] == proc['ParentProcessId']), {})
                bases = [exe.parent]
                if manager.get('ExecutablePath'):
                    parent = Path(manager['ExecutablePath']).parent
                    bases += [parent, parent / 'binConfigs']
                candidates = list(dict.fromkeys(base / path for base in bases))
            existing = [p for p in candidates if p.is_file()]
            row = {'process_pid': proc['ProcessId'], 'argument_absolute': absolute,
                   'actual_cwd_known': False, 'candidate_files_found': len(existing),
                   'loaded_content_attested': False, 'inbounds_from_candidate_only': []}
            for candidate in existing:
                private_hashes.append({'role': 'core-config-candidate', 'path': str(candidate),
                                       'sha256': sha(candidate), 'content_exported': False})
                try:
                    config = json.loads(candidate.read_text(encoding='utf-8-sig'))
                    for inbound in config.get('inbounds', []):
                        row['inbounds_from_candidate_only'].append({
                            'type': inbound.get('type') if inbound.get('type') in ('http', 'socks', 'mixed', 'tun') else 'other',
                            'listen': inbound.get('listen') if inbound.get('listen') in ('127.0.0.1', '::1') else 'redacted',
                            'port': inbound.get('listen_port')})
                    row['direct_outbound_declared_in_candidate'] = any(x.get('type') == 'direct' for x in config.get('outbounds', []))
                    row['dns_config_present'] = bool(config.get('dns'))
                except (ValueError, UnicodeError):
                    row['candidate_parse'] = 'NOT STANDARD JSON'
            facts['config_candidates'].append(row)
    facts['private_file_fingerprints'] = private_hashes
    facts['conclusion'] = 'Listener ownership does not identify protocol. Relative config argument without actual cwd does not prove loaded config. GUI policy is only saved state.'
    (OUT / 'preflight.sanitized.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    roots = [TASK, Path(r'C:\Users\REX\Downloads'), Path(r'C:\Users\REX\.codex\attachments')]
    target = 'tunnel-client-runtime-source-v0.0.16.tar.gz'
    hits = []
    for root in roots:
        for parent, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ('.git', '.venv', 'node_modules', 'site-packages', '__pycache__') and not Path(parent, d).is_symlink()]
            if target in files:
                p = Path(parent, target)
                hits.append({'path': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size})
    source = {'asset': target, 'expected_sha256': '88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0',
              'roots': list(map(str, roots)), 'matches': hits,
              'status': 'SOURCE PACK BLOCKED' if not hits else 'FOUND; VERIFY BEFORE READING',
              'remote_fetches': 0, 'git_github_calls': 0}
    (OUT / 'source_pack_search.json').write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'processes': facts['processes'], 'configs': facts['config_candidates'], 'source_pack': source['status']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
