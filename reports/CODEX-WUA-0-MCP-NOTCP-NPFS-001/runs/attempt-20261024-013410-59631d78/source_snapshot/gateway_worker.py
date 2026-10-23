"""U-owned SDK authority on a new TASK fixture; never opens an existing root.

Reuse the four tools and MCP SDK unchanged. This replaces only the channel with
in-process scoped WebAlarmApi dispatch, after fixture setup and storage pinning.
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path
sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
from common import (FIXTURE, REPO, Denied, canonical, digest, exact,
                    install_fixture_guard, parse, request_id, require, tree_hash)
from server import serve

TASK = 'CODEX-WUA-0-MCP-NOTCP-NPFS-001'

def run_root(value):
    from ctypes import windll
    p = Path(os.path.abspath(value))
    base = REPO / 'reports' / TASK / 'runs'
    require(p != base and p.is_relative_to(base) and not str(value).startswith(('\\\\', '//')), 'RUN_SCOPE')
    require(windll.kernel32.GetDriveTypeW(str(p.anchor)) in (2, 3), 'LOCAL_VOLUME')
    for node in [p, *p.parents]:
        require(node.exists() and not node.is_symlink() and not (node.stat().st_file_attributes & 0x400), 'REPARSE_PATH')
    return p

class Authority:
    def __init__(self, run):
        self.run = run
        b = parse((run / 'fixture.json').read_bytes())
        exact(b, ['schema', 'session_id', 'nonce', 'mode'])
        require(b['schema'] == 1 and type(b['schema']) is int and b['mode'] == 'synthetic_fixture_only', 'FIXTURE_ONLY')
        request_id(b['session_id'])
        require(type(b['nonce']) is str and re.fullmatch('[0-9a-f]{64}', b['nonce']), 'NONCE')
        self.b, self.rows, self.seen = b, [], set()
        self.root = run / 'owned-api-state'
        self.root.mkdir()  # no exist_ok: refuse reopening storage
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        sys.path.insert(0, str(REPO))
        from web_alarm.server import WebAlarmApi
        self.api = WebAlarmApi(self.root / 'state')
        code, _ = self.api.dispatch('POST', '/workspaces', {'workspace_id': 'synthetic_integration_ws', 'display_name': 'Disposable integration fixture', 'workspace_root': str(self.workspace)})
        require(code == 201, 'SETUP_WORKSPACE')
        code, _ = self.api.dispatch('POST', '/tasks', {'workspace_id': 'synthetic_integration_ws', 'task_id': FIXTURE, 'title': 'Synthetic MCP integration', 'raw_task': 'Synthetic read-only scope only', 'goal': 'synthetic nonce: ' + b['nonce']})
        require(code == 201, 'SETUP_TASK')
        self.baseline = tree_hash(self.root)
        self.seed_files = {p.relative_to(self.root).as_posix(): __import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}

    def call(self, operation, rid, task_id=FIXTURE):
        request_id(rid)
        require(task_id == FIXTURE and operation in ('status', 'context'), 'SCOPE_DENIED')
        require(rid not in self.seen and len(self.seen) < 64, 'REPLAY_OR_QUOTA')
        self.seen.add(rid)
        route = '/status' if operation == 'status' else '/tasks/' + FIXTURE + '/context'
        code, data = self.api.dispatch('GET', route)
        require(code == 200, 'API_READ')
        if operation == 'status':
            value = {k: data[k] for k in ['status', 'service', 'api_version', 'mode']}
        else:
            value = {'TASK': {k: data['TASK'][k] for k in ['task_id', 'title', 'status']}, **{k: data[k] for k in ['GOAL', 'CURRENT_STATUS', 'NEXT_SAFE_ACTION', 'AUTHORITY_SOURCE']}, 'CHECKPOINT': {k: data['CHECKPOINT'][k] for k in ['status', 'authoritative']}}
        current = tree_hash(self.root)
        require(current == self.baseline, 'READ_MUTATED_STORAGE')
        self.rows.append({'request_id': rid, 'operation': operation, 'route': route, 'content_sha256': digest(value)})
        return {'session_id': self.b['session_id'], 'nonce': self.b['nonce'], 'api_reads': len(self.rows), 'api_route': route, 'baseline_sha256': self.baseline, 'current_sha256': current, 'value': value}

    def close(self):
        receipt = {'schema': 1, 'session_id': self.b['session_id'], 'nonce': self.b['nonce'], 'api_reads': self.rows, 'seed_files': self.seed_files, 'baseline_sha256': self.baseline, 'final_sha256': tree_hash(self.root), 'worker_pid': os.getpid(), 'closed': True}
        with (self.run / 'authority_receipt.json').open('x', encoding='utf-8') as f:
            json.dump(receipt, f, indent=2)

def main():
    require(len(sys.argv) == 2, 'FIXTURE_ARGUMENTS')
    root = run_root(sys.argv[1])
    runner = asyncio.Runner()
    runner.get_loop()  # U-owned only; never part of C relay
    authority = None
    try:
        install_fixture_guard(root)
        authority = Authority(root)
        runner.run(serve(authority))
    finally:
        try:
            if authority:
                authority.close()
        finally:
            runner.close()

if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        sys.stderr.write('U_SDK_STOP:' + (str(exc) if isinstance(exc, Denied) else type(exc).__name__) + '\n')
        sys.exit(20)
