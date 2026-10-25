"""Strict profile compatibility checks; no account/WFP/route installation code."""
import copy,re
from common import *

# Fixed public rejection codes, never exception messages or credential values.
ADMISSION_CODES=frozenset('AUTH_USERS_REQUIRED ADMISSION_FIELDS AUTH_FIELDS AUTH_REQUIRED AUTH_MECHANISM_REQUIRED AUTH_USER_FIELDS AUTH_PRINCIPAL_INVALID CREDENTIAL_REFERENCE_INVALID UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED CONFIG_FIELDS CONFIG_SINGLE_SOURCE_REQUIRED CONFIG_FORMAT_REQUIRED CONFIG_PROTECTION_REQUIRED CONFIG_MERGE_DENIED CONFIG_RELOAD_DENIED CONFIG_ENV_OVERRIDE_DENIED CONNECT_POLICY_FIELDS CONNECT_POLICY_DENIED CONNECT_TARGET_REQUIRED CONNECT_ADDRESS_INVALID CONNECT_PORT_INVALID CONNECT_METADATA_REQUIRED CONNECT_METADATA_FIELDS CONNECT_METHOD_DENIED CONNECT_UPGRADE_DENIED CONNECT_EVENT_INVALID CONNECT_DESTINATION_DENIED'.split())

def _fields(value,fields,code):
    require(type(value) is dict and set(value)==set(fields),code)

def credential_reference(value):
    # Only an opaque reference is admitted. No lookup or secret delivery occurs.
    require(type(value) is str and value.startswith('wua-secret-ref:'),'CREDENTIAL_REFERENCE_INVALID')
    try:request_id(value[len('wua-secret-ref:'):])
    except Denied:raise Denied('CREDENTIAL_REFERENCE_INVALID') from None

def _connect_address(value):
    import ipaddress
    require(type(value) is str,'CONNECT_ADDRESS_INVALID')
    try:address=ipaddress.IPv4Address(value)
    except (ValueError,TypeError):raise Denied('CONNECT_ADDRESS_INVALID') from None
    require(str(address)==value and not (address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast) and value!='255.255.255.255','CONNECT_ADDRESS_INVALID')

def _connect_port(value):
    require(type(value) is int and 1<=value<=65535,'CONNECT_PORT_INVALID')

def validate_admission(policy,upstream_credential_ref,request_metadata=None):
    """Validate offline intent/parsed metadata, never HTTP bytes or OS authority.

    Policy lives in the existing broker contract. References/claims cannot prove
    protected storage, an engine's error handling, or actual network ownership.
    """
    require(policy is not None,'AUTH_USERS_REQUIRED')
    _fields(policy,['authentication','configuration','connect'],'ADMISSION_FIELDS')
    auth=policy['authentication']
    require(type(auth) is dict and type(auth.get('users')) is list and 1<=len(auth['users'])<=8,'AUTH_USERS_REQUIRED')
    _fields(auth,['required','mechanism','users'],'AUTH_FIELDS')
    require(auth['required'] is True,'AUTH_REQUIRED')
    require(auth['mechanism']=='BROKER_ONLY_PROTECTED_REFERENCE','AUTH_MECHANISM_REQUIRED')
    principals=set();references=set()
    for user in auth['users']:
        _fields(user,['principal','credential_ref'],'AUTH_USER_FIELDS')
        name=user['principal'];require(type(name) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}',name) and name not in principals,'AUTH_PRINCIPAL_INVALID')
        credential_reference(user['credential_ref'])
        require(user['credential_ref'] not in references,'CREDENTIAL_REFERENCE_INVALID')
        principals.add(name);references.add(user['credential_ref'])
    try:credential_reference(upstream_credential_ref)
    except Denied:raise Denied('UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED') from None
    require(upstream_credential_ref not in references,'UPSTREAM_CREDENTIAL_REFERENCE_REQUIRED')
    config=policy['configuration']
    _fields(config,['source_count','format','protection','merge','reload','environment_override'],'CONFIG_FIELDS')
    require(type(config['source_count']) is int and config['source_count']==1,'CONFIG_SINGLE_SOURCE_REQUIRED')
    require(config['format']=='CANONICAL_JSON','CONFIG_FORMAT_REQUIRED')
    require(config['protection']=='BROKER_ONLY_PROTECTED_SOURCE','CONFIG_PROTECTION_REQUIRED')
    require(config['merge'] is False,'CONFIG_MERGE_DENIED')
    require(config['reload'] is False,'CONFIG_RELOAD_DENIED')
    require(config['environment_override'] is False,'CONFIG_ENV_OVERRIDE_DENIED')
    connect=policy['connect']
    _fields(connect,['methods','targets','allow_upgrade','allow_plain_http','allow_uot','allow_background'],'CONNECT_POLICY_FIELDS')
    require(connect['methods']==['CONNECT'] and all(connect[k] is False for k in ['allow_upgrade','allow_plain_http','allow_uot','allow_background']),'CONNECT_POLICY_DENIED')
    require(type(connect['targets']) is list and len(connect['targets'])==1,'CONNECT_TARGET_REQUIRED')
    target=connect['targets'][0];_fields(target,['address','port'],'CONNECT_TARGET_REQUIRED')
    _connect_address(target['address']);_connect_port(target['port'])
    # Logical CONNECT destination is separate from the physical proxy R:Q.
    _fields(request_metadata,['method','upgrade','address','port','connect_accepted'],'CONNECT_METADATA_FIELDS')
    require(request_metadata['method']=='CONNECT','CONNECT_METHOD_DENIED')
    require(request_metadata['upgrade'] is False,'CONNECT_UPGRADE_DENIED')
    require(type(request_metadata['connect_accepted']) is bool,'CONNECT_EVENT_INVALID')
    _connect_address(request_metadata['address']);_connect_port(request_metadata['port'])
    require((request_metadata['address'],request_metadata['port'])==(target['address'],target['port']),'CONNECT_DESTINATION_DENIED')
    return {'policy_route_allowed':True,'connect_handler_event':'UNTRUSTED_ACCEPTED_CLAIM' if request_metadata['connect_accepted'] else 'UNTRUSTED_NOT_ACCEPTED_CLAIM','real_egress_verified':False,'can_apply':False,'can_start_tunnel':False,'install_uninstall':'BLOCKED'}
def sid(value):
    require(type(value) is str and re.fullmatch(r'S-1-5-21-(?:[1-9][0-9]{0,9}-){3}[1-9][0-9]{3,9}',value),'LOCAL_SID_REQUIRED')
    require(all(int(n)<=4294967295 for n in value.split('-')[4:]) and int(value.split('-')[-1])>=1000,'SID_DOMAIN')
    return value.rsplit('-',1)[0]
def validate(profile,pin):
    require(digest(profile)==pin,'STARTUP_PIN_MISMATCH')
    exact(profile,['schema','profile','owner','identities','processes','route','ipc','children','startup_state','allow_direct','secondary_proxies','environment_override','approval'])
    require(type(profile['schema']) is int and profile['schema']==1 and profile['profile']=='STRICT_V2RAY_BROKER','PROFILE')
    request_id(profile['owner']);ids=profile['identities'];exact(ids,['client','broker','ui']);prefixes=[sid(v) for v in ids.values()]
    require(len(set(ids.values()))==3 and len(set(prefixes))==1,'IDENTITY_CONFLICT')
    p=profile['processes'];exact(p,['tunnel','mcp','gateway','v2ray']);require(p['tunnel']==ids['client']==p['mcp'] and p['gateway']=='SERVER_OWNED_AUTHORITY' and p['v2ray']==ids['broker'],'V2RAY_EGRESS_OWNER_MISMATCH')
    r=profile['route'];exact(r,['layout','client_proxy_host','client_proxy_port','egress_ip','egress_port','dns','proxy_scheme','remote_protocol'])
    require(r['layout']=='DEDICATED_V2RAY_CONNECT_INBOUND' and r['client_proxy_host']=='127.0.0.1' and r['proxy_scheme']=='http' and r['remote_protocol']=='tcp','ROUTE_LAYOUT')
    for k in ['client_proxy_port','egress_port']:require(type(r[k]) is int and 1<=r[k]<=65535,'PORT_DOMAIN')
    import ipaddress
    try:ip=ipaddress.IPv4Address(r['egress_ip'])
    except (ValueError,TypeError):raise Denied('LITERAL_EGRESS_IP_REQUIRED') from None
    require(not ip.is_loopback and not ip.is_unspecified and not ip.is_multicast,'EGRESS_IP_DOMAIN');require(r['dns']=='NO_HOST_RESOLVER_LITERAL_UPSTREAM','DNS_ROUTE')
    exact(profile['ipc'],['tunnel_to_mcp','mcp_to_server','arbitrary_network_api']);require(profile['ipc']=={'tunnel_to_mcp':'STDIO','mcp_to_server':'SERVER_OWNED_AUTHENTICATED_LOCAL_PIPE','arbitrary_network_api':False},'IPC_CONFLICT')
    require(type(profile['children']) is list and len(profile['children'])==2,'CHILD_ALLOWLIST')
    require({x.get('role') for x in profile['children']}=={'mcp','v2ray'},'CHILD_ROLE')
    for child in profile['children']:
        exact(child,['role','owner_sid','sha256']);require(child['owner_sid']==(ids['client'] if child['role']=='mcp' else ids['broker']) and type(child['sha256']) is str and re.fullmatch('[0-9a-f]{64}',child['sha256']),'CHILD_OWNER_OR_HASH')
    require(profile['startup_state']=='DISABLED' and profile['allow_direct'] is False and profile['secondary_proxies']==[] and profile['environment_override'] is False,'FAIL_CLOSED_REQUIRED')
    exact(profile['approval'],['provision','native','tunnel']);require(all(type(v) is bool for v in profile['approval'].values()),'APPROVAL_TYPES')
    return {'contract_validation':'VALID','profile_sha256':pin,'can_apply':False,'can_start_tunnel':False,'install_uninstall':'BLOCKED','identities_proven':False,'WFP_proven':False,'V2Ray_route_proven':False,'status':'BLOCKED / REAL USER GO AND INDEPENDENT OS PROOFS REQUIRED','client_socket_intent':{'family':'IPv4','protocol':'TCP','destination':'127.0.0.1','port':r['client_proxy_port']},'broker_socket_intent':{'family':'IPv4','protocol':'TCP','destination':r['egress_ip'],'port':r['egress_port']},'warnings':['Names and SID strings are not LookupAccountSid/token proof','WFP exact port does not authenticate listener','Gateway pipe/ACL/impersonation and real V2Ray ownership need independent evidence','No direct, secondary proxy, resolver or host-user V2Ray delegation allowed','Installed Windows Python asyncio uses dynamic TCP selfpipe: incompatible with putting this SDK child under C-only P. A verified no-TCP C stdio-to-pipe relay and server-owned SDK peer are required; not implemented here']}
def preflight(profile,pin,evidence=None):
    try:result=validate(profile,pin)
    except (Denied,KeyError,TypeError,ValueError):return {'contract_validation':'FAIL','can_apply':False,'can_start_tunnel':False,'install_uninstall':'BLOCKED','status':'BLOCKED'}
    # Caller JSON or all-true approval never creates Windows authority.
    result['untrusted_evidence_accepted']=False;return result
def synthetic_profile():
    c='S-1-5-21-101-202-303-1001';b='S-1-5-21-101-202-303-1002';u='S-1-5-21-101-202-303-1003'
    return {'schema':1,'profile':'STRICT_V2RAY_BROKER','owner':'77777777-7777-4777-8777-777777777777','identities':{'client':c,'broker':b,'ui':u},'processes':{'tunnel':c,'mcp':c,'gateway':'SERVER_OWNED_AUTHORITY','v2ray':b},'route':{'layout':'DEDICATED_V2RAY_CONNECT_INBOUND','client_proxy_host':'127.0.0.1','client_proxy_port':32123,'egress_ip':'192.0.2.17','egress_port':443,'dns':'NO_HOST_RESOLVER_LITERAL_UPSTREAM','proxy_scheme':'http','remote_protocol':'tcp'},'ipc':{'tunnel_to_mcp':'STDIO','mcp_to_server':'SERVER_OWNED_AUTHENTICATED_LOCAL_PIPE','arbitrary_network_api':False},'children':[{'role':'mcp','owner_sid':c,'sha256':'1'*64},{'role':'v2ray','owner_sid':b,'sha256':'2'*64}],'startup_state':'DISABLED','allow_direct':False,'secondary_proxies':[],'environment_override':False,'approval':{'provision':False,'native':False,'tunnel':False}}
