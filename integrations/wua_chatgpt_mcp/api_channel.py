"""Replaceable bounded channel to a server-owned read interface.

Current executable backend is synthetic STDIO only. Production named-pipe ACL,
peer-token authentication and gateway deployment remain explicit blocking gates.
"""
from pathlib import Path
import queue,subprocess,sys,threading
from common import *
class ApiChannel:
    def __init__(self,path):
        self.bootstrap=bootstrap(path);self.lock=threading.Lock();self.messages=queue.Queue(maxsize=1);self.closed=False
        self.process=subprocess.Popen([sys.executable,'-I','-X','utf8','-B',str(PACKAGE/'api_fixture.py'),str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=clean_environment(),cwd=PACKAGE)
        self.reader=threading.Thread(target=self._pump,name='owned-api-reader',daemon=True);self.reader.start()
        try:
            ready=self._read();require(ready.get('ready') is True and ready.get('session_id')==self.bootstrap['session_id'],'API_STARTUP_DENIED');self.baseline=ready['baseline_sha256']
        except BaseException:self.close();raise
    def _pump(self):
        try:
            while True:
                raw=self.process.stdout.readline(MAX_RESPONSE+2)
                if not raw:self.messages.put_nowait(None);return
                require(raw.endswith(b'\n'),'API_RESPONSE_FRAME');v=parse(raw,MAX_RESPONSE)
                self.messages.put(v,timeout=.1)
        except BaseException:
            try:self.messages.put_nowait(None)
            except queue.Full:pass
    def _read(self):
        try:value=self.messages.get(timeout=2)
        except queue.Empty:raise Denied('API_TIMEOUT') from None
        require(type(value) is dict,'API_UNAVAILABLE');return value
    def call(self,operation,rid,task_id=FIXTURE):
        with self.lock:
            require(not self.closed,'API_STOPPED');request_id(rid);require(task_id==FIXTURE and operation in ['status','context'],'SCOPE_DENIED')
            body={'schema':1,'session_id':self.bootstrap['session_id'],'request_id':rid,'operation':operation,'task_id':task_id}
            raw=canonical({'body':body,'mac':mac(body,self.bootstrap['channel_key'])});require(len(raw)<=MAX_REQUEST,'REQUEST_SIZE')
            try:
                self.process.stdin.write(raw+b'\n');self.process.stdin.flush();value=self._read()
                require(value.get('ok') is True,'API_DENIED')
                require(value.get('request_id')==rid and value.get('session_id')==self.bootstrap['session_id'] and value.get('nonce')==self.bootstrap['nonce'],'API_IDENTITY_MISMATCH')
                require(value['value_sha256']==digest(value['value']) and value['baseline_sha256']==self.baseline==value['current_sha256'],'API_PROOF_MISMATCH')
                return value
            except (Denied,OSError,ValueError,KeyError,TypeError):self.close();raise Denied('API_READ_BLOCKED') from None
    def close(self):
        if self.closed:return
        self.closed=True
        try:self.process.stdin.close()
        except (OSError,ValueError):pass
        try:self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=1)
        self.reader.join(1)
        self.process.stdout.close()
        require(not self.reader.is_alive(),'OWNED_PROCESS_NOT_STOPPED')
        root=Path(self.bootstrap['root'])
        if root.is_dir():
            receipt=root/'owned-api-stop.json'
            with receipt.open('x',encoding='utf-8') as f:
                json.dump({'api_exit_code':self.process.returncode,'reader_stopped':not self.reader.is_alive(),'session_id':self.bootstrap['session_id']},f)
