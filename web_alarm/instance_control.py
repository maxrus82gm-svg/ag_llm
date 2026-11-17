"""Conservative local inventory of cooperative Web Alarm launcher instances.

Registry entries are hints only. A peer must answer its own loopback identity
endpoint before it can be offered for explicit graceful shutdown.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.request


ROOT = Path(tempfile.gettempdir()) / 'web-alarm-instances-v1'
MAX_ENTRIES = 64


def _record_path(instance_id: str) -> Path:
    if len(instance_id) != 32 or any(ch not in '0123456789abcdef' for ch in instance_id):
        raise ValueError('invalid_instance_id')
    return ROOT / (instance_id + '.json')


def register(server, *, profile: str, storage: str, ui_version: str) -> dict:
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = {'protocol': 1, 'instance_id': secrets.token_hex(16), 'pid': os.getpid(),
              'port': server.server_port, 'started_at': time.time(),
              'executable': str(Path(sys.executable).resolve()),
              'code_path': str(Path(__file__).resolve().parent),
              'ui_version': ui_version, 'profile': profile, 'storage': storage}
    target = _record_path(record['instance_id'])
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(temporary, target)
    server.web_alarm_instance = record
    return record


def unregister(server) -> None:
    own = getattr(server, 'web_alarm_instance', None)
    if own is None:
        return
    target = _record_path(own['instance_id'])
    try:
        if json.loads(target.read_text(encoding='utf-8')) == own:
            target.unlink()
    except (OSError, ValueError):
        pass


def _read_peer(port: int, path: str) -> dict:
    request = urllib.request.Request(f'http://127.0.0.1:{port}{path}', headers={'Cache-Control': 'no-store'})
    with urllib.request.urlopen(request, timeout=0.75) as response:
        if response.status != 200:
            raise ValueError('peer_http_status')
        raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError('peer_response_size')
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError('peer_response_shape')
    return value


def inventory(server) -> list[dict]:
    own = getattr(server, 'web_alarm_instance', None)
    if own is None:
        return []
    rows = []
    for path in sorted(ROOT.glob('*.json'))[:MAX_ENTRIES]:
        try:
            if path.stat().st_size > 8192:
                continue
            row = json.loads(path.read_text(encoding='utf-8'))
            if (type(row) is not dict or row.get('instance_id') != path.stem
                    or type(row.get('port')) is not int or not 1 <= row['port'] <= 65535
                    or type(row.get('pid')) is not int or type(row.get('ui_version')) is not str):
                continue
            if row['instance_id'] == own['instance_id']:
                state = 'CURRENT'
            else:
                try:
                    observed = _read_peer(row['port'], '/ui/instance')
                    valid = all(observed.get(k) == row.get(k) for k in
                                ('protocol', 'instance_id', 'pid', 'port', 'executable', 'code_path', 'ui_version', 'profile', 'storage'))
                except (OSError, ValueError, TimeoutError):
                    valid = False
                state = ('EXTRA_CONFIRMED' if row.get('profile') == own['profile']
                         and row.get('storage') == own['storage'] else 'OTHER_CONFIRMED') if valid else 'UNVERIFIED'
            rows.append({**row, 'state': state, 'stale_ui': row['ui_version'] != own['ui_version']})
        except (OSError, ValueError):
            continue
    if os.name == 'nt':
        registered = {row['pid'] for row in rows}
        rows.extend(_legacy_windows(registered))
    return rows


def _legacy_windows(registered: set[int]) -> list[dict]:
    # Read-only Windows inventory. Never use a process name or this output as
    # termination authority; old builds lack the cooperative identity route.
    script = ("$l=Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
              "Where-Object {$_.LocalAddress -in @('127.0.0.1','::1')}; "
              "$p=Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
              "Where-Object {$_.CommandLine -match 'web_alarm\\.launcher|web_alarm[\\\\/]launcher\\.py'}; "
              "@($p | ForEach-Object {[pscustomobject]@{pid=$_.ProcessId;started_at=[string]$_.CreationDate;"
              "executable=$_.ExecutablePath;standard=($_.CommandLine -match '--standard');"
              "test=($_.CommandLine -match '--require-test');"
              "ports=@($l | Where-Object OwningProcess -eq $_.ProcessId | ForEach-Object LocalPort)}}) | ConvertTo-Json -Compress -Depth 4")
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=5, check=True)
        found = json.loads(result.stdout)
        if type(found) is dict:
            found = [found]
        if type(found) is not list:
            return []
        return [{'protocol': 0, 'instance_id': 'legacy-pid-' + str(item['pid']),
                 'pid': item['pid'], 'port': (item.get('ports') or [None])[0],
                 'started_at': item.get('started_at'), 'executable': item.get('executable'),
                 'code_path': 'UNVERIFIED', 'ui_version': 'UNVERIFIED',
                 'profile': 'standard' if item.get('standard') else 'test' if item.get('test') else 'unknown',
                 'storage': 'UNVERIFIED', 'state': 'LEGACY_UNVERIFIED', 'stale_ui': None}
                for item in found[:32] if type(item) is dict and type(item.get('pid')) is int
                and item['pid'] not in registered]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return []


def cleanup(server, selected: list[str]) -> list[dict]:
    if (type(selected) is not list or len(selected) > 16 or any(type(v) is not str for v in selected)
            or len(set(selected)) != len(selected)):
        raise ValueError('invalid_cleanup_selection')
    current = {row['instance_id']: row for row in inventory(server)}
    results = []
    for instance_id in selected:
        row = current.get(instance_id)
        if row is None or row['state'] != 'EXTRA_CONFIRMED':
            results.append({'instance_id': instance_id, 'state': 'REFUSED_UNVERIFIED'})
            continue
        try:
            capability = _read_peer(row['port'], '/ui/ultra-chat/write-capability')['ultra_chat_write']
            if (capability.get('available') is not True or capability.get('header') != 'X-WebAlarm-Ultra-Chat-Write-Token'
                    or type(capability.get('token')) is not str):
                raise ValueError('peer_write_authority_missing')
            # Recheck identity after acquiring the peer token; port reuse fails closed.
            observed = _read_peer(row['port'], '/ui/instance')
            if any(observed.get(k) != row.get(k) for k in ('instance_id', 'pid', 'port', 'ui_version')):
                raise ValueError('peer_identity_changed')
            wire = json.dumps({'confirmation': 'SHUTDOWN WEB ALARM'}).encode('utf-8')
            request = urllib.request.Request(f"http://127.0.0.1:{row['port']}/ui/shutdown", data=wire,
                headers={'Origin': f"http://127.0.0.1:{row['port']}", 'Content-Type': 'application/json',
                         capability['header']: capability['token']}, method='POST')
            with urllib.request.urlopen(request, timeout=2) as response:
                reply = json.loads(response.read(4096))
                if response.status != 202 or reply.get('state') != 'STOPPING':
                    raise ValueError('peer_shutdown_unconfirmed')
            results.append({'instance_id': instance_id, 'state': 'STOPPING'})
        except (OSError, ValueError, TimeoutError):
            results.append({'instance_id': instance_id, 'state': 'UNCONFIRMED'})
    return results
