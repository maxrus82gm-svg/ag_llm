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
STRICT_BLOCKERS = ['UPSTREAM_SECRET_BOUNDARY_UNVERIFIED', 'CREDENTIAL_STORE_UNVERIFIED',
                   'CONFIG_SOURCE_PROTECTION_UNVERIFIED', 'CONNECT_METADATA_ORACLE_UNVERIFIED']
ROUTE_CODES = {'default':'STRICT_DEFAULT_DENIED','direct':'STRICT_DIRECT_DENIED',
               'fallback':'STRICT_FALLBACK_DENIED','secondary_proxy':'STRICT_SECONDARY_PROXY_DENIED',
               'load_balancer':'STRICT_LOAD_BALANCER_DENIED','outbound_count':'STRICT_UNDECLARED_ROUTE',
               'rule_order':'STRICT_UNDECLARED_ROUTE','companions':'STRICT_UNDECLARED_ROUTE',
               **{k:'STRICT_EXTRA_EGRESS_DENIED' for k in ['host_dns','udp','ipv6','health_dials','telemetry']}}
PUBLIC_CODES = security.ADMISSION_CODES | frozenset(ROUTE_CODES.values()) | frozenset(
    'CONFIG_PIN_MISMATCH SOURCE_PIN_MISMATCH SCHEMA_EXTERNAL_REF BROKER_SCHEMA NONROUTABLE_UPSTREAM ENGINE_IMAGE_BINDING LOCAL_SID_REQUIRED SID_DOMAIN STARTUP_PIN_MISMATCH SCHEMA PROFILE REQUEST_ID IDENTITY_CONFLICT V2RAY_EGRESS_OWNER_MISMATCH ROUTE_LAYOUT PORT_DOMAIN LITERAL_EGRESS_IP_REQUIRED EGRESS_IP_DOMAIN DNS_ROUTE IPC_CONFLICT CHILD_ALLOWLIST CHILD_ROLE CHILD_OWNER_OR_HASH FAIL_CLOSED_REQUIRED APPROVAL_TYPES SIZE_LIMIT DUPLICATE_KEY JSON_TYPE JSON_SYNTAX DEPTH_LIMIT ITEM_LIMIT KEY_LIMIT TEXT_LIMIT STRICT_INPUT_TYPE CONFIG_NOT_CANONICAL STRICT_UNDECLARED_ROUTE'.split())

def _public_reason(exc, fallback):
    # Do not stringify arbitrary errors, schema messages, headers or credentials.
    if type(exc) is Denied and len(exc.args)==1 and type(exc.args[0]) is str and exc.args[0] in PUBLIC_CODES:
        return exc.args[0]
    return fallback

def _strict_defaults(result):
    result.update(strict_admission_status='STRICT_ADMISSION_BLOCKED',strict_policy_status='NOT_EVALUATED',
                  strict_blockers=STRICT_BLOCKERS[:]+GATES[:],policy_route_allowed=False,
                  connect_handler_event='NOT_OBSERVED',real_egress_verified=False,
                  can_apply=False,can_start_tunnel=False,install_uninstall='BLOCKED',
                  untrusted_evidence_accepted=False)
    return result

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

def validate(contract, pin, expected_source_pin, *, strict_codes=False):
    from jsonschema import Draft202012Validator
    require(digest(contract) == pin, 'CONFIG_PIN_MISMATCH')
    require(source_pin() == expected_source_pin, 'SOURCE_PIN_MISMATCH')
    schema = parse(SCHEMA.read_bytes(), 32768)
    def local_refs(node):
        if type(node) is dict:
            for key, value in node.items():
                if key in ('$ref', '$dynamicRef'):
                    require(type(value) is str and value.startswith('#'), 'SCHEMA_EXTERNAL_REF')
                local_refs(value)
        elif type(node) is list:
            for value in node: local_refs(value)
    local_refs(schema)  # offline validator must never retrieve a remote schema
    Draft202012Validator.check_schema(schema)
    error=next(Draft202012Validator(schema).iter_errors(contract),None)
    if error is not None:
        code='BROKER_SCHEMA'
        # Same schema is the oracle; map its routing-const mismatch to a public
        # code without printing ValidationError.message or duplicating policy.
        if strict_codes and list(error.absolute_path)==['routing'] and type(contract.get('routing')) is dict:
            expected=schema['properties']['routing']['const']
            code=next((ROUTE_CODES.get(k,'STRICT_UNDECLARED_ROUTE') for k,v in expected.items()
                       if canonical(contract['routing'].get(k))!=canonical(v)), 'STRICT_UNDECLARED_ROUTE')
        raise Denied(code)
    base = contract['integration']
    security.validate(base, digest(base))  # one shared topology/SID/port validator
    ip = ipaddress.IPv4Address(base['route']['egress_ip'])
    require(not ip.is_link_local and str(ip) != '255.255.255.255', 'NONROUTABLE_UPSTREAM')
    declared = contract['engine']['binary_sha256']
    require(declared is None or declared == next(x['sha256'] for x in base['children'] if x['role'] == 'v2ray'), 'ENGINE_IMAGE_BINDING')
    return _strict_defaults({'profile_status': 'BROKER_PROFILE_STRUCTURALLY_VALID', 'contract_sha256': pin,
            'source_sha256': expected_source_pin, 'can_apply': False, 'can_start_tunnel': False,
            'engine_native_config': None, 'gates': GATES[:], 'native_health': 'UNKNOWN',
            'install_uninstall': 'BLOCKED', 'evidence_kind': 'OFFLINE_STRUCTURE_ONLY'})

def preflight(contract, pin, expected_source_pin, evidence=None):
    try:
        result = validate(contract, pin, expected_source_pin)
    except Exception as exc:
        result = {'profile_status': 'BROKER_PROFILE_REJECTED', 'can_apply': False,
                  'can_start_tunnel': False, 'gates': GATES[:], 'native_health': 'UNKNOWN',
                  'engine_native_config': None, 'install_uninstall': 'BLOCKED',
                  'reason': _public_reason(exc,'INTEGRATION_SHAPE_ERROR')}
    return _strict_defaults(result)

def strict_preflight(raw, pin, expected_source_pin, *, request_metadata=None):
    """One existing parse/schema/security pipeline; no runtime admission.

    Raw JSON must be canonical and pinned by the controller, not re-pinned from
    caller evidence. Parsed CONNECT metadata remains an untrusted input: an
    offline policy match does not prove Go parsing, auth, downstream or B owner.
    """
    result=_strict_defaults({'profile_status':'BROKER_PROFILE_REJECTED','gates':GATES[:],
                            'native_health':'UNKNOWN','engine_native_config':None})
    try:
        require(type(raw) is bytes,'STRICT_INPUT_TYPE')
        contract=parse(raw,32768)
        require(raw==canonical(contract),'CONFIG_NOT_CANONICAL')
        result=validate(contract,pin,expected_source_pin,strict_codes=True)
        decision=security.validate_admission(contract.get('admission'),contract['remote_identity']['credential_ref'],request_metadata)
        result.update(decision,strict_policy_status='VALID',reason='RUNTIME_SECURITY_UNVERIFIED')
    except Exception as exc:
        result.update(strict_policy_status='REJECTED',policy_route_allowed=False,
                      reason=_public_reason(exc,'STRICT_INTERNAL_FAILURE'))
        # A rejected input may contain forbidden secret material: no input/hash
        # echo in diagnostics, even if its outer structure was well formed.
        result.pop('contract_sha256',None)
    return result

def check_synthetic_observation(contract, obs, expected, seen):
    """Validate a bounded synthetic attestation. Never promotes any real gate.

    expected belongs to the test controller/observer, not the claiming engine.
    Signature-looking fields and booleans have no authority in this function.
    """
    exact(expected, ['session_id', 'generation', 'broker_pid', 'observer_epoch', 'now_tick', 'profile_sha256', 'source_sha256'])
    validate(contract, expected['profile_sha256'], expected['source_sha256'])
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
    require(obs['profile_sha256'] == expected['profile_sha256'] and obs['source_sha256'] == expected['source_sha256'], 'OBSERVATION_CONFIG_DRIFT')
    base = contract['integration']; route = base['route']; owner = base['identities']['broker']
    listener, egress = obs['listener'], obs['egress']
    for item in [listener, egress]:
        exact(item, ['pid', 'owner_sid', 'family', 'transport', 'address', 'port'])
        require(type(item['pid']) is int and item['pid'] > 0 and type(item['port']) is int, 'OBSERVATION_TYPES')
        require(item['family'] == 'IPv4' and item['transport'] == 'TCP', 'UNEXPECTED_PROTOCOL')
    require(listener['pid'] == expected['broker_pid'] and listener['owner_sid'] == owner, 'LISTENER_OWNER')
    require(egress['pid'] == listener['pid'] and egress['owner_sid'] == owner, 'EGRESS_OWNER')
    require((listener['address'], listener['port']) == ('127.0.0.1', route['client_proxy_port']), 'LISTENER_ENDPOINT')
    require((egress['address'], egress['port']) == (route['egress_ip'], route['egress_port']), 'EGRESS_ENDPOINT')
    require(obs['children'] == [], 'EXTRA_COMPANION')
    rid = request_id(obs['request_id'])
    require(rid not in seen and len(seen) < 64, 'OBSERVATION_REPLAY')
    seen.add(rid)
    return {'synthetic_health': 'VALID', 'native_health': 'UNKNOWN', 'real_owner_verified': False,
            'can_apply': False, 'can_start_tunnel': False, 'install_uninstall':'BLOCKED','gates': GATES[:]}

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
