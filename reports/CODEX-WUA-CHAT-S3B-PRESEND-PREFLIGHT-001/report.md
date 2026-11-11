# CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001

Дата: 10.11.2026. Исполнитель: Codex 007. **PARTIAL / RESULT READY, independent review pending.**

Карта P0 и pre-send стык установлены; четыре существующих отрицательных/соседних теста PASS. У действующего Ordinary bridge проверен запрет стороннего транспорта и REAL-reference. Более широкое требование «TEST нельзя переключить конфигурацией на сетевой сценарий» не подтверждается: найден F-01 в общем launcher. Production-код и существующие тесты не изменялись; исправление launcher запрещено scope этой read-only задачи. Поэтому общий результат PARTIAL. **S3b целиком OPEN; REAL/OAuth/paid не запускались.**

## Scope, источники и REUSE CHECK

Прочитаны адресные части №08, общего №000 и карточки Codex (БЛОКИ 1/4), текущие шапки №34/40, №37 §3а шаг 3, №20 §5а (актуальное CHAT FIRST уточнение, predecessors, hard safety contract), три указанных FOLLOWUP №05: ORDINARY-CHAT-POLICY, S3B-S3C-S9, STATIC-DYNAMIC-COVERAGE. Более поздние №34/40 и карточка подтверждают приёмку H29; старые OPEN шага 2 внутри №37 не выдаются за актуальный статус.

База `main@3acd5b240ea856496bcb446fdfecaa165de0c172` / №571 взята **из постановки**, без независимой проверки Git HEAD. Git/GitHub не использовались. Локальные SHA-256 30 адресных файлов сохранены в `evidence/baseline.json`, фрагменты исходников с номерами строк — в `evidence/source_excerpts.txt`. Это адресная проверка, не полный аудит репозитория.

Исследованы все пять назначенных файлов и необходимые ближайшие связи: `ordinary_chat_test_adapter`, `ultra_chat`, TEST fixture, launcher, серверная injection-граница и существующие тесты. Уже имеются общий Ordinary service, registry/model snapshot, Turn/RAW/Run Store, S2 policy и S3a ledger. Нового ядра, транспорта, ledger или финансовой статистики Workspace не требуется и не создано.

## Существующие механизмы

| Задача | Точная функция / место | Что уже обеспечивает и чего не доказывает |
| --- | --- | --- |
| Web → существующий Turn | `web_alarm/ultra_chat.py:559` `OfflineUltraChatService.submit_turn`, `:758` `OrdinaryCoreChatService._fixture_turns` | Web принимает только text/model_ref/idempotency_key, сервер задаёт OFFLINE_REF и создаёт точный OrdinaryCoreAdapter. Клиент не выбирает transport/endpoint. |
| Подготовка и модель | `ordinary_chat_service.py:90` `_model`, `:106` `prepare_request`, `:63` `PreparedRequest` | Registry snapshot, включённая поддерживаемая модель, целые пары контекста, UTF-8 byte caps, output parameter, deterministic request_ref. Это не допуск REAL и не гарантия tokenizer/provider cap. |
| Заморозка и восстановление | `web_alarm/ordinary_chat_bridge.py:37` `freeze`; `web_alarm/ordinary_chat_test_adapter.py:30` `freeze`, `:41` `restore` | Контекст собирается сервером при новом принятии под writer lock. Повтор использует сохранённый snapshot. |
| Долговечное принятие | `web_alarm/turn_service.py:367` `submit`, `:43` `identities`, `:74` `_session` | Идентификаторы по workspace/chat/key, RUN summary, prepared binding, user RAW, READY; конфликт ключа отвергается. Это не S3a reserve. |
| Начало одной попытки | `web_alarm/turn_service.py:420` `_execute` | Верификация RAW/snapshot, ATTEMPTING и turn_started до вызова adapter, исполнение вне writer lock. turn_started **не является доказательством физического HTTP**. |
| Текущий deny транспорта | `web_alarm/ordinary_chat_bridge.py:44` `execute` | Только `type(_transport) is _FixtureTransport`; иной объект получает REJECTED / NOT_STARTED / provider_admission_required до вызова. Конструктор не принимает endpoint/credentials/arbitrary transport. |
| Общая dispatch-граница | `ordinary_chat_service.py:289` `execute_request`, физический вызов протокола `:323` | Rebuild prepared и проверка модели/подписи данных, callable transport, deadline/cancellation, одна invocation без retry. Метод send пока получает новый изменяемый dict; проверки S3b и HTTP здесь нет. |
| UNKNOWN и отмена | `ordinary_chat_service.py:331–348`; `web_alarm/turn_service.py:458` `_execute_offline`, `:294` `_view`, `:496` `cancel` | Ошибка после начала → UNKNOWN; потерянный владелец ATTEMPTING проецируется UNKNOWN. Отмена до начала и поздний результат различаются; поздний ответ не делает отменённый Turn успешным. Повтор начатой попытки не вызывает adapter заново. Это не удалённая остановка уже отправленного запроса. |
| Измерение / решение S2 | `ultra_budget_policy.py:74` `serialize_request_body`, `:91` `measure_request`, `:248` `validate_policy`, `:878` `evaluate_request` | Exact wire size/hash и output reserve, DENY неизвестного route; model-specific estimate не гарантированное число токенов. S2 сам не выполняет I/O и не охраняет production. |
| Долговечный резерв S3a | `ultra_budget_ledger.py:249` `BudgetLedger.reserve`, `:261` `mark_sent`, `:267` `terminal`, `:222` `recover`, `:264` `mark_not_sent` | Shared lock, replay/identity validation, save/readback; reserve внутри replay вызывает S2 evaluate_request. Receipt и повторный receipt не дают права нового HTTP. UNKNOWN сохраняет liability (`ultra_budget_policy.py:610`), NOT_SENT требует доказательства до отправки. |

## Точный pre-send стык

```text
Prepared request (prepare_request; durable Turn snapshot)
  → Pre-send guard [НЕДОСТАЮЩАЯ СВЯЗЬ, не реализована]
      authority + model/context/cancel/owner check
      final payload → serialize_request_body → immutable wire bytes
      S3a reserve → S2 Allow/Deny → verified fresh mark_sent
  → Deny: 0 transport calls, доказанный NOT_STARTED / no success
  → Allow: ровно одна отправка ЭТИХ bytes существующим HTTP-механизмом
  → terminal / UNKNOWN → существующие Turn + S3a reconciliation
```

Логический вход будущего admission расположен после восстановления/проверки PreparedRequest и до делегирования из `OrdinaryCoreAdapter.execute` в общий service. **Обязательное физическое исполнение guard должно находиться у окончательной сериализации непосредственно перед HTTP send.** Проверка только перед `execute_request` или нажатие кнопки UI не охватывают последующую мутацию dict, другую сериализацию и другие send-маршруты. `ordinary_chat_service.execute_request:323` — вызов транспортного протокола, не физический HTTP. У текущего Ordinary bridge реального HTTP-адаптера нет: `_UsageCapture.send:65` делегирует только fixture. Общие `gigachat_transport.CHAT_URL`, `extract_usage` и существующий HTTP/OAuth механизм переиспользуются в будущей отдельно допущенной интеграции; сейчас не подключаются.

Недостающие связи и условия следующей задачи:

1. **Final bytes binding.** `PreparedRequest.request_ref` хеширует canonical payload вместе с model/limits/context; это не wire SHA. Связать turn_id/attempt_id, выбранную модель/endpoint и policy revision с окончательными байтами S2, а HTTP передавать те же bytes без повторного `json=` преобразования. Guard не должен доверять клиентскому route/ALLOW-флагу.
2. **Atomic admission.** Использовать `BudgetLedger.reserve`, который уже делает policy evaluation под lock; не добавлять параллельный счётчик или раздельную гонку check→reserve. Проверять `Receipt.replayed`, состояние и свежесть единственного `mark_sent`; повторный receipt запрещает повторную отправку. Сбой после commit перед HTTP оставляет неопределённость/резерв, не право повторить.
3. **Ordinary policy gap.** В `ultra_budget_policy.ROUTES:54` отсутствует ordinary route. Не обозначать его как executor/mcp для обхода. Нужна явно ограниченная адаптация существующей S2/S3a для Ordinary и утверждённые per-attempt пределы, без нового общего Workspace ceiling. Унаследованные RUN/Final Audit поля не активировать молча для обычного чата. Предпочтения 250k/10k/20k ещё не provider caps; текущий fake cap 128 не заменяет реальный профиль.
4. **Enrollment/adoption.** `BudgetLedger.initialize:202` допускает только fresh audit; у существующего чата/Turn audit уже есть. Нельзя вызывать initialize в pre-send как универсальное «создать пустой ledger»: получите DENY или потребность в отдельно утверждённом adoption. Порядок инициализации до появления audit и перенос прошлых UNKNOWN требуют явного решения; не обнулять историю.
5. **Cancel/retry/reopen.** Связать свежий допуск с владельцем/отменой Turn, сохранить уже готовые `_execute_offline`, `_settle_offline`, `_view` и idempotency. Текущий bridge не передаёт cancellation predicate в service; поздняя отмена обрабатывается Turn и не обещает нулевой удалённый расход. Полную гонку cancel/send и crash окна здесь не проверяли.
6. **Охват.** Этот стык относится к Ordinary. Полный S3b по №20 требует всех физических sends, включая другие runtime/standalone/plugin пути; AST inventory и четыре локальных теста не закрывают STATIC-DYNAMIC-COVERAGE. S3c/S9 и независимый допуск остаются отдельными применимыми gates. S3a bounded acceptance не означает принятия S3b.

## Проверка TEST и находка F-01

**Действующий Ordinary путь:** exact transport check в bridge; exact class и TEMP allowlist в `TurnService.__init__:51`; exact service/registry/loopback ограничения `web_alarm/server.py:1456`; серверный OFFLINE_REF. Простая подмена request config_ref или `_transport` на сторонний объект не включает реальную отправку. Это подтверждено исходниками и существующими тестами ниже. Возможность произвольно переписать/monkeypatch Python-код не является поддерживаемой пользовательской настройкой или границей Python sandbox.

**F-01 / OPEN / source-confirmed:** `Start_WebAlarm_Test.cmd:14` запускает общий launcher с `--require-test`. В `web_alarm/launcher.py:109–120` профиль `python_script` допускает любой существующий `.py` внутри репозитория и строковые args, устанавливая `standard=False`. В `:429–440` require-test проверяет только standard, а `run_script:412` запускает выбранный script. Общий launcher не устанавливает offline guard: это делает выбранный `ordinary_test_fixture.py:29`. Следовательно, замена в конфигурации самого script может миновать fixture и его guard. Пример **только по исходникам** — существующий `probe_gigachat_models.py`: при исполнении вызывает OAuth и внешний models GET. Файл не импортировался/не выполнялся; успешный REAL Chat или платный LLM-send этим примером не заявляется.

Риск относится к редактированию доверенного локального launcher config, не к удалённому Web request и не к переключению модели в текущем Ordinary UI. Активная конфигурация остаётся прежней и безопасной в исследованном сценарии. Утверждение о защите TEST от **любой** конфигурационной подмены делать нельзя. Evidence: `evidence/finding_f01.json` и source excerpts. Исправление и альтернативный запуск **NOT RUN / OUT OF SCOPE**.

## Выполненные проверки

Команда: `.venv/Scripts/python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/run_checks.py`.

Python 3.12.10 / Windows, **4 tests / 4 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, exit 0. Длительность unittest 2.234 s; полный subprocess 3.187 s. Guard установлен явно до импорта тестов; network/DNS запрещены, исключение только stdlib self-pipe asyncio; чтение credentials/.env/.git и доступ к repository live `.ultra` запрещены. Нарушений guard **0**. Synthetic Workspace созданы существующими fixtures в TEMP.

| Существующий тест | Проверяемый oracle |
| --- | --- |
| `test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_real_transport_object_is_never_dispatched` | Forbidden.send не достигается, точный REJECTED/NOT_STARTED/provider_admission_required. Подходящий отрицательный тест уже есть — дубликат не создан. |
| `test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_bad_ids_model_and_config_cannot_read_or_send` | Чужие WS/chat, неизвестная модель и REAL-reference: отказ, fake send не вызван, история пустая. |
| `test_web_alarm_perchat_usage_settings.PerChatTests.test_preflight_rejection_is_not_an_unknown_paid_attempt` | Отдельный stub REJECTED/NOT_STARTED переводит Turn в FAILED, usage attempts=0. Этот тест не инжектирует Forbidden в реальный adapter: его oracle дополняет первый, не заменяет end-to-end S3b. |
| `test_web_alarm_ordinary_core_bridge.CoreBridgeTests.test_transport_failure_does_not_replay_or_enter_next_context` | Fake exception → UNKNOWN, повтор того же ключа не вызывает второй send; failed input не попадает в следующий контекст. |

Новых unittest-тестов **0**, production-правок **0**. Все 30 исходных pins до finish совпали. Синтаксис нового отчётного runner проверен через AST. Детали команд/версий/counts, stdout/stderr и guards: `evidence/tests.result.json`, `evidence/tests.stdout.txt`, `evidence/tests.stderr.txt`, `evidence/checks.json`. Полный CI, browser/CMD launch, настоящий транспорт, OAuth, paid, реальные чаты, динамический полный S3b, аварийные/конкурентные серии S3a и независимая приёмка **NOT RUN**. Проверки нулевого платного трафика ограничены данным guarded run, не произвольными будущими конфигурациями.

## Изменения, backup и сдача

Созданы только файлы `reports/CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001/`. Production, существующие тесты, CMD, конфигурация launcher, STANDARD/Tkinter/Blueprint/Colibri и нормативные документы не редактировались. **DOC IMPACT:** новый локальный отчёт/evidence; штатный finish меняет только свой слот карточки и служебную последовательность HISTORY, создаёт snapshot/task_record. БЛОКИ 2–4 и прежняя H29 не должны измениться; результат readback сохраняется отдельно, после finish manifest актуализируется. Отчёт после регистрации не дописывать.

До первой записи создана резервная копия **только двух существующих файлов, которые понадобится изменить штатной сдаче**: карточки Codex и `reports/task_history_sequences.json`. Побайтовый readback/SHA PASS; исходные пути и хеши — `evidence/backup.json`. Код/секреты/Workspace/настоящие чаты в backup не копировались.

**TEMP: RETAINED / CLEANUP PENDING UNTIL INDEPENDENT ACCEPTANCE.**

`C:\Users\REX\AppData\Local\Temp\codex-wua-s3b-presend-backup-3h_6pzlf`

Папку сейчас не удалять: прямое требование пользователя сохранить до независимой приёмки имеет приоритет над немедленной очисткой после finish. После независимой приёмки проверить receipt/точный resolved path внутри системного TEMP, удалить только эту уникальную папку и проверить её отсутствие. finish означает SUBMITTED/REVIEW PENDING, не независимую приёмку; фактические HISTORY ID/status — в `task_record.json`, `finish_receipt.json`, `closeout.json`.

## Точный NEXT

1. Отдельная короткая задача: закрыть **F-01** на существующем `--require-test` пути — fail-closed для неразрешённого script/args с сохранением двух утверждённых offline profiles. Достаточен адресный отрицательный тест с перехваченным subprocess; реальные scripts/credentials не запускать. STANDARD/OAuth/provider код не менять. До этого считать launcher config доверенным выбором исполняемого кода, а не offline policy.
2. Следующая Ordinary S3b задача — узко связать готовые prepare/Turn и S2/S3a с точными bytes и одноразовым допуском **через fake send**, после явного решения ordinary route/per-attempt policy и enrollment/adoption. Переиспользовать существующие функции таблицы, без нового ядра, общего бюджета Workspace и real transport activation. Минимальные oracles: DENY=0 sends/no success; ALLOW=1 с теми же bytes; replay=0 новых sends; uncertain commit/cancel/reopen не снимают UNKNOWN. Полный S3b, все физические маршруты и отдельный live USER GO остаются OPEN.
