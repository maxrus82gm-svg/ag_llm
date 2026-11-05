"""Conservation, compile, source inventory and publication manifest; never restores user/editor changes."""
from pathlib import Path
from collections import Counter
import argparse
import datetime as dt
import difflib
import hashlib
import json
import platform
import subprocess
import sys

REPORT=Path(__file__).resolve().parent;ROOT=REPORT.parents[1]
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['before_finish','after_finish','manifest'],required=True);a=p.parse_args()
OWNED=['web_alarm/ultra_chat.py','web_alarm/server.py','web_alarm/ui.py','web_alarm/turn_service.py',
       'test_web_alarm_ultra_chat_turn_service.py','test_web_alarm_ultra_chat_turn_http.py','test_web_alarm_ultra_chat_ui.js']
def ref(path):
 data=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),size=len(data),sha256=hashlib.sha256(data).hexdigest())
baseline=json.loads((REPORT/'evidence/baseline.json').read_text(encoding='utf-8'))
if a.phase!='manifest':
 protected=[ref(p) for folder in ['.ultra','Чат_pro','Чат_Pro_01','.obsidian'] for p in (ROOT/folder).rglob('*') if p.is_file()]
 old={v['path']:v for v in baseline['protected']};new={v['path']:v for v in protected}
 changes=[dict(path=k,before=old.get(k),after=new.get(k)) for k in sorted(old.keys()|new.keys()) if old.get(k)!=new.get(k)]
 checks=[]
 for before in baseline['source']:
  name=before['path'];backup=REPORT/'before'/(name+'.source.txt')
  assert hashlib.sha256(backup.read_bytes()).hexdigest()==before['sha256']
  if name not in OWNED:
   checks.append(dict(path=name,unchanged=ref(ROOT/name)==before,native_card=name=='Документация/000_Задачи Codex.md' and a.phase=='after_finish'))
  else:
   diff=''.join(difflib.unified_diff(backup.read_text(encoding='utf-8').splitlines(keepends=True),(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='before/'+name,tofile='after/'+name))
   (REPORT/'evidence'/(name.replace('/','_')+'.diff.txt')).write_text(diff,encoding='utf-8')
 compile_files=[name for name in OWNED if name.endswith('.py')]
 for name in compile_files:compile((ROOT/name).read_text(encoding='utf-8'),name,'exec')
 config=json.loads((ROOT/'web_alarm/launch_config.json').read_text(encoding='utf-8'))
 value=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),platform=platform.platform(),python=sys.version,
            node=subprocess.check_output(['node','--version'],text=True).strip(),
            protected_counts=dict(Counter(v['path'].split('/')[0] for v in protected)),
            user_storage_changes=[v for v in changes if not v['path'].startswith('.obsidian/')],
            editor_changes=[v for v in changes if v['path'].startswith('.obsidian/')],
            baseline_copies_verified=len(baseline['source']),readonly=checks,compile_passed=len(compile_files),launcher=config['active'])
 (REPORT/'evidence'/('conservation_'+a.phase+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(value,ensure_ascii=False,indent=2))
 assert not value['user_storage_changes']
 assert all(v['unchanged'] or v['native_card'] for v in checks)
 assert config['active']=='standard'
else:
 record=REPORT/'task_record.json';history=json.loads(record.read_text(encoding='utf-8')) if record.exists() else None
 files=[ref(p) for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name!='manifest.json']
 value=dict(task_id=REPORT.name,status='RESULT READY / AWAITING INDEPENDENT VERIFICATION',history_id=history['history_id'] if history else None,
            independent_review='NOT VERIFIED',publication='LOCAL ONLY; user publication pending',
            sources=[ref(ROOT/name) for name in OWNED],files=files,
            readonly=[ref(ROOT/name) for name in ['context_storage.py','run_store.py','audit_storage.py','Start_WebAlarm.bat','web_alarm/launch_config.json','tools/task_slot_rotate.py']],
            native_finish_exception='Unmodified task_slot_rotate.py finish: card/history/snapshot generated artifacts',
            self_hash='excluded to avoid circular digest')
 (REPORT/'manifest.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 assert all(ref(ROOT/v['path'])==v for v in files+value['sources']+value['readonly'])
 print(json.dumps(dict(files=len(files),source=len(OWNED),history_id=value['history_id'],verified=True)))
