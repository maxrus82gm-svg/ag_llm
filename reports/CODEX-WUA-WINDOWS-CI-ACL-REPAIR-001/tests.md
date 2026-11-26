# Команды и результаты локальной Windows OFFLINE-проверки

Windows 10.0.26300 AMD64, Python 3.12.10 из локальной venv, pywin32 312, httpx 0.28.1, jsonschema 4.26.0, MCP 2.2.0, Node.js 22.20.0. Зафиксированные в workflow зависимости не менялись. Рабочий каталог — корень WUA.

## Подготовка

Временные каталоги перенаправлены в `_ultra_agent_test/scratch`. Для каждого запуска использовалось уникальное `WUA_OFFLINE_RUN`. `offline_runner.py` настраивает TEMP, TMP, TMPDIR, APPDATA и LOCALAPPDATA только для процесса теста. Audit hook запрещает внешние TCP/DNS и вызовы Git/gh из тестового Python. Реальные credentials очищены. CMD запускаются на изолированном LOCALAPPDATA и свободных loopback-портах, открытие браузера заглушено. Дочерние Python-процессы CMD отдельно блокируют внешние сетевые обращения. Bridge HTTP обслуживает MockTransport.

### Воспроизведение

```powershell
$py = '.venv/Scripts/python.exe'
$dir = '_ultra_agent_test/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:WUA_OFFLINE_RUN = 'ca_acl_before'
& $py -B -X utf8 "$dir/acl_probe.py"
$env:WUA_OFFLINE_RUN = 'ca_acl_after'
& $py -B -X utf8 "$dir/acl_probe.py"
$env:WUA_OFFLINE_RUN = 'ca_sparse'
& $py -B -X utf8 "$dir/sparse_probe.py"
```

Первый ACL probe выполнялся до правок, второй сравнил прежнюю копию с изменённым кодом. Sparse probe сравнивает утверждённый локальный baseline из Backups с новым cone, копирует выбранные скрипты в пустые корни, вызывает production `load_launch()` без запуска профилей и сверяет трассу прямых импортов.

### Workflow и дополнительные локальные checks

```powershell
$py = '.venv/Scripts/python.exe'
$dir = '_ultra_agent_test/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001'
$runner = "$dir/offline_runner.py"
$unittest = 'import runpy,sys,unittest; runpy.run_path(sys.argv.pop(1)); unittest.main(module=None)'
$script = "import runpy,sys; runpy.run_path(sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name='__main__')"
$env:PYTHONDONTWRITEBYTECODE = '1'

$env:WUA_OFFLINE_RUN = 'ca_bridge_final'
& $py -B -u -X utf8 -c $unittest $runner -v test_web_alarm_colibri_bridge_transport test_web_alarm_launcher

$env:WUA_OFFLINE_RUN = 'ca_s1static'
& $py -B -u -X utf8 -c $script $runner 'reports/CHATGPT-WUA-COLIBRI-MVP1-CI-S1S2D8-20261123-001/ci_s1_source.py'

$env:WUA_OFFLINE_RUN = 'ca_s1'
Remove-Item Env:RT002_S1_EVIDENCE_ROOT -ErrorAction SilentlyContinue
& $py -B -u -X utf8 -c $script $runner test_rt002_s1_routes.py

$env:WUA_OFFLINE_RUN = 'ca_s2'
& $py -B -u -X utf8 -c $script $runner test_rt002_s2_budget_policy.py

$env:WUA_OFFLINE_RUN = 'ca_d8'
& $py -B -u -X utf8 -c $unittest $runner -v test_web_alarm_ultra_chat.DataTests.test_d8_adapter_imports_no_transport_and_core_errors_never_reach_the_browser test_wua_666_gates

$env:WUA_OFFLINE_RUN = 'ca_chat'
& $py -B -u -X utf8 -c $unittest $runner -v test_web_alarm_ultra_chat test_web_alarm_ordinary_application

node --test test_web_alarm_ultra_chat_ui.js test_web_alarm_evm_ui.js test_web_alarm_operator_ui.js

& $py -B -X utf8 -c "from mcp.server.mcpserver import MCPServer; from importlib.metadata import version; print('MCP_SERVER_IMPORT_PASS',version('mcp'))"

$env:WUA_OFFLINE_RUN = 'ca_cmd'
& $py -B -u -X utf8 "$dir/launcher_smoke.py"
```

Проверка Bridge и Launcher выполнялась также на исходниках до изменений (`ca_baseline`) и после первого варианта исправления (`ca_bridge`). Исходный локальный прогон дал 37/37. Первый вариант дал 38 PASS и 1 ERROR с кодом 1 из-за WinError 5 при настройке token после изменения DACL родителя. Итоговый прогон дал 39/39 и код 0 после изменения порядка создания. Остальные итоговые количества и коды указаны в [отчёте](report.md).

Перед полным S1 проверены размеры и SHA-256 всех шести защищённых входов по pins. Штатный gate повторно валидировал pins и использовал изолированные снимки. Сырые данные в пакет не включены. Negative controls S1, S2, D8, owner, public ACE и sparse RED сохранили ожидаемые отказы.

Сырые логи доступны локально в `reports/_local/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001/`. Точные имена, SHA-256 и результаты, пригодные для передачи WEB 36, приведены в [evidence.json](evidence.json).
