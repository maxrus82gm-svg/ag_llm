# WEB27 / H-CODEX-000028 — независимая приёмка TEST activation

**Задача:** `CODEX-WUA-CHAT-ORDINARY-TEST-ACTIVATION-001`. **Основание:** пользовательский №568 `78a8f5f0277f35228c66d4f199dc2024562fc1a9`. **Дата:** 09.11.2026.

**VERDICT: PASS / BOUNDED INDEPENDENT OFFLINE P0+P1. P2 (per-chat usage UI) OPEN.** Постоянный `Start_WebAlarm_Test.cmd` подключает ранее принятый Ordinary Core fake bridge. STANDARD и старый Stage5 rollback неизменны. REAL/S3b/Stage6/7 HOLD.

## Доказательства

- Сверены SHA-256 опубликованных `web_alarm/ordinary_test_fixture.py`, `web_alarm/launch_test_config.json`, `test_web_alarm_ordinary_test_activation.py` и неизменённого `web_alarm/launcher.py` с Windows исходниками; два CMD хешированы и не изменялись.
- На том же источнике независимо повторены 3 `ActivationTests` и 4 `StableEntryTests`: **7/7 PASS, 0 FAIL/ERROR, exit 0, 11.168 сек** (Windows Python 3.12.10). Проверены физический TEST CMD, два чата, история/контекст, retry без дублей, HTTP-read/reopen, запрет REAL, Enter→TEMP cleanup, Stage5 rollback, отсутствие fallback на STANDARD.
- Запись тестовых evidence направлена во временный каталог, не в авторский отчёт. Две предварительные ошибки PowerShell quoting/import временного runner были исправлены до успешного прогона и не связаны с кодом проекта.
- Bootstrap ставит ранее принятый guard из `reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py` до импорта core; этот файл сохранять в поставке.

## Ограничения и NEXT

Ручной визуальный **GUI/F5 NOT RUN** (browser API и HTTP проверены, но не ручное взаимодействие). P2 input/output/known reasoning/UNKNOWN, настройки отдельного чата и продуктовые 250k/10k/20k **не реализованы**. Не запускались full CI, clean install, real STANDARD GUI, native Tk, power-loss/force-kill и настоящие GigaChat/OAuth/paid запросы. S3b/RT-002/B2 безопасность обязана быть реализована и независимо принята до отдельного USER GO на real. Глобальный бюджет Workspace DEFERRED.

NEXT: короткая пользовательская ручная проверка по `reports/CODEX-WUA-CHAT-ORDINARY-TEST-ACTIVATION-001/user-smoke.md`, после неё отдельно поручить per-chat usage/settings, отдельно S3b. `FOLLOWUP-WUA-ORDINARY-CORE-BRIDGE-ACTIVATION-001` остаётся PARTIAL/OPEN. Никакой новой задачи или real GO этот review не назначает.
