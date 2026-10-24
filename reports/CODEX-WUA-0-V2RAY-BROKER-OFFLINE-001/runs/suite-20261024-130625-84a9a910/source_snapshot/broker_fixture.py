"""SYNTHETIC ONLY: one process accepts CONNECT and dials one owned loopback receiver.

This is NOT V2Ray, TLS or an engine config compatibility test. No async runtime,
SOCKS intermediary, helper, alternate route, resolver, retry or public endpoint.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Denied, canonical, exact, parse, request_id, require
import broker
from route_simulation import receive

def run(path, pin, source):
    path = broker.task_path(path)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin and broker.source_pin() == source, 'FIXTURE_PIN')
    b = parse(raw)
    exact(b, ['schema', 'mode', 'session_id', 'instance_id', 'upstream_port', 'listen_port', 'upstream_address'])
    require(type(b['schema']) is int and b['schema'] == 1 and b['mode'] == 'SYNTHETIC_LOOPBACK_ONLY', 'FIXTURE_ONLY')
    request_id(b['session_id']); request_id(b['instance_id'])
    require(b['upstream_address'] == '127.0.0.1', 'OWNED_LOOPBACK_ONLY')
    require(type(b['upstream_port']) is int and 1 <= b['upstream_port'] <= 65535 and type(b['listen_port']) is int and 0 <= b['listen_port'] <= 65535, 'FIXTURE_PORT')
    try:
        with (path.parent / 'instance_claim.json').open('x', encoding='utf-8') as claim:
            json.dump({'session_id': b['session_id'], 'instance_id': b['instance_id'], 'pid': os.getpid()}, claim)
    except FileExistsError:
        raise Denied('FRESH_FIXTURE_REQUIRED') from None
    allowed = ('127.0.0.1', b['upstream_port'])
    events = []
    def guard(event, args):
        if event == 'socket.__new__':
            require(args[1] == socket.AF_INET and args[2] == socket.SOCK_STREAM, 'FIXTURE_TCP4_ONLY')
        if event in ['socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr']:
            events.append({'kind': 'DNS_DENIED'}); raise PermissionError('NO_DNS')
        if event == 'socket.bind':
            require(args[1] == ('127.0.0.1', b['listen_port']), 'FIXTURE_BIND')
        if event == 'socket.connect':
            ok = args[1] == allowed and args[0].family == socket.AF_INET and args[0].type == socket.SOCK_STREAM
            events.append({'kind': 'connect', 'allowed': ok, 'role': 'B_MODEL', 'pid': os.getpid()})
            require(ok, 'FIXTURE_EGRESS')
        if event in ['subprocess.Popen', 'os.system', 'os.posix_spawn']:
            raise PermissionError('NO_FIXTURE_CHILD')
    sys.addaudithook(guard)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if os.name == 'nt': listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(('127.0.0.1', b['listen_port'])); listener.listen(1); listener.settimeout(3)
            print(json.dumps({'ready': True, 'pid': os.getpid(), 'port': listener.getsockname()[1]}), flush=True)
            with listener.accept()[0] as client:
                deadline = time.monotonic() + 1
                header = b''
                while not header.endswith(b'\r\n\r\n'):
                    require(len(header) < 2048, 'CONNECT_LIMIT'); header += receive(client, 1, deadline)
                lines = header.decode('ascii').split('\r\n')
                require(lines[0] in ['CONNECT '+name+'.invalid:443 HTTP/1.1' for name in ['control', 'mcp', 'oauth', 'harpoon']], 'CONNECT_TARGET')
                require(lines[1] == 'Host: ' + lines[0].split(' ')[1] and lines[2:] == ['', ''], 'CONNECT_FIELDS')
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upstream:
                    upstream.settimeout(.5)
                    upstream.connect(allowed)
                    client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                    deadline = time.monotonic() + 2; idle = time.monotonic() + .7; total = 0
                    while time.monotonic() < min(deadline, idle):
                        ready, _, _ = select.select([client, upstream], [], [], .03)
                        for src in ready:
                            data = src.recv(4096)
                            if not data: return
                            total += len(data); require(total <= 32768, 'RELAY_LIMIT')
                            (upstream if src is client else client).sendall(data)
                            idle = time.monotonic() + .7
                    raise Denied('FIXTURE_TIMEOUT')
    finally:
        with (path.parent / 'worker_receipt.json').open('x', encoding='utf-8') as f:
            json.dump({'pid': os.getpid(), 'session_id': b['session_id'], 'events': events, 'fixture_only': True}, f, indent=2)

if __name__ == '__main__':
    try:
        require(len(sys.argv) == 4, 'FIXTURE_ARGUMENTS')
        run(*sys.argv[1:])
    except BaseException as exc:
        print('BROKER_FIXTURE_STOP:' + (str(exc) if isinstance(exc, Denied) else type(exc).__name__), file=sys.stderr)
        sys.exit(20)
