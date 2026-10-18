"""Synchronous control-policy reference, NEVER an OS/WFP/native launcher.

New hypothesis: policy denial, audited dial attempt and chain-wide lease revocation
must remain distinguishable. Logical identities are synthetic, not real PIDs or
authenticated Windows tokens. No environment, DNS, alternate endpoint, process
creation or reconnection. Tested only with owned loopback fixtures.
"""
from dataclasses import dataclass
import socket
import threading
import time

CURRENT_OPERATION = threading.local()


class GateDenied(RuntimeError):
    pass


class ProtocolFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int
    transport: str = 'tcp4'

    def __post_init__(self):
        if self.host != '127.0.0.1' or self.transport != 'tcp4':
            raise ValueError('synthetic literal IPv4 TCP endpoint required')
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError('invalid synthetic port')


def close(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def valid_identity(value):
    return (type(value) is tuple and len(value)==2 and type(value[0]) is str and
            1<=len(value[0])<=32 and value[0].isascii() and value[0].isalpha() and
            type(value[1]) is int and 1<=value[1]<=2147483647)


class ReferenceGate:
    def __init__(self, endpoint, scope='synthetic-scope'):
        if not isinstance(endpoint, Endpoint):
            raise ValueError('explicit validated endpoint required')
        self.endpoint, self.scope = endpoint, scope
        self.state = 'READY'
        self.members = {('root', 1)}
        self.sockets = set()
        self.ledger = []
        self.sequence = 0

    def event(self, code, **fields):
        if len(self.ledger) >= 128:
            self.trip('LEDGER_LIMIT')
            raise GateDenied('ledger bound reached')
        self.ledger.append({'code':code,**fields})

    def trip(self, reason):
        if self.state == 'CLOSED':
            return
        self.state = 'TRIPPED'
        for sock in list(self.sockets):
            close(sock)
        self.sockets.clear()
        # Bound without recursively invoking event() on ledger overflow.
        if len(self.ledger) < 128:
            self.ledger.append({'code':'CHAIN_TRIPPED','reason':reason})

    def admit_child(self, parent, child, controller_authorized=False):
        # Capability registry MODEL only. No actual process is created/resumed.
        if (self.state != 'READY' or not valid_identity(parent) or not valid_identity(child) or
                parent not in self.members or controller_authorized is not True or child in self.members):
            self.event('CHILD_REFUSED_NOT_CREATED')
            self.trip('CHILD_NOT_AUTHORIZED')
            raise GateDenied('synthetic child denied')
        self.members.add(child)
        self.event('MODEL_CHILD_ADMITTED')

    def connect(self, identity=('root',1), requested=None):
        requested = self.endpoint if requested is None else requested
        if self.state != 'READY' or not valid_identity(identity) or identity not in self.members or requested != self.endpoint:
            self.event('REFUSED_BEFORE_DIAL')
            self.trip('IDENTITY_OR_EDGE_DENIED')
            raise GateDenied('connection refused before API call')
        self.sequence += 1
        operation = self.scope + ':' + str(self.sequence)
        self.event('DIAL_API_INTENT',operation=operation)
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.settimeout(0.25)
        CURRENT_OPERATION.value = operation
        try:
            sock.connect((self.endpoint.host,self.endpoint.port))
            self.sockets.add(sock)
            self.event('CONNECTED',operation=operation)
            return sock
        except BaseException as exc:
            close(sock)
            self.event('DIAL_FAILED',operation=operation,error_type=type(exc).__name__)
            self.trip('CONNECT_FAILED')
            raise
        finally:
            CURRENT_OPERATION.value = None

    def socks_probe(self, port):
        if type(port) is not int or not 1 <= port <= 65535:
            self.trip('SYNTHETIC_DESTINATION_INVALID')
            raise ValueError('invalid synthetic destination')
        sock = self.connect()
        deadline = time.monotonic()+0.25
        def read(count):
            data = bytearray()
            while len(data)<count:
                left=deadline-time.monotonic()
                if left<=0:raise TimeoutError('bounded fixture handshake')
                sock.settimeout(left)
                part=sock.recv(count-len(data))
                if not part:raise ProtocolFailure('fixture disconnected')
                data.extend(part)
            return bytes(data)
        try:
            sock.sendall(b'\x05\x01\x00')
            if read(2)!=b'\x05\x00':raise ProtocolFailure('fixture method rejected')
            name=b'origin.invalid'
            sock.sendall(b'\x05\x01\x00\x03'+bytes([len(name)])+name+port.to_bytes(2,'big'))
            if read(4)!=b'\x05\x00\x00\x01':raise ProtocolFailure('fixture CONNECT rejected')
            read(6)
            self.event('FIXTURE_HANDSHAKE_OK')
            return sock
        except BaseException as exc:
            self.event('FIXTURE_HANDSHAKE_FAILED',error_type=type(exc).__name__)
            self.trip('UPSTREAM_PROTOCOL_FAILED')
            raise

    def observe_unbrokered_attempt(self):
        self.event('UNBROKERED_API_ATTEMPT')
        self.trip('AUDIT_MISMATCH')

    def stop(self):
        self.trip('STOP')
        self.state='CLOSED'


if __name__=='__main__':
    raise SystemExit('Reference helper only: no native process or OS policy entry point.')
