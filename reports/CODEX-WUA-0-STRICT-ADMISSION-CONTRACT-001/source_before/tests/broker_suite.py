"""Windows offline broker contracts + isolated loopback model + fault/mutation oracles."""
import argparse
import copy
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import struct
import subprocess
import sys
import threading
import time
import types
import unittest
import uuid
sys.dont_write_bytecode = True
PKG=Path(__file__).resolve().parents[1];REPO=PKG.parents[1]
sys.path.insert(0,str(PKG))
import common,broker,route_simulation as route
OUT=None;ACTIVE=None;OBS=[];RESULTS=[]
K=ct.WinDLL('kernel32',use_last_error=True)
K.GetCurrentProcess.restype=wt.HANDLE
K.QueryFullProcessImageNameW.argtypes=[wt.HANDLE,wt.DWORD,wt.LPWSTR,ct.POINTER(wt.DWORD)]

def interpreter():
    b=ct.create_unicode_buffer(32768);n=wt.DWORD(len(b))
    assert K.QueryFullProcessImageNameW(K.GetCurrentProcess(),0,b,ct.byref(n))
    return b.value # actual interpreter, not a venv redirector: one owned worker PID
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def contract():return json.loads((PKG/'configs/broker.v1.synthetic.example.json').read_text())
def fresh(name):
    p=OUT/(name+'-'+uuid.uuid4().hex[:8]);p.mkdir();return p
def tcp_rows():
    api=ct.WinDLL('iphlpapi').GetExtendedTcpTable;n=wt.ULONG()
    assert api(None,ct.byref(n),False,2,5,0) in [0,122]
    b=ct.create_string_buffer(n.value);assert api(b,ct.byref(n),False,2,5,0)==0
    return [struct.unpack_from('<6I',b.raw,4+i*24) for i in range(struct.unpack_from('<I',b.raw)[0])]
def port(n):return socket.ntohs(n & 0xffff)
def owner_for_flow(peer_port,receiver_port):
    matches=[r[5] for r in tcp_rows() if r[0]==5 and port(r[2])==peer_port and port(r[4])==receiver_port]
    assert len(set(matches))==1,('FLOW_OWNER_NOT_OBSERVED',matches)
    return matches[0]
def observe(event,args):
    ctx=ACTIVE
    if ctx is None:return
    if event in ['socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr']:
        ctx['violations'].append('DNS');raise PermissionError('NO_DNS')
    if event=='socket.__new__' and (args[1]!=socket.AF_INET or args[2]!=socket.SOCK_STREAM):
        ctx['violations'].append('UDP_OR_IPV6');raise PermissionError('ONLY_FIXTURE_TCP4')
    if event=='socket.bind':
        assert args[1][0]=='127.0.0.1' and args[1][1] in {0,*ctx['owned_ports']},'FIXTURE_BIND_ONLY'
    if event=='socket.connect':
        addr=args[1];ok=addr[0]=='127.0.0.1' and addr[1] in ctx['owned_ports']
        ctx['attempts'].append({'port':addr[1],'allowed_containment':ok,'pid':os.getpid()})
        if not ok:raise PermissionError('ONLY_OWNED_LOOPBACK')
        if addr[1]!=ctx['broker_port']:ctx['violations'].append('DIRECT_OR_SECOND_PROXY')
sys.addaudithook(observe)

def head(c):
    raw=b'';deadline=time.monotonic()+1
    while not raw.endswith(b'\r\n\r\n'):
        assert len(raw)<2048
        raw+=route.receive(c,1,deadline)
    return raw.decode('ascii').split('\r\n')

class Harness:
    def __init__(self,name,fault=None):
        global ACTIVE
        self.root=fresh(name);self.fault=fault;self.key=secrets.token_bytes(32);self.nonce=secrets.token_hex(32)
        self.receipts=[];self.errors=[];self.stop=threading.Event();self.clients=[];self.worker=None;self.ready=None
        self.monitor={'owned_ports':set(),'broker_port':None,'attempts':[],'violations':[]};ACTIVE=self.monitor
        self.listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        self.listener.bind(('127.0.0.1',0));self.receiver_port=self.listener.getsockname()[1]
        self.monitor['owned_ports'].add(self.receiver_port)
        self.listener.listen(2);self.listener.settimeout(.05)
        self.thread=threading.Thread(target=self._receive,daemon=True);self.thread.start()
        self.boot={'schema':1,'mode':'SYNTHETIC_LOOPBACK_ONLY','session_id':str(uuid.uuid4()),'instance_id':str(uuid.uuid4()),'upstream_port':self.receiver_port,'listen_port':0,'upstream_address':'127.0.0.1'}
        put(self.root/'fixture.json',self.boot)
    def _receive(self):
        while not self.stop.is_set():
            try:c,peer=self.listener.accept()
            except socket.timeout:continue
            except OSError:return
            self.clients.append(c)
            try:
                if self.fault=='reset':c.close();continue
                if self.fault=='timeout':self.stop.wait(1.5);continue
                lines=head(c)
                assert lines[0].startswith('GET /')
                phase=lines[0].split(' ')[1][1:]
                rid=next(s.split(':',1)[1].strip() for s in lines if s.startswith('X-Request-ID:'))
                owner=owner_for_flow(peer[1],self.receiver_port)
                record={'request_id':rid,'phase':phase,'session_id':self.boot['session_id'],'receiver_peer_port':peer[1],'receiver_port':self.receiver_port,'observed_sender_pid':owner,'current_user_only':True}
                record['receipt_hmac']=hmac.new(self.key,common.canonical(record),hashlib.sha256).hexdigest()
                self.receipts.append(record)
                if self.fault=='partial':c.sendall(b'HTTP/1.1 200');continue
                if self.fault=='redirect':c.sendall(b'HTTP/1.1 307 Temporary Redirect\r\nLocation: http://other.invalid/\r\nContent-Length: 0\r\n\r\n');continue
                data=common.canonical({'request_id':rid,'route_nonce':'foreign' if self.fault=='takeover' else self.nonce,'phase':phase})
                c.sendall(('HTTP/1.1 200 OK\r\nContent-Length: '+str(len(data))+'\r\n\r\n').encode()+data)
            except (OSError,common.Denied,TimeoutError):pass
            except BaseException as e:self.errors.append(type(e).__name__+':'+str(e))
            finally:
                try:c.close()
                except OSError:pass
    def start(self,bootstrap_change=None,pin_change=False):
        self.ready=None
        if bootstrap_change:
            self.boot.update(bootstrap_change);put(self.root/'fixture.json',self.boot)
        path=self.root/'fixture.json';expected=sha(path)
        if pin_change:path.write_bytes(path.read_bytes()+b' ')
        self.worker=subprocess.Popen([interpreter(),'-I','-X','utf8','-B',str(PKG/'broker_fixture.py'),str(path),expected,broker.source_pin()],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=common.clean_environment())
        messages=queue.Queue(1)
        def pump():messages.put(self.worker.stdout.readline())
        t=threading.Thread(target=pump,daemon=True);t.start()
        raw=messages.get(timeout=4);t.join(1)
        if raw:
            self.ready=json.loads(raw);assert self.ready['pid']==self.worker.pid
            self.monitor['broker_port']=self.ready['port'];self.monitor['owned_ports'].add(self.ready['port'])
            assert any(row[0]==2 and port(row[2])==self.ready['port'] and row[5]==self.worker.pid for row in tcp_rows())
        return self
    def request(self,ambient=None):return route.control_request(self.ready['port'],'control.invalid:443','poll',self.nonce,ambient)
    def reserve_failed_broker(self):
        p=self.ready['port'];self.worker.terminate();self.worker.wait(3)
        self.reservation=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        self.reservation.bind(('127.0.0.1',p)) # bound, not listening; cannot reach an unrelated process
    def refuse_receiver(self):
        self.stop.set();self.listener.close();self.thread.join(2)
        self.receiver_reservation=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.receiver_reservation.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        self.receiver_reservation.bind(('127.0.0.1',self.receiver_port))
    def finish(self):
        global ACTIVE
        if self.worker:
            try:self.worker.wait(4)
            except subprocess.TimeoutExpired:self.worker.terminate();self.worker.wait(3)
            stdout,stderr=self.worker.communicate(timeout=2)
            put(self.root/'process.json',{'pid':self.worker.pid,'exit':self.worker.returncode,'stderr':stderr.decode(errors='replace'),'remaining_stdout':stdout.decode(errors='replace')})
        self.stop.set()
        self.listener.close()
        for c in self.clients:
            try:c.close()
            except OSError:pass
        self.thread.join(2)
        if hasattr(self,'reservation'):self.reservation.close()
        if hasattr(self,'receiver_reservation'):self.receiver_reservation.close()
        ACTIVE=None
        assert not self.thread.is_alive(),'RECEIVER_THREAD_LEAK'
        assert not self.errors,self.errors
        put(self.root/'receiver_receipts.json',self.receipts)
        put(self.root/'observer.json',{'attempts':self.monitor['attempts'],'violations':self.monitor['violations'],'owned_ports':sorted(self.monitor['owned_ports']),'worker_pid':self.worker.pid if self.worker else None})
        OBS.append({'root':str(self.root.relative_to(broker.REPORT)), 'receipts':len(self.receipts),'violations':self.monitor['violations']})
    def __enter__(self):return self
    def __exit__(self,*exc):self.finish()

def observation():
    p=contract();r=p['integration']['route'];sid=p['integration']['identities']['broker'];session=str(uuid.uuid4());epoch=str(uuid.uuid4())
    expected={'session_id':session,'generation':1,'broker_pid':12345,'observer_epoch':epoch,'now_tick':1010,'profile_sha256':common.digest(p),'source_sha256':broker.source_pin()}
    def sock(addr,port):return {'pid':12345,'owner_sid':sid,'family':'IPv4','transport':'TCP','address':addr,'port':port}
    o={'schema':1,'kind':'SYNTHETIC_ONLY','session_id':session,'generation':1,'observer_epoch':epoch,'issued_tick':1000,'expires_tick':2000,'profile_sha256':common.digest(p),'source_sha256':broker.source_pin(),'request_id':str(uuid.uuid4()),'listener':sock('127.0.0.1',r['client_proxy_port']),'egress':sock(r['egress_ip'],r['egress_port']),'children':[]}
    return p,o,expected

class ContractTests(unittest.TestCase):
    def reject(self,p):
        v=broker.preflight(p,common.digest(p),broker.source_pin());self.assertEqual(v['profile_status'],'BROKER_PROFILE_REJECTED');self.assertFalse(v['can_apply'] or v['can_start_tunnel'])
    def test_valid_contract_is_always_disabled(self):
        p=contract();v=broker.preflight(p,common.digest(p),broker.source_pin());self.assertEqual(v['profile_status'],'BROKER_PROFILE_STRUCTURALLY_VALID');self.assertFalse(v['can_apply'] or v['can_start_tunnel']);self.assertIsNone(v['engine_native_config']);self.assertIn('ENGINE_CONFIG_COMPATIBILITY_BLOCKED',v['gates'])
    def test_unbound_template_rejected(self):
        self.reject(json.loads((PKG/'configs/v2ray.engine.disabled.contract.json').read_text()))
    def test_startup_policy_cannot_be_enabled_by_data(self):
        p=contract();p['lifecycle']['startup']='ENABLED';self.reject(p)
        p=contract();p['lifecycle']['on_observer_or_policy_loss']='KEEP_EXISTING_FLOWS';self.reject(p)
    def test_owner_sid_and_wrapper_rejected(self):
        for role in ['ui','client']:
            p=contract();p['integration']['processes']['v2ray']=p['integration']['identities'][role];self.reject(p)
        p=contract();p['ownership']['egress']='USER_PROCESS';self.reject(p)
    def test_direct_fallback_second_proxy_and_rule_precedence(self):
        for key in ['direct','fallback','secondary_proxy','load_balancer','host_dns','udp','ipv6','health_dials','telemetry']:
            p=contract();p['routing'][key]=True;self.reject(p)
        p=contract();p['routing']['rule_order'].reverse();self.reject(p)
        p=contract();p['routing']['default']='DIRECT';self.reject(p)
    def test_literal_ip_port_and_protocol(self):
        for key,val in [('egress_ip','upstream.invalid'),('egress_ip','::1'),('egress_ip','127.0.0.1'),('egress_ip','169.254.1.1'),('egress_ip','255.255.255.255'),('egress_port',True),('client_proxy_port',65536),('remote_protocol','udp'),('proxy_scheme','socks5')]:
            p=contract();p['integration']['route'][key]=val;self.reject(p)
    def test_extra_companion_and_user_socks_layout(self):
        p=contract();p['routing']['companions']=['helper.exe'];self.reject(p)
        p=contract();p['integration']['route']['layout']='WRAPPER_TO_USER_SOCKS';self.reject(p)
    def test_config_and_source_drift(self):
        p=contract()
        for pin,source,code in [('0'*64,broker.source_pin(),'CONFIG_PIN_MISMATCH'),(common.digest(p),'0'*64,'SOURCE_PIN_MISMATCH')]:
            v=broker.preflight(p,pin,source);self.assertEqual(v['reason'],code)
    def test_native_config_and_engine_switch_rejected(self):
        p=contract();p['native_config']={'outbounds':[{'protocol':'freedom'}]};self.reject(p)
        p=contract();p['engine']['family']='sing-box';self.reject(p)
    def test_approval_claims_never_activate(self):
        p=contract();p['integration']['approval']={k:True for k in p['integration']['approval']}
        v=broker.preflight(p,common.digest(p),broker.source_pin(),{'all_approved':True,'signature':'looks-signed','engine_verified':True});self.assertFalse(v['can_apply'] or v['can_start_tunnel'] or v['untrusted_evidence_accepted'])
        p['all_approved']=True;self.reject(p)
    def test_claimed_version_and_hash_not_verification(self):
        p=contract();p['engine'].update(implementation='untrusted claim',version='99.99',source_sha256='1'*64,config_schema_sha256='3'*64,binary_sha256='2'*64)
        v=broker.preflight(p,common.digest(p),broker.source_pin());self.assertIn('ENGINE_VERSION_SOURCE_BLOCKED',v['gates']);self.assertIn('ENGINE_CONFIG_COMPATIBILITY_BLOCKED',v['gates'])
        p['engine']['binary_sha256']='4'*64;self.reject(p)
    def test_unknown_fields_duplicate_json_and_malformed_legacy_child(self):
        p=contract();p['engine']['environment_override']=True;self.reject(p)
        with self.assertRaises(common.Denied):common.parse(b'{"schema":1,"schema":1}')
        p=contract();p['integration']['children']=['bad','shape'];self.reject(p)
    def test_valid_synthetic_observation_never_native_health(self):
        p,o,e=observation();r=broker.check_synthetic_observation(p,o,e,set());self.assertEqual(r['synthetic_health'],'VALID');self.assertEqual(r['native_health'],'UNKNOWN');self.assertFalse(r['real_owner_verified'] or r['can_apply'])
    def test_whole_config_substitution_still_uses_controller_pin(self):
        p,o,e=observation();p['integration']['route']['egress_port']=444;o['egress']['port']=444;o['profile_sha256']=common.digest(p)
        with self.assertRaisesRegex(common.Denied,'CONFIG_PIN_MISMATCH'):broker.check_synthetic_observation(p,o,e,set())
    def test_remote_schema_reference_is_refused_without_dial(self):
        original=broker.SCHEMA
        with Harness('schema-ref') as h:
            path=h.root/'remote-ref.json';put(path,{'$ref':'http://127.0.0.1:'+str(h.receiver_port)+'/schema'})
            try:
                broker.SCHEMA=path;p=contract();v=broker.preflight(p,common.digest(p),broker.source_pin());self.assertEqual(v['reason'],'SCHEMA_EXTERNAL_REF');self.assertEqual(h.monitor['attempts'],[])
            finally:broker.SCHEMA=original
    def test_observation_owner_egress_must_be_same_engine(self):
        p,o,e=observation();o['egress'].update(pid=54321,owner_sid=p['integration']['identities']['ui'])
        with self.assertRaisesRegex(common.Denied,'EGRESS_OWNER'):broker.check_synthetic_observation(p,o,e,set())
    def test_observation_takeover_scope_protocol_companion(self):
        for location,key,val in [('listener','pid',54321),('listener','address','0.0.0.0'),('egress','address','other.invalid'),('egress','port',10808),('egress','family','IPv6'),('egress','transport','UDP')]:
            p,o,e=observation();o[location][key]=val
            with self.assertRaises(common.Denied):broker.check_synthetic_observation(p,o,e,set())
        p,o,e=observation();o['children']=['companion']
        with self.assertRaises(common.Denied):broker.check_synthetic_observation(p,o,e,set())
    def test_observation_stale_replay_generation_source_and_observer_loss(self):
        p,o,e=observation();seen=set();broker.check_synthetic_observation(p,o,e,seen)
        with self.assertRaisesRegex(common.Denied,'REPLAY'):broker.check_synthetic_observation(p,o,e,seen)
        for key,val in [('expires_tick',1001),('generation',2),('session_id',str(uuid.uuid4())),('profile_sha256','0'*64),('source_sha256','0'*64),('observer_epoch',str(uuid.uuid4()))]:
            p,o,e=observation();o[key]=val
            with self.assertRaises(common.Denied):broker.check_synthetic_observation(p,o,e,set())
    def test_cli_always_exit20_and_output_scope(self):
        root=fresh('cli');p=contract();args=[sys.executable,'-I','-X','utf8','-B',str(PKG/'broker.py'),'--contract',str(PKG/'configs/broker.v1.synthetic.example.json'),'--pin',common.digest(p),'--source-pin',broker.source_pin(),'--output',str(root/'preflight.json')]
        done=subprocess.run(args,capture_output=True,text=True,timeout=10);self.assertEqual(done.returncode,20);v=json.loads((root/'preflight.json').read_text());self.assertFalse(v['can_apply'] or v['can_start_tunnel'])
        with self.assertRaises(common.Denied):broker.task_path(REPO/'web_alarm/server.py')
    def test_source_and_schema_syntax(self):
        for name in ['broker.py','broker_fixture.py']:
            compile((PKG/name).read_bytes(),name,'exec')
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(json.loads(broker.SCHEMA.read_text()))
    def test_existing_activation_gates_remain_blocked(self):
        # Static contracts/source plus the existing pure preflight; no installer,
        # NPFS process, assembly or native WFP function is executed here.
        npfs=PKG/'configs/npfs.fixture.contract.json'
        wfp=REPO/'reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/contracts/backend-contract.json'
        core=wfp.parents[1]/'source/Core.cs'
        toolkit=REPO/'reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/toolkit/backends/UnavailableWfpBackend.cs'
        n=json.loads(npfs.read_text());w=json.loads(wfp.read_text())
        self.assertFalse(n['can_apply'] or n['can_start_tunnel'] or w['CanApply'])
        self.assertEqual(n['install_uninstall'],'BLOCKED')
        self.assertIn('public static bool CanApply{get{return false;}}',core.read_text())
        self.assertIn('BLOCKED:NO_LAB_ACCEPTED_NATIVE_BACKEND',core.read_text())
        self.assertIn('public bool CanApply { get { return false; } }',toolkit.read_text())
        self.assertIn('NO_REVIEWED_EXECUTABLE_SECURITY_BACKEND',toolkit.read_text())
        p=contract()['integration'];p['approval']={k:True for k in p['approval']}
        v=broker.security.preflight(p,common.digest(p),{'all_approved':True})
        self.assertFalse(v['can_apply'] or v['can_start_tunnel'])
        put(fresh('legacy-gates')/'checks.json',{'method':'static contracts/source plus existing pure preflight; not native execution','can_apply':False,'can_start_tunnel':False,'sources':{p.relative_to(REPO).as_posix():sha(p) for p in [npfs,wfp,core,toolkit]}})

class RouteTests(unittest.TestCase):
    def test_same_fixture_instance_cannot_restart(self):
        with Harness('duplicate-instance') as h:
            h.start();h.request();first=h.worker;stdout,stderr=first.communicate(timeout=4);put(h.root/'first_process.json',{'pid':first.pid,'exit':first.returncode,'stderr':stderr.decode(errors='replace')})
            h.start();self.assertIsNone(h.ready);self.assertEqual(h.worker.wait(3),20)
        self.assertIn('FRESH_FIXTURE_REQUIRED',json.loads((h.root/'process.json').read_text())['stderr'])
    def test_upstream_connection_refused(self):
        with Harness('upstream-refused') as h:
            h.refuse_receiver();h.start()
            with self.assertRaises((common.Denied,OSError,TimeoutError)):h.request()
            self.assertEqual(h.receipts,[]);self.assertEqual(h.monitor['violations'],[])
        self.assertEqual(len(json.loads((h.root/'worker_receipt.json').read_text())['events']),1)
    def test_port_takeover_is_observed_and_response_rejected(self):
        with Harness('port-takeover') as h:
            h.start();expected_pid=h.worker.pid;h.reserve_failed_broker();h.reservation.listen(1);h.reservation.settimeout(2)
            owners={row[5] for row in tcp_rows() if row[0]==2 and port(row[2])==h.ready['port']}
            self.assertEqual(owners,{os.getpid()});self.assertNotIn(expected_pid,owners)
            errors=[]
            def wrong_peer():
                try:
                    with h.reservation.accept()[0] as c:
                        head(c);c.sendall(b'HTTP/1.1 200 OK\r\n\r\n');request=head(c);rid=next(x.split(':',1)[1].strip() for x in request if x.startswith('X-Request-ID:'));body=common.canonical({'request_id':rid,'route_nonce':'wrong-instance','phase':'poll'});c.sendall(('HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body))+'\r\n\r\n').encode()+body)
                except BaseException as e:errors.append(type(e).__name__)
            t=threading.Thread(target=wrong_peer,daemon=True);t.start()
            try:
                with self.assertRaisesRegex(common.Denied,'FIXTURE_AUTHORITY_MISMATCH'):h.request()
            finally:t.join(3)
            self.assertFalse(t.is_alive());self.assertEqual(errors,[]);self.assertEqual(h.receipts,[])
            put(h.root/'takeover.json',{'expected_pid':expected_pid,'actual_listener_pid':os.getpid(),'wrong_nonce_rejected':True,'Windows_token_proof':False})
    def test_same_process_connect_and_egress_receipt(self):
        with Harness('route') as h:
            h.start();result=h.request();self.assertEqual(len(h.receipts),1);receipt=h.receipts[0]
            self.assertEqual(receipt['request_id'],result['request_id']);self.assertEqual(receipt['observed_sender_pid'],h.worker.pid)
            body={k:v for k,v in receipt.items() if k!='receipt_hmac'};self.assertEqual(receipt['receipt_hmac'],hmac.new(h.key,common.canonical(body),hashlib.sha256).hexdigest())
            self.assertEqual(h.monitor['violations'],[])
        worker=json.loads((h.root/'worker_receipt.json').read_text());self.assertEqual(len(worker['events']),1);self.assertTrue(worker['events'][0]['allowed'])
    def test_receiver_fault_matrix_bounded_no_fallback(self):
        for fault in ['reset','timeout','partial','redirect','takeover']:
            with Harness('fault-'+fault,fault) as h:
                h.start();start=time.monotonic()
                with self.assertRaises((common.Denied,OSError,TimeoutError)):h.request()
                self.assertLess(time.monotonic()-start,3);self.assertEqual(h.monitor['violations'],[])
    def test_broker_listener_failure_no_receiver_receipt(self):
        with Harness('failed-listener') as h:
            h.start();h.reserve_failed_broker()
            with self.assertRaises((common.Denied,OSError,TimeoutError)):h.request()
            self.assertEqual(h.receipts,[]);self.assertEqual(h.monitor['violations'],[])
    def test_partial_connect_and_timeout(self):
        with Harness('partial-connect') as h:
            h.start()
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                s.settimeout(2);s.connect(('127.0.0.1',h.ready['port']));s.sendall(b'CONN')
                self.assertEqual(s.recv(10),b'')
            self.assertEqual(h.receipts,[])
    def test_fixture_pin_and_hostname_rejected_before_bind(self):
        for change,tamper in [({},True),({'upstream_address':'upstream.invalid'},False)]:
            with Harness('bad-start') as h:
                h.start(change,tamper);self.assertIsNone(h.ready);self.assertEqual(h.worker.wait(3),20);self.assertEqual(h.receipts,[])
    def test_ambient_proxy_no_fallback_and_dns_udp_ipv6_guard(self):
        with Harness('ambient') as h:
            h.start()
            with self.assertRaisesRegex(common.Denied,'ENV_OVERRIDE'):h.request({'NO_PROXY':'*','ALL_PROXY':'socks5://other.invalid:9'})
            self.assertEqual(h.monitor['attempts'],[])
            with self.assertRaises(PermissionError):socket.getaddrinfo('forbidden.invalid',443)
            for family,kind in [(socket.AF_INET6,socket.SOCK_STREAM),(socket.AF_INET,socket.SOCK_DGRAM)]:
                with self.assertRaises(PermissionError):socket.socket(family,kind)
    def test_restart_has_fresh_instance_and_receipt_session(self):
        sessions=[]
        for _ in range(2):
            with Harness('restart') as h:
                h.start();h.request();sessions.append((h.boot['session_id'],h.boot['instance_id'],h.receipts[0]['session_id']))
        self.assertNotEqual(sessions[0][:2],sessions[1][:2]);self.assertTrue(all(x[0]==x[2] for x in sessions))
    def test_direct_mutation_oracle(self):
        normal='def call(h):\n    return route.control_request(h.ready["port"],"control.invalid:443","poll",h.nonce)\n'
        changed=normal.replace('return route.control_request(h.ready["port"],"control.invalid:443","poll",h.nonce)','return direct(h)')
        def direct(h):
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
                s.settimeout(1);s.connect(('127.0.0.1',h.receiver_port));rid=str(uuid.uuid4());s.sendall(('GET /poll HTTP/1.1\r\nHost: control.invalid:443\r\nX-Request-ID: '+rid+'\r\n\r\n').encode());code,headers=route.header(s,time.monotonic()+1);self.assertEqual(code,200);return route.receive(s,int(headers['content-length']),time.monotonic()+1)
        with Harness('direct-mutant') as h:
            h.start();h.reserve_failed_broker();scope={'route':route,'direct':direct};exec(compile(changed,'direct_mutant','exec'),scope)
            scope['call'](h)
            self.assertEqual(h.receipts[0]['observed_sender_pid'],os.getpid());self.assertIn('DIRECT_OR_SECOND_PROXY',h.monitor['violations'])
            put(h.root/'mutation.json',{'oracle':'FAIL (required detection)','source':changed,'normal_sha256':hashlib.sha256(normal.encode()).hexdigest(),'mutant_sha256':hashlib.sha256(changed.encode()).hexdigest(),'trigger':'real direct GET reached independent receiver while broker refused'})
    def test_owner_mutation_oracle(self):
        source=(PKG/'broker.py').read_text();old="require(egress['pid'] == listener['pid'] and egress['owner_sid'] == owner, 'EGRESS_OWNER')";self.assertEqual(source.count(old),1)
        changed=source.replace(old,"require(True, 'EGRESS_OWNER')");m=types.ModuleType('owner_mutant');m.__file__=str(PKG/'broker.py');exec(compile(changed,str(PKG/'broker.py'),'exec'),m.__dict__)
        p,o,e=observation();o['egress'].update(pid=54321,owner_sid=p['integration']['identities']['ui'])
        class Oracle(unittest.TestCase):
            def runTest(self):
                with self.assertRaises(common.Denied):m.check_synthetic_observation(p,o,e,set())
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream).run(Oracle())
        self.assertEqual(len(result.failures),1);self.assertEqual(len(result.errors),0)
        root=fresh('owner-mutant');(root/'broker_mutant.py').write_text(changed,encoding='utf-8');put(root/'mutation.json',{'oracle':'FAIL (required detection)','inner_collected':result.testsRun,'inner_failures':len(result.failures),'inner_errors':len(result.errors),'trigger':'egress attestation names different process and UI SID','scope':'synthetic assertion, not actual Windows SID proof','runner':stream.getvalue()})

class Result(unittest.TextTestResult):
    def addSuccess(self,test):super().addSuccess(test);RESULTS.append({'id':test.id(),'status':'PASS'})
    def addFailure(self,test,err):super().addFailure(test,err);RESULTS.append({'id':test.id(),'status':'FAIL','traceback':self._exc_info_to_string(err,test)})
    def addError(self,test,err):super().addError(test,err);RESULTS.append({'id':test.id(),'status':'ERROR','traceback':self._exc_info_to_string(err,test)})

def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--select');a=p.parse_args()
    OUT=broker.REPORT/'runs'/('suite-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);OUT.mkdir()
    snap=OUT/'source_snapshot';snap.mkdir()
    paths=[PKG/'broker.py',PKG/'broker_fixture.py',PKG/'configs/broker.v1.schema.json',Path(__file__).resolve(),PKG/'common.py',PKG/'security_contract.py',PKG/'route_simulation.py']
    pins={str(x.relative_to(REPO)):sha(x) for x in paths}
    for x in paths:(snap/x.name).write_bytes(x.read_bytes())
    put(OUT/'source_pins.json',pins)
    suite=unittest.defaultTestLoader.loadTestsFromName(a.select,module=sys.modules[__name__]) if a.select else unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in [ContractTests,RouteTests])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    value={'task':broker.TASK,'collected':result.testsRun,'passed':sum(x['status']=='PASS' for x in RESULTS),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'tests':RESULTS,'observations':OBS,'source_pin':broker.source_pin(),'python':sys.version,'engine_runs':0,'Windows_B_identity_proof':False}
    put(OUT/'result.json',value);print('EVIDENCE '+str(OUT));return 0 if result.testsRun and result.wasSuccessful() else 1
if __name__=='__main__':sys.exit(main())
