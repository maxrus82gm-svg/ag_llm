"""Bounded synthetic control-plane client through one explicit CONNECT broker.

Only .invalid synthetic authorities; never a replacement for official Go client.
No CLI, DNS, environment proxy lookup, secondary proxy, retry or direct fallback.
"""
import socket,time
from common import *
def receive(sock,n,deadline):
    data=b''
    while len(data)<n:
        require(time.monotonic()<deadline,'ROUTE_TIMEOUT');sock.settimeout(max(.001,deadline-time.monotonic()));x=sock.recv(n-len(data));require(bool(x),'ROUTE_EOF');data+=x
    return data
def header(sock,deadline):
    data=b''
    while not data.endswith(b'\r\n\r\n'):
        require(len(data)<2048,'HEADER_LIMIT');data+=receive(sock,1,deadline)
    try:lines=data.decode('ascii').split('\r\n');code=int(lines[0].split(' ')[1])
    except (UnicodeError,ValueError,IndexError):raise Denied('HEADER_FORMAT') from None
    fields={}
    for line in lines[1:-2]:
        require(':' in line,'HEADER_FORMAT');k,v=line.split(':',1);k=k.lower();require(k not in fields,'HEADER_DUPLICATE');fields[k]=v.strip()
    require('transfer-encoding' not in fields,'TRANSFER_DENIED');return code,fields
def control_request(broker_port,authority,phase,nonce,ambient=None):
    require(type(broker_port) is int and 1<=broker_port<=65535,'BROKER_PORT')
    require(authority in ['control.invalid:443','mcp.invalid:443','oauth.invalid:443','harpoon.invalid:443'],'TARGET_DENIED')
    require(phase in ['poll','result','secret','health','mcp','oauth','harpoon'],'PHASE')
    require(not ambient or not any(ambient.values()),'ENV_OVERRIDE_DENIED');rid=str(uuid.uuid4());deadline=time.monotonic()+1.5
    # Exactly one dial site, always the explicit owned loopback broker. No resolver.
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(1);sock.connect(('127.0.0.1',broker_port))
        sock.sendall(('CONNECT '+authority+' HTTP/1.1\r\nHost: '+authority+'\r\n\r\n').encode('ascii'))
        code,_=header(sock,deadline);require(code==200,'CONNECT_REJECTED')
        sock.sendall(('GET /'+phase+' HTTP/1.1\r\nHost: '+authority+'\r\nX-Request-ID: '+rid+'\r\n\r\n').encode('ascii'))
        code,fields=header(sock,deadline);require(code==200,'REDIRECT_OR_RESPONSE_DENIED')
        try:n=int(fields.get('content-length','-1'))
        except ValueError:raise Denied('BODY_LIMIT') from None
        require(0<=n<=8192,'BODY_LIMIT');value=parse(receive(sock,n,deadline))
        require(value=={'request_id':rid,'route_nonce':nonce,'phase':phase},'FIXTURE_AUTHORITY_MISMATCH')
        return {'request_id':rid,'phase':phase,'response_sha256':digest(value),'route':'ONE_EXPLICIT_LOOPBACK_CONNECT_ONLY','direct_attempts':0,'native_route_proof':False}
