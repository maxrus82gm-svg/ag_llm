# CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001 — итоговый отчёт

**Статус: RESULT READY / AUTHOR OFFLINE TESTS PASS / AWAITING INDEPENDENT VERIFICATION.**

Исполнитель: Codex 007, текущая основная модель GPT-6.1 Sol. Дата: 09.11.2026. ARCH CLASS: Ultra Chat / shared core integration; применены №36.1/36.3 и существующие Web HTTP/UI selectors. Субагенты не использовались.

## Основание и исходная база

Пользователь прямо запустил одноимённую задачу из БЛОКА 1: CHAT FIRST, минимальное соединение существующего Web Chat с Ultra Core, STRICT OFFLINE. Это отдельное новое инженерное поручение; прежний запрет ротации аналитической задачи Астры на данную TASK не переносится. Для текущей задачи явно запрошена штатная сдача с HISTORY ID.

Assigned base: `main@c9fe58e87a64d553a527f510c34405eef4bfcacd`, №565. Git/GitHub не использовались: в TASK они запрещены. Локальные CHAT FIRST редакции №08/20/34/37/40 и сохранённый координаторский report №565 соответствуют назначению; все 13 файлов кода, ранее закреплённых независимым аналитическим манифестом на базе №563, совпали по SHA-256. Документный переход №565 прямо сообщает отсутствие изменений кода. Несоответствий локального source поручению не обнаружено; **точный Git HEAD независимо не подтверждён**, источником ревизии остаются назначение и локальные документные свидетельства. Самостоятельной проверки опубликованного SHA не заявляется.

До изменений сохранены 289 контрольных хешей существующих корневых Python/JS, web_alarm, tools и документов; точные копии изменяемых модулей и карточки — в `before/`, основание — в `assignment_source.txt`. Свежие правила/полный БЛОК 1, №34/40, относящиеся №37 §2–3а, №20 §5а и OPEN №05, №36.1/36.3 изучены адресно. Применимый новый функциональный scope зафиксирован ниже; чужие WA4-R/MCP/Blueprint/Colibri и код агентских действий не затрагивались.

## Что уже существовало

- Ordinary Chat Service: prepare/execute/parse, снимок модели/параметров, deadline/cancellation и нормализация основных usage.
- Model Registry, GigaChat usage parser; реальные OAuth/HTTP функции не вызывались.
- Turn v1/v2, idempotency и один локальный attempt, durable events/result, RAW commit и recovery через общий Run Store.
- Stage5 `OfflineUltraChatService`: готовые web routes, capabilities, fake-only исполнение, изолированные данные и прежний веб-интерфейс. Его контекст ограничивался одной предыдущей успешной парой и синтетической system-строкой.

## Что реализовано

| Файл | Минимальная доработка |
| --- | --- |
| `web_alarm/ordinary_chat_bridge.py` — новый | `OrdinaryCoreAdapter`: переиспользует snapshot freeze/restore существующего адаптера и общий prepare/execute, выполняет server-owned загрузку контекста при принятии нового Turn. Пропускает только точный in-memory fixture transport; подмена объектом реального транспорта даёт REJECTED / NOT_STARTED / provider_admission_required. Добавлена необязательная вложенная метрика reasoning |
| `web_alarm/ultra_chat.py` | `OrdinaryCoreChatService` поверх прежней изолированной Stage5 оболочки: весь разрешённый контекст выбранного Chat, проверенные завершённые пары, существующий PROJECT CONTEXT, подготовка под shared writer lock, отказ при повреждении/переполнении. Старый класс Stage5 сохранён |
| `web_alarm/turn_service.py` | Точный список допустимых offline adapters расширен одним классом при прежнем TEMP allowlist. Контракт durable usage принимает optional reasoning_tokens и проверяет его вложенность в completion. Прежние записи без этого поля читаются без миграции |
| `web_alarm/server.py` | Существующий create_server принимает новый точный класс в той же закрытой disposable/loopback конфигурации. HTTP routes, access/origin/write tokens и UI повторно используются |
| `test_web_alarm_ordinary_core_bridge.py` — новый | 14 адресных проверок нового маршрута, включая loopback HTTP и отрицательные ветви; участвуют в общей корневой unittest-базе |

Model Registry, Ordinary Chat Service, gigachat_transport, context_storage, Run Store, прежний адаптер, web UI и Tkinter не переписывались. Новых реестров, RAW-форматов, журналов ответов или Workspace бюджета нет.

Запуск подготовленной интеграции из доверенного тестового Python bootstrap: создать TEMP root, `WebAlarmApi(root / "registry")`, `OrdinaryCoreChatService(api.registry, root)` и передать его как `offline_chat=` существующему create_server. Это тот же web UI/API, без нового сервера или пользовательского CMD. **Текущий постоянный TEST launcher продолжает открывать прежний Stage5 fixture**; его и STANDARD конфигурацию эта TASK не переключает. Проверяемое подключение нового моста осуществляется явным server-side объектом, не URL/config_ref флагом. STANDARD по умолчанию сохраняет отказ отправки.

## Данные и сохранение

Контекст собирается при `adapter.freeze` под существующим writer lock Turn, до user RAW и до попытки. Для повторного ключа loader больше не вызывается: используется сохранённый prepared snapshot, даже если PROJECT CONTEXT изменился. Новый запрос другого владельца при незавершённом durable Turn блокируется до отправки. HTTP и обновление/повторное открытие страницы читают прежние Turn/RAW через существующие endpoints.

Успешные пары проверяются через Turn и неизменяемые message IDs. FAILED/CANCELLED/UNKNOWN запросы не превращаются в успешную модельную историю. Persisted UNKNOWN после отмены не повышается до SUCCEEDED из-за позднего результата; известный usage позднего результата сохраняется без публикации ответа. Явный повтор может завершить уже долговечно записанный результат старого ATTEMPTING, как и раньше; он не выполняет transport заново.

Usage остаётся в существующих terminal events, связан с Turn/Chat/RUN/attempt. Поля prompt/completion/total — существующая семантика общего парсера. Новое optional reasoning принимается только как каноническая вложенная метрика `completion_tokens_details.reasoning_tokens` с точным целым 0…completion; **не добавляется ещё раз к total**. Missing/unsupported/malformed reasoning остаётся None, неподтверждённые total не превращаются в 0. Это синтетический интеграционный контракт, не заявление о поддержке reasoning конкретной моделью GigaChat и не provider-wide S9.

## Испытания и evidence

Все прогоны — Windows 11, Python 3.12.10 из .venv; без bytecode/plugin auto-discovery, с ранним process guard, наследуемым Python children. Loopback разрешён только там, где нужен собственный HTTP fixture. Команды, точные source pins, platform, elapsed и exit — в `evidence/*.result.json`, raw stdout/stderr сохранены отдельно. Точный состав финального unittest-прогона — `evidence/collection.json`.

| Проверка | Результат |
| --- | --- |
| Baseline: Ordinary + S4B + прежний Stage5 OfflineChatTests | 66 PASS, exit 0 |
| Первый запуск нового набора | 10 PASS / 1 FAIL: тестовая история оказалась ниже предполагаемого cap, отрицательный trigger исправлен; первый FAIL сохранён |
| Адресный повтор после исправления размера истории | 11 PASS, exit 0; затем добавлены ещё три проверки |
| Финальный новый + затронутый Stage3/HTTP/S4A/S4B/Stage5 набор | **109 PASS, 0 FAIL/ERROR/SKIP**, exit 0; 14 новых bridge tests входят в 109 |
| Прежний Web Chat JavaScript VM/fetch fixture | **52 PASS**, 0 fail/skip, exit 0 |
| Python syntax для пяти затронутых файлов | 5 PASS, exit 0 |
| Guard probes: external socket, DNS, env credential, .env file, repository live storage, non-Python process | 6/6 BLOCKED, exit 0, побочные действия предотвращены |
| Отрицательный контроль: тот же новый full-history oracle на реальном прежнем Stage5 классе | **1 ожидаемый FAIL**, exit 1: третьему запросу передана только одна предыдущая пара; новый тест обнаруживает потерю истории |

Один ранний вызов test runner передал --network после positional remainder: Python завершился exit 2 до collection. Это ошибка команды исполнения, сохранена как `bridge_first`, а не продуктовая регрессия. `bridge_second` — первый фактический прогон новых тестов. RED/позднейшие результаты не перезаписывались.

В baseline и regression guard-log содержат по шесть отказов существующих намеренных guard-negative controls (две тройки socket/DNS/credential). В собственном guard_probes — шесть ожидаемых отказов. Новые bridge-positive tests не требуют внешних подключений. Реальных provider/OAuth/paid вызовов — 0; отсутствие настоящей сети обеспечено guard и отсутствием достижимого реального sender в новом мосте.

## MANUAL ENGINEERING REVIEW

Прослежены ветви: HTTP capability/origin → безопасное разрешение Workspace/Chat → schema/body validation → запись accepted snapshot/user RAW → durable start → общий prepare/execute → event/result → RAW commit → read/replay/cancel. Чтение контекста перемещено внутрь имеющейся транзакции принятия, чтобы другой владелец не отправил запрос со stale историей. Блокировка не удерживается во время transport; отмена остаётся доступной. Durable start и result/recovery не реализовывались повторно.

Проверены альтернативы: замена всего Turn/storage отвергнута; отдельный реестр/Workspace ledger не нужен. Полная переделка старого Stage5 оставила бы больше регрессий и пересечение с Tk fixture, поэтому сохранён прежний класс, новый маршрут подключается через существующий server injection. Раннее включение real sender по bool/config_ref отвергнуто: текущий точный allowlist физически не содержит реального транспорта. Перезапуск общего механизма учёта не нужен: добавлена только связь и одна optional metric.

Рассмотрены partial write/recovery, concurrent owners, corrupted RAW, loss of HTTP reply, immutable prepared model/system/settings, known usage после отмены и отсутствие metric. Соответствующие новые и прежние tests проверяют реальные durable events/RAW, а не только enum. UNKNOWN_VIEW при потерянном owner и долговечно CANCELLED/UNKNOWN различаются: новая работа не маскирует это как доказательство удалённого исполнения.

Открытые границы: arbitrary user code в процессе способен monkeypatch Python; точный class guard не заявляется sandbox против злонамеренного плагина. Гарантия здесь — HTTP/config_ref не выбирает реальный sender, доверенный server bootstrap остаётся fake-only и отдельно защищён TEMP/loopback. Распределённое fencing/аппаратный power-loss не проверялись.

## Ограничения и необходимое до GigaChat

- **S2:** existing pure policy без нового production ordinary route; этот bridge его не обходит и не включает.
- **S3a:** existing independently bounded OFFLINE ledger не изменён и к новому send не подключён. Fake Turn start не объявляется B2 reserve receipt.
- **S3b:** не реализован/не принят, REAL закрыт. S3c/S4/S13a и иные применимые gates не снимаются этой TASK. Синтетический usage — интеграционный минимум, не полный S9 acceptance.
- Текущие 2048 byte user-message / 8192 byte request/response / 32 messages / 128 output / 8 seconds — унаследованные **границы offline fixture**, не новые продуктовые defaults и не модельные пределы. История сверх границы отклоняется целиком. Настройки 250k/10k/20k — следующий отдельный scope с модельным admission, здесь не включены.
- Новый projector принимает подтверждённые Ordinary/Stage5 пары. Legacy Tk/agent RAW с неподтверждённым происхождением отвергается `context_source_unsupported`, а не незаметно становится успешным контекстом. Перенос таких данных потребует явного правила отбора; это не новый формат storage.
- Новый transport boundary сохраняет существующий общий async send protocol и parser. Реальные adapters/модели иных provider ещё не реализованы; нейтральная граница не означает всеобщей совместимости API.
- UI настройки per-chat и суммарные счётчики чата, подключение нового моста в постоянный TEST profile — не менялись автоматически; существующий UI/маршруты проверены на новом service через HTTP и отдельно через JS fixture.
- NOT RUN: реальные GigaChat/OAuth/paid/Colibri, CI/независимая проверка, Chromium visual, native Tk, clean Windows installation/portability, полный несвязанный suite, аппаратный crash/power-loss и реальная проверка provider caps. STANDARD живое хранилище/профили и API credentials не открывались.

## DOC IMPACT, OPEN и сдача

Общие №05/20/34/37/40/43, тестовые нормы, карточки других исполнителей и старый отчёт Астры не менялись. SHARED DOC DELTA координатору после независимого review: новый additive fake bridge и 14 selectors готовы; это шаг 1 CHAT FIRST в bounded OFFLINE scope, не Stage6 DONE/live GO. Добавление нового selector в общий документационный test catalog — передать координатору, здесь общий профиль READ-ONLY.

Сохраняются относящиеся OPEN: S3B-S3C-S9, STATIC-DYNAMIC-COVERAGE, S3A adoption/privacy/durability, FOLLOWUP-WUA-S4A-INTEGRATION-001, FOLLOWUP-WUA-S5-FINAL-BROWSER-001, FOLLOWUP-WUA-S5-CLEAN-WINDOWS-001, historical writer-busy и прочие bounded Stage5 остатки. Их закрытие этой сдачей не заявляется. Конкретный NEXT — `next-task-proposal.md`, предложение, не новая назначенная задача.

После готовности report/manifest выполняется штатный finish текущего TASK ID. **Источник факта ротации и HISTORY ID — только `finish_receipt.json`, `task_record.json`, `closeout.json` и readback карточки.** Этот отчёт после регистрации не редактируется, чтобы сохранить зарегистрированный hash. Авторская сдача не является независимым PASS или публикацией. Передача пользователю — локальный полный пакет, затем один пользовательский атомарный commit и независимая проверка. Git/commit/push/merge NOT PERFORMED.
