"""Own-loopback runtime compatibility probe; never installs or evaluates WFP."""
from pathlib import Path
import asyncio,hashlib,inspect,json,socket,sys
OUT=Path(sys.argv[1]);REPO=Path(__file__).resolve().parents[3]
assert OUT.is_relative_to(REPO/'reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001') and not OUT.exists()
events=[];active=False
def hook(event,args):
    if active and event in ['socket.connect','socket.bind']:
        address=args[1]
        assert type(address) is tuple and address[0]=='127.0.0.1','PROBE_ONLY_OWN_LOOPBACK'
        events.append({'event':event,'host':address[0],'port':address[1]})
sys.addaudithook(hook)
with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reserved_broker:
    reserved_broker.bind(('127.0.0.1',0));reserved_broker.listen(1);broker_port=reserved_broker.getsockname()[1]
    runner=asyncio.Runner();active=True
    try:loop=runner.get_loop();loop_kind=type(loop).__name__
    finally:active=False;runner.close()
source=inspect.getsource(socket.socketpair)
connects=[e for e in events if e['event']=='socket.connect']
conflict=bool(connects and any(e['port']!=broker_port for e in connects))
record={'python':sys.version.split()[0],'loop_class':loop_kind,'socketpair_function':socket.socketpair.__name__,'AF_UNIX_available':hasattr(socket,'AF_UNIX'),'socketpair_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'owned_reserved_broker_port':broker_port,'observed_runtime_edges':events,'candidate_single_edge_conflict':conflict,'status':'BLOCKED / DYNAMIC INTERNAL TCP UNDER CLIENT SID' if conflict else 'NOT ESTABLISHED','interpretation':'Actual own-loopback runtime behavior observed, compared with prior single-edge predicate intent only. No Windows SID/WFP rules applied; not a native filtering verdict. The fixture audit guard installed after loop construction does NOT cover this initialization.','production_alternative':'Separate reviewed host-owned MCP SDK gateway plus a C-owned synchronous STDIO-to-local-pipe bridge with no TCP runtime, or a demonstrably compatible runtime. Neither activated/implemented here. No new port exception granted.'}
OUT.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({'loop':loop_kind,'internal_connects':len(connects),'single_edge_conflict':conflict}));sys.exit(0 if conflict else 3)
