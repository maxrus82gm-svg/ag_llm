"""Bounded Windows-only real MCP/NPFS integration and fault runner.

All output is a fresh directory in this TASK. No installs, Git, external endpoints,
accounts, WFP or working application processes. Synthetic keys stay in memory.
"""
import argparse
import asyncio
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import hmac
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
import traceback
import unittest
import uuid
sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
TASK = 'CODEX-WUA-0-MCP-NOTCP-NPFS-001'
REPORT = REPO / 'reports' / TASK
sys.path.insert(0, str(PKG))
import common
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

K = ct.WinDLL('kernel32', use_last_error=True)
A = ct.WinDLL('advapi32', use_last_error=True)
K.CreateNamedPipeW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, wt.DWORD, ct.c_void_p]
K.CreateNamedPipeW.restype = wt.HANDLE
K.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ct.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
K.CreateFileW.restype = wt.HANDLE
K.CloseHandle.argtypes = [wt.HANDLE]
K.ConnectNamedPipe.argtypes = [wt.HANDLE, ct.c_void_p]
K.ReadFile.argtypes = [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p]
K.WriteFile.argtypes = K.ReadFile.argtypes
K.WaitNamedPipeW.argtypes = [wt.LPCWSTR, wt.DWORD]
A.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wt.LPCWSTR, wt.DWORD, ct.POINTER(ct.c_void_p), ct.POINTER(wt.DWORD)]
K.LocalFree.argtypes = [ct.c_void_p]
K.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
K.OpenProcess.restype = wt.HANDLE
K.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
K.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)]
IP = ct.WinDLL('iphlpapi', use_last_error=True)

def process_image(pid):
    h=K.OpenProcess(0x1000,False,pid)
    assert h
    try:
        b=ct.create_unicode_buffer(32768);size=wt.DWORD(len(b))
        assert K.QueryFullProcessImageNameW(h,0,b,ct.byref(size))
        return Path(b.value)
    finally:K.CloseHandle(h)

def child_pids(pid):
    class PE(ct.Structure):
        _fields_=[('size',wt.DWORD),('usage',wt.DWORD),('pid',wt.DWORD),('heap',ct.c_size_t),('module',wt.DWORD),('threads',wt.DWORD),('parent',wt.DWORD),('priority',wt.LONG),('flags',wt.DWORD),('image',wt.WCHAR*260)]
    K.CreateToolhelp32Snapshot.argtypes=[wt.DWORD,wt.DWORD];K.CreateToolhelp32Snapshot.restype=wt.HANDLE
    K.Process32FirstW.argtypes=[wt.HANDLE,ct.POINTER(PE)];K.Process32NextW.argtypes=K.Process32FirstW.argtypes
    h=K.CreateToolhelp32Snapshot(2,0);assert h!=wt.HANDLE(-1).value
    try:
        item=PE();item.size=ct.sizeof(item);ok=K.Process32FirstW(h,ct.byref(item));found=[]
        while ok:
            if item.parent==pid:found.append(item.pid)
            ok=K.Process32NextW(h,ct.byref(item))
        return found
    finally:K.CloseHandle(h)

def endpoint_rows(pid):
    """Independent, unprivileged OS tables. Sampling cannot exclude transient calls."""
    rows = []
    for protocol, api, table_class, sizes in [('TCP', IP.GetExtendedTcpTable, 5, {2:24,23:56}), ('UDP', IP.GetExtendedUdpTable, 1, {2:12,23:28})]:
        for family, width in sizes.items():
            size = wt.ULONG(0)
            code = api(None, ct.byref(size), False, family, table_class, 0)
            assert code in [0,122], ('OS_TABLE',code)
            b = ct.create_string_buffer(size.value)
            assert api(b,ct.byref(size),False,family,table_class,0)==0
            count = struct.unpack_from('<I',b.raw,0)[0]
            for i in range(count):
                raw = b.raw[4+i*width:4+(i+1)*width]
                owner = struct.unpack_from('<I',raw,width-4)[0]
                if owner==pid:
                    rows.append({'protocol':protocol,'family':family,'owner_pid':owner,'raw_row_sha256':hashlib.sha256(raw).hexdigest()})
    return rows

def read_wire(peer, session, key, direction, seq):
    head = peer.read(53)
    assert head[:5] == b'WNP1'+direction and head[5:41] == session.encode()
    number, length = struct.unpack('<qi',head[41:])
    assert number==seq and 0<length<=32768
    body, tag = peer.read(length), peer.read(32)
    assert hmac.compare_digest(tag,hmac.new(key,head+body,hashlib.sha256).digest())
    return body

def fake_server_case(case, response, *, binary=None, authorized=True):
    """Independent native pipe; explicit expected peer used only by this fault test."""
    with Fixture(case) as f:
        name = 'WUA-NPFS-'+uuid.uuid4().hex
        pipe = PeerPipe(name)
        observed, faults = [], []
        def server():
            try:
                pipe.accept()
                hello = read_wire(pipe,f.session,f.key,b'C',0)
                observed.append('hello')
                assert hello==b'hello'
                pipe.write(packet(f.session,f.key,b'U',0,b'ready'))
                request = read_wire(pipe,f.session,f.key,b'C',1)
                observed.append('request')
                response(pipe,f,request)
            except (AssertionError,OSError) as e:
                faults.append(type(e).__name__)
            finally:
                pipe.close()
        t = threading.Thread(target=server,daemon=True); t.start()
        overrides = {'pipe':name}
        if authorized: overrides.update(pid=os.getpid(),hash=sha(process_image(os.getpid())))
        p = f.relay(binary,**overrides)
        # Keep STDIN open so peer faults, not client EOF, determine outcome.
        p.stdin.write(line(initialize()));p.stdin.flush()
        p.wait(7)
        v={'exit':p.returncode,'stdout':p.stdout.read().decode(errors='replace'),'stderr':p.stderr.read().decode(errors='replace')}
        t.join(3);assert not t.is_alive(), 'OWN_PEER_THREAD_LEAK'
        dump(f.root/'peer_fault.json',{'observed':observed,'peer_faults':faults,'relay':v})
        return v,observed

def compile_mutant(name, replacements):
    target=OUT/('mutant-'+name);target.mkdir()
    args=[]
    for source in ['Shared.cs','Relay.cs']:
        text=(PKG/'npfs'/source).read_text(encoding='utf-8')
        for file,old,new in replacements:
            if file==source:
                assert text.count(old)==1,old
                text=text.replace(old,new)
        p=target/source;p.write_text(text,encoding='utf-8');args.append(str(p))
    framework=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319'
    binary=target/'MutantRelay.exe'
    command=[str(framework/'csc.exe'),'/nologo','/noconfig','/nostdlib+','/platform:x64','/langversion:5','/optimize+','/debug-','/warnaserror+','/out:'+str(binary)]+['/reference:'+str(framework/n) for n in ['mscorlib.dll','System.dll','System.Core.dll','System.Web.Extensions.dll']]+args
    p=subprocess.run(command,capture_output=True,text=True,timeout=30)
    dump(target/'build.json',{'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'sources':{Path(s).name:sha(s) for s in args}})
    assert p.returncode==0,p.stdout
    return binary

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, x):
    p.write_text(json.dumps(x, indent=2, ensure_ascii=False), encoding='utf-8')

def sid():
    # whoami is read-only and no shell/profile; SID only, no account inventory.
    p = subprocess.run([str(Path(os.environ['SystemRoot']) / 'System32/whoami.exe'), '/user', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=5, check=True)
    return p.stdout.strip().split(',')[-1].strip('"')

SID = None
OUT = None
ROWS = []

def env():
    return common.clean_environment()

def argv_relay(f, binary=None, **changes):
    values = {'pipe': f.pipe, 'pid': f.gateway.pid, 'sid': SID, 'hash': sha(REPORT / 'build/WuaGateway.exe')}
    values.update(changes)
    return [str(binary or REPORT / 'build/WuaRelay.exe'), 'synthetic_fixture_only', values['pipe'], str(values['pid']), values['sid'], values['hash']]

class Fixture:
    def __init__(self, name, **updates):
        self.root = OUT / (name + '-' + uuid.uuid4().hex)
        self.root.mkdir()
        self.pipe = 'WUA-NPFS-' + uuid.uuid4().hex
        self.session, self.nonce, self.key = str(uuid.uuid4()), secrets.token_hex(32), secrets.token_bytes(32)
        self.events, self.errors, self.processes = [], [], []
        dump(self.root / 'fixture.json', {'schema': 1, 'mode': 'synthetic_fixture_only', 'session_id': self.session, 'nonce': self.nonce})
        self.config = {'schema': 1, 'mode': 'synthetic_fixture_only', 'pipe': self.pipe, 'session_id': self.session, 'client_sid': SID, 'relay_sha256': sha(REPORT / 'build/WuaRelay.exe'), 'run_root': str(self.root), 'python_sha256': sha(sys.executable), 'worker_sha256': sha(PKG / 'npfs/gateway_worker.py')}
        self.config.update(updates)
        dump(self.root / 'gateway.json', self.config)
        self.owned_env = {**env(), 'WUA_NPFS_GRANT': self.key.hex(), 'WUA_NPFS_SESSION': self.session}
        self.gateway = subprocess.Popen([str(REPORT / 'build/WuaGateway.exe'), 'synthetic_fixture_only', str(self.root / 'gateway.json')], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.owned_env)
        self.processes.append(self.gateway)
        self.lines = queue.Queue(64)
        def read():
            for b in self.gateway.stdout:
                value = b.decode('utf-8', errors='replace').rstrip()
                self.events.append(value)
                self.lines.put_nowait(value)
        def err():
            for b in self.gateway.stderr:
                self.errors.append(b.decode('utf-8', errors='replace').rstrip())
        self.threads = [threading.Thread(target=read, daemon=True), threading.Thread(target=err, daemon=True)]
        for t in self.threads:
            t.start()

    def ready(self):
        try:
            value = self.lines.get(timeout=4)
        except queue.Empty:
            raise AssertionError(('gateway-not-listening', self.gateway.poll(), self.errors)) from None
        assert value == 'GATEWAY_LISTENING', self.errors
        return self

    def relay(self, binary=None, **changes):
        p = subprocess.Popen(argv_relay(self, binary, **changes), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.owned_env)
        self.processes.append(p)
        return p

    def close(self):
        codes = []
        for p in self.processes[1:]:
            if p.poll() is None:
                try: p.stdin.close()
                except (OSError, ValueError): pass
            try: p.wait(5)
            except subprocess.TimeoutExpired: p.kill(); p.wait(3)
            codes.append({'pid': p.pid, 'exit': p.returncode})
        try: self.gateway.wait(6)
        except subprocess.TimeoutExpired: self.gateway.kill(); self.gateway.wait(3)
        for t in self.threads:
            t.join(2)
        dump(self.root / 'lifecycle.json', {'gateway_pid': self.gateway.pid, 'gateway_exit': self.gateway.returncode, 'events': self.events, 'errors': self.errors, 'owned_relays': codes, 'reader_threads_stopped': all(not t.is_alive() for t in self.threads)})
        for p in self.processes:
            for stream in [p.stdin, p.stdout, p.stderr]:
                if stream and not stream.closed: stream.close()

    def __enter__(self):
        try:
            return self.ready()
        except BaseException:
            self.close()
            raise

    def __exit__(self, *exc):
        self.close()

class PeerPipe:
    """Owned independent Win32 peer with explicit current-user DACL, never remote."""
    def __init__(self, name):
        sd, size = ct.c_void_p(), wt.DWORD()
        assert A.ConvertStringSecurityDescriptorToSecurityDescriptorW('D:P(A;;GA;;;' + SID + ')', 1, ct.byref(sd), ct.byref(size))
        class SA(ct.Structure):
            _fields_ = [('length', wt.DWORD), ('descriptor', ct.c_void_p), ('inherit', wt.BOOL)]
        sa = SA(ct.sizeof(SA), sd, False)
        self.h = K.CreateNamedPipeW('\\\\.\\pipe\\' + name, 0x80003, 8, 1, 65536, 65536, 0, ct.byref(sa))
        K.LocalFree(sd)
        assert self.h != wt.HANDLE(-1).value, ct.get_last_error()
    def accept(self):
        assert K.ConnectNamedPipe(self.h, None) or ct.get_last_error() == 535
    def read(self, n):
        out = bytearray()
        while len(out) < n:
            b, got = ct.create_string_buffer(n-len(out)), wt.DWORD()
            assert K.ReadFile(self.h, b, len(b), ct.byref(got), None) and got.value
            out.extend(b.raw[:got.value])
        return bytes(out)
    def write(self, b):
        sent = wt.DWORD()
        assert K.WriteFile(self.h, b, len(b), ct.byref(sent), None) and sent.value == len(b)
    def close(self):
        K.CloseHandle(self.h)

def packet(session, key, direction, seq, body):
    head = b'WNP1' + direction + session.encode('ascii') + struct.pack('<qi', seq, len(body))
    return head + body + hmac.new(key, head + body, hashlib.sha256).digest()

def raw_exchange(p, messages):
    data = b''.join(messages)
    stdout, stderr = p.communicate(data, timeout=10)
    return {'exit': p.returncode, 'stdout': stdout.decode('utf-8', errors='replace'), 'stderr': stderr.decode('utf-8', errors='replace')}

def initialize(i=1):
    return {'jsonrpc': '2.0', 'id': i, 'method': 'initialize', 'params': {'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'independent-npfs-test', 'version': '1'}}}

def line(obj):
    return common.canonical(obj) + b'\n'

async def sdk_session(f, ambient=False):
    e = f.owned_env.copy()
    if ambient:
        e.update(HTTPS_PROXY='http://unreachable.invalid:9', ALL_PROXY='socks5://unreachable.invalid:9', NO_PROXY='*')
    params = StdioServerParameters(command=argv_relay(f)[0], args=argv_relay(f)[1:], env=e)
    wire = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=5) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert [t.name for t in tools.tools] == common.TOOLS
            assert all(t.annotations.read_only_hint and not t.annotations.destructive_hint for t in tools.tools)
            for name in common.TOOLS:
                q = {'request_id': str(uuid.uuid4())}
                if name == 'read_synthetic_context': q['task_id'] = common.FIXTURE
                reply = await session.call_tool(name, q)
                assert not reply.is_error, reply
                v = reply.structured_content
                assert v['request_id'] == q['request_id'] and v['proof']['nonce'] == f.nonce and v['proof']['session_id'] == f.session
                assert v['content_sha256'] == hashlib.sha256(json.dumps(v['value'], sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
                assert v['proof']['baseline_sha256'] == v['proof']['current_sha256']
                if name == 'read_synthetic_context':
                    assert v['value']['TASK']['task_id'] == common.FIXTURE
                    assert v['value']['GOAL'] == 'synthetic nonce: ' + f.nonce
                wire.append(v)
            for name, q in [('read_synthetic_context', {'task_id': 'other_task', 'request_id': str(uuid.uuid4())}), ('arbitrary_write', {'request_id': str(uuid.uuid4())}), ('ping', {'request_id': 123}), ('ping', {'request_id': str(uuid.uuid4()), 'extra': 'forbidden'})]:
                reply = await session.call_tool(name, q)
                assert reply.is_error
            q = {'request_id': str(uuid.uuid4())}
            assert not (await session.call_tool('ping', q)).is_error
            assert (await session.call_tool('ping', q)).is_error
    dump(f.root / 'sdk_results.json', wire)
    return wire

class NpfsTests(unittest.TestCase):
    def test_01_official_sdk_four_tools_and_readonly(self):
        with Fixture('sdk') as f:
            wire = asyncio.run(sdk_session(f))
        receipt = json.loads((f.root / 'authority_receipt.json').read_text())
        self.assertEqual(len(receipt['api_reads']), 5)
        self.assertEqual(receipt['baseline_sha256'], receipt['final_sha256'])
        self.assertEqual(common.tree_hash(f.root / 'owned-api-state'), receipt['baseline_sha256'])
        for i in [0, 2, 3]:
            self.assertEqual(wire[i]['request_id'], receipt['api_reads'][i]['request_id'])
            self.assertEqual(wire[i]['content_sha256'], receipt['api_reads'][i]['content_sha256'])
        task_records = list((f.root / 'owned-api-state').rglob('*.json'))
        self.assertTrue(any(f.nonce in p.read_text(encoding='utf-8') for p in task_records))
        self.assertTrue(receipt['closed'])

    def test_02_restart_and_proxy_environment(self):
        sessions = []
        for _ in range(2):
            with Fixture('restart') as f:
                wire = asyncio.run(sdk_session(f, True))
                sessions.append((f.session, f.nonce, wire[2]['content_sha256']))
        self.assertNotEqual(sessions[0], sessions[1])

    def test_03_pipe_missing(self):
        f = Fixture('missing')
        try:
            f.ready()
            p = f.relay(pipe='WUA-NPFS-' + uuid.uuid4().hex)
            v = raw_exchange(p, [])
            self.assertEqual(v['exit'], 20)
            self.assertIn('PIPE_UNAVAILABLE', v['stderr'])
        finally: f.close()

    def test_04_remote_smb_and_bad_name(self):
        with Fixture('remote') as f:
            for name in ['\\\\remote.invalid\\pipe\\wua', '\\\\.\\pipe\\WUA-NPFS-' + uuid.uuid4().hex, '../other', 'WUA-NPFS-*']:
                v = raw_exchange(f.relay(pipe=name), [])
                self.assertIn('LOCAL_PIPE_NAME', v['stderr'])

    def test_05_wrong_server_pid_sid_image(self):
        for change, code in [({'pid': os.getpid()}, 'SERVER_PID_MISMATCH'), ({'sid': 'S-1-5-18'}, 'PEER_SID'), ({'hash': '0'*64}, 'PEER_IMAGE_HASH')]:
            with Fixture('server-auth') as f:
                v = raw_exchange(f.relay(**change), [])
                self.assertIn(code, v['stderr'])

    def test_06_gateway_rejects_wrong_client_image(self):
        with Fixture('client-image', relay_sha256='0'*64) as f:
            v = raw_exchange(f.relay(), [line(initialize())])
            self.assertEqual(v['exit'], 20)
        self.assertIn('GATEWAY_STOP:PEER_IMAGE_HASH', f.errors)
        self.assertFalse((f.root/'owned-api-state').exists())

    def test_07_wrong_grant(self):
        with Fixture('grant') as f:
            f.owned_env['WUA_NPFS_GRANT'] = secrets.token_hex(32)
            v = raw_exchange(f.relay(), [line(initialize())])
            self.assertEqual(v['exit'], 20)
        self.assertIn('GATEWAY_STOP:WIRE_AUTH', f.errors)
        self.assertFalse((f.root/'owned-api-state').exists())

    def test_08_session_mixing(self):
        with Fixture('session') as f:
            f.owned_env['WUA_NPFS_SESSION'] = str(uuid.uuid4())
            v = raw_exchange(f.relay(), [])
            self.assertEqual(v['exit'], 20)
        self.assertIn('GATEWAY_STOP:WIRE_SESSION', f.errors)

    def test_09_oversize_partial_duplicate_and_bad_type(self):
        cases = [(b'x'*8193+b'\n', 'MESSAGE_SIZE'), (b'{"jsonrpc":', 'PARTIAL_LINE'), (line(initialize())*2, 'RPC_REPLAY'), (b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"ping"}\n', 'JSON_KEY'), (b'{"jsonrpc":"2.0","id":true,"method":"ping"}\n', 'NUMBER')]
        for raw, code in cases:
            with Fixture('input-boundary') as f:
                v = raw_exchange(f.relay(), [raw])
                self.assertEqual(v['exit'], 20)
                self.assertIn(code, v['stderr'])

    def test_10_owner_crash_and_unresponsive_stdin(self):
        with Fixture('crash') as f:
            p = f.relay()
            self.assertIn(b'RELAY_AUTHENTICATED', p.stderr.readline())
            f.gateway.kill(); f.gateway.wait(3)
            self.assertEqual(p.wait(5), 20)
        with Fixture('idle') as f:
            p = f.relay()
            start = time.monotonic()
            self.assertEqual(p.wait(7), 20)
            self.assertLess(time.monotonic()-start, 7)

    def test_11_exclusive_instance(self):
        with Fixture('exclusive') as f:
            with self.assertRaises(AssertionError):
                peer = PeerPipe(f.pipe)
                peer.close()

    def test_12_wrong_peer_oracle_and_mutant(self):
        def response(pipe,f,request):
            pipe.write(packet(f.session,f.key,b'U',1,common.canonical({'jsonrpc':'2.0','id':1,'result':{}})))
        normal,seen=fake_server_case('wrong-peer-baseline',response,authorized=False)
        self.assertEqual(seen,[])
        self.assertIn('SERVER_PID_MISMATCH',normal['stderr'])
        mutant=compile_mutant('wrong-peer',[
            ('Relay.cs','pid==expectedPid','true'),
            ('Shared.cs','Guard.Need(ImageSha256==hash,"PEER_IMAGE_HASH")','Guard.Need(true,"PEER_IMAGE_HASH")')])
        changed,seen=fake_server_case('wrong-peer-mutant',response,binary=mutant,authorized=False)
        # Inner policy oracle must FAIL: the unintended server received an authenticated MCP request.
        violation=seen==['hello','request']
        dump(OUT/'wrong_peer_mutation.json',{'normal_policy_oracle':'PASS','mutant_policy_oracle':'FAIL' if violation else 'NOT_TRIGGERED','observed':seen,'mutant_sha256':sha(mutant)})
        self.assertTrue(violation,'WRONG_PEER_MUTATION_NOT_DETECTED')

    def test_13_pipe_response_bounds_correlation_replay_and_close(self):
        cases=[
            ('oversized-response',lambda p,f,q:p.write(packet(f.session,f.key,b'U',1,b'x'*32769)),'WIRE_SIZE'),
            ('wrong-correlation',lambda p,f,q:p.write(packet(f.session,f.key,b'U',1,common.canonical({'jsonrpc':'2.0','id':999,'result':{}}))),'RPC_CORRELATION'),
            ('wire-replay',lambda p,f,q:p.write(packet(f.session,f.key,b'U',0,b'{}')),'WIRE_REPLAY'),
            ('partial-response',lambda p,f,q:p.write(packet(f.session,f.key,b'U',1,b'{')[:-12]),'PARTIAL_OR_EOF'),
            ('protocol-version',lambda p,f,q:p.write(b'WNP2'+packet(f.session,f.key,b'U',1,b'{}')[4:]),'WIRE_SESSION'),
            ('slow-peer',lambda p,f,q:time.sleep(3),'IO_TIMEOUT')]
        for name,callback,code in cases:
            v,seen=fake_server_case(name,callback)
            self.assertEqual(seen,['hello','request'])
            self.assertEqual(v['exit'],20)
            self.assertIn(code,v['stderr'])

    def test_14_os_tables_and_tcp_mutation(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as trap:
            trap.bind(('127.0.0.1',0));trap.listen(2);trap.settimeout(3);port=trap.getsockname()[1]
            mutant=compile_mutant('tcp-dial', [('Relay.cs','try {Guard.Need(args.Length==5', 'try {using(var tcp=new System.Net.Sockets.TcpClient("127.0.0.1",'+str(port)+')) {System.Threading.Thread.Sleep(400);} Guard.Need(args.Length==5')])
            results=[]
            for binary in [REPORT/'build/WuaRelay.exe',mutant]:
                with Fixture('network-observer',relay_sha256=sha(binary)) as f:
                    p=f.relay(binary)
                    samples=[];children=[]
                    deadline=time.monotonic()+1
                    while time.monotonic()<deadline and p.poll() is None:
                        samples.append(endpoint_rows(p.pid));children.extend(child_pids(p.pid));time.sleep(.01)
                    found=[row for sample in samples for row in sample]
                    results.append({'kind':'mutant' if binary==mutant else 'normal','samples':len(samples),'rows':found,'children':sorted(set(children)),'pid':p.pid})
                    if binary==mutant:
                        conn,_=trap.accept();conn.close()
                    p.stdin.close();p.wait(5)
            dump(OUT/'os_network_samples.json',{'observations':results,'observer':'GetExtendedTcpTable/GetExtendedUdpTable AF_INET+AF_INET6, unprivileged PID sampling','continuous_from_process_creation':False,'OS_enforced':False,'negative_control':'intentional C# loopback TCP dial held 400ms','complete_no_network_proof':False})
            self.assertEqual(results[0]['rows'],[])
            self.assertEqual(results[0]['children'],[])
            self.assertTrue(any(x['protocol']=='TCP' for x in results[1]['rows']),'TCP_MUTATION_NOT_OBSERVED')

    def test_15_sdk_child_job_cleanup_after_gateway_crash(self):
        with Fixture('job-crash') as f:
            p=f.relay()
            p.stdin.write(line(initialize())+line({'jsonrpc':'2.0','method':'notifications/initialized'})+line({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'ping','arguments':{'request_id':str(uuid.uuid4())}}}));p.stdin.flush()
            first=json.loads(p.stdout.readline());self.assertEqual(first['id'],1)
            reply=json.loads(p.stdout.readline());worker=reply['result']['structuredContent']['proof']['mcp_process_id']
            h=K.OpenProcess(0x100000,False,worker);self.assertTrue(h)
            try:
                f.gateway.kill();f.gateway.wait(3)
                self.assertEqual(K.WaitForSingleObject(h,3000),0)
                self.assertEqual(p.wait(5),20)
            finally: K.CloseHandle(h)
            dump(f.root/'job_observation.json',{'sdk_pid':worker,'OS_wait_signaled':True,'gateway_killed_owned_only':True})

    def test_16_scoped_gateway_raw_wire_replay(self):
        f=Fixture('u-replay',relay_sha256=sha(process_image(os.getpid())))
        try:
            f.ready()
            name='\\\\.\\pipe\\'+f.pipe
            h=K.CreateFileW(name,0x00100083,0,None,3,0x110000,None)
            self.assertNotEqual(h,wt.HANDLE(-1).value)
            class Client(PeerPipe):
                def __init__(self, handle):self.h=handle
            client=Client(h)
            try:
                client.write(packet(f.session,f.key,b'C',0,b'hello'))
                self.assertEqual(read_wire(client,f.session,f.key,b'U',0),b'ready')
                q=common.canonical(initialize())
                client.write(packet(f.session,f.key,b'C',1,q))
                self.assertEqual(json.loads(read_wire(client,f.session,f.key,b'U',1))['id'],1)
                client.write(packet(f.session,f.key,b'C',1,q))
                self.assertEqual(f.gateway.wait(6),20)
            finally:client.close()
        finally:f.close()
        self.assertIn('GATEWAY_STOP:WIRE_REPLAY',f.errors)

    def test_17_full_duplex_concurrent_requests(self):
        async def exercise(f):
            parameters=StdioServerParameters(command=argv_relay(f)[0],args=argv_relay(f)[1:],env=f.owned_env)
            async with stdio_client(parameters) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=5) as sdk:
                    await sdk.initialize()
                    ids=[str(uuid.uuid4()) for _ in range(12)]
                    replies=await asyncio.gather(*(sdk.call_tool('ping',{'request_id':rid}) for rid in ids))
                    self.assertTrue(all(not r.is_error for r in replies))
                    self.assertEqual([r.structured_content['request_id'] for r in replies],ids)
                    self.assertEqual(sorted(r.structured_content['proof']['api_reads'] for r in replies),list(range(1,13)))
                    return ids
        with Fixture('duplex') as f:
            ids=asyncio.run(exercise(f))
        receipt=json.loads((f.root/'authority_receipt.json').read_text())
        self.assertEqual(set(ids),{r['request_id'] for r in receipt['api_reads']})

    def test_18_slow_partial_stdio_is_bounded(self):
        with Fixture('slow-stdio') as f:
            p=f.relay();p.stdin.write(b'{"jsonrpc":');p.stdin.flush()
            self.assertEqual(p.wait(7),20)
            self.assertIn(b'IO_TIMEOUT',p.stderr.read())

    def test_19_source_no_network_or_child_and_python_syntax(self):
        relay=(PKG/'npfs/Relay.cs').read_text()
        shared=(PKG/'npfs/Shared.cs').read_text()
        for forbidden in ['System.Net','TcpClient','Socket(','Dns.','WebRequest','HttpClient','Process.Start','CreateProcess','asyncio','python.exe']:
            self.assertNotIn(forbidden,relay+shared)
        for p in [PKG/'npfs/gateway_worker.py',Path(__file__),PKG/'tests/npfs_regression.py']:
            compile(p.read_bytes(),str(p),'exec')
        self.assertIn('0x8080404',(PKG/'npfs/Gateway.cs').read_text()) # suspended + handle list; separately source-reviewed constants
        for invalid in [REPO/'web_alarm',REPO/'reports/other/runs/fake']:
            with self.assertRaises(common.Denied):common.owned_path(invalid)

    def test_20_gateway_protocol_and_config_pins(self):
        f=Fixture('bad-sdk-pin',worker_sha256='0'*64)
        try:
            self.assertEqual(f.gateway.wait(5),20)
        finally:f.close()
        self.assertIn('GATEWAY_STOP:SDK_SOURCE_PIN',f.errors)
        for wrong in ['version','session']:
            f=Fixture('protocol-'+wrong,relay_sha256=sha(process_image(os.getpid())))
            try:
                f.ready();h=K.CreateFileW('\\\\.\\pipe\\'+f.pipe,0x00100083,0,None,3,0x110000,None)
                self.assertNotEqual(h,wt.HANDLE(-1).value)
                class Client(PeerPipe):
                    def __init__(self,h):self.h=h
                peer=Client(h)
                try:
                    message=packet(str(uuid.uuid4()) if wrong=='session' else f.session,f.key,b'C',0,b'hello')
                    if wrong=='version':message=b'WNP2'+message[4:]
                    peer.write(message)
                    self.assertEqual(f.gateway.wait(5),20)
                finally:peer.close()
            finally:f.close()
            self.assertIn('GATEWAY_STOP:WIRE_SESSION',f.errors)
            self.assertFalse((f.root/'owned-api-state').exists())

    def test_21_authority_session_binding(self):
        f=Fixture('authority-session',session_id=str(uuid.uuid4()))
        try:self.assertEqual(f.gateway.wait(5),20)
        finally:f.close()
        self.assertIn('GATEWAY_STOP:FIXTURE_SESSION_BINDING',f.errors)
        self.assertFalse((f.root/'owned-api-state').exists())

    def test_22_hard_lifetime_kills_only_owned_relay(self):
        # Shorten only the reviewed hard deadline; hold an owned fake peer past it.
        mutant=compile_mutant('hard-lifetime',[('Relay.cs','null,40000,Timeout.Infinite','null,500,Timeout.Infinite')])
        def hold(pipe,f,request):time.sleep(1)
        start=time.monotonic()
        result,observed=fake_server_case('hard-deadline',hold,binary=mutant)
        self.assertEqual(result['exit'],20)
        self.assertEqual(observed,['hello','request'])
        self.assertLess(time.monotonic()-start,7)

def compile_components(attempt):
    framework = Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319'
    outputs = []
    for kind in ['Relay', 'Gateway']:
        args = [str(framework/'csc.exe'), '/nologo', '/noconfig', '/nostdlib+', '/platform:x64', '/langversion:5', '/optimize+', '/debug-', '/warnaserror+', '/target:exe', '/out:'+str(REPORT/'build'/('Wua'+kind+'.exe'))]
        args += ['/reference:'+str(framework/x) for x in ['mscorlib.dll','System.dll','System.Core.dll','System.Web.Extensions.dll']]
        args += [str(PKG/'npfs/Shared.cs'), str(PKG/'npfs'/(kind+'.cs'))]
        p = subprocess.run(args, capture_output=True, text=True, timeout=30)
        outputs.append({'component': kind, 'argv': args, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    dump(attempt/'build.json', outputs)
    assert all(x['exit']==0 for x in outputs), outputs

class Results(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test); ROWS.append({'id': test.id(), 'status': 'PASS'})
    def addFailure(self, test, err):
        super().addFailure(test, err); ROWS.append({'id': test.id(), 'status': 'FAIL', 'traceback': self._exc_info_to_string(err,test)})
    def addError(self, test, err):
        super().addError(test, err); ROWS.append({'id': test.id(), 'status': 'ERROR', 'traceback': self._exc_info_to_string(err,test)})

def main():
    global OUT, SID
    parser = argparse.ArgumentParser()
    parser.add_argument('--select', default=None)
    args = parser.parse_args()
    assert os.name=='nt'
    OUT = REPORT/'runs'/('attempt-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]); OUT.mkdir()
    SID = sid()
    compile_components(OUT)
    paths=[*sorted((PKG/'npfs').glob('*.*')),Path(__file__).resolve(),PKG/'tests/npfs_regression.py',PKG/'server.py',PKG/'common.py',REPO/'web_alarm/server.py']
    sources = {p.relative_to(REPO).as_posix():sha(p) for p in paths if p.is_file()}
    dump(OUT/'source_pins.json', sources)
    snapshot=OUT/'source_snapshot';snapshot.mkdir()
    for p in paths:
        if p.is_file(): (snapshot/p.name).write_bytes(p.read_bytes())
    suite = unittest.defaultTestLoader.loadTestsFromName(args.select, module=sys.modules[__name__]) if args.select else unittest.defaultTestLoader.loadTestsFromTestCase(NpfsTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Results).run(suite)
    dump(OUT/'results.json', {'task':TASK,'collected':result.testsRun,'passed':result.testsRun-len(result.errors)-len(result.failures),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'selectors':ROWS,'python':sys.version,'mcp':__import__('importlib.metadata').metadata.version('mcp')})
    print('EVIDENCE '+str(OUT))
    return 0 if result.testsRun>0 and result.wasSuccessful() else 1

if __name__=='__main__':
    sys.exit(main())
