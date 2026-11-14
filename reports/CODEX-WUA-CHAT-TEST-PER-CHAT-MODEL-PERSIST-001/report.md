# AUTHOR RESULT READY — TEST per-chat model persistence

**TASK ID:** `CODEX-WUA-CHAT-TEST-PER-CHAT-MODEL-PERSIST-001`  
**Дата:** 2026-11-15. Автор: Codex 007. Режим: STRICT OFFLINE.  
**Результат:** **AUTHOR TESTED / TECHNICAL PASS в назначенном OFFLINE scope**. Подтверждённый дефект TEST исправлен. Независимая проверка ChatGPT и личная GUI/F5-проверка владельца ещё не выполнены.  
**HISTORY ID:** назначается штатным finish; окончательный ID и readback находятся в `task_record.json` / `closeout.json`.

| Область | Статус |
|---|---|
| RED → GREEN: модель каждого TEST-чата | PASS |
| Настоящий TEST Python entrypoint, HTTP, cleanup | PASS, `--no-browser`, только синтетические данные |
| UI-код приложения в DOM oracle, включая F5 recreation | PASS |
| Физический CMD / браузер / F5 | NOT RUN автором |
| Независимый Windows GitHub Actions | NOT RUN / REVIEW PENDING |
| USER UX | PENDING |
| STANDARD / REAL safety | прежнее поведение / REAL HOLD сохранён |
| Реальные OAuth/API/LLM/paid, Git/GitHub | NOT RUN |
| Общий REAL release | прежний HOLD, этой задачей не пересматривается |

## Причина и воспроизведение RED

В TEST ветка `openPicker()` записывала выбор только в `chatTurn.model`, общем для страницы. В `loadChatModel()` долговременное чтение было разрешено только `chatTurn.ordinary`, а TEST не записывал model_ref в метаданные. Поэтому переключение чатов переносило выбор страницы, а F5 снова выбирал начальную модель. Результат выполненного Turn и сохранённая история при этом могли быть исправными.

До реализации сохранены:

- `red_ui`: первая отрицательная проверка переключения чатов.
- `red_ui_complete`: два отрицательных UI-сценария, включая отдельный F5.
- `red_http`: TEST POST `/model` вернул **405 вместо 200**, 1 FAIL / guard 0.

Первый UI oracle неявно открывал последний чат B. После явного выбора A сценарий повторён на SHA-проверенной исходной H35 UI-копии: A → B → A даёт **Ultra вместо Lightning**, F5 даёт **Pro вместо Lightning** в synthetic каталоге oracle. `red_ui_corrected_oracle` и окончательный `baseline_reviewed_final`: **2 ожидаемых FAIL**, Node exit 1. Контроль воспроизводим из пакета без доступа к TEMP backup; исходная UI-копия — `before_ui.py.txt`, её SHA совпадает с pre-edit snapshot. Рабочий UI во время контроля не подменяется на диске.

## Исправление и хранение

Выбор хранится в прежнем `.ultra/chats/<Chat ID>/metadata.json`, внутри зарегистрированного Workspace, в поле **`test_chat_model`**. Устойчивая область — Workspace identity + Chat ID; название чата/страницы не используется. Нет глобального EVM-selection, новой системы хранения или второго Chat Core.

TEST Ordinary Core выдаёт `chat_model_preferences=true`. GET/POST существующего per-chat пути `/ultra/chat/workspaces/<ws>/chats/<chat>/model` использует прежние read/write capabilities и shared writer, identity/Chat validation и `_replace_verified`. POST принимает только один допустимый model_ref из существующего enabled GigaChat registry. Метод ограничен exact OrdinaryCoreChatService с его TEMP scope.

Если поле отсутствует, GET возвращает первую доступную модель TEST-каталога и `persisted=false`, **без записи или миграции**. Неизвестное/повреждённое сохранённое значение даёт явный 409. Явный корректный выбор может восстановить настройку. Новая TEST-база не наследует чужую модель; данные одной TEST-сессии по-прежнему удаляются её штатным cleanup, а не превращаются в production storage.

В UI новая ветка включается только по TEST capability. При открытии чата модель читается с сервера; при выборе UI ждёт подтверждения записи. Ошибка не объявляется SUCCESS: показывается предупреждение, новая неподтверждённая модель не используется для нового запроса. Epoch/revision отбрасывают поздние GET/POST другого чата; прежний picker закрывается при смене TEST-контекста. При отсутствии подтверждённого выбора новая отправка блокируется, но проверка уже принятого Turn остаётся доступна.

Выбор следующей модели не меняет незавершённый Turn. Его исходные model_ref, текст и idempotency key сохраняются; UNKNOWN replay не выполняет новый fake send. Настройка не редактирует prepared snapshot, RAW, usage или результат завершённого Turn.

## Изменённые файлы

| Файл | Изменение |
|---|---|
| `web_alarm/ultra_chat.py` | TEST-only capability, per-chat metadata GET/POST, registry validation и явные ошибки |
| `web_alarm/ui.py` | TEST-only загрузка/сохранение модели, защита от поздних ответов и ложного SUCCESS |
| `test_web_alarm_ultra_chat_ui.js` | 8 новых UI-регрессий; прежние 61 сохранены |
| `test_rt002_s2_budget_policy.py` | только точный reviewed AST-pin `web_alarm.ultra_chat`, без изменения policy/graph semantics |
| `test_web_alarm_test_model_persist.py` — новый | 9 tests: HTTP/storage/UNKNOWN и существующий TEST profile Python entrypoint |

`web_alarm/server.py`, `ordinary_provider.py`, Model Registry, transport/admission/OAuth, Turn, ledger, RAW/Run Store, launcher/config/CMD, Tkinter и 165 protected files не изменены. STANDARD сохраняет свой прежний `/model` handler, поле `ordinary_chat_model`, единственный кандидат и REAL HOLD. Его файл не редактировался; новые UI-условия для STANDARD ложны. Тест также подтверждает, что STANDARD отклоняет Ultra и прямой TEST model method.

Старый Stage5 rollback profile не менялся. Его прежняя capability не включает новую настройку; исправление относится к принятому текущему `ordinary-core-offline` TEST. Имена постоянных CMD, красная маркировка, H31 guard и cleanup сохранены.

## Проверки и evidence

Python проверки используют ранний guard до production imports: external sockets/DNS, credential reads, Git/non-Python и production writes запрещены; используются TEMP и loopback. Настоящий OAuth дополнительно является tripwire в новых HTTP tests. Node исполняет поставляемый JS с синтетическим DOM и server-store oracle без внешней сети. S1/S2 запускаются собственными acceptance runners, не подменяются pytest skip.

| Набор | Фактический результат |
|---|---|
| `regression_final`: Core/H29–H35/TEST/Turn/RAW/usage/recovery/S3a/launcher/STD HOLD | **271 PASS + 274 subtests**, 0 FAIL/ERROR/SKIP; 9 exact expected negative guard probes, unexpected 0 |
| `final_new_tests`: окончательная общая база новых tests | **9 PASS + 8 subtests**, guard 0 |
| `ui_reviewed_final`: весь поставляемый UI | **69 PASS**, 0 FAIL/SKIP |
| `baseline_reviewed_final`: исходный UI против regression oracle | **2 expected RED**, Node exit 1; контроль PASS |
| `s1_final`: standalone source/wire census, имеющийся local historical RAW | **69 PASS**, isolation violations 0 |
| `s2_final`: standalone после exact reviewed pin | **73 PASS**, isolation violations 0 |
| `quality_final`: import graph + мутации всех пяти gates | **52 PASS + 7 subtests**, guard 0 |
| `profile_entry_final`: фактический Python entrypoint постоянного TEST | **1 PASS**, guard 0; дополнительно включён в окончательные 9 tests |

Строки частично пересекаются, их нельзя суммировать. Точные команды, exit codes, cases, collection/current node, stdout/stderr и guard events находятся в `evidence/*.result.json` и соседних файлах. `source_review.json` фиксирует hashes/сохранность; `gate_review.json` — единственный изменённый pin.

Новые сценарии проверяют: Lightning в A и Ultra в B, A/B/A, F5 recreation, raw metadata readback после нового экземпляра сервиса, два Workspace, новый TEST root даже с тем же Chat ID/названием, readonly default GET, неверный/повреждённый model_ref и восстановление, отказ записи, capabilities/scope, запоздалые GET/POST, блокировку отправки до чтения, selected-model send, pending/UNKNOWN replay, byte-identical RAW/usage/готовый Turn и независимые настройки ответа.

Внутренний штатный `web_alarm/ordinary_test_fixture.py --no-browser` проверен отдельным Python child: реальный локальный сервер, настоящие TEST API и каталог, два Chat/model, synthetic Turn и его replay/history, установленный child guard без срабатываний, Enter/EOF cleanup удаляет только собственный TEMP. **Это не запуск CMD или браузера.** Readback-факты: `final_new_tests.http_trace.json` и `final_new_tests.http_trace.profile.json`.

После добавления отдельного profile probe окончательная общая база новых tests пересобрана и выполнена 9/9. Широкая регрессия ранее уже покрыла 8 functional HTTP tests; Python/HTTP runtime после неё не менялся, дополнены только evidence/probe. Последняя правка закрытия TEST picker проверена полным shipped UI suite; baseline negative control повторён окончательным runner с source/test SHA.

## Первые FAIL не скрыты

Помимо исходного RED сохранены промежуточные результаты:

- `ui_first_green`: 62 PASS / 1 FAIL из-за начального B в fixture; явно задан A, затем тот же corrected oracle показал RED на baseline и GREEN на исправленном source.
- `focused_http`: 4 PASS / 3 FAIL, 3 subtests — tests ошибочно ожидали Pro как default. Фактический исходный TEST registry начинается с GigaChat 2; требования допускают начальную доступную модель. Oracle сверяет этот прежний каталог, а runtime/catalog не меняется ради теста.
- `s2_before_review`: 72/73, ожидаемый отказ полного AST-pin изменённого reviewed модуля. После source review заменён только этот pin; node/edges и все прочие gates/capsules сохранены. Negative quality controls обнаруживают модификации и неизвестных consumers.
- `focused_final`: collection ERROR — лишняя скобка при добавлении JSON evidence probe в test-файл. Исправлена только диагностическая запись; `focused_trace_final` 8 PASS +8 subtests, затем окончательные 9 PASS +8. Runtime это исправление не затрагивало.
- `picker_context_red`: дополнительный manual review подтвердил, что старое TEST-меню оставалось открытым после перехода к другому чату во время save. Закрытие picker ограничено новой TEST-веткой; окончательные 69 UI tests повторены после этой правки. Python/HTTP runtime после широкой регрессии не менялся.

## Source, сохранность, риски и NOT RUN

Опубликованная база в постановке — `main@cd0e4d943bb8d341baf07eef2a1d5c2a1619035a`. До изменений **16/16 H35 source fingerprints** совпали exact либо LF/CRLF. Git/HEAD/remote не читались; это source-content verification, не самостоятельное подтверждение remote SHA. Активный БЛОК 1 соответствует точному TASK ID. Применены №08/18/34/40/36/36.1/36.2, правила launcher, local handoff и запрет Git.

До правок создан backup `C:\Users\REX\AppData\Local\Temp\codex-test-model-persist-backup-70svzigh`: 6 файлов, SHA-256 verified. Он сохранён до независимой приёмки; старые копии H30–H35 не трогались. Метаданные/RAW/пользовательские Workspace для тестов не копировались. Изменения производились только в исходниках и synthetic TEMP. `.gitignore`/CI не менялись; пакет использует публикуемые текст/JSON extensions, Git check-ignore не выполнялся.

Риски/ограничения: новый TEST root намеренно пуст после завершения предыдущего процесса; concurrent windows следуют прежнему shared-writer контракту, явная более поздняя запись модели может заменить предыдущую. Новый model field не является provider authority или обещанием качества реальной модели. General REAL/provider/S3b/S3c/S9/S13a HOLD из H35 остаётся прежним; S1 local RAW PASS не является independent CI evidence.

NOT RUN: физические CMD/browser/F5 владельца, независимый GitHub Actions/публикация/коммит, production, реальные OAuth/API/GigaChat/paid, внешняя сеть. Проверки собственной задачи не дают USER UX ACCEPTED или независимый VERIFIED.

## MANUAL ENGINEERING REVIEW, DOC IMPACT и NEXT

Подробный [manual review](manual_review.md) прослеживает read/write/identity, ошибки, pending Turn, backward compatibility и поздние ответы. Отклонены глобальное EVM-selection и browser-only storage: они не обеспечивали бы требуемое per-chat долговременное состояние. Переиспользован существующий metadata writer; никакой архитектурный перенос/новый core не нужен.

DOC IMPACT для ChatGPT-координатора: после независимой проверки отметить устранение GUI-дефекта модели в TEST и обновить factual №34/40/review block при необходимости; не объявлять REAL readiness. Общие документы/журналы и БЛОКИ 2–4 автором не редактировались; только собственная штатная сдача через `finish`. Report после history registration immutable, окончательные hashes/readback — `manifest.json` / `closeout.json`.

**FOLLOWUP:** обычный чат без обязательного Workspace — отдельная будущая UX-задача; здесь не реализована.

**NEXT:** пользователь публикует пакет своим разрешённым порядком; ChatGPT независимо проверяет source/evidence на Windows. Затем владелец повторяет 5 действий из [GUI handoff](gui_handoff.md). Техническая проверка TEST HTTP/DOM/хранения завершена. Теперь нужна личная пользовательская проверка TEST: выбрать Lightning/Ultra в двух чатах, переключить их и нажать F5. Оценить также удобство, размеры, расположение и необходимость элементов; после отзыва отдельно зафиксировать замечания. До этого **USER UX PENDING**, существующий **REAL HOLD сохранён**.
