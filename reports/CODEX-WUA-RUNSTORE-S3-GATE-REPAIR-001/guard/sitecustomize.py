"""Test-process guard: loopback only, no Git executables/metadata. Propagated to Python children."""
import atexit
import json
import os
import re
from pathlib import Path
import sys

denied=[]
loopback={'127.0.0.1','localhost','::1'}
def executable_name(executable,command):
    if executable is None:
        if isinstance(command,(tuple,list)):
            executable=command[0]
        else:
            # Only the executable prefix is needed. The remaining Windows -c payload is not shell syntax.
            match=re.match(r'^\s*(?:"([^"]+)"|(\S+))',command)
            if not match: raise RuntimeError('Missing executable prefix')
            executable=match.group(1) or match.group(2)
    return Path(str(executable)).name.lower()
def audit(event,args):
    if event=='socket.connect':
        address=args[1]
        if not isinstance(address,tuple) or str(address[0]).lower() not in loopback:
            denied.append(dict(event=event,target=str(address)))
            raise RuntimeError('S3 test guard: external socket denied')
    elif event=='socket.getaddrinfo' and str(args[0]).lower() not in loopback:
        denied.append(dict(event=event,target=str(args[0])))
        raise RuntimeError('S3 test guard: external DNS denied')
    elif event=='subprocess.Popen':
        name=executable_name(args[0],args[1])
        if name not in {'python.exe','pythonw.exe','python3','python','node.exe','node'}:
            denied.append(dict(event=event,executable=name))
            raise RuntimeError('S3 test guard: unapproved executable denied')
    elif event=='open' and isinstance(args[0],(str,bytes)):
        path=os.fsdecode(args[0]).replace('\\','/').lower()
        if '.git' in path.split('/'):
            denied.append(dict(event=event,target='Git metadata'))
            raise RuntimeError('S3 test guard: Git metadata denied')
sys.addaudithook(audit)
def save():
    target=os.environ.get('S3_GUARD_OUTPUT')
    if target:
        folder=Path(target)
        folder.mkdir(parents=True,exist_ok=True)
        (folder/(str(os.getpid())+'.json')).write_text(json.dumps(dict(pid=os.getpid(),guard_active=True,denied=denied,external_provider_connections=0)),encoding='utf-8')
atexit.register(save)
