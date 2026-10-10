# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- Перед TASK: `08_Старт.md` → `000_Задачи для агента.md` → `18_Регламент сопровождения документации.md` → `01` → профиль темы. Кодекс приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Минимум артефактов.** В разрешённых рабочих файлах оставлять только целевые правки, необходимые regression tests и действительно существенные evidence; Git-коммиты/публикацию организует пользователь или уполномоченный координатор. Полный task-report отдельным файлом только при необходимости для независимой проверки либо при прямом запросе пользователя. Остальные технические детали — во временном окружении Codex.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- После исполнения: сохранить полную утверждённую постановку в БЛОКЕ 2, factual result — в БЛОКЕ 3; только затем очистить БЛОК 1 до ожидания. Канонические журналы обновляются после независимого PASS, не на основании самопроверки Codex.

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

**Статус:** ОЖИДАНИЕ НОВОЙ УТВЕРЖДЁННОЙ ЗАДАЧИ.

CODEX-RT002-S0-REPAIR-001 передана на независимую проверку ChatGPT: RESULT READY / AWAITING INDEPENDENT VERIFICATION. Постановка — БЛОК 2, фактический результат — БЛОК 3. Следующие TASK, S1, 151G и старая 151C не запускать.

---

# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

Ниже полная первоначальная постановка прежнего БЛОКА 1, сохранённая без изменения bytes; её исходный статус READY относится к моменту назначения. Текущий результат и AMENDMENT — в БЛОКЕ 3.

# CODEX-RT002-S0-REPAIR-001 — Repair Evidence Freshness & Durable Outcomes

**Статус:** USER ASSIGNED / READY FOR MANUAL START после вставки пользователем.

**Исполнитель:** Codex — GPT-6 Sol, Very High.

**Проект:** `ag_llm` / GigaChat Ultra.

**Тип:** Runtime correctness & safety repair.

**Независимый verifier:** ChatGPT.

**Основная цель:** устранить две подтверждённые анализом исходников причины четырёх HIGH-нарушений, найденных в `CODEX-RT002-S0-001`, сохранив остальные гарантии Ultra.

## 1. Исходное состояние

Предыдущая S0 закончилась вердиктом `FINDINGS / NO S0 PASS`.

Codex сообщил результаты 97 offline-тестов: 93 PASS, 4 FAIL, 0 ERROR/SKIP.

Исходные доказательства:

- Коммит пользователя №247: `2fb37a266a0780191471cdcecea587fb449a4168`.
    
- Личная карточка `Документация/000_Задачи Codex.md`, БЛОК 3.
    
- Новый тестовый модуль `test_rt002_s0_kernel.py`.
    
- Независимый анализ ChatGPT и статус блокировки дальнейших задач — коммит №248.
    
- Каноническая программа — `20`, §5а; утверждённый план — `33.3 FINAL-B2`.
    

Четыре нарушения объединяются в две группы:

**Группа A — S0-F01 и S0-F02: неправильная привязка наблюдения к состоянию файла.**

- READ возвращает прежние данные, но последующий fingerprint может отражать уже изменённый файл.
    
- VERIFY успешно проверяет прежнее содержимое, однако последующее изменение файла может быть ошибочно связано с положительным результатом проверки.
    
- В обоих случаях возможны вызов Dredd и ложный `SUCCESS`.
    

**Группа B — S0-F03 и S0-F04: отсутствие обязательного сохранённого доказательства.**

- При недоступности `AuditThreadRecorder` обязательный результат может остаться только в памяти.
    
- Если запись `tool_finished` не сохранена, логический ID доказательства всё ещё может удовлетворить требование.
    
- В обоих случаях возможен `SUCCESS` без восстановимого обязательного evidence.
    

## 2. Требуемый инженерный результат

Исправить обе причины на уровне правильной архитектурной границы, а не частными условиями ради четырёх тестов.

### A. Достоверность наблюдений READ/VERIFY

Результат операции и его доказательство должны относиться к одному фактическому наблюдению.

Исследуй и при необходимости скорректируй:

- `_agent_read_file`, `_agent_verify_file_content`;
    
- `_planner_dependency_fingerprint`;
    
- post-dispatch binding в `_run_agent_task_impl`;
    
- связанные методы `task_planner.py` и lifecycle/freshness;
    
- аналогичные пути `read_file_range`, `find_text`, `list_dir`, если обнаружится та же ошибка.
    

Требования:

1. Не присваивать старому результату новый fingerprint, полученный после изменения target.
    
2. Сохранять точную identity: target, arguments, source, generation, RUN, stage и requirement.
    
3. Сопоставлять наблюдение с текущим состоянием без подмены его происхождения.
    
4. При подтверждённом расхождении требовать актуальное evidence или переходить в честный `BLOCKED`.
    
5. Не считать одинаковый content hash достаточным доказательством одинаковой authority/identity.
    
6. Сохранять семантику `equals`, `contains`, `exists`, отрицательные результаты и проверку изменений перед terminal `SUCCESS`.
    

Простой дополнительный snapshot не считается исправлением, если он снова используется для маркировки устаревшего результата.

### B. Обязательная сохранность доказательств

Исследуй `AuditThreadRecorder`, `_emit`, `tool_finished`, Run Store и финальное построение Audit Packet.

Требования:

1. Разделить необязательные диагностические события и обязательные доказательства, необходимые для утверждения результата.
    
2. Обязательный результат инструмента должен иметь действительно сохранённую, доступную и проверяемую запись.
    
3. Пустой или выдуманный `source_record_id` не может заменять durable outcome.
    
4. Ошибка обязательной записи, отсутствующий outcome, нарушение identity или повреждение evidence должны блокировать соответствующий certified `SUCCESS`.
    
5. Неполный критичный Audit Packet не должен запускать Dredd.
    
6. Сохранять негативные факты, ошибки, результат частичной операции и восстановимую историю.
    
7. Не останавливать полностью работоспособную задачу из-за отказа исключительно декоративной телеметрии, если обязательное evidence независимо сохранено и доказано.
    
8. После mutation со сбойным сохранением результата **не выполнять автоматически повторную mutation**, не доказав её безопасность.
    

Существующий механизм mandatory tool reserve и границы разрешений должны продолжать действовать.

## 3. Инженерная самостоятельность

Работай самостоятельно как опытный разработчик.

Разрешено:

- глубоко исследовать связанные исходники и зависимости;
    
- выбирать наиболее надёжное техническое решение;
    
- исправлять production-код, необходимый для закрытия указанных двух причин;
    
- добавлять и усиливать offline regression tests;
    
- устранять обнаруженные внутри этого scope сопутствующие дефекты;
    
- проводить adversarial analysis, включая не перечисленные явно edge cases.
    

Ожидаемые исходники: `server.py`, `task_planner.py`, `run_store.py`, `audit_storage.py` и непосредственно связанные с ними компоненты по фактической необходимости. Список не ограничивает глубину исследования.

**Не делать:** общую переработку архитектуры Ultra, новый Context Compiler, budget ledger, переделку интерфейса, изменение моделей и транспортов, возобновление 151C или работы над 151D/E/F/H/I.

Если обнаружен дефект за пределами repair scope — зафиксировать `FINDING / PROPOSAL` с доказательством, не расширяя самовольно задачу.

## 4. Обязательные тесты

Использовать существующий `test_rt002_s0_kernel.py` и необходимые адресные регрессионные тесты.

Минимальные сценарии:

- F01: изменение файла после READ, до evidence binding.
    
- F02: изменение файла после положительного `equals`, до binding.
    
- F03: ошибка создания обязательного recorder.
    
- F04: ошибка сохранения `tool_finished`.
    
- Положительный READ с корректно сохранённым material.
    
- Положительный VERIFY без изменения target.
    
- Корректное обнаружение устаревших source/generation и неправильного target.
    
- Missing/corrupt/partial outcome, ошибка index/append при сохранении.
    
- Recovery/restart/cancellation после операции без повторной опасной mutation.
    
- Отказ необязательной телеметрии при исправном обязательном storage.
    
- Проверки прав и разрешений, negative evidence, Final Audit, restart/replay.
    

Для нарушенных обязательных требований: **никакого ложного SUCCESS и никакого преждевременного Dredd**. Если возможно законное восстановление через новое evidence, успешное завершение должно оставаться достижимым.

**Цель regression:** перевести четыре исходных FAIL в PASS, сохранить 93 предыдущих PASS и добавить разумные проверки новых пограничных случаев. Не подменять это изменением ожидаемых результатов, отключением тестов, `expectedFailure` или удалением отрицательных fixtures.

Все тесты — offline/mock в изолированных временных Workspace. Без реального провайдера, платных API, сетевых вызовов и пользовательского production storage. Перед запуском расширенного suite проверить, что тесты не выполняют неожиданных Git/network/side-effect операций.

## 5. Визуальная и эксплуатационная сторона

Эта TASK не требует изменения GUI.

Однако Server должен формировать понятные terminal events и причины отказа, чтобы существующий монитор Ultra мог показывать отказ обязательного evidence без ложного статуса `SUCCESS`.

Если существующий монитор не умеет корректно отображать новый статус, зафиксируй адресное UI finding и предлагаемую доработку. Сам `ultra_ui.py` без отдельного разрешения не менять.

Кнопка `ULTRA-UX-STOP-001` — другая будущая задача, её здесь не реализовывать.

## 6. Документация, Git и выполнение

Перед началом: `08 → общий 000 → 34 → 18 → 01`, затем профиль `13`, программа `20 §5а`, журнал `21`, утверждённый `33.3 FINAL-B2`, собственная карточка и исходный отчёт S0.

Учесть правило `DOC-TASK-BLOCK1-01@1` из документа `18`.

**Активную постановку БЛОКА 1 не переписывать в процессе исполнения.** Небольшие уточнения пользователя, поступившие в чат, учитывать как отдельные адресные AMENDMENT и отразить в итоговом отчёте.

Локальному Codex запрещены любые Git/GitHub операции, включая read-only status/diff/log/show и косвенный запуск этих операций тестами. Нужный commit/blob provenance предоставляет пользователь или координатор. Исходные файлы читать напрямую; точные SHA-256 обычных файлов разрешены.

Нельзя удалять или перезаписывать чужие, untracked и пользовательские рабочие данные.

Общую документацию `000/05/06/13/20/21/28/33.3/34` не менять. Для неё подготовить `DOC IMPACT / SHARED DOC DELTA`; синхронизацию делает ChatGPT.

## 7. Критерии сдачи

В БЛОКЕ 3 предоставить:

- точные файлы и функции, которые изменены;
    
- объяснение обеих причин дефектов и способа устранения;
    
- результаты исходных четырёх regression probes до/после;
    
- полный набор запущенных тестов: команда, количество PASS/FAIL/ERROR/SKIP и exit code;
    
- положительные и отрицательные результаты проверки обязательного evidence;
    
- конкретные доказательства, что Dredd/SUCCESS не допускаются при неполном обязательном evidence;
    
- восстановление, ошибки storage и поведение при повторных попытках;
    
- исходные SHA-256, границы источников и возможные расхождения с GitHub baseline;
    
- риски, оставшиеся ограничения, rollback, `DOC IMPACT` и `NEXT`;
    
- отдельный перечень дополнительных AMENDMENT, если пользователь давал их в процессе.
    

После фактического завершения безопасно перенести полную первоначальную постановку в БЛОК 2, factual result — в БЛОК 3 и освободить БЛОК 1. Не удалять старый отчёт S0 и архив предыдущих задач.

**Итоговый статус:** `RESULT READY / AWAITING INDEPENDENT VERIFICATION`. Не объявлять `DONE / VERIFIED` самостоятельно.

После сдачи ChatGPT независимо рассматривает исправления и повторную S0-проверку. Только после независимой приёмки можно обсуждать следующую зависимую задачу программы.

**Важно:** никакого самостоятельного старта S1, 151G или новых TASK.

---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

**TASK ID:** CODEX-RT002-S0-REPAIR-001 — Repair Evidence Freshness & Durable Outcomes.
**СТАТУС:** **RESULT READY / AWAITING INDEPENDENT VERIFICATION**. Самопроверка Codex завершена; независимый PASS ChatGPT ещё не получен. Это не DONE / VERIFIED и не принятие всей S0 или 151C.
**Дата:** 2026-10-10. **Исполнитель:** локальный Codex; запрошенный пользователем профиль — GPT-6 Sol, Very High. Инструментального подтверждения фактического backend/effort нет; переключение модели и делегирование не выполнялись.
**Основание старта:** прямое поручение пользователя на новую REPAIR TASK и исходный БЛОК 1. **AMENDMENT:** новых уточнений во время исполнения не поступало; исходная постановка сохранена целиком в БЛОКЕ 2.

## 1. Вывод и границы результата

Обе подтверждённые причины исправлены. Сам результат READ/VERIFY теперь определяет fingerprint наблюдения; последующее чтение только проверяет свежесть. Для любого RUN, возвращающего SUCCESS обязательный выполненный outcome должен читаться по реальному указателю Run Store, совпадать по байтам и identity; RAM-ID или запись одного tool_started не являются доказательством результата.

Финальный guarded offline-прогон: **155 PASS / 0 FAIL / 0 ERROR / 0 SKIP, exit 0, isolation violations 0**. В него входят все 97 исходных тестов S0: прежние 93 положительные проверки сохранены, четыре отрицательные регрессии проходят; дополнительно 23 новых repair-тестов и 35 связанных проверок совместимости/файловых инструментов. Для четырёх исходных инъекций финальные наблюдения: **Dredd = 0, опубликованный SUCCESS = 0**, каждый RUN возвращает BLOCKED.

Изменены только server.py, run_store.py, audit_storage.py, test_rt002_s0_kernel.py; добавлен test_rt002_s0_repair.py. Документационная запись — только эта личная карточка. task_planner.py изучен, но не изменён: существующие matching/freshness/generation/recovery методы используются через исправленную серверную границу. Нет изменений GUI, моделей, транспортов, Context Compiler, budget ledger, Web Alarm и общих регламентов. S1, 151G, ULTRA-UX-STOP-001 и следующие TASK не запускались.

## 2. Причины и production-изменения

### A. Наблюдение и последующее состояние раньше смешивались

До repair dispatcher получал старый material/положительный equals, затем post-dispatch fingerprint заново читал уже изменённый target. Старое утверждение получало новый hash и проходило проверку свежести. Дополнительный snapshot сам по себе эту ошибку не устраняет.

В server.py непосредственно изменены _agent_verify_file_content, _planner_dependency_fingerprint, _run_agent_task_impl и проекция tool facts в _collect_final_audit_evidence; добавлены _tool_observation_fingerprint, _tool_evidence_binding и _validate_durable_tool_outcome. Реализации read_file/read_file_range/find_text/list_dir уже возвращали данные нужного наблюдения и не переписывались.

- Новый _tool_observation_fingerprint связывает read_file/read_file_range/find_text с content_sha256, который получен из того же логического чтения, что и material; content VERIFY — с actual_sha256 той же проверки. Проверяется нормализованный path результата; точные исходные arguments и target identity сохраняются отдельно.
- list_dir связывается с возвращёнными path/entries/truncated, а не с повторным листингом. Truncated observation не удовлетворяет обязательное evidence. Ветка git_diff использует возвращённое наблюдение; при этой TASK реальные Git-вызовы не выполнялись.
- _agent_verify_file_content для exists/absent фиксирует regular-file existence и target_exists одним stat-наблюдением. _planner_dependency_fingerprint сопоставляет ту же семантику предиката: изменение только содержимого не делает истинный exists ложным. equals не превращается в contains; положительные/отрицательные значения остаются различимы.
- Для непрозрачных проверок вроде python_compile dependency snapshot фиксируется перед исполнением, затем сравнивается с текущим состоянием. Проверка компиляции в новых тестах полностью fake, без дочернего процесса.
- Post-dispatch сохраняет старый observation fingerprint как исторический факт. Подтверждённое расхождение даёт tool_evidence_stale, execution_defect текущего stage и новую evidence_generation; старое evidence больше не закрывает этап. Executor получает явную пометку STALE и требование свежего наблюдения. Повтор READ/VERIFY после изменения может законно завершить RUN.
- Исходные проверки свежести перед Final Audit, после сбора Packet, после Dredd и перед terminal SUCCESS сохранены. Mutation не проходит через generic stale-check собственного pre-state: её фактический результат проверяется штатными receipts/obligations после durable gate.

### B. Обязательные outcomes раньше сохранялись best effort

Исключения recorder/observe подавлялись, но RAM-факт с логическим source_record_id продолжал участвовать в stage evidence. Указатель мог быть пустым или вести только на начало операции.

В run_store.py:

- append_run_record проверяет число записанных байтов outcome и index, сохраняет прежние flush/fsync для обоих файлов и возвращает SHA-256 точных записанных байтов.
- load_run_record отвергает неоднозначный ID, неверную пару source/stream, недопустимые offset/length, неполную запись, checksum mismatch и несовпадение record/index identity. Старые индексы без checksum остаются читаемыми.
- Новый validate_run_record требует реальный acknowledgement, повторно читает outcome с checksum именно из acknowledgement, проверяет event и при необходимости полный payload. Удаление checksum из mutable index не снимает эту проверку. Автоматического исправления повреждённой истории и повторного исполнения инструмента нет.

В audit_storage.py:

- _persist_event отделяет подтверждение append/index от _update_summary; observe — от _project_event. Ошибка обязательной записи продолжает распространяться. Ошибка исключительно summary/UI projection после сохранения не теряет acknowledgement; событие получает audit_summary_error/audit_projection_error.
- tool_evidence_stale добавлен в FRESHNESS_SERVER_EVENTS и сохраняется в истории. Полные tool_finished/tool_error, включая отрицательные результаты, сохраняются до закрытия этапа.

В server.py:

- _tool_evidence_binding и _validate_durable_tool_outcome проверяют source, task/RUN/plan/version/stage/candidate/generation/requirements/targets/tool/capability/status/sequence, arguments hash, observation hash и полный result hash. Packet содержит source_run_store_record_id, source_run_store_sha256, plan_id и candidate_id для независимого разрешения ссылки.
- _emit независимо от включения Planner/Final Audit требует сохранённые и читаемые tool_started перед dispatcher, final_audit_passed и terminal SUCCESS. Начало операции повторно проверяется после callback до физического исполнения. Отсутствие recorder блокирует RUN до Executor.
- _assert_durable_outcomes работает после каждого outcome, до следующей итерации/dispatch, до закрытия mutation receipt/этапа, до сбора Packet, непосредственно перед Final Dredd, перед final_audit_passed и SUCCESS. Подтверждение Final Audit также повторно проверяется перед SUCCESS.
- Ошибка обязательного storage даёт существующий run_finished(status=BLOCKED, reason=mandatory_...) и LifecycleBlocked. Если возможно, terminal reason сохраняется в lifecycle. Candidate после физической mutation с потерянным outcome помечается executed=True, outcome=UNKNOWN, evidence_status=UNAVAILABLE до остановки; повтор mutation не запускается.
- on_event получает deepcopy, поэтому внешний callback не переписывает серверный material/identity. Создание каталога и запись дополнительного runtime trace входят в best-effort блок и сами не являются обязательным evidence.

Mandatory storage-gate действует и при отключении Final Audit, и при обоих role-флагах False: эти переключатели не разрешают SUCCESS без durable outcomes. Эта дополнительная ветка того же дефекта обнаружена при заключительной экспертизе и закрыта тремя адресными regression-тестами. Observation provenance формируется и в legacy RUN без lifecycle; requirement matching/generation относятся к включённому Planner. Изменений полномочий инструментов или разрешений на Git здесь нет.

## 3. Четыре исходных regression probes: до / после

| Probe | До repair, повторено на исходных bytes | После repair, финальный прогон |
|---|---|---|
| S0-F01: READ → внешнее изменение до binding | OLD MATERIAL, fingerprint нового файла; Dredd 1, SUCCESS 1, FAIL | OLD MATERIAL остаётся со своим fingerprint; tool_evidence_stale, generation повышена; Dredd 0, SUCCESS 0, BLOCKED |
| S0-F02: успешный equals → WRONG до binding | passed=True старого done\n, fingerprint WRONG; Dredd 1, SUCCESS 1, FAIL | Старый PASS не становится доказательством WRONG; Dredd 0, SUCCESS 0, BLOCKED |
| S0-F03: constructor recorder raises OSError | RAM evidence с пустым durable pointer; Dredd 1, SUCCESS 1, FAIL | mandatory_evidence_store_unavailable, ни одного tool_started; Dredd 0, SUCCESS 0 |
| S0-F04: observe(tool_finished) raises OSError | Начало операции сохранено, outcome потерян; Dredd 1, SUCCESS 1, FAIL | mandatory_evidence_unavailable: Missing durable Run Store acknowledgement; один tool_started, Dredd 0, SUCCESS 0 |

В F01/F02 fixture намеренно больше не предоставляет свежих tool responses: после stale observation Executor повторяет финальный текст, а существующий lifecycle bound завершает RUN с run_lifecycle_budget_exhausted. Это не немедленный storage BLOCKED; причинное событие tool_evidence_stale сохраняется раньше. Отдельные новые тесты дают второе свежее чтение/проверку и получают законный SUCCESS. В equals recovery содержимое возвращается к тому же hash, но только новое source_record_id и повышенная generation удовлетворяют требование.

Исходные инъекции четырёх probes не удалены и не ослаблены. При первом прогоне исправленного production четыре диагностические строки старых тестов дали AttributeError: они безусловно читали audit.await_args, хотя безопасный сервер уже не отправлял Packet. Изменены только эти предпосылки/диагностические assertions: материал и fingerprint проверяются по сохранённому tool_finished, дополнительно требуются stale/BLOCKED и ноль Dredd. Прежнее главное требование «никакого ложного SUCCESS» сохранено. Нет expectedFailure, удаления отрицательных fixtures или отключения исходных 97 тестов; совпадение всех 97 test IDs с первым полным manifest проверено.

## 4. Дополнительные сценарии и доказательства

| Граница | Проверки и фактический исход |
|---|---|
| READ/VERIFY freshness | read_file_range, find_text и list_dir меняются после возвращённого result; exists → удаление, absent → появление файла. Все требуют свежего observation; при исчерпанном tool reserve — BLOCKED, Dredd 0, SUCCESS 0. |
| Семантика predicates | exists сохраняет истинность при изменении только content; equals/contains/sha256 и отрицательные результаты сохранены существующими и дополнительными тестами. |
| Законное восстановление | После stale READ/equals допускается новое наблюдение, повышенная generation, новый source; Final Dredd 1, SUCCESS 1. Старое evidence остаётся историей. |
| Непрозрачная проверка | Fake compile возвращает OK, но меняет dependency; pre-state не подменяется новым, stage не удовлетворён. Реальный subprocess не запускался. |
| Повреждение/адресация | 8 вариантов: missing index entry, duplicate ID, отрицательный offset, wrong event, wrong source/stream, partial record, equal-length parseable corruption, удалённый stream. Каждый блокирует до Final Dredd. |
| Identity | При одинаковом material отдельно отвергаются 19 подмен: logical/durable source, checksum, task/RUN/plan/version/stage/candidate/generation/requirements/target/tool/capability/status/arguments/observation/sequence/result. Существующий matcher дополнительно проверяет executed и source/generation eligibility. |
| Legacy index | Старый index без checksum читается; это не позволяет сертификацию без acknowledgement. Семантически эквивалентная whitespace-правка record при изменённом locator и удалённом index checksum отвергается по исходному byte checksum. |
| Реальные storage-фазы | Короткая физическая запись outcome; короткая запись index; отказ открытия index для append; отказ первого и второго fsync. 5 вариантов после физической mutation: ровно 1 mutation, Dredd 0, SUCCESS 0, частичная история не переписывается автоматически. |
| Mutation и restart | Потеря outcome после записи оставляет файл с done, candidate UNKNOWN/executed, без persistence_satisfied и без повторной записи. Новый явно начатый READ RUN в том же temp Workspace не воспроизводит старую mutation и может завершиться. Автоматического resume нет. Существующая cancellation-проба после физической записи также сохранена. |
| До dispatcher | Недоступен обязательный tool_started — физическая mutation не начинается. |
| До Dredd | Повреждение outcome при сборе Packet: Final Dredd 0, SUCCESS 0. |
| Во время/после Dredd | Повреждение source во время fake Final Audit: он уже вызван один раз, но final_audit_passed/SUCCESS не публикуются. Удаление outcome или attestation после audit-pass callback также блокирует SUCCESS. Это не обещание отменить уже отправленный запрос. |
| Terminal storage | Отказ append final_audit_passed или run_finished SUCCESS: SUCCESS не публикуется; возвращается BLOCKED. |
| Role flags | Planner ON / Final Audit OFF и оба OFF не обходят mandatory storage gate. При исправном store legacy RUN с обоими OFF по-прежнему завершается без вызова Dredd. |
| Negative facts | Ошибочный equals сохранён как tool_error с passed=False и полным binding; не закрывает обязательное требование и не запускает Final Dredd. |
| Необязательная телеметрия | Сбои summary, UI projection, executor diagnostic и дополнительного runtime log при исправном mandatory store не отменяют законное завершение. Callback не переписывает серверный result/binding. |
| Регрессии гарантий | Сохранены permission escalation/scope denial, exact requirement matching, mandatory reserve, Final Audit routing/recovery, provider unknown usage/replay accounting, backup/rollback и precise file edits. |

Все Dredd-числа здесь — await_count fake verifier, все Executor ответы/token adapters — mock. Это offline correctness evidence, не измерение качества живой модели или провайдера.

## 5. Прогоны: команды, результаты, изоляция

Рабочий каталог M:/GitHub/ag_llm. Команды ниже воспроизводимы; FULL означает manifest на соответствующей промежуточной версии harness. Финальная версия FULL содержит 155 тестов. Порядок selectors не влияет на порядок выполнения manifest.

FULL:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py
```

FOUR:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_lost_tool_outcome_cannot_return_certified_success test_missing_recorder_cannot_return_certified_success test_read_change_before_fingerprint_cannot_certify_old_content test_verify_change_before_fingerprint_cannot_certify_old_predicate
```

DEV14:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_corruption_during_final_audit_cannot_emit_pass_or_success test_corruption_during_packet_collection_never_reaches_dredd test_deleted_outcome_after_audit_pass_is_rechecked_before_success test_exists_and_absent_races_require_a_new_observation test_exists_predicate_survives_content_only_change test_fake_compile_cannot_certify_changed_dependencies test_final_attestation_and_terminal_write_failures_cannot_publish_success test_missing_corrupt_partial_or_wrong_record_blocks_before_dredd test_outcome_failure_after_mutation_records_unknown_without_retry test_projection_summary_and_diagnostic_failures_do_not_veto_valid_outcomes test_range_find_and_directory_races_never_relabel_old_observation test_required_intent_append_failure_prevents_physical_mutation test_stale_equals_can_recover_without_reusing_old_pass test_stale_read_recovers_only_with_fresh_generation
```

DEV3:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_deleted_outcome_after_audit_pass_is_rechecked_before_success test_missing_corrupt_partial_or_wrong_record_blocks_before_dredd test_range_find_and_directory_races_never_relabel_old_observation
```

DEV6:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_acknowledgement_binds_every_identity_dimension_even_with_equal_content test_final_attestation_deleted_after_callback_cannot_certify_success test_negative_verify_is_durable_and_never_certifies_success test_old_indexes_remain_readable_but_cannot_downgrade_certification test_partial_writes_index_append_and_fsync_failures_never_replay_mutation test_runtime_log_failure_is_optional_and_callbacks_cannot_rewrite_evidence
```

ROLES3:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_both_roles_disabled_cannot_bypass_durable_outcomes test_both_roles_disabled_still_allow_success_with_durable_outcome test_disabled_audit_does_not_waive_planner_durable_outcomes
```

| Прогон | Команда | TESTS | PASS / FAIL / ERROR / SKIP | exit | guard | sandbox (в системном Temp) |
|---|---|---:|---|---:|---:|---|
| До исправления | FOUR | 4 | 0 / 4 / 0 / 0 | 1 | 0 | codex-rt002-s0-lv5q4mc_ |
| Production исправлен, старая диагностика probes | FULL (97) | 97 | 93 / 0 / 4 / 0 | 1 | 0 | codex-rt002-s0-3wywtt5f |
| Исправлена диагностика четырёх probes | FOUR | 4 | 4 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-y5xd65is |
| Разработка дополнительных fixtures | DEV14 | 14 | 11 методов PASS; 2 FAIL subcases / 3 ERROR subcases; SKIP 0 | 1 | 0 | codex-rt002-s0-8iu_kw36 |
| Исправлены fixtures: безопасный deepcopy и имя text | DEV3 | 3 | 3 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-gu77ge6u |
| Новые storage/identity/terminal probes | DEV6 | 6 | 6 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-bhmx035_ |
| Полный S0 + repair | FULL (117) | 117 | 117 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-f_xd9x82 |
| Расширение старых зависимых тестов — НЕ ЗАСЧИТАНО | FULL (151) | 151 | 151 / 0 / 0 / 0; guard 2 | 1 | 2 | codex-rt002-s0-0vf3nwl0 |
| Безопасный расширенный набор до проверки role flags | FULL (152) | 152 | 152 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-u5cfuc7r |
| Role flags: адресные проверки | ROLES3 | 3 | 3 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-tkr70j9x |
| Итог после устранения обхода role flags | FULL (155) | 155 | 155 / 0 / 0 / 0 | 0 | 0 | codex-rt002-s0-bzrixjsk |

В DEV14 три метода имели неуспешные subcases; FAIL/ERROR перечислены как записи unittest, их нельзя складывать с PASS методов. Причины development-ошибок — неверное имя аргумента find_text (needle вместо text) и повтор fault callback при deepcopy тестового Events; исправлены сами новые fixtures, инъекции сохранены.

В прогоне 151 runner отклонил две попытки subprocess.Popen **до создания дочерних процессов**. Причина — прежний test_explicit_raw_task_no_mutation_policy_is_fail_closed косвенно вызвал реальные _agent_git_status/_agent_git_diff через _collect_final_audit_evidence. Ни один Git-процесс не стартовал; прогон имеет exit 1 и не считается безопасным PASS. Финальный IsolatedFileEditingToolboxTests подставляет fake unavailable Git observations для всех тестов этого класса; возвращён также ранее не включённый дополнительный test_mutation_bookkeeping_and_final_audit_evidence. Негативный тест запрета мутаций не отключён. Финальные guard counters равны нулю.

Runner устанавливает process-wide audit guards **до runtime imports**: запрещает дочерние процессы, сеть/DNS, чтение Git/production storage и записи за пределами sandbox. Штатный синхронный socketpair для Windows asyncio разрешён адресно. TEMP/TMP/LOCALAPPDATA/APPDATA перенаправлены в изоляцию, -B исключает bytecode writes; provider/token/Git diagnostics в исполняемых тестах fake. pytest-style functions вызываются адресно с временными fixtures, без plugin discovery и без полного неконтролируемого repository suite.

Финальный состав: KernelBoundaryTests 14; IdentityBoundaryTests 2; StageEvidenceContractTests 10; FinalAuditByteBudgetTests 2; PersistenceStateTests 11; RecoveryIntegration 16; PlannerIntegration whitelist 20; VerifierRuntime whitelist 10; RunStore/Provider functions 12 = исходные 97. RepairBoundaryTests 23; AuditStorageTests 9; IsolatedFileEditingToolboxTests 22; audit_v2_compatibility 2; verify_file_content 2 = ещё 58. Исключения исходной S0 (реальные Git-dependent fixtures) не превращены в скрытые SKIP.

Все результаты/manifest/наблюдения сохраняются во временных result.json и unittest.log, не в production storage и не как сырой stdout в репозитории. У временных файлов ограниченный срок доступности; независимая приёмка должна повторить финальную команду на переданных исходниках.

### Evidence paths и контрольные суммы

Общий префикс sandbox: C:/Users/REX/AppData/Local/Temp/. В каждой папке лежат result.json (полный manifest, counters, observations) и unittest.log.

| Sandbox | SHA-256 unittest.log | SHA-256 result.json |
|---|---|---|
| codex-rt002-s0-lv5q4mc_ | f3fb262fe7374f83c825f110142d67f1156ef64183c896db6bf8dfcdb020cdb1 | 7ada18cf02ec506e135555c695e3c2d26978ba266f07eca186c80b60763e957c |
| codex-rt002-s0-3wywtt5f | a5e78791d0fbe78c427b267a564783f7c7df46a20971a31df32ef87454ad0da1 | ab74b013bcdfa46da320af734687da0a13691d93d5e68b729a062f51185a404d |
| codex-rt002-s0-y5xd65is | 6105077ba800eae72bce4b93fcf9b21c2acb3b292226b6a95ec376fd4be6546e | 6133aaed9a25f15ad30d24683d5aee85185a425022a7a8264442aa772e496eb8 |
| codex-rt002-s0-8iu_kw36 | 906c44b94631c360888934ebdee27016d64585576dd841a8c936e914754729d6 | d6b6451b9975254c6af48caf2e883dfe5085756ea291487fb3caa1efbb876840 |
| codex-rt002-s0-gu77ge6u | bd900685ef3b3d60f19da0f33411e588f44fd0662e42ae16aeeba42b4ecabf63 | 5073d75e917a1a6e27bfcb63ca237a0875babd521cd86869d1a9a3af25d358f3 |
| codex-rt002-s0-bhmx035_ | 261b9801bd6b106e7444152561bcbba6098faf377b64d9ef5929cfca5eec69c4 | f812a53865e681531d0a713a2f0c06dcdfd5d20acae12654d99c40a6d14a4203 |
| codex-rt002-s0-f_xd9x82 | 3efdd8f3ad965c2b291a81ff4ed5e8b2b9633891efdb21ab46cb1747b2e2efa9 | 5e478f6bf65f0bc35f29d17453380fa838b264437279dd8cfe1735b763e077b7 |
| codex-rt002-s0-0vf3nwl0 | 1206e4110fb43c6d675af3c74797f501c0cb786edc6a1ed4c04da717d6a68140 | bba3cdc8bd5e65d31eb3d2eb5f8af88718cfece295f2da1308e9632ddbb6d2b5 |
| codex-rt002-s0-u5cfuc7r | ea746f632a1c4125411a35b3303df174ecd4202c82d9d23813a2faedcf5ff760 | 8f5dd5e4a6b05f2087fb976861859145338b5585861a4c81f8d12e6bfea193c7 |
| codex-rt002-s0-tkr70j9x | d8d5f82a383704ed25b88af76e4b61ab1f2abea32cb056a267950eda5a952846 | dbce126660ba6dd3811223d05e0e33c02d9ba4f157cdce21bbb0dd8db3330d1f |
| codex-rt002-s0-bzrixjsk | 9210fff3fff8ab87514db60dd0b6cb1800af93c8080193a9318f706979e23265 | 83db60a4e38e5237d45c604e13279c81888728cd3cd2c111155f0b615bfd8e5d |

## 6. Provenance и неизменность scope

Исследованы локальные обычные файлы по маршруту 08 → общий 000 → 34 → 18 → 01, затем профиль 13, программа 20 §5а, журнал 21, 33.3 FINAL-B2, личная карточка и исходный S0-отчёт. Правила DOC-GIT-01@1 и DOC-TASK-BLOCK1-01@1 соблюдаются; прямой новый старт пользователя имеет приоритет над отстающим общим маршрутизатором. Общая документация не синхронизировалась локальным Codex.

Commit №247 (2fb37a266a0780191471cdcecea587fb449a4168), независимый review №248 и immutable FINAL-B2 commit №242 (e7365ea773c9adc4e813e05a58810e40b4de4bb4) — provenance из переданной постановки/документов, а не результат локального чтения истории. Git dirty state, HEAD и актуальное совпадение с GitHub не установлены: полномочий на такие операции не было. Возможное расхождение remote baseline с локальными bytes нельзя исключить без координатора.

До edits сняты SHA-256 167 обычных root/Документация файлов; это файловый контроль ограниченного множества, не Git status и не заявление об инвентаризации всех ignored/untracked/subdirectories. В этом множестве до ротации карточки изменены только три production-файла и исходный S0 harness; добавлен один repair test module. task_planner.py, ultra_ui.py, verifier_runtime.py, planner_runtime.py, shared docs и исходные сторонние тесты совпадают с начальной фиксацией.

| Файл | Исходный SHA-256 | Финальный SHA-256 |
|---|---|---|
| server.py | 404d43d6a39924a3a0d725650f0cf4ba67591bca13e071794ab4d576f378090a | 5899125a4c54e629da0f2417aa5d9f7450e19942e4e4137ab8c0b1f77cc374a3 |
| run_store.py | 91f82db61a75980ebae8a0ee4e707ac2c09e33628021991d70d639b97b2eef44 | a57a250a20ea49ab3cc5b85cd8eaccdc2666baf694209ce4382bb3456d50b8b6 |
| audit_storage.py | 15466977e17d2f48e377ccd9b77d7ecc01aaec82c2aabf4501f8cd3c11595905 | 5d91a6f9842b1dd7e79afd69f7cd5bd984ec828c79a39939144c2d87b558851c |
| task_planner.py | c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346 | c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346 |
| test_rt002_s0_kernel.py | 845134a0ee3493e31213107c52bba7437c2364505d3036bda4556b5e3a9c5341 | cf9b1d771e7e83888378108a8a6de1fc8e5bcc6e3673f6fc0b6ec5b1fb821e3b |
| test_rt002_s0_repair.py | NEW | f1da9db3b6407f8389e0452f9a414358ce27e0b60bdf84a8febeccd6acd0090e |
| ultra_ui.py | 7bd32cad56c6f94056a291cc7beb570475be4bb3af88fd6749d66ceb021e547d | 7bd32cad56c6f94056a291cc7beb570475be4bb3af88fd6749d66ceb021e547d |
| verifier_runtime.py | 7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228 | 7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228 |
| planner_runtime.py | ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e | ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e |
| Документация/33.3_Круглый стол - итоговый план.md | c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf | c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf |

Исходная полная личная карточка: SHA-256 0f8b0b6c89499b8067170a2b4e277c6b4867f8f75e0d6f723317dc094fbf5809. Её bytes оставались неизменны на всех этапах исполнения и тестирования; только финальная атомарная ротация создаёт новую редакцию. Исходная постановка без заголовка БЛОКА 1, перенесённая целиком в БЛОК 2: 16095 bytes, SHA-256 b55a38f46e4717fa166abc1ecc7c4384e4d6352fa04e70d0da44d688c19e63e9. Предыдущие S0 БЛОКИ 2/3 сохранены дословно в архиве ниже, SHA-256 исходного фрагмента cb11c9c44cd36fab17605acd3719e7ca44a2c0648d76fe6627df562284e0f699; весь более ранний хвост с REVIEW-1/151C/DOC-034 сохранён, SHA-256 7c43ac7dbdddb9dfc18fdd5177606444687fa31b84dd1e01a66d56c338f0856d.

## 7. Ограничения, риски и rollback

- Это self-test локального repair, не независимое принятие S0. Ни live provider, ни платные API, ни production storage, ни реальная GUI-сессия не использовались. Две попытки дочернего процесса в незасчитанном расширенном прогоне пресечены runner до запуска; финальный набор полностью offline.
- Повторное разрешение records/index увеличивает локальный I/O; число remote/provider calls от durability gate не растёт. Профилирование latency, большой истории и бюджетов относится к дальнейшей программе, здесь не выполнялось.
- Freshness остаётся проверкой на границах фаз, а не блокировкой файловой системы: изменение после последней проверки, ABA без наблюдаемого промежуточного состояния, подмена самой доверенной среды или многопроцессный writer одного RUN не сертифицированы этими тестами. Проверенный ABA с зарегистрированным stale-event требует нового source/generation.
- Durable означает успешные записи/flush/fsync, acknowledgement и read-back в существующем Run Store. Fault injection не является испытанием отключения питания/сбоев оборудования. Частично записанные или недоступные records/index сохраняются; автоматического self-heal/возобновления mutation нет.
- При неуспешной записи terminal-события в сыром журнале может остаться неподтверждённый фрагмент/попытка записи. Это не опубликованный certified SUCCESS; сервер возвращает BLOCKED и пытается сохранить его. При полном отказе storage причина всё равно передаётся on_event и в возвращённом тексте. Нельзя принимать произвольную строку сырого tail за прошедший gate verdict.
- Отказ необязательной summary/UI projection может оставить видимую проекцию отстающей, хотя mandatory record исправен. Источник истины — проверяемый indexed outcome и terminal event, не одна карточка summary.
- В F01/F02 без нового tool response используется существующий lifecycle bound; новый быстрый stop/экономия циклов при упрямом Executor здесь не реализованы. Recovery с новым evidence проверен.

**UI FINDING / PROPOSAL (не блокирует этот repair):** ultra_ui.py:5551 форматирует run_finished со статусом, но без reason; :5960 явно поддерживает BLOCKED, а возвращаемый chat payload содержит причину. Новый tool_evidence_stale выводится общим trace-форматтером. При отдельной доработке показывать reason для BLOCKED, содержательные stale facts и audit_summary_error/audit_projection_error. GUI и кнопка Stop не изменены.

**Rollback:** только по отдельному решению пользователя/координатора восстановить согласованные исходные bytes server.py/run_store.py/audit_storage.py по таблице; тесты можно оставить как воспроизводимые safety probes. Не откатывать рабочие данные, Run Store и историю, не выполнять автоматические reset/checkout/replay. Возврат старых production bytes возвращает четыре известных HIGH; это риск rollback, а не рекомендуемое действие.

## 8. DOC IMPACT / SHARED DOC DELTA

Это пакет для ChatGPT, а не внесённые локально нормативные изменения.

| Владелец | Предлагаемая синхронизация после независимого рассмотрения |
|---|---|
| Общий 000 и 34 | Устранить отставание маршрутизатора; сослаться на эту REPAIR, статус ожидания независимой проверки и отсутствие следующего разрешённого старта. |
| 05 / 06 | Отразить отдельную REPAIR TASK и factual handoff; не переписывать исходный FINDINGS / NO S0 PASS и четыре HIGH как будто их не было. |
| 13 | После принятия зафиксировать различие observation/provenance/freshness, проверяемый durable outcome и fail-closed certification boundary. |
| 20 §5а | Перед зависимыми задачами требуется независимое решение по repair/S0; self-test 155 PASS не открывает S1 автоматически. |
| 21 | Записать before/after F01–F04, команды, hashes, ограничения и независимый вердикт отдельным событием. |
| 01 | После принятия обновить фактическое runtime-состояние по трём изменённым production-файлам. |
| 28 / 33.3 | При необходимости добавить внешний указатель на review evidence в протокол; утверждённый immutable FINAL-B2 не переписывать. |
| 18 / 08 / инструкции агентов | Нового изменения Git-контракта эта TASK не требует; действующее правило без разрешения на git log также сохраняется. |

## 9. NEXT — независимая приёмка

1. ChatGPT проверяет три production-изменения, целостность binding/locator/hash, границы certified режима и исключение повторной mutation; сверяет переданные file SHA-256 с этой редакцией.
2. Повторяет FULL: .venv/Scripts/python.exe -B test_rt002_s0_kernel.py. Ожидается 155 PASS, exit 0 и guard 0; никакого uncontrolled discovery, live provider или real Git.
3. Отдельно проверяет сохранение исходных отрицательных инъекций F01–F04, ноль Final Dredd/SUCCESS при недостающем proof и достижимость законного fresh-evidence recovery. Старые 93 PASS не должны быть потеряны.
4. Проверяет ротацию: первоначальный БЛОК 1 целиком в БЛОКЕ 2, прежняя S0 и более ранние архивы сохранены; новые AMENDMENT отсутствуют.
5. Выносит независимый verdict, затем согласует SHARED DOC DELTA. До него: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**, следующие задачи не разрешены. Публикацию/commit/push выполняет пользователь либо отдельно уполномоченный внешний координатор.

---

## AMENDMENT — финальная проверка S0: терминальный on_event / SUCCESS (2026-10-10 → 2026-10-11)

**TASK:** CODEX-RT002-S0-REPAIR-001, продолжение по прямому дополнению пользователя; новая TASK не открыта. **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. Это self-test исполнителя, не DONE / VERIFIED и не независимый S0 PASS.

Предыдущий отчёт БЛОКА 3 выше сохранён дословно. Его 155 PASS относятся к прежней редакции; актуальный результат этой редакции — **166 PASS** ниже. Уточнение снимает предположение, что проверок перед терминальным callback достаточно для безопасного возврата. Ранее обозначенное общее ограничение «после последней проверки» не оправдывает обнаруженное синхронное окно: управляемый сервером callback входит в завершение RUN и теперь охвачен повторным gate.

### A1. Авторизация, исходные данные и границы

AMENDMENT пользователя: сначала изолированно воспроизвести удаление/повреждение обязательной записи Run Store, изменение исходного файла/обязательной зависимости и исключение/нарушение terminal invariants именно в синхронном on_event при run_finished: SUCCESS. При подтверждении минимально исправить S0; проверить Final Audit ON/OFF, исходные F01–F04, Repair и релевантную полную offline regression; сохранить команды, счётчики, исходные версии и ограничения. БЛОК 1 не заполнять, БЛОК 2 не менять, прежний БЛОК 3 сохранить и дополнить. После отчёта остановиться до независимой приёмки. UI, S1/S2, бюджетная система, Stage Compiler, live/HTTP, Git/GitHub, commit/push не разрешены.

Пользователь сообщил о публикации основной REPAIR в №250. Локальный 000_Задачи для агента.md содержит №250 / 321f7436337f162b7741a13619954a49ed80d117, а 34 — открытый непроверенный callback-window. Это provenance из обычных документов и чата, **не результат чтения Git** и не доказательство совпадения local bytes с remote/HEAD. История не запрашивалась и не читалась.

Прочитанные локальные маршрутизаторы/владельцы: 08 → общий 000 → 34 → 18 → 01; task-card БЛОКИ 2/3, server.py, task_planner.py, run_store.py, audit_storage.py и offline fixtures. Действуют rule-ref:DOC-GIT-01@1 и DOC-TASK-BLOCK1-01@1. Явный AMENDMENT пользователя разрешает это продолжение при WAITING в БЛОКЕ 1; карточка не заполнялась заново. Общие документы и immutable FINAL-B2 не редактировались.

### A2. Дефект подтверждён до изменения production

Исходная версия server.py: SHA-256 5899125a4c54e629da0f2417aa5d9f7450e19942e4e4137ab8c0b1f77cc374a3, 321998 bytes. На ней сначала добавлены только adversarial tests, затем выполнены прогоны BEFORE и BEFORE-CERT из A5.

В исходном _emit mandatory outcomes/certifications и сохранённая terminal SUCCESS проверялись **перед** on_event. Callback получал deepcopy, поэтому не менял серверный payload непосредственно, но мог изменить файлы/Run Store. Затем исключение класса Exception подавлялось, best-effort trace записывался, _emit возвращался без новой проверки. Оба вызывающих пути возвращали content. Следовательно, проверка была корректной на прежний момент и уже не доказывала состояние при фактическом возврате.

Подтверждённые исходные инъекции:

| Группа | Сценарии до исправления | Фактический исход исходного server.py |
|---|---|---|
| Durable outcome | missing/duplicate index, неверный locator/event/source, partial stream, corruption, deleted stream × Final Audit ON/OFF = 16 | Вернулся Finished; последнее событие SUCCESS; fault callback вызван один раз. |
| Сертификация | Удаление/повреждение final_audit_passed при ON; удаление/повреждение самой run_finished при ON/OFF = 6 | Вернулся Finished даже без проверяемой ранее принятой записи. |
| Свежесть и persistence | READ, equals VERIFY, list_dir, fake compile dependency, persistence target × ON/OFF = 10 | Вернулся Finished после изменения обязательного состояния. |
| Мутация + исключение | Изменение READ target и RuntimeError из callback × ON/OFF = 2 | Exception подавлен, вернулся Finished на устаревшем evidence. |
| Контроль | Только RuntimeError и изменение копии event, доказательства целы × ON/OFF = 2 | Законный Finished. Исключение декоративного наблюдателя само по себе не делает результат ложным. |

Итого **34 различных отрицательных сценария воспроизведены** на исходном production; 2 положительных контроля сохранили законный успех. В первом BEFORE fixture повреждения attestation искал отсутствующий в ней ключ status: одна инъекция final_audit_passed:corrupt была неполной, cleanup добавил одну FAIL-запись. Это ошибка нового теста, не подтверждение этого сценария; в unittest.log явно записан один callback_errors element. До production-правки fixture исправлен на порчу существующего заголовка event; BEFORE-CERT повторил все 6 certification cases и получил все 6 ожидаемых нарушений. Остальные 33 отрицательных сценария первого BEFORE были реальными. Assertions и fault injections после воспроизведения не ослаблялись.

### A3. Минимальное общее исправление S0

Изменён только production **server.py**; Run Store schema, audit_storage.py, task_planner.py, UI и planner/provider протоколы не менялись.

1. _terminal_evidence_snapshot перед терминальным _emit повторяет существующие условия обязательного evidence и satisfied/persistence obligations; сохраняет snapshot актуальных зависимостей. Это также закрывает callbacks planner_session_completed/final_audit_skipped между gate вызывающего кода и входом в _emit.
2. После возврата из on_event и best-effort runtime trace _emit снова проверяет все mandatory outcomes, сохранённые final_audit_passed и **свою собственную** terminal record по исходному acknowledgement и expected payload. Затем повторяет freshness/obligations и сравнивает snapshot. Удаление, порча, потеря identity, устаревание либо сбой обязательной проверки запрещают успешный возврат.
3. При нарушении используется существующий _block_evidence / LifecycleBlocked: конечный результат BLOCKED; корректирующее run_finished BLOCKED пытается сохраниться и доставляется наблюдателю. Ни Executor, ни Dredd, ни mutation не повторяются; новой retry loop нет.
4. Для legacy callers без TaskLifecycle snapshot берёт реальные аргументы из **проверенного durable outcome**, а не отсутствующее поле arguments RAM-факта. _validate_durable_tool_outcome теперь возвращает уже проверенную запись; все прежние проверки binding/result/hash сохранены. Файловая свежесть сверяется до/после callback; дополнительных Git diagnostics не введено, git_diff из этого fallback исключён.
5. Обычный Exception только в декоративном callback по-прежнему best-effort: если обязательные инварианты после него целы, SUCCESS законен. Если callback успел что-либо повредить, исключение не обходит post-check. BaseException, включая asyncio.CancelledError, не подавляется: перед распространением того же экземпляра исключения сервер пытается зафиксировать BLOCKED с reason terminal_callback_interrupted.

Кодовые точки текущей редакции: server.py:3558 (_validate_durable_tool_outcome), :3754 (_terminal_evidence_snapshot), :3784 (_emit), :3822 (interruption), :3836 (post-callback gate). SUCCESS-пути: :6377 (Final Audit OFF), :7128 (ON). Проверки добавлены в общий _emit, поэтому покрывают оба пути, включая legacy callers.

Наблюдаемая граница точна: callback по определению **уже получил SUCCESS**, иначе описанная пользователем инъекция не сработала бы. Для такого синхронного наблюдателя это provisional notification до возврата callback и post-check; при нарушении следует корректирующий BLOCKED и нет успешного return. Исправление не утверждает, что невозможно увидеть промежуточное SUCCESS в событиях/сырой истории. Удалять или переписывать прежнюю запись ради такого утверждения было бы потерей истории.

### A4. Финальные adversarial checks — 11 методов / 61 сценарий

Новые методы находятся в test_rt002_s0_repair.py:90–385. Исходные 23 repair methods не переписаны: удаление только добавленного диапазона в памяти восстанавливает исходные 32366 bytes и SHA-256 f1da9db3b6407f8389e0452f9a414358ce27e0b60bdf84a8febeccd6acd0090e. Guarded runner test_rt002_s0_kernel.py не изменён. Все 155 прежних exact test IDs присутствуют в финальном manifest.

| Проверка нового набора | Сценариев | Финальное поведение |
|---|---:|---|
| 8 видов damage outcome × ON/OFF | 16 | BLOCKED, последняя terminal notification BLOCKED; один fault callback. |
| Attestation/terminal record: missing/corrupt | 6 | BLOCKED, проверяется и собственный acknowledgement SUCCESS. |
| READ drift/deletion, equals, directory, compile, вторичная compile dependency, persistence target × ON/OFF | 14 | BLOCKED; для вторичной зависимости исходный result.md остаётся прежним. |
| Мутация источника + RuntimeError × ON/OFF | 2 | BLOCKED, исключение не прячет drift. |
| Только Exception/deepcopy tampering × ON/OFF | 2 | Finished, доказательства и сохранённая terminal SUCCESS проверяемы. |
| CancelledError и собственный BaseException × ON/OFF | 4 | Исходный экземпляр исключения распространяется; последняя сохранённая/доставленная terminal запись BLOCKED; нормального return нет. |
| Legacy: source/outcome/terminal damage × ON/OFF | 6 | BLOCKED и без TaskLifecycle. |
| exists меняет только content; READ меняет только unrelated file × ON/OFF | 4 | Законный Finished: семантическая свежесть не заменена излишним запретом любых файловых изменений. |
| Повреждение SATISFIED stage state × ON/OFF | 2 | BLOCKED, status не принимается на доверии. |
| Outcome пропал, запись корректирующего BLOCKED также отказывает × ON/OFF | 2 | Возвращён и доставлен BLOCKED, ровно одна попытка corrective append; отказ store не разрешает SUCCESS. |
| Drift из planner_session_completed (ON/OFF) и final_audit_skipped (OFF) до _emit SUCCESS | 3 | BLOCKED **до** публикации SUCCESS. |
| **Итого** | **61** | **51 BLOCKED return + 4 interruption (terminal BLOCKED) + 6 valid Finished**. |

В 48 отрицательных инъекциях, сработавших внутри SUCCESS callback, тест намеренно требует одну уже полученную provisional SUCCESS и последующую BLOCKED, а не невозможное «callback сработал на SUCCESS, но никогда его не видел». Проверяются отсутствие повторного callback SUCCESS/новых Executor/Dredd вызовов, два исходных Executor fake responses, Dredd=1 при ON и 0 при OFF. 3 ранних boundary injections не видят SUCCESS вообще. CancelledError/другой BaseException проверены отдельно от обычного Exception.

**Исходные F01–F04 повторены в FULL:** все четыре PASS; в каждом returned BLOCKED, Dredd=0, SUCCESS events=0. F01/F02 без свежего tool response достигают существующего run_lifecycle_budget_exhausted; законное восстановление свежим READ/VERIFY остаётся в прежних Repair tests и PASS. F03 — mandatory_evidence_store_unavailable; F04 — mandatory_evidence_unavailable / missing durable acknowledgement.

### A5. Команды и полная хронология результатов

CWD: M:/GitHub/ag_llm. Runtime — локальная .venv, pyvenv.cfg: Python 3.12.10. Единственная точка запуска suite — standalone runner, без pytest/unittest discovery и plugins. Селекторы — реальные имена методов manifest; никаких expectedFailure/xfail или скрытых SKIP.

C1 — исходные 5 targeted methods (до/после исправления):

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_terminal_callback_outcome_damage_cannot_return_success test_terminal_callback_certification_damage_cannot_return_success test_terminal_callback_dependency_drift_cannot_return_success test_terminal_callback_mutation_then_exception_cannot_return_success test_terminal_callback_exception_only_remains_optional
```

C2 — повтор исправленного certification fixture на исходном production:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_terminal_callback_certification_damage_cannot_return_success
```

C3 — расширенные edge cases:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_terminal_callback_dependency_drift_cannot_return_success test_terminal_callback_interruption_propagates_with_blocked_terminal test_terminal_callback_legacy_file_and_record_damage_cannot_return_success test_terminal_callback_semantic_and_unrelated_changes_allow_success test_terminal_callback_stage_state_damage_cannot_return_success test_terminal_callback_damage_and_blocked_append_failure_still_fail_closed test_terminal_boundary_rechecks_events_after_the_callers_freshness_gate
```

C4 — повтор legacy после устранения найденного обхода:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_terminal_callback_legacy_file_and_record_damage_cannot_return_success
```

C5 — релевантный полный regression, включая F01–F04, весь прежний S0 Repair и все новые методы:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py
```

| Прогон | Команда | Methods PASS / FAIL / ERROR / SKIP | FAIL entries unittest | Exit | Guard violations | Seconds | Sandbox suffix |
|---|---|---|---:|---:|---:|---:|---|
| BEFORE: production исходный | C1 | 1 / 4 / 0 / 0 | 35 | 1 | 0 | 25.848 | zi73nazj |
| BEFORE-CERT: production исходный, fixture исправлен | C2 | 0 / 1 / 0 / 0 | 6 | 1 | 0 | 4.617 | o2zqft5a |
| Первое исправление | C1 | 5 / 0 / 0 / 0 | 0 | 0 | 0 | 25.648 | jv7p4sp9 |
| Дополнительные edge cases | C3 | 6 / 1 / 0 / 0 | 2 | 1 | 0 | 20.657 | tf1r3xvw |
| Legacy arguments исправлены | C4 | 1 / 0 / 0 / 0 | 0 | 0 | 0 | 2.427 | ywv_8gzr |
| **FINAL FULL** | **C5** | **166 / 0 / 0 / 0** | **0** | **0** | **0** | **108.891** | **e3w2yqjs** |

PASS/FAIL в этой таблице считают методы, поэтому в BEFORE 1+4=5. FAIL entries — отдельные subTest/cleanup записи unittest: 35 не является числом запущенных методов. BEFORE-CERT = 6 subTest violations одного метода. В C3 обе FAIL entries относятся к одному legacy method: RAM-факт не содержал arguments, initial fallback пропускал source. Корень исправлен чтением проверенного durable record; C4 и FULL подтверждают устранение. Промежуточные red runs раскрыты и не выдаются за успешную приёмку.

Состав FINAL FULL: прежние 155 test IDs + 11 новых = 166. Прежние 97 S0 (14 Kernel, 2 Identity, 10 Stage Evidence, 2 byte budget, 11 persistence, 16 recovery, 20 Planner whitelist, 10 Verifier whitelist, 12 RunStore/provider functions), прежние 23 Repair и 35 compatibility/storage/file-tool tests сохранены. Новые 11 увеличили RepairBoundaryTests до 34. Результат self-test: **PASS 166 / FAIL 0 / ERROR 0 / SKIP 0, exit 0, guard 0**.

Все artifacts ниже находятся **в TEMP**, не в репозитории. Общая база: C:/Users/REX/AppData/Local/Temp/codex-rt002-s0-<suffix>/; в каждой — unittest.log и result.json (manifest, failures/errors/skips/guards, events, packets, observations). Они могут исчезнуть при очистке TEMP; для воспроизведения достаточно текущих исходников/runner, а не сохранности TEMP.

| Suffix | SHA-256 unittest.log | SHA-256 result.json |
|---|---|---|
| zi73nazj | 96e9a761e2ec4c7131a143b18693cf2375315fe26473b6ec90548d336fe59f7a | bf34d8b706ce481283c85678560b7b7433b3c2deee0c5d27cf08961df3eb2220 |
| o2zqft5a | 976db8ba858f00d4bec7ea35e6b8ecae1bf0ea0971b841c8dba5ac103a19361b | 46f5220db7110dfa9b69746856492c24b6416ae4be5a87fbe751806d288c3c12 |
| jv7p4sp9 | 8f67e727978f5bcdd34df5e661802754af0de079a2d16c33c462d0d48b1e88d2 | 19ebafb8091d438ca5a5379b934a17a9e9197636f00f0c4613791759f22de3f6 |
| tf1r3xvw | e5bc5d4166c6e1c14dfabb4aca5757c5410ac0f30ed8ec8e44c1e55a6bc6c526 | 9346a9f7d948702766015debc9d0b2a23e695caa40e2eefd7fff16fb38280d60 |
| ywv_8gzr | 2cb6483dd6a31adba8e9e1bf2486cfd7779002133cc75387ea9d1c3345b3b512 | 4e157bf893fbaf71ea4095c785c8e5352aa66cdd8535d46fca1443ec2b9fc69d |
| e3w2yqjs | 4e7aadd433c94210e7c2ac59d4024486a39585275270b926902e106a35f51fa2 | 0538b35585760804891976f62cc4240a5628b4ee45583931f37291e67af673ca |

### A6. Версии, изоляция и loss check

Версии ниже установлены прямым чтением файлов и SHA-256, без Git. FINAL FULL выполнен именно на указанных AFTER bytes; после suite хеши server.py, test module и runner повторно совпали. Исходная карточка перед AMENDMENT: 124347 bytes, SHA-256 170c9791cc45936abf5c14aebe6e316b112e764a2770d6809d475cde371a7cef.

| Файл | BEFORE bytes / SHA-256 | AFTER bytes / SHA-256 |
|---|---|---|
| server.py | 321998 / 5899125a4c54e629da0f2417aa5d9f7450e19942e4e4137ab8c0b1f77cc374a3 | 324699 / 44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54 |
| test_rt002_s0_repair.py | 32366 / f1da9db3b6407f8389e0452f9a414358ce27e0b60bdf84a8febeccd6acd0090e | 52829 / 860f723f4c864deb0fbf6a7699a0ef9b44a29fc6c08038cffb026b36e32fb868 |

Неизменённые опорные файлы:

| Файл | Bytes | SHA-256 (BEFORE = AFTER) |
|---|---:|---|
| run_store.py | 23844 | a57a250a20ea49ab3cc5b85cd8eaccdc2666baf694209ce4382bb3456d50b8b6 |
| audit_storage.py | 31728 | 5d91a6f9842b1dd7e79afd69f7cd5bd984ec828c79a39939144c2d87b558851c |
| test_rt002_s0_kernel.py | 28657 | cf9b1d771e7e83888378108a8a6de1fc8e5bcc6e3673f6fc0b6ec5b1fb821e3b |
| task_planner.py | 55904 | c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346 |
| ultra_ui.py | 246742 | 7bd32cad56c6f94056a291cc7beb570475be4bb3af88fd6749d66ceb021e547d |
| Документация/33.3_Круглый стол - итоговый план.md | 45043 | c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf |

rule_set_ref: документ 18_Регламент сопровождения документации.md, прочитанная локальная редакция SHA-256 0b4ce6e621f372bdd2ea268c28e899cd137bdbcd60c8e6846a8f4c428854b51b; DOC-GIT-01@1, DOC-TASK-BLOCK1-01@1. Документы 08/000/34/01 не превращались в разрешение на Git, live или новые этапы.

Снимок 168 обычных py/md/json/toml файлов корня и Документация перед/после работы до сохранения отчёта обнаружил изменения только server.py и test_rt002_s0_repair.py. Это файловая сверка указанного охвата, **не Git status и не заявление о clean tree**. При closeout добавляется только настоящая вставка в персональный БЛОК 3; сырые логи, массовые backups и новые task/report files в репозитории не создавались.

Сохранность карточки контролируется exact bytes:

| Неизменяемый фрагмент | SHA-256 |
|---|---|
| Начало карточки, БЛОКИ 1/2 до заголовка БЛОКА 3 | 5db744ea99fcb2982ebfa6bfe64fcfc70b13603e734fd80be49ed42146c73004 |
| Прежний полный отчёт БЛОКА 3 до ARCHIVED S0-001 | 9d00f3e6f81970480e75142903343c84a69a2cdd1916f195fe02d45b4565adc7 |
| ARCHIVED S0-001 и вся последующая история | 1627e88619646cbc41fcf16b3c263a3d02e9dfcb613f588de3b845631d4a0925 |

Перед записью проверяется byte equality всей карточки с исходным снимком и неизменность протестированных production/test bytes. Вставка располагается непосредственно **перед ARCHIVED S0-001**, с сохранением prefix, старого отчёта и tail; atomic sibling-temp replacement, readback equality и отдельная проверка трёх фрагментов. БЛОК 1 остаётся WAITING, БЛОК 2 и архивы не меняются. Старый NEXT §9 выше — исторический handoff до AMENDMENT; его слова «новые AMENDMENT отсутствуют» не относятся к текущему состоянию. Актуальный NEXT — A8 ниже.

Все шесть запусков работали под существующими process-wide guards **до runtime imports**: запрещены subprocess/process launch, HTTP/сеть/DNS, чтение .git/production .ultra и запись за пределами временного sandbox. Windows asyncio socketpair разрешён адресно существующим механизмом. TEMP/TMP/LOCALAPPDATA/APPDATA перенаправлены; -B исключает bytecode writes. Token/provider transports, Planner/Dredd, Git diagnostics, compile/tool subprocess и backup/runtime paths безопасно подменены. Adversarial callbacks повреждали только временные fixture-файлы. **Guard violations во всех запусках = 0**; live-вызовов и реальных Git-команд не было.

### A7. Ограничения и риски

- Post-check доказывает возможность безопасного завершения на проверяемой границе, а не блокирует файловую систему. Внешний процесс после последнего чтения, ABA с восстановлением прежнего наблюдаемого состояния, подмена самой доверенной среды, deferred callbacks/другие потоки остаются за пределами этой гарантии. Snapshot comparison не обещает detection невидимого промежуточного изменения.
- SUCCESS notification/запись существовала до исполнения fault callback. Уже доставленное уведомление нельзя отозвать; исправление даёт окончательный BLOCKED и запрещает успешный return. Историческая SUCCESS не удаляется. Потребитель не должен считать произвольную раннюю/raw строку отдельным окончательным verdict, игнорируя последующий BLOCKED и обязательный proof. UI/API семантика не перепроектировалась и UI не менялся.
- Если store после fault недоступен, сервер не может обещать durable corrective BLOCKED; проверено, что обычный отказ этой записи не отменяет BLOCKED return/notification и не вызывает повторов. Если и внешняя доставка не работает, её успешность также нельзя гарантировать. Сохранённая старшая SUCCESS/отставшая summary без повторной проверки mandatory proof не является достаточным свидетельством успешного RUN.
- При ON Final Audit уже был вызван один раз до terminal fault: невозможность вернуть SUCCESS не отменяет совершённый запрос. Нового Dredd/Executor/physical mutation после terminal fault нет.
- Legacy snapshot не создаёт несуществующий декларативный stage contract и не сертифицирует legacy freshness до начала этой границы. Он ловит изменения наблюдаемых файлов в terminal callback; git_diff исключён из legacy fallback ради отсутствия новых Git diagnostics. В V6 declared requirements/persistence действуют существующие полноценные gates. Это не реализация S1/S2.
- OFF/ON paths, CancelledError/BaseException и logical dependency freshness проверены offline; настоящий provider/network, реальные compile/backend subprocess, GUI Stop, multi-process races и Git-dependent fixtures намеренно не запускались. **SKIP=0 относится к explicit 166-test manifest**, а не к любому тесту проекта. Полного unrestricted discovery не было; исключённые unsafe tests не объявлены PASS.
- TEMP evidence может быть очищено системой. Git HEAD/dirty state/remote identity не проверены; №250 и SHA из маршрутизатора — переданный provenance. Независимая приёмка должна сверять эти новые file hashes и повторить guarded suite; прежний статический review №250 сам по себе не принимает текущую правку.

Rollback — только по отдельному решению пользователя/координатора, восстановлением согласованных исходных server.py bytes. Автоматического reset/checkout/replay не выполнять; рабочие данные/Run Store/историю не откатывать. Такой возврат снова открывает подтверждённое terminal window. Новые regression tests полезно сохранять как воспроизведение дефекта.

### A8. DOC IMPACT и NEXT для независимой приёмки

```text
DOC IMPACT: YES
CURRENT STATE IMPACT: YES
ARCHITECTURE IMPACT: NO (граница S0 укреплена, новый subsystem/protocol не вводился)
CONTEXT LIBRARY IMPACT: NO
REGISTRY / ROUTING IMPACT: YES (только дельта для координатора)
NEW DOCUMENT REQUIRED: NO
CANONICAL OWNER: 13_Архитектура оперативной верификации и контроля выполнения задач.md
AFFECTED DOCUMENTS: персональный 000_Задачи Codex.md; после independent review — общий 000, 34, 01/13, 05/06, 20 §5а, 21
CONTRADICTION CHECK: REQUIRED
LOSS CHECK: PASS (предыдущий отчёт/БЛОКИ 1–2/архивы сохранены; исходные 155 tests retained)
```

SHARED DOC DELTA **предложена, не внесена локально**: общий 000/34 должны заменить «callback-window NOT REPRODUCED» на «подтверждён и исправлен; 166 PASS self-reported, независимая приёмка ожидается»; 01/13 — отразить post-callback terminal gate и точный предел provisional notification; 21 — before/after, хеши, 61 scenario и ограничения; 05/06 — отдельное append-only событие AMENDMENT; 20 §5а — сохранить S1/S2/151G закрытыми до независимого решения. Immutable 33.3 и прежние findings не переписывать, новой нумерации коммитов не выдумывать. Новых нормативных изменений Git-контракта нет.

NEXT (ChatGPT):

1. Независимо сверить server.py/test hashes из A6, проверить оба call sites и post-callback gate, собственный terminal acknowledgement, legacy arguments, обычный Exception и распространение BaseException. Отдельно оценить provisional SUCCESS / corrective BLOCKED semantics и отказ corrective append; не подменять их обещанием «SUCCESS вообще не наблюдался».
2. Повторить C5 **с guards**, ожидая 166 PASS / 0 FAIL/ERROR/SKIP, exit 0, guard 0. Проверить inclusion всех прежних 155 test IDs, исходные F01–F04 (Dredd=0/SUCCESS=0), 11 новых methods / 61 scenario, отсутствие replay/новых фаз.
3. Проверить loss check карточки: исходный БЛОК 1 WAITING, БЛОК 2 прежний, старый БЛОК 3 и архивы целы; AMENDMENT только дописан. Согласовать SHARED DOC DELTA после независимого verdict.
4. Commit/push/публикация — пользователь или отдельно уполномоченный внешний координатор. Самостоятельной независимой приёмки, DONE/VERIFIED, открытия S1/S2/151G и нового TASK старта здесь нет.

**RESULT READY / AWAITING INDEPENDENT VERIFICATION. После сохранения отчёта исполнитель остановлен до независимой приёмки.**

---

## ARCHIVED S0-001 — прежние БЛОКИ 2/3 (сохранено при REPAIR, 2026-10-10)

Историческая постановка S0 и отчёт FINDINGS / NO S0 PASS сохранены дословно. Это не активная задача и не новый verdict.

```````text
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

**TASK ID:** CODEX-RT002-S0-001 — RT-002/B2 / S0: Fresh Kernel Integration Baseline and Safety Gate.
**Статус:** **USER APPROVED / READY FOR MANUAL START** (2026-10-10), одна задача за раз; исполнитель — **Codex, GPT-6 Sol, Very High** (выбрано пользователем, реальный backend/effort проверять отдельно).
**ARCH CLASS:** Ultra Runtime / Verification / Safe Rebaseline.
**PRIMARY PROFILE:** \`13_Архитектура оперативной верификации и контроля выполнения задач.md\`.
**SECONDARY:** \`20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md\` (§5а), \`21_Журнал качественного перехода - решения, метрики и аудит.md\`; при необходимости \`01\`.
**Утверждённое основание:** итоговый план \`33.3 FINAL-B2\`, immutable commit №242 \`e7365ea773c9adc4e813e05a58810e40b4de4bb4\`, SHA256 \`c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf\`; внешний **USER PLAN APPROVAL** в документе \`28\`, canonical handoff в \`20 §5а\` (commit №244). **Старая 151C PARKED / КТ-3 PENDING**, её НЕ принимать под видом S0.
**Snapshot от координатора до нового назначения:** \`main@cd48ff1629a8e04a734e36196d32ee52e37c103b\`, \`server.py\` blob \`a2e362e552e77b60378b794fe0bec819ec7a0608\`, \`task_planner.py\` \`07f170d07951ee3bd3def22be545bc579dddf6c2\`, \`run_store.py\` \`b5b0e5d6375d8c51b673c0ad14c1d7298fa29c6d\`, \`verifier_runtime.py\` \`4c6b7b08a50cd6698822c7eaba27718c91d9d11e\`; локальные bytes/dirty state могут отличаться и требуют точной, не-Git проверки.

## Зачем нужна S0

Проверь **доказательно**, пригоден ли реально существующий код Ultra для новой защищённой ветки S2/S3→S6a/151G. До изменения архитектуры нужны permission/scope, exact evidence, freshness и recovery гарантии. Результат — один из **BASELINE SUITABLE FOR NAMED NEW SCOPE / FINDINGS / BLOCKED**, с четкими границами доказанного. S0 **не** означает независимую приёмку всей старой 151C и не выдаёт КТ-3 DONE.

## Рабочий маршрут и самостоятельность

1. После пользовательского **GitHub Desktop Fetch/Pull** пройти обычный старт \`08 → общий 000 → 34 → 18 → 01 → персональный 000\`; прочитать \`13\`, \`20 §5а\`, адресно \`21\`, \`33.3 B2\`, \`28\` (USER PLAN APPROVAL) и действующие правила \`DOC-GIT/READ/VERSION/CHANGE @1\` с dependencies. Историческая шапка sealed B2 была DRAFT на момент seal; текущие полномочия **в 28 + 20**, не объявлять план неутверждённым по старой immutable шапке.
2. **Тебе разрешена глубокая инженерная самостоятельность:** сам выбери порядок чтения, AST/source review, изолированные mock/fixtures, offline targeted tests и adversarial edge cases. Перечисленные файлы — **не ограничение на чтение**. При обнаружении в scope существенной неучтённой проблемы зафиксируй факт, риск, severity, repro и возможное безопасное решение, не скрывай его ради быстрого PASS.
3. Основные entry points: \`server.py\` (permissions, accepted args/target, tool dispatch, Final Audit packet, SUCCESS), \`task_planner.py\` (RAW TASK/requirements/contains/equals), \`run_store.py\` (source/generation/attempt identities и restart), \`verifier_runtime.py\`, storage/accounting по необходимости; тесты \`test_final_audit_recovery.py\`, \`test_final_audit.py\`, прочие адресные \`test_*.py\`. Не повторять вслепую дорогие исторические архивы. Ссылаться на реальные source selector/revision, отделяя наблюдение от historical claim.
4. **Никакого локального Git/GitHub**, включая status/diff/log/read .git/API или их запуск через tests/helpers; это \`DOC-GIT-01@1\`. Git evidence/SHA от координатора, локально читать файлы напрямую и при необходимости вычислять локальные SHA-256 без Git. Если для конкретного вывода необходима история, дать \`GIT_DATA_REQUIRED\` с точным запросом и продолжить независимые безопасные пункты.
5. **Никакого платного/live провайдера, сетевых вызовов, R-031 stress, пользовательского production storage и других агентов.** Для тестов применять temp workspace, fake socket/HTTP, подменённые adapters; перед большим suite проверить отсутствие скрытых Git/network/write side effects. Если опасность не исключена — skip соответствующий suite и отметить честное ограничение.

## Минимальные инварианты (не потолок исследования)

- **Authority / source identity:** Server scope, task/run/plan/stage/generation/requirement, разрешённый target и аргументы READ/VERIFY; wrong target, denied scope, wrong predicate, false equality/blocking.
- **Полнота до Dredd:** обязательный source/negative tail, truncated/missing READ, wrong target/old generation не могут удовлетворить requirement; incomplete mandatory packet ⇒ \`0 Dredd sends\`, \`0 SUCCESS\`. Проверка пакета против исторического 151C shape — только новая узкая интеграционная пригодность.
- **Freshness/transition:** replan, repair, mutation и внешние изменения требуют свежего proof; после Audit Packet и перед SUCCESS прежний PASS перепроверяется, hash/same bytes другой identity недостаточно.
- **Reserve/recovery:** существующий mandatory physical-tool reserve, restart/replay без повторной мутации, отсутствие ложной успешности при missing evidence/UNKNOWN/storage problem.
- **Positive + negative:** проверить законно выполнимую простую fixture (чтобы guard не блокировал всё), а также deliberate wrong args/target, stale/negative, truncated, restart/abort, permission-denied, unsupported material и failure diagnostics. Найди дополнительные edge cases самостоятельно.

## Что можно менять в этой одной TASK

**Разрешено:** адресные новые или исправленные **изолированные offline regression tests/fixtures** (например \`test_rt002_s0_kernel.py\` и при необходимости \`test_final_audit_recovery.py\`), и только они, если это повышает доказательность. Локальный Codex вправе глубоко читать релевантный production code и сам решать, какие тесты нужны. **Production runtime/config/transport/UI не менять** в S0 — это отдельные будущие TASK после S0 PASS. При найденном небольшом production дефекте приложить repro и предложить минимальный патч для следующей отдельно разрешаемой работы; не маскировать исходное состояние исправлением до проверки.

**Документы:** локально разрешена только собственная task-card \`000_Задачи Codex.md\` для handoff; общие \`000/05/06/13/20/21/28/33.3/34/01\` не редактировать, их сопровождает ChatGPT после независимой приёмки. **Не удалять и не затирать старые карточки** — DOC-034 и REVIEW-1 сохранены ниже в истории. По завершении безопасно перенести S0 постановку в БЛОК 2 и factual result в БЛОК 3, сохранить архив, затем очистить БЛОК 1 до ожидания. Никаких git commit/push.

## Acceptance / отчёт

В БЛОКЕ 3: \`TASK ID\`, прочитанные source и локальные точные hashes, что совпало с предоставленным baseline, что не доказано; \`PASS/FINDING/BLOCKED\` по каждому инварианту со source path/selector; targeted offline commands + **реальные числа** и network/Git isolation; изменённые test paths, found defects, rollback test changes, DOC IMPACT и строго ограниченный NEXT. Фактическое \`RESULT READY / AWAITING INDEPENDENT VERIFICATION\` **не** \`DONE\`. Не сдавай большой общий обзор вместо воспроизводимых probes.

**Завершение:** независимый ChatGPT verifier по опубликованным изменениям и отчёту отдельно устанавливает \`SUITABLE FOR NAMED SCOPE / FINDINGS / BLOCKED\`. Пока нет этого решения, S1 и другие новые TASK не запускать. **Стартовать только по ручной команде пользователя.**


---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

## CODEX-RT002-S0-001 — factual baseline / 2026-10-10

**Статус исполнения:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. **Предлагаемый verdict:** FINDINGS; пригодность для новой защищённой ветки S2/S3 → S6a/151G пока НЕ доказана. Это локальная самопроверка, не независимый PASS, не DONE и не закрытие 151C/КТ-3. Найдены четыре HIGH-воспроизведения с двумя общими причинами. Production оставлен в исходном состоянии.

**Исполнитель:** локальный Codex. Пользователь запросил GPT-6 Sol / Very High; фактический backend и reasoning effort доступными средствами независимо не подтверждены. Другие агенты не привлекались.

### 1. Основание, источник и границы

Применён маршрут 08 → общий 000 → 34 → 18 → 01 → собственная карточка. Адресно прочитаны 13 (server authority, evidence/freshness, §18 Final Audit и pending recovery), 20 §5а, текущая RT-002 запись 21, внешний USER PLAN APPROVAL в 28, 33.3 FINAL-B2 (§2 T0/S0, §3 DAG и границы последующих этапов). Получены определения `DOC-GIT-01@1`, `DOC-READ-01@1`, `DOC-VERSION-01@1`, `DOC-CHANGE-01@1` из 18 вместе с requires; использовано ручное адресное чтение, не несуществующий автоматический resolver.

33.3: **45043 исходных UTF-8 bytes**, полный SHA-256 **c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf** — точное совпадение с утверждённым B2, без нормализации переводов строк. Immutable commit №242 / `e7365ea773c9adc4e813e05a58810e40b4de4bb4` и разрешение/handoff №244 приняты как сведения координатора; старый DRAFT внутри immutable B2 не отменяет внешнее утверждение.

Четыре runtime-файла локально совпали по SHA-256 с байтами, изученными в предыдущем REVIEW. Это сравнение обычных файлов, **не** доказательство совпадения Git blob. Координаторский `main@cd48ff1629a8e04a734e36196d32ee52e37c103b` и предоставленные blob IDs сохранены в полной постановке БЛОКА 2; локальные Git state/HEAD/dirty status не исследовались.

**GIT_DATA_REQUIRED, только для committed↔local сверки:** координатору предоставить полные обычные file-byte SHA-256 либо экспортированные bytes `server.py`, `task_planner.py`, `run_store.py`, `verifier_runtime.py` из указанного snapshot с точным revision. Текущие probes от этого не зависели; утверждение «проверена именно committed версия» остаётся недоказанным. Git-object hashes не вычислялись обходным способом.

### 2. Что изменено и как воспроизвести

Создан только `M:/GitHub/ag_llm/test_rt002_s0_kernel.py` (27453 bytes, SHA-256 **845134a0ee3493e31213107c52bba7437c2364505d3036bda4556b5e3a9c5341**). Это отдельный guarded runner, 16 новых тестовых методов и явный manifest 81 существующей проверки; существующие тесты не изменены. Документационное изменение — только эта карточка: полная S0 постановка перенесена в БЛОК 2, прежние REVIEW-1 БЛОКИ 2/3 сохранены ниже, старые архивы оставлены.

Из `M:/GitHub/ag_llm`:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py
```

**Финальный запуск: 97 tests = 93 PASS + 4 FAIL; 0 ERROR, 0 SKIP, exit 1.** Красные проверки намеренно показывают дефекты baseline; не помечены expectedFailure и не замаскированы общим PASS.

| Группа | Число |
|---|---:|
| Новые KernelBoundaryTests / IdentityBoundaryTests | 14 / 2 |
| StageEvidenceContractTests | 10 |
| FinalAuditByteBudgetTests / RecoveryIntegrationTests | 2 / 16 |
| PersistenceStateTests / PlannerIntegrationTests | 11 / 20 |
| VerifierRuntimeTests, адресный protocol subset | 10 |
| Run Store v2 / provider accounting, прямой вызов pure fixtures | 9 / 3 |
| Всего | 97 |

Повтор четырёх дефектов на том же финальном test-файле:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_read_change_before_fingerprint_cannot_certify_old_content test_verify_change_before_fingerprint_cannot_certify_old_predicate test_missing_recorder_cannot_return_certified_success test_lost_tool_outcome_cannot_return_certified_success
```

**4 tests, 4 FAIL, 0 ERROR/SKIP, exit 1.** Все четыре вновь дошли до одного mock Dredd вызова и одного SUCCESS. Изоляция обоих запусков: **0 guard violations**, реальных provider/Git/network вызовов нет.

Проверка обычного unittest discovery:

```powershell
.venv/Scripts/python.exe -B -m unittest test_rt002_s0_kernel -v
```

**0 tests, 1 module SKIP, exit 0** — ожидаемо: без standalone-изоляции модуль не импортирует runtime и не устанавливает глобальные hooks в чужой suite. Это проверка безопасного включения файла, не дополнительный runtime PASS. Промежуточные запуски с доработкой fixtures не включены в 97; ошибки настройки denied scope, ожидаемого LOOP DETECTED и Windows newline устранены до финального результата.

### 3. Изоляция и предел доказательности

Guard устанавливается **до** imports server/legacy fixtures: audit hook блокирует subprocess/os.system/spawn, Python socket connect/bind/DNS, чтение .git, чтение production .ultra и файловые мутации вне уникального temp root. Единственное разрешённое socket housekeeping — синхронный stdlib socketpair для Windows asyncio. LOCALAPPDATA/APPDATA/TEMP/TMP направлены в sandbox; -B запрещает pycache writes.

Executor HTTP, token acquisition, Planner и Dredd заменены fake/AsyncMock adapters; server Git helpers заменены фиктивными обычными словарями. Без этих mocks исходный runtime умеет обращаться к Git: наличие проверки S0 не меняет его архитектуру и не даёт такого права локальному агенту. Из manifest исключены весь FinalAuditGitScopeTests и методы recovery `test_ignored_file_material_remains_available_without_git_diff` / `test_git_diff_state_drift_requires_new_source_evidence`; они не исполнялись. Полный неотобранный legacy suite не запускался. Pytest-style функции вызваны напрямую с temp fixtures и MonkeyPatch, без plugin discovery.

Это process-local Python guard плюс проверка выбранных путей, **не OS sandbox** и не сертификация произвольных сторонних расширений. Stress, GUI, реальные provider/transport и Git semantics не проверены. Mock PASS намеренно используется для проверки механических server gates: выводы не зависят от добросовестности LLM.

### 4. Инварианты: результат с точными selectors

В таблице имена test_* относятся к manifest runner; полный список каждого вызова сохраняется в result.json и воспроизводится из _manifest().

| Инвариант | Verdict | Доказательство / предел |
|---|---|---|
| Server permissions, READ/VERIFY scope, traversal, WRITE denial/grant | PASS в проверенных случаях | Новые test_read_and_verify_denied_scopes_and_traversal, test_denied_read_never_satisfies_requirement_or_calls_dredd; PlannerIntegration test_scope_violation_does_not_reach_audit_or_force, test_write_off_uses_existing_permission_escalation, test_explicit_permission_grant_allows_same_contract_to_continue. Denied READ заканчивается LOOP DETECTED после трёх ошибок, не SUCCESS; диагностируется PermissionError. |
| task/run/plan/stage/generation/requirement/source + exact arguments | PASS в проверенных случаях | test_identity_dimensions_and_same_hash_other_target_are_rejected: 9 подмен identity/status/executed и другой target при одинаковом content hash; StageEvidenceContract old_plan_version, execution_repair_generation, missing_source_record_identity; PlannerIntegration wrong_successful_verify и server_evidence_gate. Аргументы связываются arguments_sha256; модельный текст не становится authoritative fact. |
| equals ≠ contains; false equality | PASS без гонки; FINDING при гонке | test_exact_equality_is_not_contains_and_false_block_is_explicit; test_required_false_equals_blocks_without_dredd: 0 audit, 0 SUCCESS, VerificationError/LOOP DETECTED. Положительный точный equals и READ проходят; F02 показывает отдельную потерю свежести. |
| Полнота обязательного material до Dredd | PASS для missing/truncated/budget cases; FINDING по durability | Recovery test_missing_required_material_blocks_before_dredd, required_material_budget_exhaustion, deduplicated_required_large_read, tool_level_truncated_find_text, truncated_model_result; PlannerIntegration incomplete_requirement_coverage. В этих случаях 0 mock audit, 0 SUCCESS. Но F03/F04: отсутствующий durable source не признаётся incomplete. |
| Negative tail / failed exact outcome / dedup | PASS в проверенных случаях | Recovery failed_exact_check_keeps_details_and_its_outcome_record, failed_exact_metadata_survives_zero_material_budget, empty_search_negative_fact_survives_no_preview_budget, complete_deduplicated_material_keeps_an_explicit_source. count=0 и expected/actual остаются явными; старый truncated generation не блокирует новый fresh proof. |
| replan/repair/mutation/dependency drift | PASS для проверенных transitions | StageEvidenceContract old_plan_version, execution_repair_generation, target_state_drift, dependency_drift_in_compile_paths; PersistenceState stale_candidate, server_binding_other_plan_version, satisfied_receipt_invalidated_by_external_change и replan_cannot_silently_drop_obligation. |
| freshness после packet, после Dredd и перед terminal SUCCESS | PASS в проверенных поздних окнах; FINDING в исходном observation binding | PlannerIntegration state_change_during_packet_collection и state_change_during_final_audit; Recovery directory_listing_drift_after_pass; новый test_mutation_after_audit_pass_before_terminal_gate_requires_new_read: изменение в callback final_audit_passed вызывает terminal_evidence_freshness_blocked, fresh READ и второй audit, только затем SUCCESS. F01/F02 подменяют исходный binding раньше этих gates, поэтому поздние сравнения его не исправляют. |
| Mandatory physical-tool reserve | PASS в проверенных случаях | PlannerIntegration test_tool_reserve_preserves_mandatory_write_read_verify_calls: лимит 3, ровно WRITE/READ/VERIFY; лишние calls остановлены до выполнения. test_tool_reserve_blocks_impossible_plan_before_executor_api: лимит 2, 0 executor API, 0 audit. Это существующий reserve, не будущий S3 resource ledger. |
| abort/restart/replay, UNKNOWN | PASS узко; полного crash recovery proof нет | Новый test_abort_after_write_records_no_success_and_does_not_auto_replay: физический WRITE=1, cancellation до receipt, 0 audit/SUCCESS; новый controller не загружает и не переигрывает старый latch. Existing successful_persistence_advances_before_executor_can_repeat_write не допускает повторного WRITE. Unknown usage остаётся incomplete; duplicate terminal не удваивает usage. Это не доказательство exactly-once при power loss и не реализованный resume interrupted RUN. |
| Storage failures | FINDING | Плановый atomic_state failure прекращает RUN до executor/audit; last-state preservation, retry/fallback generation проверены. Однако F03/F04 допускают SUCCESS без обязательного durable outcome. |
| Unsupported material / diagnostics / protocol | PASS в проверенных случаях | test_missing_oversized_unsupported_and_invalid_predicate_fail_closed: missing file, binary suffix, file limit, bad kind/hash/exists args. Dispatcher failure оставляет tool_started → tool_error. Verifier malformed/unknown/mismatched verdict/check_type и unsupported provider/model не превращаются в PASS и не fallback. Реальный транспорт не тестировался. |

### 5. Findings: воспроизведение, причина и безопасное предложение

#### S0-F01 — HIGH: READ material и observed_state относятся к разным состояниям файла

**Repro:** `KernelBoundaryTests.test_read_change_before_fingerprint_cannot_certify_old_content`. Только temp target: READ возвращает `OLD MATERIAL`; wrapper сразу после реального READ заменяет файл на `NEW MATERIAL`, до возврата управления server evidence binding. Не подменяются result, contract, hashes, lifecycle или решение Server. Это детерминированное воспроизведение внешнего изменения в реальном промежутке между чтением и повторным snapshot.

**Факт:** packet содержит `OLD MATERIAL`, а `observed_state_sha256` совпадает с fingerprint уже `NEW MATERIAL`. completeness.complete=true / critical_for_success=false; mock Dredd=1, terminal SUCCESS=1. Следующие freshness checks сравнивают текущий файл с ошибочно новым binding и не видят старость READ.

**Источник:** server.py `_agent_read_file`, `_planner_dependency_fingerprint`, `_run_agent_task_impl` — формирование observed_state_sha256 и consistency_tool_facts после dispatcher; task_planner.py `evidence_dependency_state_fingerprint` / `_matched_evidence_requirement_ids_for_stage`. Значимость: сервер заявляет свежий обязательный READ, который фактически не видел текущего содержимого.

**Минимальный будущий patch, НЕ применён:** строить observation fingerprint из того же наблюдения/байтов, что породили tool result (для READ — content_sha256 и canonical target/exists). Отдельный текущий snapshot использовать только для сравнения, не для присвоения старому result нового observed_state. При несовпадении reopen generation / запрос fresh proof или явный BLOCKED; проверить read_file_range/find_text/list_dir тем же принципом. Простой дополнительный post-read snapshot сам по себе проблему не решает, если им снова маркируется старый material.

#### S0-F02 — HIGH: старый положительный equals сертифицирует уже неверный target

**Repro:** `KernelBoundaryTests.test_verify_change_before_fingerprint_cannot_certify_old_predicate`. Файл физически записан как `done\n` с newline="", real verify(kind=equals,value="done\n") возвращает true; до binding wrapper меняет target на `WRONG`. Положительный control `test_positive_exact_verify_control_for_fingerprint_race` с теми же исходными bytes/args без изменения проходит.

**Факт:** packet verification.passed=true и actual_sha256=`SHA256("done\n")`, но observed_state относится к `WRONG`; mock Dredd=1, SUCCESS=1. Это не смешение contains/equals и не Windows newline artifact. Причина общая с F01, но проверяется более сильный детерминированный predicate.

**Источник:** server.py `_agent_verify_file_content`, post-dispatch observed_state binding; task_planner.py matcher и freshness. **Будущий patch:** bind VERIFY к actual observation, включая exists/actual_sha256 и args fingerprint; при current state mismatch обязательный свежий VERIFY. Для exists/absent отдельно зафиксировать наблюдаемую existence; для directory/multi-path dependencies не притворяться, что file-only fingerprint универсален. F01/F02 — одна обязательная область исправления и два независимых repro, а не два разных архитектурных механизма.

#### S0-F03 — HIGH: недоступный Run Store не блокирует защищённый SUCCESS

**Repro:** `KernelBoundaryTests.test_missing_recorder_cannot_return_certified_success`: constructor `AuditThreadRecorder` выдаёт OSError, имитируя недоступное хранилище. READ и lifecycle работают в temp; result существует только в оперативном контуре.

**Факт:** audit_storage_error наблюдаем, `source_run_store_record_id=null`, но сгенерированный RAM `source_record_id=evidence_...` достаточен для complete=true / critical_for_success=false; mock Dredd=1, SUCCESS=1.

**Источник:** server.py `_run_agent_task_impl`, init AuditThreadRecorder (комментарий “Audit observability is not allowed to veto the Executor RUN”), `_emit`; `_final_audit_requirement_coverage` / packet completeness. Это действующий best-effort design, а не утверждение о случайной новой регрессии. Он не обеспечивает требуемую S0 гарантию сохранённого обязательного proof/recovery.

**Будущий patch:** разделить необязательную observability и обязательное evidence storage. Для protected requirement нужен успешно сохранённый и адресуемый outcome с RUN/plan/stage/generation/args/target identity; иначе critical_for_success до Dredd и запрет certified SUCCESS. Не превращать любой сбой cosmetic trace/UI logging в общий veto. UI/config в S0 не трогались.

#### S0-F04 — HIGH: потеря durable tool_finished оставляет ложную полноту packet

**Repro:** `KernelBoundaryTests.test_lost_tool_outcome_cannot_return_certified_success`: recorder создаётся, tool_started и другие события записываются; только `observe(tool_finished)` выдаёт OSError.

**Факт:** outcome pointer становится null; fault виден в событии, но completeness снова complete=true / critical_for_success=false; mock Dredd=1, SUCCESS=1. Сохранённый tool_started и RAM material не заменяют запись результата инструмента. Отдельная обычная положительная READ fixture проверяет, что непотерянный source действительно разрешается через load_run_record.

**Источник:** server.py `_emit`, обработка tool_result_record после tool_finished и присваивание source_run_store_record_id; task_planner.py matcher требует только непустой logical source_record_id; packet requirement coverage не проверяет durable outcome availability.

**Будущий patch:** сохранять обязательный outcome до удовлетворения requirement; проверять существование/целостность и точную identity адресуемой записи, а не только непустую строку-ID. Отклонять отсутствующий/недоступный/повреждённый outcome. Явно обрабатывать partial append/index failure и cancellation между mutation и receipt без автоматического retry mutation. F03/F04 — две точки отказа одной обязательной области storage.

**Рекомендация для независимой приёмки:** признать FINDINGS и не выдавать SUITABLE FOR NAMED NEW SCOPE до адресного исправления двух причин и повторной S0-проверки. Наличие 93 зелёных проверок не компенсирует четыре нарушения обязательных guarantees. Выпуск исправлений требует новой отдельно разрешённой TASK; её создание/старт здесь не выполнялись.

### 6. Доступные evidence / reproducibility

Финальный sandbox: `C:/Users/REX/AppData/Local/Temp/codex-rt002-s0-y3mo_q14/`.
- `result.json`: manifest всех 97 cases, фактические counts, isolation violations, events и packets четырёх repro; SHA-256 **72b278ab3cd4a42b735d180c33794179880d40482cb3dd1f52828b0aa0e0b848**.
- `unittest.log`: SHA-256 **9d28dcc90474fc683ff666263e76c1126f1aa78a79a0ce3c6eecb331d237d209**.
- Время runner 27.949 s. Случайные RUN/record IDs и время при повторе закономерно меняются; критерии counts/identity/гейтов остаются теми же.

Повтор: `C:/Users/REX/AppData/Local/Temp/codex-rt002-s0-ltmtrjzz/`.
- `result.json`: SHA-256 **95de5c259e67afccf2ce73c93575b17f39023e2938d6759a344853fb72d8cafd**.
- `unittest.log`: SHA-256 **0ff71ec5a138b610cca0882d4fbaebcf166f8d9bcba2e4811831c6b417e43153**.
- Время runner 2.612 s.

Доступность обоих JSON/log и соответствие log hashes проверены. Это временные локальные evidence, **не immutable archive и не SUBMITTED seal**. Внутренние temp workspaces отдельных fixtures очищаются; воспроизводимый test source и достаточные факты сохранены в разрешённых рабочих файлах. До внешней публикации/печати статус остаётся RESULT READY; номер коммита не придуман. Hash этой карточки публикуется отдельно от её собственных bytes.

### 7. Локальные source revisions (полные file-byte SHA-256)

Пути ниже относятся к `M:/GitHub/ag_llm/`; это точные байты локальных файлов, не Git blobs. Исходный snapshot карточки до ротации: **8ceb169dcafa555dcb67e278d939ae545e032ddbc6bdd70b5c7cae1113b5f4d7**. Финальная проверка охватывает 166 исходных файлов корня и документации: изменена только собственная карточка, остальные **165 byte-identical**; дополнительно создан один разрешённый test-файл. Production/config/transport/UI и существующие tests не изменены.

| Runtime / fixture source | SHA-256 |
|---|---|
| `audit_storage.py` | `15466977e17d2f48e377ccd9b77d7ecc01aaec82c2aabf4501f8cd3c11595905` |
| `planner_runtime.py` | `ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e` |
| `provider_accounting.py` | `dd83dbf7a22154347ac6f17ca2110e78757338248bd466f86a0d3599db510902` |
| `run_store.py` | `91f82db61a75980ebae8a0ee4e707ac2c09e33628021991d70d639b97b2eef44` |
| `server.py` | `404d43d6a39924a3a0d725650f0cf4ba67591bca13e071794ab4d576f378090a` |
| `task_planner.py` | `c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346` |
| `test_final_audit_recovery.py` | `8dc022756d5a3b4abb46c86d68f4ea0c9771b4ccba264253843b47b7ade32442` |
| `test_final_audit.py` | `1e7f883ab9579d9775e6f1603dea46dba37f6f95a8eccf5c1ef39846dd383c57` |
| `test_provider_accounting.py` | `5c16cc5ab0d55a9ca88720e4c1b42031f4c3cb5657501045403d235fddb00738` |
| `test_run_store_v2.py` | `28334ef3a59d8ed375eaca7e91e97048cd07f1fdd53526672391546e8fe4b4a2` |
| `test_stage_evidence_contract.py` | `3467538143c6b7bbab031211a9a6f8d18882899f3a60d877dcd4f91f6eaf12c9` |
| `test_task_planner.py` | `49ba81617fb85da8656e67db3613a7b641479ad3f177238ad736df6ae019cfa9` |
| `test_verifier_runtime.py` | `905b6b4cf5553b4f0cfd29edcf3157daa9faa4c78d96416323772880a520cd1a` |
| `verifier_runtime.py` | `7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228` |

| Нормативный source (Документация/) | SHA-256 |
|---|---|
| `000_Задачи для агента.md` | `159584416c3edc8d285143bf4e1349d51a8535753922608f1963a9782de30a12` |
| `01_Архитектура и текущее состояние.md` | `0d292f590dfce4f9a72abebb7067c2bbd8eaa1ead3d662ac227d586c4b6bc5da` |
| `08_Старт.md` | `143cd3fb5b7d22d8288726753bfaf248f4d8a5dcd7f2a4e96dd02ba629ce16b0` |
| `13_Архитектура оперативной верификации и контроля выполнения задач.md` | `994cd41a3ca460753b665c901667548f46462ebf2b2e7167341e7d9bae88f742` |
| `18_Регламент сопровождения документации.md` | `88fab7b4a23f1dda95ee1fc2c83417fc261333ffdcac1dfb6d8d21d3444c94aa` |
| `20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md` | `22c7786c41ce7000c640ac82f523270cc98f1e4287277fa1b02b4f15ffee048a` |
| `21_Журнал качественного перехода - решения, метрики и аудит.md` | `0c1b020bbe0661420b618e1afcd945479028dc58b5e87de57fd009c352b50793` |
| `28_Круглый стол - протокол и текущий вопрос.md` | `1cbb8d05596085955a22575e0c46cb3a3ee05f5bc4ef74515ea593feec8fe9d1` |
| `33.3_Круглый стол - итоговый план.md` | `c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf` |
| `34_TACTICAL_CONTEXT.md` | `a487b36fb181d0328ce772b7f681f5f963c9af881ea327638bef858a5c295e11` |

### 8. Closeout / DOC IMPACT / NEXT

**Rollback test changes:** удалить только созданный `test_rt002_s0_kernel.py`, если пользователь отклонит этот набор; runtime откатывать нечего. Возврат карточки возможен из сохранённой постановки БЛОКА 2 и архива REVIEW-1, без уничтожения factual result/истории; никаких reset/checkout. Временные sandbox logs можно удалить после независимой приёмки/сохранения нужных evidence, только по точным путям. Очистка сейчас не выполнялась.

**Documentation Change Impact:** нормативные Rule-ID/contract не изменены. Обязательные БЛОКИ 1/2/3 сохранены; S0 assignment скопирован полностью, REVIEW-1 БЛОКИ 2/3 сохранены отдельным архивом, прежние 151C/DOC-034 архивы — byte-exact. Текст до БЛОКА 1 сохранён byte-exact. Новых wiki/Markdown graph edges не добавлено, прежние ссылки не переименованы; механическая проверка структуры/сохранения выполнена. Это не визуальный Obsidian Graph PASS и не принятие старой DOC-034.

**SHARED DOC DELTA — передать ChatGPT после независимого рассмотрения:**
- 20 §5а / 21: зафиксировать локальный S0 result FINDINGS, 97=93+4 и четыре repro/two root causes; независимый verdict и возможные исправления записывать отдельно. Не выдавать старт S0 за его приёмку.
- общий 000 / 34: отразить ожидание независимой проверки/решения, не объявлять S1 или зависимые этапы разблокированными.
- 13: при подтверждении findings уточнить предел текущего observation binding / durable source guarantees; исправленный runtime описывать только после отдельной реализации и проверки.
- 28 / 33.3: утверждение B2 и immutable bytes не менять; результаты S0 не являются новой редакцией плана или принятием 151C. S13a ACCEPTED before S6b остаётся условием канонического маршрута.

Общие документы вне write-scope не правились. **DOC CLOSEOUT INCOMPLETE для общего контура:** ждёт решения и записей уполномоченного координатора; персональный factual handoff подготовлен.

**Строго ограниченный NEXT:** пользователь публикует локальные изменения; ChatGPT независимо проверяет source hashes, isolation/manifest, воспроизводит четыре failures и устанавливает S0 verdict. При подтверждении — согласовать отдельную TASK исправления двух причин и повтор S0. **Никакой S1+ здесь не начат; 151C PARKED / КТ-3 PENDING сохранены.**


---


```````

---

## ARCHIVED REVIEW-1 — прежние БЛОКИ 2/3 (сохранено при S0, 2026-10-10)

Ниже прежний closeout сохранён дословно; fenced snapshot не является новым назначением.

````text
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

**TASK:** CODEX-RT-002-PLAN-REVIEW-001 (историческая, сдана и внешне запечатана). Полная утверждённая постановка и closeout неизменно восстанавливаются из GitHub `main@cd48ff1629a8e04a734e36196d32ee52e37c103b` в старом БЛОКЕ 1; оригинальный документ результата — `33.1` immutable commit №238. Характер: REVIEW / NOT BLIND первоначального 33 по V1…V13 с 15 findings, DAG и A1…A8, без кода. **Планирование завершено, не исполнять повторно.**

---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

**TASK:** CODEX-RT-002-PLAN-REVIEW-001
**Статус:** SUBMITTED / EXTERNALLY SEALED (документальный REVIEW, не runtime DONE). **Result:** `33.1` Codex REVIEW-1, commit №238 `c6b910bde7280ace7250d032ba495554b6c41356`, 15 findings: 9 HIGH / 5 MEDIUM / 1 LOW; seal `28/SEAL-CODEX-REVIEW-1`. Итог B2 создан/утверждён человеком, но Codex-probes не являются независимым runtime PASS.
**Открыто:** CODEX-ULTRA-151C-RECOVERY-001 PARKED/KT-3 PENDING; CODEX-DOC-034-GRAPH-001 результат archived below, всё ещё требует отдельной независимой/визуальной проверки.
**NEXT:** только новая USER ASSIGNED `CODEX-RT002-S0-001` в БЛОКЕ 1.

---


````

## Архив приоритета 151C — решение пользователя 2026-10-10

`CODEX-ULTRA-151C-RECOVERY-001` снята из активного БЛОКА 1 **без признания DONE**. Первоначальная полная постановка и factual recovery-report сохранились неизменёнными в GitHub `main@27ddda0162959f23fabf92ea80a9a58006af93fc`, файл `Документация/000_Задачи Codex.md`, старый БЛОК 1. Результат 151C — `RESULT READY / AWAITING INDEPENDENT VERIFICATION` / КТ-3 `PENDING`; пользователь отложил эту отдельную приёмку и поручил сначала пересмотреть весь план RT-002. Это не означает принятия 151C и не отменяет требований доказательности для будущих TASK.

БЛОКИ 2–3 по `CODEX-DOC-034-GRAPH-001` — **исторический незакрытый RESULT READY**, сохранены без изменений. Следующая ротация только после безопасной координации, не перетирать историю автоматически.

## ARCHIVED DOC-034 — прежний БЛОК 2

**ИСТОРИЧЕСКАЯ КОПИЯ — НЕ CURRENT БЛОК**, original GitHub cd48ff1629a8e04a734e36196d32ee52e37c103b. История не является выполненной независимой приёмкой.

~~~~text
**TASK:** CODEX-DOC-034-GRAPH-001
**Статус:** APPROVED FOR EXECUTION (утверждённая постановка).
**ARCH CLASS:** Documentation / Obsidian Graph; архитектура и runtime не меняются.
**PRIMARY PROFILE:** 18_Регламент сопровождения документации.md.
**CHECK 01:** выполнен; архитектурного влияния нет.
**REGISTRY IMPACT:** NO — сохранить существующую связь 05 → 34.
**CONTEXT LIBRARY IMPACT:** NO — библиотека 14–16 и модельный prompt не затрагиваются.
**DOC IMPACT:** 00, 08, 34 и персональная карточка Codex; правила сопровождения 18 сохраняются.
**Baseline:** HEAD 3b5ab323446c16cacadf9ce2c796af8b8d75c85a; исходные пользовательские изменения .obsidian/graph.json и .obsidian/workspace.json сохраняются.

TASK: CODEX-DOC-034-GRAPH-001 — Исправление связей Tactical Context в Obsidian
Исполнитель: Codex
Проект: ag_llm
Тип: Documentation / Obsidian Graph
Статус: APPROVED FOR EXECUTION
Основание: прямое поручение пользователя в текущем чате.
1. Цель
Исправить связи документа 34_TACTICAL_CONTEXT.md в графе Obsidian.
Требуемая схема:
00_Главная - карта проекта
          │
          ▼
05_Реестр задач
          │
          ▼
34_TACTICAL_CONTEXT

Документ 34_TACTICAL_CONTEXT.md должен иметь ровно одну связь — с 05_Реестр задач.md.
Никаких других связей у документа 34 быть не должно.
2. Что необходимо сделать
1. Открыть репозиторий ag_llm и ознакомиться с Документация/08_Старт.md, глобальным 000_Задачи для агента.md, 34_TACTICAL_CONTEXT.md и правилами документации.
2. Найти все входящие и исходящие связи документа 34_TACTICAL_CONTEXT.md во всём Obsidian Vault.
3. Удалить лишние Wiki Links и Markdown-ссылки, создающие рёбра графа между документом 34 и другими документами.
4. Сохранить связь 05_Реестр задач.md → 34_TACTICAL_CONTEXT.md.
5. Убедиться, что 00_Главная - карта проекта.md связан с 05_Реестр задач.md.
6. Удалить прямую связь 00_Главная - карта проекта.md → 34_TACTICAL_CONTEXT.md, если она существует.
7. Проверить YAML frontmatter документа 34. Если теги continuity, tactical-context или другие метаданные создают дополнительные узлы и связи в графе, убрать соответствующие теги.
8. Убедиться, что другие документы не создают обратных ссылок на 34.
Важно: обычные текстовые упоминания документа 34 удалять не требуется. Если ссылка нужна для инструкции или маршрута чтения, заменить её на обычное текстовое название файла без создания ребра Obsidian Graph.
3. Обязательные ограничения
- Не удалять сам документ 34_TACTICAL_CONTEXT.md.
- Не удалять его оперативный контекст, сведения о задачах, статусах и правилах обновления.
- Не нарушать регламент постоянного сопровождения Tactical Context.
- Не изменять связи между другими документами, кроме необходимого восстановления цепочки 00 → 05 → 34.
- Не менять программный код, runtime и тесты проекта.
- Не сбрасывать настройки Obsidian Graph для маскировки лишних связей. Исправить именно источники этих связей.
- Не выполнять commit/push — это сделает пользователь.
4. Критерии приёмки
После выполнения в Obsidian Graph:
Должно быть:
00_Главная - карта проекта ↔ 05_Реестр задач ↔ 34_TACTICAL_CONTEXT
Не должно быть:
Прямых связей документа 34 с 000_Задачи для агента, 01_Архитектура, 06_Журнал, 08_Старт, 18_Регламент, 23, 24, 25 или любыми другими документами.
Также не должно оставаться связей документа 34 с узлами тегов.
Итог: у узла 34_TACTICAL_CONTEXT должна быть ровно одна связь — с 05_Реестр задач.
5. Порядок выполнения и отчёт
Codex, прочитай эту задачу непосредственно из текущего чата и приступай к исполнению. Дополнительного подтверждения в рамках указанного scope не требуется.
Соблюдай установленный документационный workflow проекта, включая персональную карточку 000_Задачи Codex.md.
После изменений:
1. Проверь ссылки и обратные ссылки по всему Vault.
2. Проверь отсутствие нежелательных связей через YAML-теги.
3. Убедись, что содержание Tactical Context не потеряно.
4. Проверь git diff --check.
5. Подготовь отчёт: какие файлы изменены, какие связи удалены, какие сохранены.
6. Если доступна проверка непосредственно в Obsidian Graph, выполни её. Иначе явно укажи, что проверена структура Markdown, но не визуальное отображение.
Результат передать на независимую проверку ChatGPT.
Код проекта не затрагивать. Не выполнять никаких дополнительных улучшений вне этой задачи.
Codex: задача утверждена пользователем. Прочитай постановку выше, выполни её самостоятельно и предоставь результат для проверки.

---
~~~~


## ARCHIVED DOC-034 — прежний БЛОК 3

**ИСТОРИЧЕСКАЯ КОПИЯ — НЕ CURRENT БЛОК**, original GitHub cd48ff1629a8e04a734e36196d32ee52e37c103b. История не является выполненной независимой приёмкой.

~~~~text
**TASK:** CODEX-DOC-034-GRAPH-001
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**Дата:** 2026-10-09.
**Baseline:** main, HEAD 3b5ab323446c16cacadf9ce2c796af8b8d75c85a; commit/push не выполнялись.

**Результат:** по структуре Markdown цепочка 00 ↔ 05 ↔ 34 сохранена, у узла 34 ровно один уникальный сосед — 05_Реестр задач.md. Сохранены исходная ссылка 05 → 34 и обе существовавшие ссылки 34 → 05; три вхождения ссылок образуют одно ребро, а не три разных соседа.

**Изменены только четыре Markdown-файла:**

- Документация/00_Главная - карта проекта.md — ссылка на 34 заменена текстовым именем файла; существующие ссылки на 05 сохранены.
- Документация/08_Старт.md — ссылка на 34 заменена текстовым именем файла; обязательный маршрут чтения и closeout сохранены.
- Документация/34_TACTICAL_CONTEXT.md — 11 исходящих ссылок на другие документы заменены текстовыми именами файлов, удалены YAML-теги project/continuity и project/tactical-context; aliases сохранены. Выполнен обязательный delta-handoff: текущая документальная TASK, сверка Git, NEXT и последний handoff; оперативные задачи, статусы, открытые вопросы и правила сопровождения сохранены.
- Документация/000_Задачи Codex.md — полная утверждённая постановка сохранена в БЛОКЕ 2, factual result в БЛОКЕ 3; БЛОК 1 возвращён в ожидание после проверки сохранённых блоков.

**Удалены:** 13 вхождений Wiki Links, образовавших 9 лишних рёбер между 34 и документами 00, 000, 01, 06, 08, 18, 23, 24, 25. Новых рёбер нет. Markdown-ссылок на 34, требующих удаления, не обнаружено. Теги 34 удалены из источника, настройки графа не менялись.

**Проверки:** весь Vault, включая скрытые/ignored каталоги, кроме служебной .git: 301 Markdown-файл, 0 Canvas, 0 символических ссылок; обработаны Wiki Links, Markdown/HTML-ссылки, reference links, пути/расширения/URL encoding и aliases. После изменений остался только источник входящей ссылки 05; исходящие ссылки 34 ведут только в 05. YAML/inline tags у 34 отсутствуют. Полный набор остальных рёбер совпадает с исходным. Loss check: после исключения разрешённых замен ссылок/тегов и трёх closeout-дельт с одной актуальной Git-сверкой весь остальной текст 34 совпадает с исходным. Все семь разделов, карта чтения и регламент DELTA сохранены. Реестр 05 и регламент 18 побайтово не менялись. SHA-256 остальных 1 207 tracked-файлов совпали со снимком на входе. git diff --check — PASS.

**Границы и риски:** структура Markdown проверена, визуальное отображение Obsidian Graph не проверено: доступного управления Obsidian/CLI в текущем окружении нет. Независимый PASS ещё не получен. На входе уже были изменены .obsidian/graph.json и .obsidian/workspace.json; их текущие байты сохранены. Код, runtime, тесты, Alarm, глобальная карточка и канонические журналы не изменялись; новые файлы не создавались. Git HEAD/index не менялись.

**DOC IMPACT:** 00, 08, 34, персональная карточка Codex. REGISTRY IMPACT: NO — существующая связь 05 сохранена без изменения реестра. CONTEXT LIBRARY IMPACT: NO — библиотека 14–16 и runtime prompt не затронуты.

**NEXT:** независимая проверка ChatGPT по этой постановке и diff, затем визуально подтвердить в Obsidian Graph единственного соседа 34 — реестр 05; commit/push выполняет пользователь. Статус не повышать до DONE / VERIFIED до принятого независимого PASS.
~~~~

