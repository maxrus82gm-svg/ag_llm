"""Review aids for SYNTHETIC observation contracts, not a native verifier.

No network, policy enforcement, signature/receipt authentication or installation.
Even consistent input returns OFFLINE_CONSISTENT, never VERIFIED or permission.
"""
import re

SOURCES = {'initiator':'TRUSTED_LAB_OBSERVER','policy':'INDEPENDENT_POLICY_OBSERVER',
           'receiver':'OWNED_RECEIVER_OBSERVER','lifecycle':'INDEPENDENT_LIFECYCLE_OBSERVER'}

def bound(row, source, run):
    return (type(row) is dict and row.get('source') == source and row.get('run') == run
            and row.get('fresh') is True and row.get('complete_window') is True)

def evaluate(sample):
    """Explicit evidence requirements. Input assertions are not trusted OS facts."""
    def deny(code):
        return {'status':'INCOMPLETE','reason':code,'native_verified':False,'can_apply':False,'can_start_tunnel':False}
    if type(sample) is not dict or sample.get('boundary') != 'SYNTHETIC_OFFLINE_ONLY':
        return deny('SYNTHETIC_BOUNDARY_REQUIRED')
    run = sample.get('run')
    if type(run) is not str or not re.fullmatch('[a-f0-9]{32}', run):
        return deny('RUN_BINDING_REQUIRED')
    kind = sample.get('kind')
    if type(kind) is not str or kind not in {'DENY','ALLOW','QUIESCENCE'}:
        return deny('SCENARIO_KIND_REQUIRED')
    required = {'QUIESCENCE':['lifecycle','policy'], 'DENY':['initiator','policy','receiver'],
                'ALLOW':['initiator','policy','receiver']}[kind]
    if any(not bound(sample.get(name), SOURCES[name], run) for name in required):
        return deny('INDEPENDENT_FRESH_OBSERVATIONS_REQUIRED')
    if kind == 'QUIESCENCE':
        life = sample['lifecycle']
        if sample['policy'].get('effective_readback') is not True:
            return deny('EFFECTIVE_POLICY_UNPROVED')
        if not (life.get('admissions_frozen') is True and life.get('startup_disabled') is True
                and all(type(life.get(k)) is int and life[k] == 0 for k in ['processes','flows','queued_work','inherited_handles'])
                and sample['policy'].get('deny_retained') is True):
            return deny('KEEP_DENY_QUIESCENCE_UNPROVED')
    else:
        attempt, policy, receiver = [sample[name] for name in ['initiator','policy','receiver']]
        if not (attempt.get('initiated') is True and attempt.get('token_observed') is True
                and (kind != 'DENY' or (type(attempt.get('role')) is str and attempt['role'] in {'C','B_ENGINE'}))
                and attempt.get('image_pinned') is True and attempt.get('tuple_bound') is True
                and attempt.get('nonce_correlated') is True and attempt.get('observer_control_valid') is True):
            return deny('ATTEMPT_OR_CONTROL_UNPROVED')
        if policy.get('effective_readback') is not True or policy.get('competing_filters_reviewed') is not True:
            return deny('EFFECTIVE_POLICY_UNPROVED')
        if type(receiver.get('receipts')) is not int or receiver['receipts'] < 0:
            return deny('RECEIVER_COUNT_INVALID')
        if kind == 'DENY':
            if not (policy.get('attributable_deny') is True and receiver['receipts'] == 0):
                return deny('DENIAL_UNPROVED')
        elif not (attempt.get('role') == 'B_ENGINE' and attempt.get('socket_owner_observed') is True
                  and attempt.get('exact_upstream') is True and receiver['receipts'] == 1
                  and receiver.get('payload_nonce_match') is True and policy.get('attributable_deny') is False):
            return deny('B_ROUTE_UNPROVED')
    return {'status':'OFFLINE_CONSISTENT','reason':'SYNTHETIC_REQUIREMENTS_ONLY','native_verified':False,
            'can_apply':False,'can_start_tunnel':False}
