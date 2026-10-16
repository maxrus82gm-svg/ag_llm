"""Exact rollback of this task's WUA addition, refusing to erase later changes.

Run only when rollback is requested. Full backup remains outside the repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tomllib

BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true', help='Restore exact pre-registration bytes')
args = parser.parse_args()
record = json.loads((BASE / 'stdio_registration_01.json').read_bytes())
state_path = Path(record['backup_state_path'])
state = json.loads(state_path.read_bytes())
config = Path(state['config_path'])
before = Path(state['backup_path']).read_bytes()
block = Path(state['appended_path']).read_bytes()
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(before) == state['before_sha256']
assert sha(before + block) == state['after_sha256']
current = config.read_bytes()
if current == before:
    print('Already at the exact pre-registration configuration; no changes.')
    raise SystemExit(0)
if current != before + block:
    raise SystemExit('Refusing rollback: config has later changes. Preserve them; inspect only the WUA section separately.')
assert tomllib.loads(current.decode('utf-8-sig'))['mcp_servers'][state['added_key']] == state['entry']
if not args.apply:
    print(json.dumps({'rollback_ready': True, 'exact_before_sha256': state['before_sha256'],
                      'config_path': str(config), 'mutated': False}))
    raise SystemExit(0)
fd, name = tempfile.mkstemp(prefix='rollback-wua-', suffix='.tmp', dir=state_path.parent)
temp = Path(name)
try:
    with os.fdopen(fd, 'wb') as handle:
        handle.write(before)
        handle.flush()
        os.fsync(handle.fileno())
    if config.read_bytes() != current:
        raise RuntimeError('Concurrent config change; refusing rollback')
    os.replace(temp, config)
    assert config.read_bytes() == before
    print(json.dumps({'rolled_back': True, 'sha256': sha(config.read_bytes())}))
finally:
    if temp.exists():
        temp.unlink()
