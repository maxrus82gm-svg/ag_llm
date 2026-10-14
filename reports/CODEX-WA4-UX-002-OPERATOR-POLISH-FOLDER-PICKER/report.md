# CODEX-WA4-UX-002-OPERATOR-POLISH-FOLDER-PICKER

2026-10-14 · Codex 007 · Windows local implementation.

**RESULT READY / AWAITING INDEPENDENT VERIFICATION** — результат самопроверки, не DONE/VERIFIED. Независимая техническая приёмка: ChatGPT; визуальная и native-dialog приёмка: пользователь. Финальные машинные результаты и pins находятся в `checks.json` / `versions.json`; прежние попытки сохранены отдельно.

## 1. Результат и полномочия

Исправлены уведомления регистрации и реализован настоящий opt-in Windows folder picker через ограниченный по времени Python/Tk helper. Выбор только заполняет поле пути; отдельное подтверждение регистрации Workspace сохранено. Реальный native SELECTED и подтверждённый CANCELLED HTTP-ответ ещё требуют человеческой приёмки: mock PASS не считается их визуальным доказательством.

Исходный БЛОК 1 не менялся во время реализации. **AMENDMENT:** пользователь отдельно ответил «Разрешаю указанные четыре файла и контракт» на техническое предложение `folder-picker-proposal.md`. Это разрешило только picker transport в `web_alarm/server.py`, новый `web_alarm/folder_picker.py`, новый `test_web_alarm_folder_picker.py` и включение в `wa4o_ui_demo.py`, дополнительно к исходному UI/test scope. Это не разрешение менять lifecycle, Registry authority, Ultra, Git/GitHub или CI.

Обязательный маршрут регламентов и профиля тестирования пройден. Simple local helper был недоступен; работу и решения выполнил основной агент. Git/GitHub не использовались, история/commit SHA самостоятельно не читались; исходные версии указаны локальными SHA-256. Соседняя карточка Claude изменилась параллельно и не откатывалась.

## 2. Изменённые файлы

| Файл | Изменение |
|---|---|
| `web_alarm/ui.py` | Один слот операции наверху main; точные severity/сообщения; picker controls, capabilities, защищённый запрос, защита позднего ответа/формы; корректное восстановление freshness-плашки редактора. |
| `web_alarm/server.py` | Два защищённых picker routes, opt-in конфигурация/CLI и frame denial HTML. Существующий WebAlarmApi.dispatch не менялся. |
| `web_alarm/folder_picker.py` — новый | Windows-only native dialog в bounded helper; singleflight, строгая проверка результата, отсутствие регистрации/проектных записей. |
| `wa4o_ui_demo.py` | Только явное включение picker в demo. Launcher/BAT не менялись. |
| `test_web_alarm_operator_ui.js` | Прежние 57 сценариев сохранены, добавлены 20; проверяется настоящий shipped script в offline DOM adapter. Один старый mock регистрации дополнен полноценным acknowledgement без ослабления защиты. |
| `test_web_alarm_ui_ux.py` | Прежние два теста сохранены; добавлен real-HTTP контроль единственного центрального notice slot и неизменности raw fixture. |
| `test_web_alarm_folder_picker.py` — новый | 16 HTTP/security/native-worker tests, включая настоящий subprocess timeout/reap на безопасном sleep helper. Native GUI в регрессии подменён. |

Дополнительные записи: собственные review/evidence в этой папке и регламентная ротация собственной карточки. Производственные модули authority/state machine/executor/Registry, WA4-R, Ultra, общие документы, существующие runners/CI не исправлялись.

## 3. UX-002-A: семантика уведомлений

- Успех: зелёный `role=status`, например `Workspace «123» успешно зарегистрирован.` / `TASK «…» успешно зарегистрирована.`; нет утверждения о запуске исполнения.
- Pending заменяется результатом в одном элементе, список не накапливается. Элемент находится в потоке центральной области перед карточками, не перекрывает их.
- Подтверждённый отказ сервера 4xx: error; 5xx, потеря ответа, некорректный acknowledgement: unknown warning. Успешный GET не превращает unknown в успех.
- Факт подтверждённой регистрации сохраняется при неудачном последующем GET. Health и ошибки чтения показываются независимо. Завершённое rejected notice очищается успешным обновлением каталога.
- TASK durable pending до POST, защита unknown от повторной отправки, исходный текст, Web Locks и Workspace ID/root binding сохранены. Формы и поздние ответы различаются по generation.
- При восстановлении каталога в режиме draft старое сообщение о недоступных данных очищается через `setFresh(false)`: это не объявляет TASK-снимок свежим и не разрешает копировать NEXT/context. Unknown registration warning и защита текста сохраняются.

## 4. UX-002-B: точный native контракт

| Условие / запрос | Результат |
|---|---|
| Общий сервер без opt-in / не Windows / отсутствует Tk | capability unavailable, ручной путь остаётся. |
| Demo / CLI `--enable-folder-picker` | Возможность включена явно; проверка availability не открывает диалог. |
| `GET /ui/capabilities` | Доступность, причина, process-local token только для разрешённого loopback origin. |
| `POST /ui/pick-workspace-folder` | Пустой JSON object, точный same-origin Origin и `X-WebAlarm-Folder-Token`; клиент не передаёт путь/команду. |
| Выбран каталог | `SELECTED` + существующий абсолютный canonical directory; UI заполняет input без регистрации. |
| Отмена | `CANCELLED`, без пути и изменения прежнего input. |
| Некорректный запрос / origin | 400/403/405/415 до helper. |
| Занят / timeout / недоступность | 409 / 504 / 503; честное сообщение, ручная альтернатива, lock освобождается. |

До helper проверяются loopback peer и фактический bind, единственный точный Host с портом, Origin/Fetch Metadata, token (включая запрет не-ASCII), Content-Length/JSON/media/query. CORS grants отсутствуют; HTML запрещено помещать во frame. Token только в памяти, не storage/log. Изменение этих routes не является защитой всех исторических API.

Helper запускается списком фиксированных аргументов без shell. Таймаут сервера ≤120 s, browser timeout 125 s; subprocess.run убивает/reaps собственного ребёнка. Native worker имеет дополнительный watchdog 125 s, но аварийное исчезновение родителя независимо не тестировалось. В выбранный проект собственный код ничего не записывает. Возможные действия пользователя внутри Windows Shell и его OS/cache effects находятся вне этого обещания.

Late selection не заменяет вручную изменённый путь, закрытую/новую форму; во время picker регистрация заблокирована. После restart/403 capability обновляется без автоматического повторного открытия. Registry повторно применяет существующие проверки при отдельной регистрации.

## 5. Тестовая доказательность

Итоговые числа собраны из сохранённых машинных результатов. Не суммировать focused и full как уникальные тесты. Исторические FAIL не стёрты и не переименованы в PASS.

| Попытка / версия | PASS | FAIL | ERROR | SKIP | Isolation |
|---|---:|---:|---:|---:|---:|
| Python picker-first | 14 | 1 | 0 | 0 | 1 |
| Python picker-fixed | 15 | 0 | 0 | 0 | 0 |
| Python focused | 52 | 0 | 0 | 0 | 0 |
| Python full | 786 | 0 | 0 | 1 | 0 |
| Python header-red | 0 | 1 | 0 | 0 | 0 |
| Python focused-final | 53 | 0 | 0 | 0 | 0 |
| Python full-final | 787 | 0 | 0 | 1 | 0 |
| Python focused-release | 53 | 0 | 0 | 0 | 0 |
| Python full-release | 787 | 0 | 0 | 1 | 0 |
| Node baseline-js | 57 | 0 | 0 | 0 | offline adapter |
| Node notices-red-js | 57 | 10 | 0 | 0 | offline adapter |
| Node notices-green-js | 67 | 0 | 0 | 0 | offline adapter |
| Node picker-ui-red | 67 | 8 | 0 | 0 | offline adapter |
| Node picker-ui-green | 75 | 0 | 0 | 0 | offline adapter |
| Node reviewed-js | 77 | 0 | 0 | 0 | offline adapter |
| Node recovery-banner-red | 0 | 1 | 0 | 0 | offline adapter |
| Node release-js | 77 | 0 | 0 | 0 | offline adapter |
| Quality UI final (10 ожидаемых inner FAIL) | 10 outer | 0 outer | 0 | 0 | no network |
| Quality native final (1 ожидаемый inner FAIL) | 1 outer | 0 outer | 0 | 0 | 0 |
| Quality UI повтор, занятый TEMP wrapper | 0 | 0 | 1 setup | 0 | не запускался |

**Финальная версия: 53 focused PASS; 788 full IDs = 787 PASS / 0 FAIL / 0 ERROR / 1 SKIP; isolation 0; JavaScript 77 PASS; quality 11/11 outer PASS.** SKIP: `test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed` — symlink creation is not permitted here. Последний полный прогон повторён после реальной browser-находки freshness; предыдущие два не выдаются за результаты другой версии.

Сохранены исходные красные проверки уведомлений (57 PASS / 10 FAIL), отсутствовавшего picker UI (67 PASS / 8 FAIL), guard DEVNULL (14 PASS / 1 FAIL + одна зарегистрированная isolation violation), не-ASCII capability (один FAIL: 500 вместо 403), а также адресная проверка stale freshness после offline/recovery. Исправления не ослабляют assertions/guard.

Negative controls меняют код только в отдельной временной копии или памяти: прежние draft/lock/pending/stale-NEXT controls, UX-001 binding/incoherent timeline, новые severity/late-selection/header-merge и Origin denial. **Каждый положительный outer результат означает ожидаемый внутренний assertion FAIL на нужном trigger**, а не прохождение сломанного кода. Подробности: `quality_controls.js`, `quality_native.py`, JSON evidence.

Python-регрессии запускаются неизменённым `wa4a_acceptance.py` под guard: запрет Git, внешних HTTP и записей за пределами disposable TEMP. Обычный production picker включался отдельно только в изолированном browser demo. Статические проверки compile/Node --check не заменяют runtime tests.

## 6. Команды воспроизведения

Рабочий каталог `M:\GitHub\ag_llm`, Windows Python 3.12.10, Node v22.20.0, Tcl/Tk 8.6. Новый уникальный `$out` должен находиться в TEMP и не существовать до запуска; команды не требуют Git или live storage.

```powershell
$env:PYTHONUTF8='1'
node --test test_web_alarm_operator_ui.js
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-UX-002-OPERATOR-POLISH-FOLDER-PICKER --output "$out\focused" test_web_alarm_ui test_web_alarm_operator_ui test_web_alarm_ui_ux test_web_alarm_ui_launcher test_web_alarm_folder_picker
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-UX-002-OPERATOR-POLISH-FOLDER-PICKER --output "$out\all" all
node reports\CODEX-WA4-UX-002-OPERATOR-POLISH-FOLDER-PICKER\quality_controls.js "$out\quality-ui"
.venv\Scripts\python.exe -B -X utf8 reports\CODEX-WA4-UX-002-OPERATOR-POLISH-FOLDER-PICKER\quality_native.py "$out\quality-native"
```

## 7. Browser и raw-state evidence

Только disposable fixture в `C:\Users\REX\AppData\Local\Temp\codex-wa4ux002-4o4x02db\demo`, loopback `http://127.0.0.1:58871/`; пользовательские `123` и `Чат_pro` не использовались.

1. Настоящая регистрация TASK через UI создала ровно `task.json`, `task.md`, `plan.json` для `task_cdef9893d73640f18c2f463a3e6bf629`. Статус PLANNED, список этапов пуст, операций нет. Все 70 прежних файлов byte-identical; Workspace Registry и проектные config bytes не менялись. Центральный зелёный результат не стал красным после refresh: `task-success.png`, DOM JSON.
2. Настоящий offline POST после остановки только собственного demo: warning unknown, исходный текст сохранён, повтор/удаление заблокированы. После restart каталоги снова доступны, warning и защита остаются; новых серверных TASK/файлов нет. `unknown-operation.png` и recovery DOM/raw hashes. Это проверка transport uncertainty, не утверждение о настоящем durable server commit до потери ответа — последний отдельно покрыт прежними lost-response regression tests.
3. Настоящий picker helper запускался собственным PID с `--native-worker`; после 120 s получен `folder_picker_timeout`, helper исчез, ручной путь и fixture bytes сохранились. `folder-picker-timeout.png`. Пользователь отдельно сообщил «Увидел диалог и нажал Отмена». Коррелированного CANCELLED HTTP response нет: **USER REPORTED appearance/cancel**, **OBSERVED timeout**, настоящий SELECTED **NOT RUN**.
4. Встроенный браузер не показал/не позволил обработать штатный Workspace window.confirm; пользователь подтвердил «Окна подтверждения не видно». Тестовая вкладка закрыта без регистрации; подтверждение не обходилось. Happy path Workspace, выбор/отмена и confirmation gate проверены автоматическими mocks/HTTP, но не объявлены новым полным browser PASS.

Временный viewport сброшен. `task-success.png`, `unknown-operation.png` и native-timeout capture предшествуют последней адресной freshness-коррекции; `recovered-draft.png` и final recovery DOM сняты с финального UI. Console error/warn inspection после сценариев не обнаружил uncaught JS ошибок. `browser.json` содержит детализацию и hashes; реальные native и визуальные сценарии не подменены DOM adapter.

## 8. Инженерная ревизия и ограничения

Полная ручная ревизия: `manual-review.md`. Дополнительно к плановым тестам найдены и исправлены не-ASCII token (500 → 403), поздний Workspace acknowledgement для повторно открытой формы, renewal capability без auto retry и stale freshness редактора при восстановлении связи.

Остаточные ограничения: реальные SELECTED/CANCELLED outcomes и расположение системного окна требуют человеческой приёмки; IAB confirm ограничен инструментом; noninteractive desktop может вернуть unavailable; watchdog при hard-crash не испытан; symlink test SKIP по правам Windows. Process-local singleflight не синхронизирует разные независимо запущенные серверы. Capability защищает от чужих origin, но не от same-origin XSS или злонамеренного локального процесса. Полноценное планирование/исполнение/recovery UI здесь не добавлялось.

## 9. SHARED DOC DELTA — только предложение координатору

После независимого решения предложены: 24 — bounded operation notices/native path/confirmation/manual fallback; 23/25 — два opt-in transport routes, trust boundary, availability, Windows/runtime и launcher contract; 36.2 — точные новые selectors и quality controls, разделение mock/HTTP/native/user evidence, единственный SKIP. По принятому verdict координатор обновляет 01/05/06/34 и общий 000 адресными указателями/статусами, если это требуется действующим маршрутом. Новый канонический документ/Rule-ID не создавался; DOC-GIT-01 не меняется. Общие документы самостоятельно не редактировались.

## 10. Handoff / NEXT

Source pins, команды, test IDs и исходные FAIL сохранены переносимым `evidence.zip`; `source-changes.diff` получен сравнением локальных bytes без Git. `manifest.json` проверяет пакет; `rotation.json` — дословность постановки и прежних БЛОКОВ 2–3. Сырые логи/fixtures дополнительно остаются в TEMP; report не зависит только от временных путей.

ChatGPT должен независимо сверить scope AMENDMENT, pins, изменения, invariant tests/negative controls и сохранность карточки. Пользователь может запустить `Start_WebAlarm_Demo.cmd`, проверить зелёный успех регистрации, кнопку «Обзор…» → существующий disposable каталог → подстановку, отмену без изменения поля и отдельное подтверждение Workspace. Если новое окно подтверждения не видно в IAB, проверить штатный браузер Chrome/Edge; защиту не отключать. До приёмки не присваивать DONE/VERIFIED, не коммитить/пушить от имени агента и не запускать следующие стадии.
