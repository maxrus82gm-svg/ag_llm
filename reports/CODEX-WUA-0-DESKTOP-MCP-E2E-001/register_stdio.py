"""Authorized append-only registration in documented user config; no UI automation.

Full config backup stays outside the repository. No existing setting is replaced.
Abort on a name collision or config drift. Writes only this task and own user backup,
plus the one explicitly authorized config file.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import uuid

BASE = Path(__file__).resolve().parent
CONFIG = Path('C:/Users/REX/.codex/config.toml')
CLI = Path('C:/Users/REX/AppData/Local/OpenAI/Codex/bin/9614f1d9b40d9c4f/codex.exe')
KEY = 'wua_desktop_readonly'
TASK = 'CODEX-WUA-0-DESKTOP-MCP-E2E-001'
BACKUPS = Path('C:/Users/REX/.codex/backups') / TASK


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main():
    if os.environ.get('CODEX_HOME'):
        raise RuntimeError('Unexpected CODEX_HOME; inspect host before registration')
    output = BASE / 'stdio_registration_01.json'
    if output.exists():
        raise RuntimeError('Registration record exists; do not repeat mutation')
    source_path = BASE / 'plugin/mcp.json'
    source_raw = source_path.read_bytes()
    source = json.loads(source_raw)['mcpServers'][KEY]
    if source['type'] != 'stdio':
        raise RuntimeError('Expected stdio candidate')
    plugin_root = (BASE / 'plugin').as_posix()
    entry = {
        'command': source['command'],
        'args': [item.replace('${PLUGIN_ROOT}', plugin_root) for item in source['args']],
        'cwd': source['cwd'].replace('${PLUGIN_ROOT}', plugin_root),
    }
    if not Path(entry['command']).is_file() or not Path(entry['cwd']).is_dir():
        raise RuntimeError('Command or cwd missing')
    if not Path(entry['args'][-1]).is_file():
        raise RuntimeError('Entry point missing')
    before = CONFIG.read_bytes()
    parsed_before = tomllib.loads(before.decode('utf-8-sig'))
    if KEY in parsed_before.get('mcp_servers', {}):
        raise RuntimeError('Existing WUA config; refuse to overwrite')
    newline = '\r\n' if b'\r\n' in before else '\n'
    block = (newline + '# WUA Desktop Read-only; ' + TASK + newline
             + '[mcp_servers.' + KEY + ']' + newline
             + 'command = ' + json.dumps(entry['command']) + newline
             + 'args = ' + json.dumps(entry['args']) + newline
             + 'cwd = ' + json.dumps(entry['cwd']) + newline).encode('utf-8')
    after = before + block
    parsed_after = tomllib.loads(after.decode('utf-8-sig'))
    assert parsed_after['mcp_servers'].pop(KEY) == entry
    if parsed_after != parsed_before:
        raise RuntimeError('Proposed change affects another setting')
    checkpoint = BASE / 'checkpoints/pre_stdio_registration'
    checkpoint.mkdir(exist_ok=False)
    for name in ('report.md', 'status.json', 'manifest.json'):
        write_new(checkpoint / name, (BASE / name).read_bytes())
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    backup = BACKUPS / stamp
    backup.mkdir(parents=True, exist_ok=False)
    write_new(backup / 'config.before.toml', before)
    write_new(backup / 'wua.appended.bin', block)
    state = {
        'task_id': TASK, 'config_path': str(CONFIG), 'backup_path': str(backup / 'config.before.toml'),
        'appended_path': str(backup / 'wua.appended.bin'),
        'before_sha256': sha(before), 'after_sha256': sha(after),
        'source_mcp_sha256': sha(source_raw), 'added_key': KEY, 'entry': entry,
    }
    write_new(backup / 'state.json', json.dumps(state, indent=2).encode('utf-8'))
    descriptor, temporary = tempfile.mkstemp(prefix='config.wua-', suffix='.tmp', dir=backup)
    temp_path = Path(temporary)
    applied = False
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        if CONFIG.read_bytes() != before:
            raise RuntimeError('Config changed after backup; no mutation performed')
        os.replace(temp_path, CONFIG)
        applied = True
        observed = CONFIG.read_bytes()
        if observed != after:
            raise RuntimeError('Config drift after write; preserve backup and inspect')
        readback = subprocess.run([str(CLI), 'mcp', 'get', KEY, '--json'],
                                  capture_output=True, text=True, encoding='utf-8', timeout=20)
        if readback.returncode:
            raise RuntimeError('CLI readback failed: ' + readback.stderr[:600])
        readback_value = json.loads(readback.stdout)
        transport = readback_value['transport']
        if transport['type'] != 'stdio' or any(transport[k] != entry[k] for k in entry):
            raise RuntimeError('CLI readback differs from exact candidate values')
        record = {
            **state, 'registered_utc': datetime.now(timezone.utc).isoformat(),
            'method': 'Official documented ~/.codex/config.toml, append-only new MCP table',
            'supported_scope': 'ChatGPT Desktop / CLI / IDE sharing same local Codex host; ordinary Chat exposure unverified',
            'backup_state_path': str(backup / 'state.json'),
            'original_bytes_preserved_as_prefix': observed.startswith(before),
            'all_existing_settings_unchanged': True,
            'existing_mcp_servers_unchanged': sorted(parsed_before.get('mcp_servers', {})),
            'cli_get': readback_value, 'desktop_e2e': 'NOT VERIFIED / MCP TOOLS UNAVAILABLE',
            'ordinary_chat_real_tool_calls': 0,
            'app_restarted': False, 'permissions_changed': False, 'network_settings_changed': False,
            'github_actions': 0,
        }
        write_new(output, json.dumps(record, ensure_ascii=False, indent=2).encode('utf-8'))
        print(json.dumps({'registered': True, 'key': KEY, 'backup_state_path': str(backup / 'state.json'),
                          'existing_settings_unchanged': True, 'config_after_sha256': sha(observed),
                          'desktop_e2e': record['desktop_e2e']}, ensure_ascii=False))
    except BaseException:
        if applied and CONFIG.read_bytes() == after:
            recovery = backup / 'config.recover.tmp'
            write_new(recovery, before)
            os.replace(recovery, CONFIG)
            assert CONFIG.read_bytes() == before
        raise
    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == '__main__':
    main()
