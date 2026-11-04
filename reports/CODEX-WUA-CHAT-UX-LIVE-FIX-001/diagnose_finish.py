"""Run the unmodified standard finish entry point once with an observational exception trace."""
from pathlib import Path
import contextlib
import io
import json
import runpy
import shutil
import sys
import time

REPORT=Path(__file__).resolve().parent
ROOT=REPORT.parents[1]
OUT=REPORT/'evidence'
for name in ['finish.json','finish_execution.json']:
    dst=OUT/name.replace('.json','_attempt_2.json')
    assert not dst.exists()
    shutil.copy2(OUT/name,dst)
argv=['tools/task_slot_rotate.py','finish','--card','Документация/000_Задачи Codex.md',
      '--task-id','CODEX-WUA-CHAT-UX-LIVE-FIX-001','--no-chat-amendment','--apply','--headless']
events=[]
def observe(frame,event,arg):
    if event=='exception' and frame.f_code.co_name=='atomic_write' and isinstance(arg[1],OSError):
        e=arg[1]
        events.append(dict(type=type(e).__name__,errno=e.errno,winerror=getattr(e,'winerror',None),
                           filename=e.filename,filename2=e.filename2,message=str(e),line=frame.f_lineno))
    return observe
stdout=io.StringIO(); stderr=io.StringIO(); code=0; start=time.monotonic()
sys.argv=argv
try:
    with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
        sys.settrace(observe)
        runpy.run_path(str(ROOT/argv[0]),run_name='__main__')
except SystemExit as e:
    code=int(e.code or 0)
finally:
    sys.settrace(None)
(OUT/'finish.json').write_text(stdout.getvalue(),encoding='utf-8')
meta=dict(argv=argv,entry_point='unmodified tools/task_slot_rotate.py through runpy __main__',
          code_changed=False,guards_changed=False,exit_code=code,stderr=stderr.getvalue(),
          seconds=round(time.monotonic()-start,2),os_errors=events)
(OUT/'finish_execution.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(stdout.getvalue()); print(json.dumps(meta,ensure_ascii=False))
raise SystemExit(code)
