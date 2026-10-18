"""NEW chain-lease/attempt-oracle tests; does not rerun prior 19/5/36 suites.

Imports hash-pinned AM07 synthetic fixtures only. No native client, WFP, real DNS
or external addresses. Popen negative control is denied by Python audit BEFORE
CreateProcess; local stdlib source ordering captured by collect_readonly.py.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import traceback
import unittest

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
PRIOR=ROOT/'reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/http_socks_adapter_20261018'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value
    spec.loader.exec_module(value)
    return value


baseline=json.loads((OUT/'inputs_before.json').read_text(encoding='utf-8'))
for path in (PRIOR/'adapter.py',PRIOR/'test_adapter.py'):
    item=next(x for x in baseline['inputs'] if x['path']==str(path.relative_to(ROOT)).replace('\\','/'))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],'PRIOR SOURCE DRIFT'
fixtures=module('pinned_am07_fixtures',PRIOR/'test_adapter.py')
reference=module('new_egress_reference',OUT/'egress_reference.py')
guard=fixtures.GUARD
OBSERVED=[]


def observer(event,args):
    if event in ('socket.connect','subprocess.Popen'):
        record={'case':guard.case,'event':event,
                'operation':getattr(reference.CURRENT_OPERATION,'value',None),
                'role':guard.role()}
        if event=='socket.connect':
            address=args[1]
            record.update(host=address[0] if address[0]=='127.0.0.1' else 'denied-address',port=address[1])
        OBSERVED.append(record)


class Tests(unittest.TestCase):
    def setUp(self):
        guard.case=self._testMethodName
        self.start_index=len(OBSERVED)
        self.deny_index=len(guard.violations)
        self.expected_denials=[]
        self.origin=fixtures.Fixture('origin')
        self.socks=None
        self.gate=None
        self.leases=[]
        self.observed={}

    def start(self,mode='echo'):
        self.socks=fixtures.Fixture('socks',mode=mode,origin=self.origin)
        guard.allow('socks',self.origin.port)
        guard.allow('driver',self.socks.port)
        self.gate=reference.ReferenceGate(reference.Endpoint('127.0.0.1',self.socks.port),self._testMethodName)

    def own_raw(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.settimeout(0.5)
        self.leases.append(sock)
        return sock

    def api_events(self):return OBSERVED[self.start_index:]

    def assert_no_attempt(self,action,error=reference.GateDenied):
        before=len(OBSERVED)
        with self.assertRaises(error):action()
        self.assertEqual(len(OBSERVED),before)

    def denied_after_fault(self,mode,exc):
        self.start(mode)
        self.gate.admit_child(('root',1),('child',1),True)
        with self.assertRaises(exc):self.gate.socks_probe(self.origin.port)
        self.assertEqual(self.gate.state,'TRIPPED')
        self.assertEqual(len(self.api_events()),1)
        self.assertEqual(len(self.gate.sockets),0)
        self.assertIn('METHOD_RECEIVED',self.socks.markers)
        self.assert_no_attempt(lambda:self.gate.connect(('child',1)))
        self.assert_no_attempt(lambda:self.gate.connect())
        self.assertEqual(self.origin.peers,[])

    def tearDown(self):
        ledger=list(self.gate.ledger) if self.gate else []
        if self.gate:self.gate.stop()
        for sock in self.leases:fixtures.close(sock)
        for obj in (self.socks,self.origin):
            if obj:obj.stop()
        denies=guard.violations[self.deny_index:]
        errors=(self.socks.errors if self.socks else [])+self.origin.errors
        self.observed.update({'api_events':list(self.api_events()),'ledger':ledger,
                              'python_guard_denials':denies,'expected_denials':self.expected_denials,
                              'socks_markers':list(self.socks.markers) if self.socks else [],
                              'origin_peer_ports':list(self.origin.peers),'fixture_errors':errors,
                              'gate_sockets_remaining':len(self.gate.sockets) if self.gate else 0})
        guard.reset_ports()
        self.assertEqual([x['event'] for x in denies],self.expected_denials)
        self.assertEqual(errors,[])
        self.assertEqual(self.observed['gate_sockets_remaining'],0)

    def test_01_approved_lease_control(self):
        self.start()
        sock=self.gate.socks_probe(self.origin.port)
        sock.sendall(b'lease')
        self.assertEqual(fixtures.read_n(sock,5),b'lease')
        direct=[x for x in self.api_events() if x['role']=='driver']
        self.assertEqual(len(direct),1)
        self.assertTrue(direct[0]['operation'])
        self.assertEqual(self.gate.state,'READY')

    def test_02_missing_proxy_no_api_call(self):
        self.assert_no_attempt(lambda:reference.ReferenceGate(None),ValueError)

    def test_03_hostname_config_no_resolver_call(self):
        self.assert_no_attempt(lambda:reference.Endpoint('unresolved.invalid',443),ValueError)

    def test_04_unapproved_owned_port_no_api_call(self):
        self.start()
        target=reference.Endpoint('127.0.0.1',self.origin.port)
        self.assert_no_attempt(lambda:self.gate.connect(requested=target))
        self.assertEqual(self.origin.peers,[])

    def test_05_absent_endpoint_attempt_then_tree_stops(self):
        lease=self.own_raw()
        lease.bind(('127.0.0.1',0))
        port=lease.getsockname()[1]
        guard.own(port);guard.allow('driver',port)
        self.gate=reference.ReferenceGate(reference.Endpoint('127.0.0.1',port))
        self.gate.admit_child(('root',1),('child',1),True)
        with self.assertRaises(OSError):self.gate.connect()
        self.assertEqual(len(self.api_events()),1)
        self.assertEqual(self.gate.state,'TRIPPED')
        self.assert_no_attempt(lambda:self.gate.connect(('child',1)))

    def test_06_socks_refusal_revokes_tree(self):self.denied_after_fault('refuse',reference.ProtocolFailure)
    def test_07_socks_timeout_revokes_tree(self):self.denied_after_fault('timeout',TimeoutError)
    def test_08_socks_disconnect_revokes_tree(self):self.denied_after_fault('close',reference.ProtocolFailure)
    def test_09_malformed_socks_revokes_tree(self):self.denied_after_fault('bad_method',reference.ProtocolFailure)

    def test_10_trip_closes_existing_socket(self):
        self.start()
        sock=self.gate.socks_probe(self.origin.port)
        self.gate.trip('ROUTE_LEASE_LOST')
        self.assertEqual(sock.fileno(),-1)
        self.assert_no_attempt(lambda:self.gate.connect())

    def test_11_environment_cannot_renew_failed_lease(self):
        names=('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy')
        before={n:os.environ.get(n) for n in names}
        try:
            for name in names:os.environ[name]='*' if name.lower()=='no_proxy' else 'http://127.0.0.1:%d'%self.origin.port
            self.denied_after_fault('refuse',reference.ProtocolFailure)
        finally:
            for name,value in before.items():
                if value is None:os.environ.pop(name,None)
                else:os.environ[name]=value
        self.assertEqual(before,{n:os.environ.get(n) for n in names})
        self.observed['environment_restored']=True

    def test_12_unknown_child_no_create_and_lease_revocation(self):
        self.start();sock=self.gate.socks_probe(self.origin.port)
        self.assert_no_attempt(lambda:self.gate.admit_child(('root',1),('unknown',1)))
        self.assertEqual(sock.fileno(),-1)
        self.assertIn('CHILD_REFUSED_NOT_CREATED',[x['code'] for x in self.gate.ledger])

    def test_13_controller_admitted_child_is_model_only(self):
        self.start();self.gate.admit_child(('root',1),('child',1),True)
        self.gate.connect(('child',1))
        self.assertEqual(len(self.api_events()),1)
        self.observed['native_processes_created']=0

    def test_14_reused_name_different_generation_denied(self):
        self.start()
        self.assert_no_attempt(lambda:self.gate.connect(('root',2)))

    def test_15_bool_generation_is_not_valid_identity(self):
        self.start()
        self.assert_no_attempt(lambda:self.gate.connect(('root',True)))

    def test_16_udp_configuration_no_socket_attempt(self):
        self.assert_no_attempt(lambda:reference.Endpoint('127.0.0.1',443,'udp'),ValueError)

    def test_17_ipv6_configuration_no_socket_attempt(self):
        self.assert_no_attempt(lambda:reference.Endpoint('::1',443),ValueError)

    def test_18_loopback_connect_attempt_blocked_before_winsock(self):
        self.start()
        sock=self.own_raw()
        self.expected_denials=['socket.connect']
        with self.assertRaises(fixtures.IsolationError):sock.connect(('127.0.0.1',self.origin.port))
        self.gate.observe_unbrokered_attempt()
        self.assertEqual(len(self.api_events()),1)
        self.assertIsNone(self.api_events()[0]['operation'])
        self.assertEqual(self.origin.peers,[])
        self.observed['classification']='ATTEMPT_BLOCKED_BY_PYTHON_GUARD; NOT OS ENFORCEMENT'

    def test_19_popen_attempt_blocked_before_createprocess(self):
        self.start()
        self.expected_denials=['subprocess.Popen']
        with self.assertRaises(fixtures.IsolationError):subprocess.Popen(['synthetic-child-never-created.exe'])
        self.gate.observe_unbrokered_attempt()
        self.assertEqual([x['event'] for x in self.api_events()],['subprocess.Popen'])
        self.observed['classification']='POPEN_ATTEMPT_BLOCKED_BEFORE_CREATEPROCESS'
        self.observed['native_processes_created']=0

    def test_20_unbrokered_success_oracle_is_not_a_false_no_attempt(self):
        self.start()
        guard.allow('driver',self.origin.port) # own-loopback negative control only
        sock=self.own_raw();sock.connect(('127.0.0.1',self.origin.port))
        sock.sendall(b'qc');self.assertEqual(fixtures.read_n(sock,2),b'qc')
        orphan=[x for x in self.api_events() if x['role']=='driver' and x['operation'] is None]
        self.assertEqual(len(orphan),1)
        self.gate.observe_unbrokered_attempt()
        self.assertEqual(self.gate.state,'TRIPPED')
        self.observed['classification']='INTENTIONAL OWN-LOOPBACK UNBROKERED CONNECT DETECTED'

    def test_21_monitor_loss_stops_open_lease(self):
        self.start();sock=self.gate.socks_probe(self.origin.port)
        self.gate.trip('MONITOR_LOST')
        self.assertEqual(sock.fileno(),-1)
        self.assert_no_attempt(lambda:self.gate.connect())

    def test_22_stop_does_not_reconnect(self):
        self.start();self.gate.connect();self.gate.stop()
        before=len(OBSERVED)
        self.assert_no_attempt(lambda:self.gate.connect())
        self.assertEqual(len(OBSERVED),before)
        self.assertEqual(self.gate.state,'CLOSED')


class Result(unittest.TestResult):
    def __init__(self):super().__init__();self.rows=[]
    def record(self,test,status,err=None):
        row={'id':test._testMethodName,'status':status,'observed':test.observed}
        if err:row['error']={'type':err[0].__name__,'frames':[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(err[2])[-8:]]}
        self.rows.append(row)
        delta=guard.violations[test.deny_index:]
        if [x['event'] for x in delta]!=test.expected_denials:self.stop()
    def addSuccess(self,test):super().addSuccess(test);self.record(test,'PASS')
    def addFailure(self,test,err):super().addFailure(test,err);self.record(test,'FAIL',err)
    def addError(self,test,err):super().addError(test,err);self.record(test,'ERROR',err)


def main():
    sys.addaudithook(observer) # observe before guard denial; no sensitive args
    sys.addaudithook(guard.audit)
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    collected=suite.countTestCases();result=Result();suite.run(result)
    counts={s:sum(x['status']==s for x in result.rows) for s in ('PASS','FAIL','ERROR','SKIP')}
    leaks=[t.name for t in threading.enumerate() if t.name.startswith(('socks-','origin-'))]
    expected=sum(len(x['observed'].get('expected_denials',[])) for x in result.rows)
    ok=collected==result.testsRun==counts['PASS']==22 and len(guard.violations)==expected==2 and not guard.ports and not leaks
    index=1
    while (OUT/('attempt%02d_results.json'%index)).exists():index+=1
    data={'task_id':'CODEX-WUA-0-NATIVE-EGRESS-GATE-001','scope':'CONTROL-POLICY REFERENCE / PYTHON GUARD ONLY; NOT OS/NATIVE',
          'attempt':index,'status':'PASS' if ok else 'FAIL','collected':collected,'executed':result.testsRun,'counts':counts,
          'cases':result.rows,'api_events':OBSERVED,'socket_trace':guard.trace,'guard_denials':guard.violations,
          'expected_guard_denials':expected,'unexpected_guard_denials':len(guard.violations)-expected,
          'ports_remaining':sorted(guard.ports),'worker_leaks':leaks,
          'actual_native_processes_created':0,'native_tunnel_client_runs':0,'prior_suites_rerun':False,
          'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'egress_reference.py',Path(__file__)]},
          'fixture_dependency_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [PRIOR/'adapter.py',PRIOR/'test_adapter.py']}}
    (OUT/('attempt%02d_results.json'%index)).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'attempt':index,'status':data['status'],'collected':collected,'executed':result.testsRun,'counts':counts,
                      'connect_attempts':len(guard.trace),'expected_guard_denials':expected,
                      'unexpected_guard_denials':data['unexpected_guard_denials'],'worker_leaks':leaks,'ports_remaining':sorted(guard.ports)}))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
