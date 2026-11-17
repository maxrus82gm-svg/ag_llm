# H43 — адресная инженерная доработка legacy session / instance control

**Дата:** 17.11.2026
**Review/repair ID:** `CHATGPT-WUA-H43-LEGACY-RECOVERY-REPAIR-20261117-001`
**Связь:** `H-CODEX-000043` / `CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001`
**Исполнитель:** ChatGPT по прямому USER GO на домашнем компьютере `DESKTOP-SC96D3U`
**Исход:** `PARTIAL / OFFLINE DEVELOPMENT PASS / INDEPENDENT CI NOT RUN / OWNER GUI NOT RUN / REAL HOLD`

## Начальное состояние

- `main@7504b761` (№644); `GPT@b36b5b13` (№643, ancestor of main).
- Сохранены незавершённые локальные изменения Codex: `web_alarm/launcher.py`, `server.py`, `ui.py`, новый `instance_control.py`, тесты/AMENDMENT/evidence. Чужая `rt002_multimodel_reconciliation.json` также modified, самостоятельно не перезаписывалась.
- H43 автор ранее PARTIAL, `H-CODEX-000043`; авторские тесты не являются independent PASS.
- Прежняя независимая диагностика: STANDARD на 8765 не запущен; legacy account `ACTIVE` без `owner_lock` в личном хранилище и старом `live_bootstrap`; один grant ACTIVE, два CLOSED; ledger personal 30 событий / 10 попыток, в том числе один `UNKNOWN_TERMINAL`.

## Реализация

1. Создан только operator-side модуль `tools/legacy_session_recovery.py`. Не включён в `web_alarm` production imports, HTTP endpoints, браузер, launcher или автоматический startup. Не содержит OAuth/catalog/inference.
2. При inspection используется фактический embedded `workspace_id` и существующий `BudgetLedger.recover()`, без enrollment/обнуления.
3. Проверяет совпадение account/grant, неизменность grant bytes, account SHA identity, VALID ACTIVE legacy schema, counts, confirmed versions, отсутствие второго ACTIVE grant для того же account в том же workspace; защищает от повторной миграции.
4. Использует тот же account OS-lock, что и H43 runtime, и существующий writer-lock workspace. При apply нужна отдельная `owner_authorized=True` и доверенный `owner_quiescent` callback; для НЕ-TEMP workspace также обязательный fail-closed Windows процессный scan. Доказательство отсутствия удалённых процессов таким scan не достигается: нужен maintenance control владельца.
5. Лишь после проверки и повторного ledger recover публикует новый неизменяемый original-account evidence file; затем атомарно закрывает только account, сохраняя confirmed versions. Старый grant, Turn/RAW и ledger остаются без изменений. При прерывании между evidence и account замена не повторяется автоматически.
6. Новый `test_web_alarm_legacy_session_recovery.py`: отдельные TEMP workspaces, positive/negative, competing owner lock, integrity, idempotence, no permission.
7. H43 amendment inventory: `instance_control.py` добавляет ровно три локальных сетевых construction. S1 expected inventory дополняется **точными** site/owner pins (`import:urllib.request`, `_read_peer.urlopen`, `cleanup.urlopen`) с прежней консервативной классификацией UNKNOWN, без wildcard и без превращения их в одобренные LLM endpoints.

## Фактические проверки на домашнем ПК

- `.venv/Scripts/python.exe -B -X utf8 -m unittest test_web_alarm_legacy_session_recovery -q`: **7/7 PASS**.
- `.venv/Scripts/python.exe -B -X utf8 -m unittest test_web_alarm_standard_live test_web_alarm_instance_control test_web_alarm_legacy_session_recovery -q`: **23/23 PASS**.
- `.venv/Scripts/python.exe -B -X utf8 -m unittest test_web_alarm_instance_control -v`: **3/3 PASS**.
- `.venv/Scripts/python.exe -B -X utf8 -m unittest test_web_alarm_graceful_exit test_web_alarm_gigachat_live_control test_web_alarm_launcher -q`: **31/31 PASS** (additional local developer regression).
- `.venv/Scripts/python.exe -B test_rt002_s1_routes.py`: первоначально **68/69 FAIL** (новые локальные peer send sites отсутствовали в точном inventory). После адресного обновления S1 **69/69 PASS**, gate PASS, 0 isolation violations, synthetic traffic only.
- `.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py`: первоначально **72/73 FAIL** из-за imports recovery внутри production. После переноса в `tools` S2 **73/73 PASS**, gate PASS, 0 isolation violations. Исходные негативные наблюдения не стирать.
- Проверка штатного личного хранилища через dry-run: `ELIGIBLE_FOR_MANUAL_RECOVERY`, 30 ledger events, 10 ledger attempts, 3 pinned versions. Не выполнялся apply.
- Сверка исходных четырёх JSON личных provider_sessions с вне-Git backup `%LOCALAPPDATA%/WebAlarmRecovery/H43_20261117_222742`: **4/4 SHA-256 MATCH** после всех чтений.
- Windows проверка на локальные процессы-владельцы завершилась CLEAR в момент запуска; это не является гарантией отсутствия remote owner.
- Ни один настоящий GigaChat OAuth/catalog/inference в этой доработке не выполнялся. Реальное `ACTIVE` не изменено. Существующие UNKNOWN ledger attempts не повторялись.
- Авторские сырые debug-логи поправки H43 и независимый локальный отчёт диагностики с путями домашнего ПК сохранены на HOME **без изменения**, но исключены из публичного GPT-коммита ради конфиденциальности; контрольные факты и ограничения зафиксированы в настоящем очищенном отчёте. Их файлы остаются локально незакоммиченными.

## Не закрыто

- `H43` остаётся `PARTIAL / NOT VERIFIED`. Реальная процедура изменения persistent account/grant до отдельного USER GO запрещена.
- Второй legacy ACTIVE в прежнем live_bootstrap остаётся; при фактической миграции требуется глобальная quiescence verification, включая все Workspace и другие хосты.
- Реальный GUI STANDARD (кнопка завершения, cleanup, версия UI F5, EVM, рестарт и физический GigaChat send) не проверен; проверялся только тестовый loopback.
- Independent GitHub Actions Windows с source SHA/run artifact, CI S1/S2 и физическое GUI — NOT RUN на момент этого отчёта. Все приведённые PASS являются локальными developer tests, не независимой приёмкой.
- Задача H43/история H-CODEX-000043 сохраняет авторский PARTIAL. БЛОК 1/1.1 не менять вручную. Финальный commit/публикация и пользовательский merge — отдельные gates.

**Перед реальным apply:** отдельное разрешение владельца на конкретные account files, закрытие всех старых экземпляров Web Alarm (не Codex/MCP), проверка ревизии/идентичностей/ledger, удержание OS-lock и maintenance window, readback, затем ручное восстановление STANDARD без автоматических платных Turn.
