"""Strict profile compatibility checks; no account/WFP/route installation code."""
import copy,re
from common import *
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
    p=profile['processes'];exact(p,['tunnel','mcp','gateway','v2ray']);require(p['tunnel']==ids['client']==p['mcp'] and p['gateway']=='SERVER_OWNED_AUTHORITY' and True,'V2RAY_EGRESS_OWNER_MISMATCH')
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
    return {'contract_validation':'VALID','profile_sha256':pin,'can_apply':False,'can_start_tunnel':False,'identities_proven':False,'WFP_proven':False,'V2Ray_route_proven':False,'status':'BLOCKED / REAL USER GO AND INDEPENDENT OS PROOFS REQUIRED','client_socket_intent':{'family':'IPv4','protocol':'TCP','destination':'127.0.0.1','port':r['client_proxy_port']},'broker_socket_intent':{'family':'IPv4','protocol':'TCP','destination':r['egress_ip'],'port':r['egress_port']},'warnings':['Names and SID strings are not LookupAccountSid/token proof','WFP exact port does not authenticate listener','Gateway pipe/ACL/impersonation and real V2Ray ownership need independent evidence','No direct, secondary proxy, resolver or host-user V2Ray delegation allowed','Installed Windows Python asyncio uses dynamic TCP selfpipe: incompatible with putting this SDK child under C-only P. A verified no-TCP C stdio-to-pipe relay and server-owned SDK peer are required; not implemented here']}
def preflight(profile,pin,evidence=None):
    try:result=validate(profile,pin)
    except (Denied,KeyError,TypeError,ValueError):return {'contract_validation':'FAIL','can_apply':False,'can_start_tunnel':False,'status':'BLOCKED'}
    # Caller JSON or all-true approval never creates Windows authority.
    result['untrusted_evidence_accepted']=False;return result
def synthetic_profile():
    c='S-1-5-21-101-202-303-1001';b='S-1-5-21-101-202-303-1002';u='S-1-5-21-101-202-303-1003'
    return {'schema':1,'profile':'STRICT_V2RAY_BROKER','owner':'77777777-7777-4777-8777-777777777777','identities':{'client':c,'broker':b,'ui':u},'processes':{'tunnel':c,'mcp':c,'gateway':'SERVER_OWNED_AUTHORITY','v2ray':b},'route':{'layout':'DEDICATED_V2RAY_CONNECT_INBOUND','client_proxy_host':'127.0.0.1','client_proxy_port':32123,'egress_ip':'192.0.2.17','egress_port':443,'dns':'NO_HOST_RESOLVER_LITERAL_UPSTREAM','proxy_scheme':'http','remote_protocol':'tcp'},'ipc':{'tunnel_to_mcp':'STDIO','mcp_to_server':'SERVER_OWNED_AUTHENTICATED_LOCAL_PIPE','arbitrary_network_api':False},'children':[{'role':'mcp','owner_sid':c,'sha256':'1'*64},{'role':'v2ray','owner_sid':b,'sha256':'2'*64}],'startup_state':'DISABLED','allow_direct':False,'secondary_proxies':[],'environment_override':False,'approval':{'provision':False,'native':False,'tunnel':False}}
