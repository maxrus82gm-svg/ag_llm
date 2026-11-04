"""Refresh the publication inventory without Git or mutable self-hashes."""
from pathlib import Path
import datetime as dt
import hashlib
import json

REPORT = Path(__file__).resolve().parent
ROOT = REPORT.parents[1]
def ref(path):
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), size=len(data), sha256=hashlib.sha256(data).hexdigest())

files = [ref(p) for p in sorted(REPORT.rglob('*')) if p.is_file() and p.name != 'manifest.json']
sources = [ref(ROOT/p) for p in ['run_store.py', 'test_run_store_v2.py', 'test_web_alarm_ultra_chat_turn.py']]
readonly = [ref(ROOT/p) for p in ['context_storage.py', 'audit_storage.py', 'web_alarm/server.py',
                                'web_alarm/ui.py', 'web_alarm/ultra_chat.py', 'Start_WebAlarm.bat',
                                'web_alarm/launch_config.json', 'tools/task_slot_rotate.py']]
record = REPORT/'task_record.json'
history = json.loads(record.read_text(encoding='utf-8')) if record.exists() else None
value = dict(task_id=REPORT.name, status='RESULT READY / AWAITING INDEPENDENT VERIFICATION',
             generated_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
             history_id=history['history_id'] if history else None,
             independent_review='NOT VERIFIED', publication='LOCAL ONLY; Git/GitHub not used',
             write_scope=['run_store.py','test_run_store_v2.py','test_web_alarm_ultra_chat_turn.py',str(REPORT.relative_to(ROOT)).replace('\\','/')+'/'],
             native_finish_exception='Unmodified tools/task_slot_rotate.py finish; generated card/history artifacts only',
             sources=sources, readonly_sources=readonly, files=files,
             manifest_self_hash='excluded to avoid a circular digest',
             result_summary='evidence/results_summary.json',
             open=['Independent WEB23 review pending','Same-user final TOCTOU residual','Picker WinError10053 intermittent; outside scope',
                   'Windows native file/directory symlink tests skipped for missing privilege','Stage3 HOLD; no implementation GO'])
(REPORT/'manifest.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(ref(ROOT/p['path']) == p for p in files+sources+readonly)
print(json.dumps(dict(files=len(files),sources=len(sources),history_id=value['history_id'],verified=True),ensure_ascii=False))
