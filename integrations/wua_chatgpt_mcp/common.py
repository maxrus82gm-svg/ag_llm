"""Bounded local integration contract. No Windows/network activation API."""
from pathlib import Path
import hashlib,hmac,json,os,re,sys,uuid
PACKAGE=Path(__file__).resolve().parent
REPO=PACKAGE.parents[1]
TASK='CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001'
REPORT=REPO/'reports'/TASK
FIXTURE='synthetic_wua_integration_001'
VERSION='0.1.0'
TOOLS=['ping','list_capabilities','read_synthetic_context','get_status']
MAX_REQUEST=8192
MAX_RESPONSE=32768
class Denied(Exception):pass
def require(ok,code):
    if not ok:raise Denied(code)
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode('ascii')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def parse(raw,limit=MAX_REQUEST):
    require(len(raw)<=limit,'SIZE_LIMIT')
    def pairs(rows):
        d={}
        for k,v in rows:require(k not in d,'DUPLICATE_KEY');d[k]=v
        return d
    try:x=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Denied('JSON_TYPE')))
    except (ValueError,RecursionError):raise Denied('JSON_SYNTAX') from None
    def walk(v,depth=0):
        require(depth<=12,'DEPTH_LIMIT')
        if type(v) is dict:
            require(len(v)<=64,'ITEM_LIMIT')
            for k,w in v.items():require(type(k) is str and len(k)<=128,'KEY_LIMIT');walk(w,depth+1)
        elif type(v) is list:
            require(len(v)<=64,'ITEM_LIMIT')
            for w in v:walk(w,depth+1)
        elif type(v) is str:require(len(v)<=16384,'TEXT_LIMIT')
        else:require(v is None or type(v) in (int,bool),'JSON_TYPE')
    walk(x);return x
def exact(x,fields):require(type(x) is dict and set(x)==set(fields),'SCHEMA')
def request_id(value):
    try:require(type(value) is str and str(uuid.UUID(value))==value and uuid.UUID(value).int!=0,'REQUEST_ID')
    except (ValueError,TypeError,AttributeError):raise Denied('REQUEST_ID') from None
    return value
def owned_path(value,existing=True):
    text=str(value);require(not text.startswith(('\\\\','//')) and '://' not in text,'LOCAL_PATH_REQUIRED')
    p=Path(os.path.abspath(text));bases=[REPORT/'runs',REPO/'reports'/'CODEX-WUA-0-MCP-NOTCP-NPFS-001'/'runs']
    # The new NPFS TASK reruns the existing fixture baseline without writing historical reports.
    require(any(p!=base and p.is_relative_to(base) for base in bases),'FIXTURE_SCOPE')
    if os.name=='nt':
        import ctypes
        fn=ctypes.windll.kernel32.GetDriveTypeW;fn.argtypes=[ctypes.c_wchar_p];fn.restype=ctypes.c_uint
        require(fn(p.anchor) in (2,3),'LOCAL_VOLUME_REQUIRED')
    cursor=Path(p.anchor)
    for part in p.parts[1:]:
        cursor/=part
        if cursor==p and not existing:break
        try:attrs=cursor.lstat()
        except OSError:raise Denied('FIXTURE_PATH_UNAVAILABLE') from None
        require(not cursor.is_symlink() and not getattr(attrs,'st_file_attributes',0)&(0x400|0x1000|0x40000|0x400000),'UNSAFE_PATH')
    return p
def bootstrap(path):
    p=owned_path(path);b=parse(p.read_bytes());exact(b,['schema','mode','fixture_id','root','session_id','nonce','channel_key','client_role'])
    require(type(b['schema']) is int and b['schema']==1 and b['mode']=='synthetic_fixture_only' and b['fixture_id']==FIXTURE,'FIXTURE_ONLY')
    require(b['client_role']=='wua-client','CLIENT_ROLE')
    request_id(b['session_id'])
    for k in ['nonce','channel_key']:require(type(b[k]) is str and re.fullmatch('[0-9a-f]{64}',b[k]),'BOOTSTRAP_FORMAT')
    root=owned_path(b['root'],False);require(root.parent==p.parent and root.name=='owned-api-state','ROOT_BINDING')
    return b
def mac(body,key):return hmac.new(bytes.fromhex(key),canonical(body),hashlib.sha256).hexdigest()
def clean_environment():
    return {k:os.environ[k] for k in ['SystemRoot','WINDIR','COMSPEC'] if k in os.environ}
def tree_hash(root):
    rows={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    return digest(rows)
def install_fixture_guard(write_root,network=False):
    """Python audit guard for this reviewed fixture process ONLY; never OS proof."""
    def hook(event,args):
        if event in ['socket.connect','socket.bind','socket.getaddrinfo','socket.gethostbyname'] and not network:raise PermissionError('FIXTURE_NETWORK_DENIED')
        if event in ['os.system','os.posix_spawn']:raise PermissionError('FIXTURE_EXEC_DENIED')
        if event=='open' and not isinstance(args[0],int):
            flags=args[2]
            if type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if str(args[0]).casefold()==os.devnull.casefold():return # reviewed child stderr sink, not persisted storage
                require(Path(os.path.abspath(args[0])).is_relative_to(write_root),'FIXTURE_WRITE_DENIED')
    sys.addaudithook(hook)
