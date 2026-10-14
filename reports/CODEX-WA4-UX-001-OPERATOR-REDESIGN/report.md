# CODEX-WA4-UX-001-OPERATOR-REDESIGN — factual result

**RESULT READY / AWAITING INDEPENDENT VERIFICATION** · Codex 007 · 2026-10-14.

ARCH CLASS: Web Alarm Workspace / Operator UI / UX. PRIMARY 23; IMPLEMENTATION 24, WA-4.6, UX A/B/C; TEST 36/36.1/36.2. Независимый verifier — ChatGPT / WEB_07; визуальное принятие — пользователь. DONE / VERIFIED не присваивается.

## 1. Результат, scope и AMENDMENT

Рабочий UI переработан с сохранением тёмного оформления: проекты слева, полноценная карточка в центре, TASK выбранного Workspace справа. Новая постановка вводится в одно свободное поле. Пустая форма не создаёт TASK; непустой browser-local draft восстанавливается после reload. Только явная регистрация обращается к существующему POST /tasks; планирование и исполнение не запускаются.

Изменены:

- **web_alarm/ui.py** — единственный production-файл.
- **test_web_alarm_operator_ui.js** — актуализация и расширение проверок.
- **test_web_alarm_ui_ux.py** — два новых HTTP/интеграционных теста.
- Собственная папка reports/CODEX-WA4-UX-001-OPERATOR-REDESIGN/ и персональная карточка при заключительной ротации.

Прежние Python UI/operator/launcher tests сохранены без изменений. Backend, WA4-R, Ultra, общие runners, CI, launcher и общие документы не изменялись. Git/GitHub, включая read-only и альтернативные интерфейсы, не использовались.

**AMENDMENT:** пользователь отдельно разрешил адресное изменение test_web_alarm_operator_ui.js в ответ на вопрос об устаревших проверках Name/Goal/RAW и объединённого навигатора. Первоначальный БЛОК 1 во время исполнения не изменялся; разрешение не расширялось на backend или другие файлы.

Пройден маршрут 08 → общий 000 → персональная постановка → 34 → 18 → 01 → 23/24/25 → 36/36.1/36.2. Код/API/тесты сверены адресно; владение файлами проверено перед записью. Внешнее изменение персональной карточки Claude сохранено, его работа не затронута. Разрешённый простой локальный helper оказался недоступен из-за модели/account; окончательные исследования и решения выполнены основным агентом.

## 2. Требования → реализация

| Требование | Фактический результат |
|---|---|
| UX-A: три независимые области | Desktop: 230 px Workspace / гибкий main / 286 px TASK, собственный overflow каждой области. Старый смешанный navigator удалён после переноса функций. |
| Проекты | Список, выделение выбранного, добавление через прежний API, путь в tooltip и раскрываемых свойствах. Длинные пути постоянно не показаны. |
| TASK выбранного проекта | Active/planned/recovery и completed из серверного каталога, фильтр workspace_id, название и фактическое состояние. Локальный draft отдельно подписан. |
| Полноценная карточка | RAW/goal, этапы по порядку плана, текущий этап/операция, verified progress, recovery, NEXT, reports/evidence/диагностика. Human REPORT доступен внутри соответствующего этапа. |
| UX-B: понятность | RU labels известных состояний, исходный enum в tooltip. DONE отделён от VERIFIED; UNKNOWN не превращается в FAILED. Новых машинных состояний нет. |
| Соединение | Настоящий GET /status с сигнатурой web_alarm_server. Доступность сервера отделена от доступности каталога. Aging 45 s без свежего подтверждения. |
| Loading/empty/error | Явные ожидание, пустые списки, отсутствие плана, недоступность API, recovery. Повреждённый/частично отрисованный снимок скрыт, экспорт блокируется. |
| Адаптивность | До 850 px проекты/TASK раскрываются над основным содержимым, без перекрытия текста. Выбор новой карточки возвращает начало чтения; refresh сохраняет позицию. |
| UX-C: новая постановка | Плюс открывает один textarea, без обязательных Name/Goal/ID/этапов. Пустая форма уходит без предупреждения и server persistence. |
| Защита непустого текста | Автосохранение точного текста, reload, различение RAM/local draft/неизвестной регистрации/серверного подтверждения. Межвкладочный Web Lock. |
| Явная регистрация | Серверный task_id, title из первой строки, goal/raw из нормализованного source. Нет planner, операций или мутаций физического проекта. |
| Прежние гарантии | GET-only просмотр; свежесть и согласованность контекста/NEXT; защита от позднего ответа другой TASK/Workspace; immutable RAW/evidence; безопасный textContent. |

NEXT SAFE ACTION сохраняет точную серверную формулировку, даже английскую. Неизвестные/непереведённые технические значения остаются исходными, например NO_MICROTASK в списке. Основная карточка объясняет отсутствие плана по-русски, без искусственного прогресса 0/0.

## 3. Решения по черновику и регистрации

Черновик — browser-local запись, **не TASK и не backend lifecycle**. Ключ учитывает origin, workspace_id и workspace_root. Другой порт/профиль или очистка site data могут сделать запись недоступной; UI предлагает отдельно сохранять важный текст. Это не зашифрованный vault и не серверный backup.

Редактор получает exclusive Web Lock и повторно читает запись внутри захваченного lock: другая вкладка могла изменить её после первого чтения. При занятом lock доступны чтение/копирование. Отсутствие Web Locks, ошибка доступа к storage или повреждённая запись не маскируются под сохранение: редактор/регистрация блокируются, исходная запись не перезаписывается. Для редактирования нужен совместимый браузер, например Chrome/Edge на localhost.

Каждый input сохраняет точный текст синхронно. Ошибка quota/storage оставляет предупреждение и dirty-флаг; уход требует подтверждения, закрытие страницы защищено beforeunload. Refresh не переписывает textarea/каретку. Удаление локального draft подтверждается, не вызывает DELETE TASK и не затрагивает серверные evidence.

**До POST обязательно сохраняется pending registration.** Если storage отказал, POST отсутствует. Любой неподтверждённый outcome, включая HTTP error или некорректный ack, сохраняет текст и блокирует повтор/удаление. Reload делает оставшийся pending явно неизвестным. Auto-retry нет. Это консервативно: повтор может блокироваться и после фактического отказа сервера, поскольку отсутствие ответа не доказывает отсутствие созданной TASK.

Ack проверяется по task_id, workspace_id, title, goal и raw_task. Поздний ответ не очищает draft другого Workspace и не возвращает пользователя в чужую карточку. При уходе во время POST исходная pending-запись может остаться неизвестной даже после положительного ответа; нужна сверка. Ошибка локальной очистки после ack также не разрешает повторную отправку.

При регистрации используется нормализация существующего API — внешние пробелы обрезаются; это раскрыто в UI. Draft до регистрации хранится точно. Title — первые 120 Unicode codepoints первой строки, goal — полный нормализованный source. Это адаптация существующего контракта, не автоматическое понимание цели.

## 4. MANUAL ENGINEERING REVIEW

Отдельная ревизия проведена после реализации, сверх PASS автотестов:

1. **Authority:** UI читает Projection/operator view, не угадывает текущую операцию и не заменяет server NEXT рекомендацией отчёта. Контекст/NEXT экспортируются только из fresh/coherent snapshot. Отсутствие плана не считается доказанным прогрессом.
2. **Workspace/async:** epoch и task/workspace identity отбрасывают поздние ответы. Draft связан с ID/root. Потеря подтверждения Workspace блокирует регистрацию, сохраняя текст.
3. **Lock/resource:** проверено окно read/acquire; lock освобождается при уходе; поздний callback не получает новый editor epoch. Refresh не сбрасывает dirty text, каретку или чтение.
4. **Неопределённая запись:** durable pending и отсутствие auto-retry важнее внешне гладкого перехода. LocalStorage и совпадение текста в каталоге не названы authoritative receipt.
5. **Невалидные API:** обнаружены четыре дополнительных дефекта — утверждение пустого плана при incoherent snapshot; сохранение online при null health; принятие нечислового progress/неboolean coherence; сохранение частично отрисованного снимка для экспорта после render exception. Сначала добавлены красные тесты, затем исправлены порядок вывода, health guard, типы/границы и публикация view.data только после успешного render.
6. **Текст/мутации:** source/REPORT/errors используют textContent, HTML не исполняется. Просмотр не запускает execution/recovery/rebuild. Проверены реальные bytes fixture, отсутствие операций при регистрации и server DELETE при удалении draft.
7. **Побочные эффекты:** backend/state machine/полномочия неизменны. Web Locks ограничивает совместимость старых браузеров; безопасный read/copy fallback явный. Browser storage не даёт межустройственной/межпортовой долговечности.

Это разбор исполнителя, не независимая приёмка. Не заявляется schema validation любого будущего API или защита browser storage от очистки внешними средствами.

## 5. Тесты и доказательность

Windows 10; Python 3.12.10 x64; Node v22.20.0; CWD M:\GitHub\ag_llm.

Raw outputs/fixtures сохранены в отдельном TEMP:
C:\Users\REX\AppData\Local\Temp\codex-wa4ux001-md3m9ccc

checks.json содержит счётчики, exit, SHA-256 stdout/results, полный финальный test ID/status list и source pins. first-reds.json — буквальные excerpts первоначальных красных assertions; полные исходные logs остаются в TEMP. source-evidence.zip — baseline, difflib patches и версии первого full. Ни один исходный красный продуктовый прогон не заменён PASS.

| Прогон | PASS | FAIL | ERROR | SKIP | Примечание |
|---|---:|---:|---:|---:|---|
| Baseline Python/HTTP | 34 | 0 | 0 | 0 | До изменений |
| Baseline JS | 23 | 0 | 0 | 0 | До изменений |
| Legacy JS после нового UI | 17 | 6 | 0 | 0 | Старые layout/form/label assertions; обновлены по AMENDMENT |
| Draft до lock repair | 43 | 1 | 0 | 0 | Реальный read/acquire gap |
| Visual polish до repair | 47 | 2 | 0 | 0 | Scroll новой карточки, отсутствие плана |
| Adversarial до финального repair | 49 | 4 | 0 | 0 | Четыре API-сценария из §4 |
| **Финальный JS** | **53** | **0** | **0** | **0** | cancel/todo=0 |
| **Финальный focused Python/HTTP** | **36** | **0** | **0** | **0** | 42.290 s, exit 0 |
| Первый full, до поздних UI исправлений | 770 | 0 | 0 | 1 | 696.185 s, точная версия сохранена |
| **Финальный full Web Alarm** | **770** | **0** | **0** | **1** | 771 IDs; 711.164 s; exit 0 |

SKIP: test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed — symlink creation is not permitted here. Это ограничение Windows permissions, не PASS. Focused 36 входят в full 771; их нельзя складывать как уникальные тесты. Full повторён из-за последующих доказанных исправлений, не ради дополнительного зелёного результата.

Python collection **769 → 771**, удалённых IDs нет. Два новых OperatorUxTests проверяют реальный HTTP/HTML контракт областей/одного поля и большой Unicode/HTML REPORT (~60 тыс. символов), связанный только со своим этапом, с контролем неизменности fixture.

JS **23 → 53**: 21 исходное имя сохранено, 2 переименованы под явную регистрацию и отдельные adaptive panels, добавлены 30 сценариев. Сохранены исходные freshness/coherence/XSS/async/unknown POST/error/mutation guarantees. Добавлены storage/quota/corruption/reload/locks/late response/Workspace removal/dirty draft/no-plan/render failure проверки. Выполняется реальный script из ui.py.

**Negative controls: 4/4 PASS.** In-memory mutants снимают under-lock reread, durable-pending guard, свежесть копирования NEXT и запрет повтора unknown registration. Каждый вызвал ровно один ожидаемый assertion FAIL и exit 1; trigger достигнут. Это доказательство чувствительности oracle, не ошибки финального продукта. Production-файлы не мутировались. Selectors, excerpts и финальные source SHA — quality.json.

Команды финальных прогонов, output directories были новыми:

~~~powershell
$env:PYTHONUTF8='1'
$runRoot='C:\Users\REX\AppData\Local\Temp\codex-wa4ux001-md3m9ccc'
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-UX-001-OPERATOR-REDESIGN --output "$runRoot\focused-final-reviewed" test_web_alarm_ui test_web_alarm_operator_ui test_web_alarm_ui_ux test_web_alarm_ui_launcher
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-UX-001-OPERATOR-REDESIGN --output "$runRoot\full-final-reviewed" all
node --test test_web_alarm_operator_ui.js
node --check "$runRoot\client-reviewed.js"
node reports\CODEX-WA4-UX-001-OPERATOR-REDESIGN\quality_controls.js "$runRoot\quality-final-reviewed"
~~~

Для независимого повторения выбрать новый TEMP output. quality_controls.js — адресная вспомогательная проверка собственного отчёта, не изменение общего runner/CI. Python isolation guard: **0 violations**. Browser guard log пустой. Внешние HTTP/Git/реальные проектные мутации не требовались; loopback и disposable fixture writes разрешены.

Первый запуск вспомогательного demo упал из-за неверного helper method report_microtask; исправлен через существующий API dispatch в новом fixture. Отдельный исходный stderr tooling-ошибки не сохранён; она не засчитана как продуктовый PASS/FAIL.

## 6. Browser evidence и открытие результата

Проверен настоящий Codex In-app Browser с локальным сервером. Полученный /ui byte-identical INDEX_HTML окончательной версии. Финальные screenshots привязаны к source SHA в browser.json. Временный viewport override снят; console errors не обнаружены.

- Desktop **1440×1000**: x=0/230/1154, widths=230/924/286, height=927, overflowY=auto. Main длиннее viewport; sidebars имеют независимую прокрутку.
- Узкое окно **390×844**: document scrollWidth=375, textarea=317 px, горизонтального переполнения нет. Реальный reload восстановил draft. Редактирование начала текста сохраняло caret=8.
- Human REPORT раскрыт в своём этапе: mainScroll=418, left/rightScroll=0. Большой REPORT и HTML как данные дополнительно проверены HTTP/JS.
- Два Workspace и разные TASK проверены. Просмотры/refresh/drafts/переключения сохранили исходные **70 файлов** byte-identical.
- Явная регистрация task_9ff21ec520af4667bb40aa5939795b9b: PLANNED, plan_ids=[], operations отсутствуют. Добавлены только task.json/task.md/plan.json, существующие файлы и физические проекты неизменны.
- После fresh-process reopen и финальных проверок все **73 файла** byte-identical.
- Настоящая остановка собственного helper: «Нет свежего соединения», snapshot stale, копирование NEXT/контекста disabled. Повторный запуск того же fixture восстановил соединение.

PNG: desktop-recovery.png, narrow-draft.png, desktop-offline.png. Факты, source hashes, raw-tree hashes и регистрация — browser.json.

**Открыть демо: http://127.0.0.1:53833/**. Это disposable TEMP fixture, не live Workspace. На момент сдачи helper PID **16072**; root сохранён в browser.json. Для обычного запуска доступен неизменённый **M:\GitHub\ag_llm\Start_WebAlarm_Demo.cmd**, создающий своё окружение/порт. На другом порту прежний browser draft автоматически не доступен.

## 7. Ограничения / BLOCKED / PROPOSAL

| Возможность | Необходимое решение |
|---|---|
| Unknown POST создания | **BLOCKED / PROPOSAL:** request identity/idempotency и authoritative lookup/receipt API. Пока текст защищён, повтор блокирован, нужна ручная сверка; совпадение source в каталоге не считается receipt. |
| Серверные drafts | **PROPOSAL:** отдельные storage/ownership/recovery/retention contracts. Local draft их не подменяет. |
| Planner | **BLOCKED:** отсутствует API/полномочие этой задачи. Регистрация не создаёт этапы. |
| Нативный folder picker / Explorer | **PROPOSAL:** native bridge, проверка абсолютного root и подтверждение. Браузерный picker не даёт требуемого trusted path; пока ручной ввод через прежний API. |
| Rename display label | **PROPOSAL:** серверный mutable metadata contract без изменения ID/immutable RAW/evidence. |
| Archive/delete/retention | **PROPOSAL:** lifecycle/ownership/recovery/history policy и подтверждение. Физического удаления TASK UI не делает. |
| PAUSED и новые права мутаций | **OUT OF SCOPE:** state machine и authority не изменены. |
| Передача агенту | Есть только явное копирование свежего coherent source+plan+reports. Автодоставка/запуск требуют transport/authority contract. |

Локальная регрессия не закрывает исторические F1–F3, STRICT или PR findings. CI, Git revision equivalence, другие ОС/browser engines и человеческая визуальная приёмка **NOT RUN**. DOM adapter не заменяет настоящий browser; локальный browser не заменяет межбраузерный аудит.

## 8. DOC IMPACT / SHARED DOC DELTA

Общие документы **не редактировались**. Предлагаемая дельта после независимой приёмки:

- **23:** три области UI; browser-local draft origin/ID/root и Web Locks; явная регистрация через прежний API; неизменная Projection/NEXT authority. Unknown-create обозначить незакрытым backend contract.
- **24, WA-4.6 A/B/C:** реализованная ограниченная итерация и BLOCKED/PROPOSAL. Раннее предположение о пустой persistent TASK уступает UX-C; историю пересмотра не стирать.
- **25:** factual запись TASK с pins, 770/0/0/1 + JS53 + controls4, browser evidence, независимой/визуальной приёмкой в ожидании.
- **36.2:** два новых Python selectors и расширенные JS draft/storage/async/invalid API scenarios, два переименования и negative controls. Общие 36/runner/CI в этой задаче менять не требуется.
- **01/05/06/34 и общий 000:** краткое текущее состояние UI, статус, ссылка на отчёт и согласованный NEXT после verifier. Нового канонического документа/Obsidian node не нужно.
- **Персональный 000:** исходная полная постановка → БЛОК 2, factual result → БЛОК 3, затем БЛОК 1 → ожидание. Прежние БЛОКИ 2–3 сохраняются дословно в fenced архиве; проверка rotation.json.

~~~text
DOC IMPACT: YES
CURRENT STATE IMPACT: YES
ARCHITECTURE IMPACT: YES — UI/browser layer, backend authority unchanged
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: YES — task handoff/status; no new canonical route
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 23; implementation 24; audit 25; test catalog 36.2
AFFECTED DOCUMENTS: personal 000 actual; 23/24/25/36.2/01/05/06/34/global 000 proposed only
CONTRADICTION CHECK: REQUIRED; UX-C priority applied; proposals are not accepted rules
LOSS CHECK: PASS — exact assignment and previous blocks preserved; rotation.json
~~~

## 9. Source pins и передача

~~~text
web_alarm/ui.py
eb4b54035664560897aba2d1a8cea2420fa78fbe2c250ee24e7d449e305cf420
test_web_alarm_operator_ui.js
5f25b1763ef43a07f12fa71c32d3f439d458013b78a9dd0360d777cdbca1dc0e
test_web_alarm_ui_ux.py
ef066644a793c9023363f75d2546d1f350e85ad36035f58db74869a95d51299b
~~~

versions.json фиксирует baseline/final hashes, добавленные selectors и scope. checks.json связывает Python runs с их source. Финальные focused/full/JS/controls соответствуют этим hashes. Первый full привязан к сохранённой предыдущей версии, не выдан за проверку поздних исправлений.

**NEXT SAFE ACTION:** ChatGPT / WEB_07 независимо проверяет diff, oracles, raw evidence и ограничения; пользователь оценивает демо. После решения координатор синхронизирует shared docs и отдельно определяет необходимость backend request-identity/draft contract. Codex следующую стадию не начинает и ничего не публикует.
