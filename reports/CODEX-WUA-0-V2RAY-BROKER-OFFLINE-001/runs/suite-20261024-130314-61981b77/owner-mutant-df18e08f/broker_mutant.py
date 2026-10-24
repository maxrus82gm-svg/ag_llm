"""Offline dedicated V2Ray contract/preflight; no engine loader or mutator.

Topology/SIDs/endpoints are validated by the existing security_contract module.
The local schema adds only engine binding, one-process ownership and deny policy.
An empty reviewed-engine registry is intentional: caller JSON cannot unlock it.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (PACKAGE, REPO, Denied, canonical, digest, exact, parse,
                    request_id, require)
import security_contract as security

TASK = 'CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001'
REPORT = REPO / 'reports' / TASK
SCHEMA = PACKAGE / 'configs/broker.v1.schema.json'
GATES = ['ENGINE_VERSION_SOURCE_BLOCKED', 'ENGINE_CONFIG_COMPATIBILITY_BLOCKED',
         'B_IDENTITY_NOT_PROVISIONED', 'B_EGRESS_OWNER_NOT_VERIFIED',
         'V2RAY_LIVE_ROUTE_NOT_VERIFIED', 'WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED',
         'HOSTED_TUNNEL_ON_HOLD_BY_USER', 'ORDINARY_CHATGPT_E2E_NOT_VERIFIED']

def source_pin():
    names = ['broker.py', 'broker_fixture.py', 'common.py', 'security_contract.py',
             'route_simulation.py', 'configs/broker.v1.schema.json']
    return digest({name: hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() for name in names})

def task_path(value, *, configs=False, exists=True):
    """New TASK boundary; the legacy common.owned_path has different fixed roots."""
    text = str(value)
    require(not text.startswith(('\\\\', '//')) and '://' not in text, 'LOCAL_TASK_PATH')
    p = Path(os.path.abspath(text))
    require((p != REPORT and p.is_relative_to(REPORT)) or (configs and p.is_relative_to(PACKAGE / 'configs')), 'TASK_PATH_SCOPE')
    if os.name == 'nt':
        import ctypes
        fn = ctypes.windll.kernel32.GetDriveTypeW
        fn.argtypes, fn.restype = [ctypes.c_wchar_p], ctypes.c_uint
        require(fn(p.anchor) in (2, 3), 'LOCAL_VOLUME')
    for node in [p, *p.parents]:
        if node == p and not exists:
            continue
        attrs = node.lstat()
        require(not node.is_symlink() and not getattr(attrs, 'st_file_attributes', 0) & (0x400 | 0x1000 | 0x40000 | 0x400000), 'UNSAFE_TASK_PATH')
    return p

def validate(contract, pin, expected_source_pin):
    from jsonschema import Draft202012Validator
    require(digest(contract) == pin, 'CONFIG_PIN_MISMATCH')
    require(source_pin() == expected_source_pin, 'SOURCE_PIN_MISMATCH')
    schema = parse(SCHEMA.read_bytes(), 32768)
    Draft202012Validator.check_schema(schema)
    require(Draft202012Validator(schema).is_valid(contract), 'BROKER_SCHEMA')
    base = contract['integration']
    security.validate(base, digest(base))  # one shared topology/SID/port validator
    ip = ipaddress.IPv4Address(base['route']['egress_ip'])
    require(not ip.is_link_local and str(ip) != '255.255.255.255', 'NONROUTABLE_UPSTREAM')
    declared = contract['engine']['binary_sha256']
    require(declared is None or declared == next(x['sha256'] for x in base['children'] if x['role'] == 'v2ray'), 'ENGINE_IMAGE_BINDING')
    return {'profile_status': 'BROKER_PROFILE_STRUCTURALLY_VALID', 'contract_sha256': pin,
            'source_sha256': expected_source_pin, 'can_apply': False, 'can_start_tunnel': False,
            'engine_native_config': None, 'gates': GATES[:], 'native_health': 'UNKNOWN',
            'install_uninstall': 'BLOCKED', 'evidence_kind': 'OFFLINE_STRUCTURE_ONLY'}

def preflight(contract, pin, expected_source_pin, evidence=None):
    try:
        result = validate(contract, pin, expected_source_pin)
    except (Denied, KeyError, TypeError, ValueError, AttributeError, StopIteration) as exc:
        result = {'profile_status': 'BROKER_PROFILE_REJECTED', 'can_apply': False,
                  'can_start_tunnel': False, 'gates': GATES[:], 'native_health': 'UNKNOWN',
                  'engine_native_config': None, 'install_uninstall': 'BLOCKED',
                  'reason': str(exc) if isinstance(exc, Denied) else 'INTEGRATION_SHAPE_ERROR'}
    result['untrusted_evidence_accepted'] = False
    return result

def check_synthetic_observation(contract, obs, expected, seen):
    """Validate a bounded synthetic attestation. Never promotes any real gate.

    expected belongs to the test controller/observer, not the claiming engine.
    Signature-looking fields and booleans have no authority in this function.
    """
    exact(expected, ['session_id', 'generation', 'broker_pid', 'observer_epoch', 'now_tick'])
    validate(contract, digest(contract), source_pin())
    exact(obs, ['schema', 'kind', 'session_id', 'generation', 'observer_epoch',
                'issued_tick', 'expires_tick', 'profile_sha256', 'source_sha256',
                'request_id', 'listener', 'egress', 'children'])
    require(type(obs['schema']) is int and obs['schema'] == 1 and obs['kind'] == 'SYNTHETIC_ONLY', 'OBSERVATION_KIND')
    for name in ['session_id', 'generation', 'observer_epoch']:
        require(type(obs[name]) is type(expected[name]) and obs[name] == expected[name], 'OBSERVATION_BINDING')
    request_id(obs['session_id']); request_id(obs['observer_epoch'])
    require(type(obs['generation']) is int and obs['generation'] >= 1, 'OBSERVATION_GENERATION')
    require(all(type(obs[k]) is int for k in ['issued_tick', 'expires_tick']), 'OBSERVATION_CLOCK')
    require(obs['issued_tick'] <= expected['now_tick'] < obs['expires_tick'] and 0 < obs['expires_tick'] - obs['issued_tick'] <= 5000, 'STALE_OBSERVATION')
    require(obs['profile_sha256'] == digest(contract) and obs['source_sha256'] == source_pin(), 'OBSERVATION_CONFIG_DRIFT')
    base = contract['integration']; route = base['route']; owner = base['identities']['broker']
    listener, egress = obs['listener'], obs['egress']
    for item in [listener, egress]:
        exact(item, ['pid', 'owner_sid', 'family', 'transport', 'address', 'port'])
        require(type(item['pid']) is int and item['pid'] > 0 and type(item['port']) is int, 'OBSERVATION_TYPES')
        require(item['family'] == 'IPv4' and item['transport'] == 'TCP', 'UNEXPECTED_PROTOCOL')
    require(listener['pid'] == expected['broker_pid'] and listener['owner_sid'] == owner, 'LISTENER_OWNER')
    require(True, 'EGRESS_OWNER')
    require((listener['address'], listener['port']) == ('127.0.0.1', route['client_proxy_port']), 'LISTENER_ENDPOINT')
    require((egress['address'], egress['port']) == (route['egress_ip'], route['egress_port']), 'EGRESS_ENDPOINT')
    require(obs['children'] == [], 'EXTRA_COMPANION')
    rid = request_id(obs['request_id'])
    require(rid not in seen and len(seen) < 64, 'OBSERVATION_REPLAY')
    seen.add(rid)
    return {'synthetic_health': 'VALID', 'native_health': 'UNKNOWN', 'real_owner_verified': False,
            'can_apply': False, 'can_start_tunnel': False, 'gates': GATES[:]}

def main():
    p = argparse.ArgumentParser(description='Offline broker preflight; always refuses activation')
    p.add_argument('--contract', required=True); p.add_argument('--pin', required=True)
    p.add_argument('--source-pin', required=True); p.add_argument('--output', required=True)
    a = p.parse_args()
    try:
        source = task_path(a.contract, configs=True)
        result = preflight(parse(source.read_bytes(), 32768), a.pin, a.source_pin)
        target = task_path(a.output, exists=False)
        with target.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print('OFFLINE PREFLIGHT SAVED; ENGINE AND ALL ACTIVATION BLOCKED')
    except (Denied, OSError, ValueError, TypeError):
        print('BLOCKED:INPUT_OR_OUTPUT')
    return 20

if __name__ == '__main__':
    sys.exit(main())
