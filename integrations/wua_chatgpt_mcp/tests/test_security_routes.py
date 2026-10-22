"""Owned-loopback route faults + contract/security tests, not native isolation."""
import copy,importlib.util,io,json,os,queue,secrets,select,socket,sys,threading,time,types,unittest,uuid
from pathlib import Path
PKG=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PKG))
import common,security_contract as security,route_simulation as route
from reference_connect import Adapter,Config,close,recv_exact
from api_channel import ApiChannel
OUT=Path(sys.argv[1]);MUTANT=sys.argv[2] if len(sys.argv)>2 else None
assert MUTANT in [None,'route','owner']
if MUTANT:
    source=PKG/('route_simulation.py' if MUTANT=='route' else 'security_contract.py');text=source.read_text(encoding='utf-8')
    old="sock.connect(('127.0.0.1',broker_port))" if MUTANT=='route' else "p['v2ray']==ids['broker']"
    new="sock.connect(('127.0.0.1',broker_port+1))" if MUTANT=='route' else 'True'
    assert text.count(old)==1;text=text.replace(old,new);(OUT/'mutated_source.py').write_text(text,encoding='utf-8')
    module=types.ModuleType('reviewed_mutant');module.__file__=str(source);exec(compile(text,str(source),'exec'),module.__dict__)
    if MUTANT=='route':route=module
    else:security=module
ACTIVE=None
def observe(event,args):
    monitor=ACTIVE
    if monitor is None:return
    if event in ['socket.getaddrinfo','socket.gethostbyname']:
        monitor['violations'].append({'kind':'DNS_ATTEMPT'});raise PermissionError('NO_FIXTURE_DNS')
    if event=='socket.bind':
        addr=args[1]
        if addr[0]!='127.0.0.1' or addr[1] not in {0,*monitor['owned_ports']}:
            monitor['violations'].append({'kind':'BIND_OUTSIDE_FIXTURE'});raise PermissionError('OWNED_BIND_ONLY')
    if event=='socket.connect':
        addr=args[1];name=threading.current_thread().name
        role='broker' if name=='adapter-worker' else 'socks' if name=='fixture-socks-worker' else 'client'
        allowed=monitor['edges'].get(role,set());ok=addr in allowed
        monitor['attempts'].append({'role':role,'target_port':addr[1] if type(addr) is tuple else None,'allowed':ok})
        if not ok:monitor['violations'].append({'kind':'UNEXPECTED_CONNECT','role':role});raise PermissionError('OWNED_EDGE_ONLY')
sys.addaudithook(observe)
class OwnedServer:
    def __init__(self,kind,handler,port=0):
        self.kind=kind;self.handler=handler;self.stop_event=threading.Event();self.clients=[];self.threads=[];self.errors=[]
        self.listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM);self.listener.bind(('127.0.0.1',port));self.port=self.listener.getsockname()[1]
        if ACTIVE is not None:ACTIVE['owned_ports'].add(self.port)
        self.listener.listen(4);self.listener.settimeout(.05);self.thread=threading.Thread(target=self.loop,name='fixture-'+kind);self.thread.start()
    def loop(self):
        while not self.stop_event.is_set():
            try:c,_=self.listener.accept()
            except TimeoutError:continue
            except OSError:return
            self.clients.append(c);t=threading.Thread(target=self.handle,args=(c,),name='fixture-'+self.kind+'-worker');self.threads.append(t);t.start()
    def handle(self,c):
        try:self.handler(c)
        except (OSError,common.Denied,TimeoutError):pass
        except BaseException as e:self.errors.append(type(e).__name__)
        finally:close(c)
    def stop(self):
        self.stop_event.set();close(self.listener)
        for c in self.clients:close(c)
        self.thread.join(1)
        for t in self.threads:t.join(1)
        assert not self.thread.is_alive() and not any(t.is_alive() for t in self.threads),'OWNED_THREAD_LEAK'
        assert not self.errors,'FIXTURE_UNEXPECTED_ERRORS'
def read_head(c):
    raw=b'';deadline=time.monotonic()+1
    while not raw.endswith(b'\r\n\r\n'):
        assert len(raw)<2048;raw+=recv_exact(c,1,deadline)
    return raw.decode('ascii').split('\r\n')
class RouteHarness:
    def __init__(self,socks_fault=None,control_fault=None):
        global ACTIVE
        ACTIVE={'attempts':[],'violations':[],'edges':{},'owned_ports':set()};self.monitor=ACTIVE;self.nonce=secrets.token_hex(32);self.receipts=[];self.socks_seen=[];self.fault=socks_fault
        def control(c):
            lines=read_head(c);phase=lines[0].split(' ')[1][1:];rid=next(x.split(':',1)[1].strip() for x in lines if x.lower().startswith('x-request-id:'))
            self.receipts.append({'phase':phase,'request_id':rid})
            if control_fault=='redirect':c.sendall(b'HTTP/1.1 307 Temporary Redirect\r\nContent-Length: 0\r\nLocation: https://redirect.invalid/\r\n\r\n');return
            v={'request_id':rid,'route_nonce':'incorrect' if control_fault=='takeover' else self.nonce,'phase':phase};data=json.dumps(v).encode()
            n=99999 if control_fault=='oversize' else len(data)
            c.sendall(('HTTP/1.1 200 OK\r\nContent-Length: '+str(n)+'\r\n\r\n').encode()+data)
        self.control=OwnedServer('control',control)
        def socks(c):
            if self.fault=='abrupt':return
            if self.fault=='timeout':self.socks.stop_event.wait(.4);return
            assert recv_exact(c,3,time.monotonic()+1)==b'\x05\x01\x00'
            c.sendall(b'\x04\x00' if self.fault=='malformed' else b'\x05\x00')
            if self.fault=='malformed':return
            assert recv_exact(c,4,time.monotonic()+1)==b'\x05\x01\x00\x03';n=recv_exact(c,1,time.monotonic()+1)[0];host=recv_exact(c,n,time.monotonic()+1).decode();port=int.from_bytes(recv_exact(c,2,time.monotonic()+1),'big');self.socks_seen.append((host,port))
            assert host in ['control.invalid','mcp.invalid','oauth.invalid','harpoon.invalid'] and port==443
            if self.fault=='refused':c.sendall(b'\x05\x05\x00\x01'+bytes(6));return
            c.sendall(b'\x05\x00\x00\x01'+bytes(6))
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as upstream:
                upstream.settimeout(1);upstream.connect(('127.0.0.1',self.control.port));deadline=time.monotonic()+2
                while time.monotonic()<deadline and not self.socks.stop_event.is_set():
                    ready,_,_=select.select([c,upstream],[],[],.03)
                    for source in ready:
                        data=source.recv(4096)
                        if not data:return
                        (upstream if source is c else c).sendall(data)
        self.socks=OwnedServer('socks',socks)
        self.monitor['edges']['socks']={('127.0.0.1',self.control.port)}
        self.monitor['edges']['broker']={('127.0.0.1',self.socks.port)}
        cfg=Config('127.0.0.1',self.socks.port,frozenset(h+':443' for h in ['control.invalid','mcp.invalid','oauth.invalid','harpoon.invalid']),handshake_timeout=.15,idle_timeout=.4,max_duration=1.5)
        self.adapter=Adapter(cfg).start();self.monitor['owned_ports'].add(self.adapter.port);self.monitor['edges']['client']={('127.0.0.1',self.adapter.port)}
    def request(self,authority='control.invalid:443',phase='poll',ambient=None):return route.control_request(self.adapter.port,authority,phase,self.nonce,ambient)
    def stop(self):
        global ACTIVE
        self.adapter.stop();self.socks.stop();self.control.stop();ACTIVE=None
        assert not self.adapter.unexpected,'ADAPTER_UNEXPECTED_ERROR'
class RouteTests(unittest.TestCase):
    def setUp(self):self.h=None
    def tearDown(self):
        if self.h:
            self.h.stop();OBSERVATIONS.append({'case':self._testMethodName,'attempts':self.h.monitor['attempts'],'violations':self.h.monitor['violations'],'control_receipts':self.h.receipts,'broker_event_codes':[v['code'] for v in self.h.adapter.events]})
    def test_control_plane_paths_and_receipt_correlation(self):
        self.h=RouteHarness()
        for authority,phase in [('control','poll'),('control','result'),('control','secret'),('control','health'),('mcp','mcp'),('oauth','oauth'),('harpoon','harpoon')]:
            try:r=self.h.request(authority+'.invalid:443',phase)
            except (common.Denied,OSError,TimeoutError):self.fail('Expected approved route did not reach independent receiver')
            self.assertIn({'request_id':r['request_id'],'phase':phase},self.h.receipts)
        self.assertEqual(len(self.h.receipts),7);self.assertEqual(self.h.monitor['violations'],[]);self.assertEqual(len([x for x in self.h.monitor['attempts'] if x['role']=='client']),7)
    def test_socks_fault_matrix_no_direct_fallback(self):
        for fault in ['refused','timeout','abrupt','malformed']:
            h=RouteHarness(fault)
            try:
                with self.assertRaises((common.Denied,OSError,TimeoutError)):h.request()
                self.assertEqual(h.receipts,[]);self.assertEqual(h.monitor['violations'],[]);self.assertEqual([x['role'] for x in h.monitor['attempts']],['client','broker'])
            finally:h.stop();OBSERVATIONS.append({'case':'socks_'+fault,'attempts':h.monitor['attempts'],'violations':h.monitor['violations'],'broker_event_codes':[v['code'] for v in h.adapter.events]})
    def test_closed_socks_listener_bounded_no_fallback(self):
        self.h=RouteHarness();self.h.socks.stop()
        with self.assertRaises((common.Denied,OSError)):self.h.request()
        self.assertEqual(self.h.receipts,[]);self.assertEqual(self.h.monitor['violations'],[])
    def test_closed_broker_listener_bounded(self):
        self.h=RouteHarness();self.h.adapter.stop()
        with self.assertRaises(OSError):self.h.request()
        self.assertEqual([v['role'] for v in self.h.monitor['attempts']],['client']);self.assertEqual(self.h.receipts,[])
    def test_redirect_and_oversized_response_denied(self):
        for fault in ['redirect','oversize']:
            h=RouteHarness(control_fault=fault)
            try:
                with self.assertRaises(common.Denied):h.request()
                self.assertEqual(len(h.receipts),1);self.assertEqual(h.monitor['violations'],[])
            finally:h.stop()
    def test_environment_secondary_proxy_no_proxy_rejected_before_dial(self):
        self.h=RouteHarness()
        for env in [{'HTTP_PROXY':'http://secondary.invalid:1'},{'HTTPS_PROXY':'http://secondary.invalid:2'},{'ALL_PROXY':'socks5://secondary.invalid:3'},{'NO_PROXY':'*'},{'CLOUDFLARED_MANAGED':'true'}]:
            with self.assertRaises(common.Denied):self.h.request(ambient=env)
        self.assertEqual(self.h.monitor['attempts'],[])
    def test_endpoint_substitution_and_method_rejected(self):
        self.h=RouteHarness()
        with self.assertRaises(common.Denied):self.h.request('unapproved.invalid:443')
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1',self.h.adapter.port));s.sendall(b'GET http://unapproved.invalid/ HTTP/1.1\r\n\r\n');self.assertIn(b'405',s.recv(256))
        self.assertEqual(self.h.receipts,[]);self.assertEqual(self.h.socks_seen,[])
    def test_port_takeover_fails_authority_nonce(self):
        self.h=RouteHarness();port=self.h.adapter.port;self.h.adapter.stop()
        def impostor(c):
            read_head(c);c.sendall(b'HTTP/1.1 200 OK\r\n\r\n');lines=read_head(c);rid=next(x.split(':',1)[1].strip() for x in lines if x.lower().startswith('x-request-id:'));data=json.dumps({'request_id':rid,'route_nonce':'wrong_owner','phase':'poll'}).encode();c.sendall(('HTTP/1.1 200 OK\r\nContent-Length: '+str(len(data))+'\r\n\r\n').encode()+data)
        fake=OwnedServer('impostor',impostor,port)
        try:
            with self.assertRaises(common.Denied):self.h.request()
            self.assertEqual(self.h.receipts,[])
        finally:fake.stop()
    def test_observer_flags_unexpected_owned_loopback_attempt(self):
        self.h=RouteHarness()
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
            with self.assertRaises(PermissionError):s.connect(('127.0.0.1',self.h.control.port))
        self.assertEqual(self.h.monitor['violations'],[{'kind':'UNEXPECTED_CONNECT','role':'client'}]);self.assertEqual(self.h.receipts,[])
class SecurityTests(unittest.TestCase):
    def test_reference_broker_rejects_unbounded_or_nonloopback_config(self):
        for fields in [{'socks_host':'0.0.0.0'},{'socks_port':True},{'max_connections':1000},{'handshake_timeout':float('inf')},{'listen_port':-1},{'max_tunnel_bytes':0}]:
            values={'socks_host':'127.0.0.1','socks_port':32124,'allowlist':frozenset(['control.invalid:443'])};values.update(fields)
            with self.assertRaises(ValueError):Config(**values)
    def test_valid_synthetic_contract_still_blocks_real_activation(self):
        p=security.synthetic_profile();r=security.validate(p,common.digest(p));self.assertEqual(r['contract_validation'],'VALID');self.assertFalse(r['can_apply'] or r['can_start_tunnel'])
    def test_v2ray_host_user_owner_mismatch_denied(self):
        p=security.synthetic_profile();p['processes']['v2ray']=p['identities']['ui']
        with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
    def test_same_foreign_builtin_or_ui_SID_denied(self):
        for v in ['S-1-5-18','S-1-5-21-101-202-303-1001','S-1-5-21-909-202-303-1002']:
            p=security.synthetic_profile();p['identities']['broker']=v
            with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
    def test_unknown_child_wrong_owner_and_hash_denied(self):
        for mutation in ['role','owner','hash']:
            p=security.synthetic_profile()
            if mutation=='role':p['children'][0]['role']='browser'
            elif mutation=='owner':p['children'][0]['owner_sid']=p['identities']['ui']
            else:p['children'][0]['sha256']='not_a_hash'
            with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
    def test_extra_TCP_or_regular_user_socks_route_denied(self):
        for key,value in [('layout','REFERENCE_CONNECT_TO_HOST_USER_SOCKS'),('client_proxy_host','0.0.0.0'),('proxy_scheme','socks5'),('dns','HOST_RESOLVER')]:
            p=security.synthetic_profile();p['route'][key]=value
            with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
        p=security.synthetic_profile();p['ipc']['mcp_to_server']='HTTP_OTHER_PORT'
        with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
    def test_config_flags_fake_proofs_cannot_activate(self):
        p=security.synthetic_profile();p['approval']={k:True for k in p['approval']};r=security.preflight(p,common.digest(p),{'WFP':True,'accounts':True,'verified':True});self.assertFalse(r['can_apply'] or r['can_start_tunnel'] or r['untrusted_evidence_accepted'])
        for key,value in [('allow_direct',True),('secondary_proxies',['http://secondary.invalid']),('startup_state','ENABLED'),('environment_override',True)]:
            q=copy.deepcopy(p);q[key]=value;self.assertEqual(security.preflight(q,common.digest(q))['contract_validation'],'FAIL')
    def test_startup_pin_tampering_and_unknown_field_denied(self):
        p=security.synthetic_profile();pin=common.digest(p);p['route']['client_proxy_port']+=1
        with self.assertRaises(common.Denied):security.validate(p,pin)
        p['required']=True
        with self.assertRaises(common.Denied):security.validate(p,common.digest(p))
    def test_strict_parser_and_path_scope(self):
        for raw in [b'{"x":1,"x":2}',b'{"v":NaN}',b'{"v":1.5}',b'['*20+b']'*20,b'"'+b'a'*8192+b'"']:
            with self.assertRaises(common.Denied):common.parse(raw)
        for path in ['https://example.invalid/x','\\\\server\\share\\x','M:/GitHub/ag_llm/.ultra']:
            with self.assertRaises(common.Denied):common.owned_path(path)
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.root=OUT/('api-'+uuid.uuid4().hex);self.root.mkdir();self.path=self.root/'bootstrap.json';self.session=str(uuid.uuid4());self.nonce=secrets.token_hex(32)
        self.b={'schema':1,'mode':'synthetic_fixture_only','fixture_id':common.FIXTURE,'root':str(self.root/'owned-api-state'),'session_id':self.session,'nonce':self.nonce,'channel_key':secrets.token_hex(32),'client_role':'wua-client'};self.path.write_text(json.dumps(self.b),encoding='utf-8');self.ch=None
    def tearDown(self):
        if self.ch:self.ch.close()
        self.path.unlink()
    def test_independent_api_auth_replay_and_readonly_scope(self):
        self.ch=ApiChannel(self.path);r=self.ch.call('context',str(uuid.uuid4()));self.assertIn(self.nonce,r['value']['GOAL']);self.assertEqual(r['baseline_sha256'],r['current_sha256'])
        body={'schema':1,'session_id':self.session,'request_id':str(uuid.uuid4()),'operation':'context','task_id':'other_task'}
        self.ch.process.stdin.write(common.canonical({'body':body,'mac':common.mac(body,self.b['channel_key'])})+b'\n');self.ch.process.stdin.flush();self.assertFalse(self.ch._read()['ok'])
        body['task_id']=common.FIXTURE;body['operation']='write';self.ch.process.stdin.write(common.canonical({'body':body,'mac':common.mac(body,self.b['channel_key'])})+b'\n');self.ch.process.stdin.flush();self.assertFalse(self.ch._read()['ok'])
        rid=str(uuid.uuid4());self.ch.call('status',rid)
        with self.assertRaises(common.Denied):self.ch.call('status',rid)
        self.assertIsNotNone(self.ch.process.poll());self.assertFalse(self.ch.reader.is_alive())
    def test_wrong_MAC_fail_closed_and_child_stops(self):
        self.ch=ApiChannel(self.path);self.ch.bootstrap['channel_key']='0'*64
        with self.assertRaises(common.Denied):self.ch.call('status',str(uuid.uuid4()))
        self.assertIsNotNone(self.ch.process.poll());self.assertFalse(self.ch.reader.is_alive())
    def test_child_exit_no_retry_or_replacement(self):
        self.ch=ApiChannel(self.path);pid=self.ch.process.pid;self.ch.process.terminate();self.ch.process.wait(1)
        with self.assertRaises(common.Denied):self.ch.call('status',str(uuid.uuid4()))
        self.assertEqual(pid,self.ch.process.pid);self.assertFalse(self.ch.reader.is_alive())
    def test_response_nonce_session_hash_and_storage_substitution_denied(self):
        for field in ['nonce','session_id','value_sha256','current_sha256']:
            stage=self.root/field;stage.mkdir();boot=stage/'bootstrap.json';data=copy.deepcopy(self.b);data['root']=str(stage/'owned-api-state');boot.write_text(json.dumps(data),encoding='utf-8');channel=None
            try:
                channel=ApiChannel(boot);original=channel._read
                def altered():
                    response=original();response[field]='substituted';return response
                channel._read=altered
                with self.assertRaises(common.Denied):channel.call('context',str(uuid.uuid4()))
                self.assertIsNotNone(channel.process.poll());self.assertFalse(channel.reader.is_alive())
            finally:
                if channel:channel.close()
                boot.unlink()
    def test_production_root_and_untrusted_bootstrap_denied(self):
        self.b['root']=str(common.REPO/'.ultra');self.path.write_text(json.dumps(self.b),encoding='utf-8')
        with self.assertRaises(common.Denied):ApiChannel(self.path)
    def test_oversized_real_MCP_frame_stops_and_reaps_API_child(self):
        import subprocess
        env=common.clean_environment()
        p=subprocess.run([sys.executable,'-I','-X','utf8','-B',str(PKG/'server.py'),str(self.path)],input=b'{"padding":"'+b'x'*9000+b'"}\n',capture_output=True,env=env,cwd=PKG,timeout=7)
        self.assertEqual(p.returncode,20);self.assertNotIn(b'Traceback',p.stderr)
        stopped=json.loads((self.root/'owned-api-state/owned-api-stop.json').read_bytes());self.assertEqual(stopped['api_exit_code'],0);self.assertTrue(stopped['reader_stopped'])
OBSERVATIONS=[]
class Result(unittest.TextTestResult):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.rows=[]
    def addSuccess(self,t):super().addSuccess(t);self.rows.append({'name':t._testMethodName,'status':'PASS'})
    def addFailure(self,t,e):super().addFailure(t,e);self.rows.append({'name':t._testMethodName,'status':'FAIL'})
    def addError(self,t,e):super().addError(t,e);self.rows.append({'name':t._testMethodName,'status':'ERROR','class':e[0].__name__})
if __name__=='__main__':
    stream=io.StringIO()
    if MUTANT=='route':suite=unittest.TestSuite([RouteTests('test_control_plane_paths_and_receipt_correlation')])
    elif MUTANT=='owner':suite=unittest.TestSuite([SecurityTests('test_v2ray_host_user_owner_mismatch_denied')])
    else:suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(x) for x in [RouteTests,SecurityTests,ApiTests])
    r=unittest.TextTestRunner(stream=stream,resultclass=Result).run(suite)
    value={'total':r.testsRun,'passed':sum(x['status']=='PASS' for x in r.rows),'failed':len(r.failures),'errors':len(r.errors),'tests':r.rows,'route_observations':OBSERVATIONS,'synthetic_only':True,'native_calls':0,'mutation':MUTANT}
    (OUT/'result.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');(OUT/'runner.txt').write_text(stream.getvalue().replace(str(common.REPO),'<REPO>').replace(sys.base_prefix,'<PYTHON>'),encoding='utf-8');print(json.dumps({k:value[k] for k in ['total','passed','failed','errors','mutation']}));sys.exit(0 if r.wasSuccessful() else 1)
