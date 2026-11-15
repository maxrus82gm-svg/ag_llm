"""No Git/network. Seal explicit changed sources and this task's artifacts."""
from pathlib import Path
import ast
import hashlib
import json
import sys

PKG=Path(__file__).resolve().parent
ROOT=PKG.parents[1]
SOURCES=['gigachat_runtime.py','gigachat_transport.py','gigachat_admission.py',
 'ordinary_gigachat_transport.py','ordinary_chat_service.py','web_alarm/ordinary_chat_bridge.py',
 'web_alarm/ordinary_provider.py','web_alarm/turn_service.py','web_alarm/ultra_chat.py','web_alarm/ui.py',
 'test_web_alarm_gigachat_multimodel.py','test_web_alarm_ordinary_application.py',
 'test_web_alarm_test_model_persist.py','test_web_alarm_launcher.py','test_web_alarm_ultra_chat_ui.js',
 'test_rt002_s1_routes.py','test_rt002_s2_budget_policy.py','rt002_multimodel_reconciliation.json']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

syntax=[]
for name in SOURCES:
    if name.endswith('.py'):
        compile((ROOT/name).read_text(encoding='utf-8'),name,'exec')
        syntax.append(name)
(PKG/'evidence/syntax.json').write_text(json.dumps(dict(python=sys.version,compiled=syntax,exit_code=0),indent=2),encoding='utf-8')

baseline=json.loads((ROOT/'reports/CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001/evidence/protected_before.json').read_text('utf-8'))
changed=[name for name,digest in baseline.items() if not (ROOT/name).is_file() or sha(ROOT/name)!=digest]
untouched=['context_storage.py','run_store.py','audit_storage.py','provider_accounting.py','model_registry.py',
 'ultra_budget_ledger.py','ultra_budget_policy.py','ultra_ui.py','Start_Ultra.cmd',
 'Start_WebAlarm_Standard.cmd','Start_WebAlarm_Test.cmd','web_alarm/launcher.py',
 'web_alarm/launch_config.json','web_alarm/launch_test_config.json','web_alarm/server.py']
verified={name:dict(sha256=sha(ROOT/name),h37_equal=sha(ROOT/name)==baseline.get(name)) for name in untouched}
assert all(f['h37_equal'] for f in verified.values()),verified
(PKG/'evidence/preservation.json').write_text(json.dumps(dict(
 reference='H37 protected_before (historical reference, not current-task before snapshot)',
 checked=len(baseline),differences_from_h37=changed,explicit_unchanged=verified,
 production_data='Not read/used by tests; no claim of full private-file census',
 writes='Only explicit source/test/package + scripted own finish'),indent=2,ensure_ascii=False),encoding='utf-8')

results={p.stem:json.loads(p.read_text('utf-8')) for p in sorted((PKG/'evidence').glob('*.result.json'))}
lines=['# Авторские тесты — результаты','',
 'Acceptance children: Python 3.12.10 / httpx 0.28.1. Node v22.20.0. External provider/OAuth calls 0.',
 'Наборы пересекаются; counts не складывать. Точные команды и cases находятся в одноимённых JSON/stdout/stderr.','',
 '| Evidence | Exit | Фактические counts |','|---|---:|---|']
for name,result in results.items():
    lines.append('| '+name+' | '+str(result.get('exit_code'))+' | '+json.dumps(result.get('counts',{}),ensure_ascii=False)+' |')
lines += ['', 'UI: evidence/ui.stdout.txt — initial 69 PASS/1 helper FAIL; evidence/ui_final.stdout.txt и ui_complete.stdout.txt — 70 PASS, 0 FAIL/cancel/skip.',
 'S1 historical RAW local runner реально выполнен и pins проверены; GitHub availability/independent run NOT RUN.',
 'regression_selected: 5 исходных FAIL (contract/optional usage/parent cmd guard), regression_repaired: 245 PASS +329 subtests /1 stale retired-BAT FAIL; final_affected: 180 PASS +222 subtests. После финальных response-version/cached изменений повторён final_protocol_usage; после probe-only refinement — sealed_protocol.',
 'mutant_version_red/mutant_reserve_red — ожидаемый RED по вторичной durable binding/reserve проверке, 1 failure каждый; источники не мутировали.',
 'Неверные имена файлов regression_initial/regression_final дали exit4/0 collected, это ошибки command selection, не тестовый PASS.',
 'Physical CMD child отказан guard; native CMD/Chromium/user UX/clean Windows/TLS handshake/LIVE NOT RUN. Полный B2 independent NOT RUN.']
(PKG/'test-results.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

record=PKG/'task_record.json'
saved_record=json.loads(record.read_text('utf-8')) if record.exists() else None
history=saved_record.get('history_id') if saved_record else None
if saved_record:
    for item in saved_record['sources'].values():
        assert sha(ROOT/item['path']) == item['sha256'], item['path']
    old=(PKG/'before/card_pre_finish.md').read_bytes()
    current=(ROOT/'Документация/000_Задачи Codex.md').read_bytes()
    marker='# БЛОК 2 — '.encode('utf-8')
    assert old.split(marker,1)[1] == current.split(marker,1)[1]
    (PKG/'evidence/closeout.json').write_text(json.dumps(dict(task_id=PKG.name,history_id=history,
        result='ROTATED / SUBMITTED / REVIEW PENDING',record_sources_verified=True,
        blocks_2_to_4_unchanged=True,real_calls=0,independent='NOT RUN',release='HOLD'),indent=2),encoding='utf-8')
manifest=dict(task_id=PKG.name,history_id=history,status='AUTHOR IMPLEMENTED / PARTIAL / REAL RELEASE HOLD',
 independent='NOT RUN / REVIEW PENDING',real_calls=0,
 sources={name:dict(bytes=(ROOT/name).stat().st_size,sha256=sha(ROOT/name)) for name in SOURCES},
 artifacts={p.relative_to(PKG).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
            for p in sorted(PKG.rglob('*')) if p.is_file() and p.name!='manifest.json'})
(PKG/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(task_id=PKG.name,history_id=history,sources=len(SOURCES),artifacts=len(manifest['artifacts']),
                     protected_verified=len(verified),results=len(results)),ensure_ascii=False))
