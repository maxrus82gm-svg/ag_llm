"""Focused SDK check using the registered config, explicitly NOT Desktop E2E."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation

BASE = Path(__file__).resolve().parent
KEY = 'wua_desktop_readonly'
TOOLS = ('ping', 'list_capabilities', 'read_synthetic_context')
canonical_sha = lambda obj: hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


async def run(record):
    registration = json.loads((BASE / 'stdio_registration_01.json').read_bytes())
    config_raw = Path(registration['config_path']).read_bytes()
    entry = tomllib.loads(config_raw.decode('utf-8-sig'))['mcp_servers'][KEY]
    assert entry == registration['entry']
    record['registered_entry_matches'] = True
    record['config_sha256'] = hashlib.sha256(config_raw).hexdigest()
    params = StdioServerParameters(command=entry['command'], args=entry['args'], cwd=entry['cwd'])
    values = []
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as stderr:
        try:
            async with stdio_client(params, errlog=stderr) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=8,
                    client_info=Implementation(name='WUA Local SDK Regression - Registered STDIO Diagnostic', version='0.2.0')) as session:
                    init = await session.initialize()
                    record['server'] = init.server_info.model_dump(mode='json')
                    record['protocol'] = init.protocol_version
                    listing = await session.list_tools()
                    record['tools'] = [t.model_dump(mode='json', by_alias=True, exclude_none=True) for t in listing.tools]
                    assert {t.name for t in listing.tools} == set(TOOLS)
                    assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in listing.tools)
                    for name in TOOLS:
                        result = await session.call_tool(name)
                        record['calls'].append({'tool': name, 'result': result.model_dump(mode='json', by_alias=True, exclude_none=True)})
                        assert not result.is_error
                        values.append(result.structured_content or json.loads(result.content[0].text))
                    assert len({v['session_id'] for v in values}) == 1
                    assert len({v['nonce'] for v in values}) == 1
                    assert canonical_sha(values[2]['context']) == values[2]['context_sha256'] == values[1]['expected_context_sha256']
        finally:
            stderr.seek(0)
            record['stderr'] = stderr.read()[:2000]
    proof_path = Path(values[0]['proof_path'])
    assert proof_path.is_relative_to(BASE / 'evidence')
    proof = json.loads(proof_path.read_bytes())
    assert proof['state'] == 'closed' and proof['storage_unchanged']
    assert all(value == 0 for value in proof['guard_denials'].values())
    assert proof['session_id'] == values[0]['session_id']
    record['proof_path'] = str(proof_path)
    record['proof_sha256'] = hashlib.sha256(proof_path.read_bytes()).hexdigest()
    record['sdk_session_id'] = proof['session_id']
    record['storage_unchanged'] = True
    record['guard_denials'] = proof['guard_denials']
    record['sdk_tool_calls'] = len(values)


if __name__ == '__main__':
    output = BASE / 'registered_stdio_check_01.json'
    assert not output.exists(), 'Use a new evidence record; do not overwrite'
    record = {'task_id': 'CODEX-WUA-0-DESKTOP-MCP-E2E-001',
              'checked_utc': datetime.now(timezone.utc).isoformat(),
              'origin': 'EXPLICIT SDK USING REGISTERED CONFIG; NOT DESKTOP E2E',
              'ordinary_chat_real_tool_calls': 0, 'desktop_e2e': 'NOT VERIFIED / MCP TOOLS UNAVAILABLE',
              'calls': []}
    try:
        asyncio.run(run(record))
        record['pass'] = True
    except BaseException as exc:
        record['pass'] = False
        record['error'] = {'type': type(exc).__name__, 'text': str(exc)}
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: record.get(key) for key in ('pass', 'origin', 'sdk_tool_calls', 'ordinary_chat_real_tool_calls', 'protocol', 'proof_path', 'error')}, ensure_ascii=False))
    raise SystemExit(0 if record['pass'] else 1)
