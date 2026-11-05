"""TASK TEST entry on disposable data; STANDARD configuration is never changed.

--smoke performs the create/send/restart/history scenario. Interactive demo has a bounded lifetime
and a report-local stop file, so automation can close it and let TemporaryDirectory clean up.
"""
from pathlib import Path
import argparse
import hashlib
import http.client
import json
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import context_storage as core
from web_alarm.server import WebAlarmApi,create_server

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args();assert 1<=args.seconds<=1800
    report=Path(__file__).resolve().parent
    stop=report/'evidence/demo.stop'
    with tempfile.TemporaryDirectory(prefix='CODEX-WUA-CHAT-S3-TEST-') as temporary:
        base=Path(temporary);workspace=base/'workspace';workspace.mkdir()
        core.ensure_workspace_storage(workspace)
        chat=core.create_chat(workspace,'TEST · Stage 3')['chat_id']
        api=WebAlarmApi(base/'storage');record=api.registry.register('TEST · синтетический Workspace',workspace)
        def start():
            server=create_server(api,port=0,test_turn_roots=[workspace]);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();return server,thread
        server,thread=start()
        print(json.dumps(dict(task='CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001',mode='TEST',url=f'http://127.0.0.1:{server.server_port}',workspace=record.workspace_id,chat=chat),ensure_ascii=False),flush=True)
        try:
            if args.smoke:
                def request(method,path,body=None,headers=None):
                    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15)
                    raw=json.dumps(body,ensure_ascii=False).encode() if body is not None else None
                    sent={'Origin':f'http://127.0.0.1:{server.server_port}','Content-Type':'application/json',**(headers or {})}
                    try:
                        conn.request(method,path,raw,sent);r=conn.getresponse();value=json.loads(r.read());assert r.status==200,(r.status,value);return value
                    finally:conn.close()
                write=request('GET','/ui/ultra-chat/write-capability')['ultra_chat_write']
                prefix=f'/ultra/chat/workspaces/{record.workspace_id}/chats/{chat}'
                result=request('POST',prefix+'/turns',dict(idempotency_key='demo_s3_0000000000001',text='Проверка TEST',model_ref='local-test:v1',context_ref='empty:v1',config_ref='test-only:v1'),{write['header']:write['token']})
                assert result['state']=='SUCCEEDED'
                before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (workspace/'.ultra/chats'/chat/'messages').glob('*.json')}
                server.shutdown();server.server_close();thread.join(3)
                server,thread=start()
                read=request('GET','/ui/ultra-chat/capability')['ultra_chat']
                history=request('GET',prefix+'/messages',headers={read['header']:read['token']})
                assert [m['text'] for m in history['messages']]==['Проверка TEST','TEST: сообщение принято.']
                assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (workspace/'.ultra/chats'/chat/'messages').glob('*.json')}
                print(json.dumps(dict(create_chat=True,send=result,restart=True,history=history,raw_sha256=before),ensure_ascii=False),flush=True)
            else:
                deadline=time.monotonic()+args.seconds
                while time.monotonic()<deadline and not stop.exists():time.sleep(.1)
        finally:server.shutdown();server.server_close();thread.join(3)
    print('TEST temporary data cleaned; STANDARD unchanged',flush=True)

if __name__=='__main__':main()
