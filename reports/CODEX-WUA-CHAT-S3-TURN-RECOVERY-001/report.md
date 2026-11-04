# CODEX-WUA-CHAT-S3-TURN-RECOVERY-001 — проверка prerequisites этапа 3

STATUS: PARTIAL / RUN STORE BLOCKED / AWAITING INDEPENDENT REVIEW.
Исполнитель: Codex 007. Координатор: ChatGPT WEB22. 04.11.2026, Windows 10 19045.
Итерация диагностики и разрешённые проверки завершены. Stage3 не реализован и не объявляется принятым.
Git/GitHub, реальные provider/OAuth/LLM-запросы и изменение пользовательского сервера не выполнялись.

## Результат и решение по scope

Подтверждены два блокера существующего общего Run Store, перечисленные в TASK §4.4: запись через `.ultra/audit` junction вне Workspace и конкурентные записи одного RUN с одинаковым sequence. Текущая TASK разрешает только чтение `run_store.py`. По прямому условию §4.4/§6/§9 зависимая реализация Turn/attempt/recovery остановлена, сохранены воспроизводимые RED и конкретное предложение отдельного ремонта.

**Продуктовые файлы не изменены.** В проект добавлен только разрешённый `test_web_alarm_ultra_chat_turn.py` и этот пакет. Новые Turn API, устойчивые записи Turn, RUN-адаптер исполнения, имитатор и TEST-composer не выпускались. Текущая отправка в UI остаётся disabled. Принятие новых сообщений с последующим небезопасным RUN не включалось: это оставило бы новый durable lifecycle без проверяемого пути исполнения/результата. Второго Run Store, подмены audit-каталога или альтернативного journal не создавалось.

Закрытая безопасная часть: исследование контрактов, два воспроизведения с реальными Windows-файлами/процессами, положительный контроль прежнего RUN, полная адресная регрессия существующего UX/storage/P9, проект общего Turn-контракта и карта проверок. Это законченная **PARTIAL-итерация**, а не незавершённый зелёный Stage3.

## Локальная база и чтение

Reference revision `main@e6715314cc5fc980b0a2b704685c5275f4edf8b5` взята из пользовательской постановки; локальное соответствие Git SHA не проверялось, Git запрещён. Источник доказательств — сохранённые текущие bytes/SHA. До записи теста сохранены 15 адресных файлов в `before/*.source.txt`, а также fingerprint 611 защищённых файлов в `evidence/baseline.json`. Прежний UX-пакет/поправки не откатывались.

Прочитаны текущий БЛОК 1/правила/относящийся БЛОК 4; №08 (роль/безопасность/сдача); №18 (DOC-BLOCK1-SLOT-01@2, Git/сдача/launcher/read scope); №37 §2.3/2.4 и этапы 3–7; №03 (Workspace/Chat identities, RAW, producer, Working Representation, Project/Message Context); №34/40 (актуальные owners и OPEN); только связанные FOLLOWUP №05; применимые TEST-* №36.1 и UL-I01/07/08/10/11 №36.3, scope/oracle №36.2. Из кода исследованы `context_storage.commit_raw_message`, общий writer lock/no-follow/publish/readback, Run Store summary/index/stream и `UltraConnectionService.selection('chat')`. Полные исторические архивы не сканировались.

Наблюдение по источникам: №34/40 содержат старую формулировку Stage3 HOLD/WAITING после предыдущего UX. Это не отменяет новый прямой USER GO в действующем БЛОКЕ 1; реальные P9/storage gates остаются обязательными, как требует сама новая TASK.

## Воспроизведённые дефекты

### S3-B01 / FOLLOWUP-WUA-P9-AUDIT-PATH-001

`run_store.audit_root()` строит `<root>/.ultra/audit`; `_index_lock` защищает `.ultra/locks`, но не проверяет audit directory. `create_run_summary()` через `_atomic_json` создаёт родительские каталоги и обычный файл по этому пути, следуя junction.

Oracle `TurnPrerequisiteTests.test_audit_junction_must_not_write_outside_workspace` создаёт валидный синтетический Workspace/Chat и собственный Windows junction `.ultra/audit → <owned TEMP>/outside`. Внешняя цель — отдельная папка внутри того же выделенного TEMP, не пользовательский каталог. До вызова там только `untouched.txt`. После обычного `create_run_summary` там появились `index.json` и `<chat_id>/run_s3/summary.json`, отказа не было. Ожидание «внешние bytes/набор файлов не меняются» даёт FAIL. Исходный marker не повреждён. `evidence/prerequisites_oracles_final/audit_path.json`, raw stdout в `prerequisites_guarded_final.txt`.

Это фактический дефект, а не гипотеза или ссылка на старый report. Для приёма/исполнения Turn нельзя считать такой audit writer безопасной границей. Обход в `ultra_turn.py` или переключение на второй store не является ремонтом общего писателя.

### S3-B02 / FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001

`append_run_record()` получает `_next_sequence`, затем пишет stream и индекс без Workspace/per-RUN lock. Два настоящих Python-процесса пишут один синтетический RUN. Первый останавливается после прочтения следующего sequence; второй успевает подтвердить запись; затем первый продолжает. Оба процесса заканчивают с exit 0, оба receipt возвращают sequence 1. Реальный `records.idx.jsonl` содержит `[1,1]`, а независимый oracle требует `[1,2]` либо явного отказа второго писателя.

Тест `test_same_run_two_processes_have_unique_sequences_or_visible_refusal` допускает будущую сериализацию или bounded WorkspaceBusyError; он не требует входа обоих процессов под один искусственный barrier, который ломал бы корректный mutex. Phase marker подтверждён. Сохранены raw index records, SHA, receipts и порядок фаз: `evidence/prerequisites_oracles_final/same_run_writers.json`.

Индексная регрессия P9 21/21 PASS не покрывала этот механизм; её зелёный результат не снимает найденный RED. Проверка `normal_run_roundtrip_uses_existing_store` отдельно PASS: record читается по своему SHA, summary сохраняет Workspace ID, общий Chat читабелен.

## Команды и результаты

Python 3.12.10 из `.venv`, Node v22.20.0, pytest 9.1.1. Все процессы завершены; собственные TEMP/junction удалены штатным fixture cleanup.

| Проверка | Результат / evidence |
| --- | --- |
| Исходный prerequisite запуск без test guard | 3 collected / 1 PASS / 2 FAIL / 0 ERROR / 0 SKIP, unittest exit 1; `prerequisites_red.json/.txt` |
| `run_checks.py prerequisites --label final` | 3 collected / 1 PASS / 2 FAIL / 0 ERROR / 0 SKIP, exit 1; оба дефекта по-прежнему RED; guard 3 receipts, 0 denials |
| `run_checks.py js` | 158 collected / 158 PASS / 0 SKIP, exit 0; прежний Ultra Chat + operator + EVM |
| `run_checks.py python --label final` | 171 collected / 166 PASS / 5 SKIP / 0 FAIL / 0 ERROR, exit 0; HTTP/UI, общее storage/read, registry и folder-picker |
| `run_checks.py run_store --label final_v3` | pytest `test_run_store_v2.py`: 21 PASS, exit 0; 13 guard receipts, 0 denials |
| Compile/syntax/launcher | `ast.parse` + `compile` новых Python в памяти; поставляемый JS `node --check`: exit 0; `syntax_launcher.json` |

Для всех команд выше префикс: `.venv/Scripts/python.exe -B -X utf8 reports/CODEX-WUA-CHAT-S3-TURN-RECOVERY-001/`. Новые RED не XFAIL/skip и не «исправлены» ослаблением oracle. Результаты повторов не суммируются. Пять SKIP существующего набора — права Windows на symlink, junction/hardlink checks выполнены.

### Ошибки нового guard — сохранённые отдельные harness failures

Первый guard ошибочно распознавал `executable=None` в Windows `subprocess.Popen`: prerequisite 1 FAIL/1 ERROR, Python 27 ERROR/5 SKIP, P9 6 FAIL/15 PASS. Это ошибки нового test harness, не новые продуктовые дефекты. Исправление v2 разрешило Python children, prerequisite RED и Python regression стали достоверны, но P9 дал 4 harness FAIL/17 PASS: POSIX shlex разбирал Windows `-c` payload с кавычками. Итоговый v3 разбирает только executable prefix, а не тело программы; 6 чистых parser cases PASS без запуска процессов. P9 повторён и прошёл. Первые stdout/stderr/JSON и обе версии guard сохранены в `evidence/initial_guard/`, `initial_guard_v2/`; новые прогоны имеют отдельные имена. Продукт не менялся между ними.

### Изоляция и ноль provider calls

Ни имитатор исполнения, ни provider transport не подключались. Пробы выполняют только shared storage/Run Store над синтетическими данными. В JS используется прежний fixture-fetch. Python audit guard установлен до runtime imports и унаследован детьми: внешние socket/DNS, Git metadata и неразрешённые executables запрещены; loopback оставлен для собственных HTTP-fixtures. Новые child-пробы дополнительно запрещают любые sockets. В достоверных финальных прогонах guard denials = 0. Реальных GigaChat/Ollama/Colibri/OAuth/MCP вызовов — 0. Это не результат вызова модели с «нулевым usage»: никакого реального вызова не запускалось.

## Обязательные Stage3-сценарии и NOT RUN

`risk_test_matrix.md` адресно покрывает все 14 требований TASK §7. Продуктовые сценарии Turn idempotency, два HTTP клиента одного ключа, новый ключ того же текста, Turn/RAW crash/restart, lost response recovery, поздний/повторный ответ, cancel/UNKNOWN, model/context snapshot и новый TEST-composer — **NOT RUN / DEPENDENCY BLOCKED**, поскольку соответствующая реализация остановлена до небезопасной RUN-интеграции. Эти пункты не объявляются покрытыми старой регрессией RAW/Chat.

Реальный browser/TEST-UI, запуск имитатора, независимый Stage3 runtime и CI — NOT RUN. Детерминированные процессы в prerequisite oracle воспроизводят ошибки storage и не являются имитатором полного Turn.

## MANUAL ENGINEERING REVIEW

Просмотрены отдельно: границы общего Workspace lock и незащищённого append, порядок получения sequence → stream fsync → index fsync; audit/index/summary path construction; общий core no-follow/expected identity; receipt/readback и восстановление partial stream/index; model selection против разрешённого контекста; различие RAW и Working Representation; cancel до/после начала. Ранняя гипотеза «P9 уже сериализует все RUN mutations» отвергнута кодом и двумя process receipts. Гипотеза «lock на `.ultra/locks` одновременно защищает audit path» отвергнута junction oracle. Положительный normal roundtrip показывает, что ошибки относятся к этим границам, а не ко всем RUN.

Стадия после stream append до index commit остаётся отдельным crash window, не закрывается одной блокировкой. Вложенные audit child paths, file handles, revisions/offsets и переносимость требуют согласованного ремонта общего Run Store. Staging/first-Chat crash hypotheses из `FOLLOWUP-WUA-S2-CHAT-STAGING-001` и `FOLLOWUP-WUA-CHAT-UX-CRASH-001` не воспроизводились заново и остаются OPEN; их статус не повышен до доказанного дефекта. Полный Stage3 в безопасном виде не обоснован.

Предложение — `proposed_run_store_NOT_APPLIED.patch` и `followup_request.md`. Patch конкретно показывает места audit preflight и сериализации append; он не применён, не исполнялся и не выдаётся за полный hardening. Нужна отдельная адресная USER TASK на read-only сейчас `run_store.py` и относящиеся тесты. Контракт будущего Turn/state/recovery — `turn_contract.md`, DESIGN ONLY; рабочие Turn-файлы не создавались.

## Сохранность и STANDARD

Проверяются точные bytes 15 входных файлов и всех пользовательских history файлов относительно baseline. Код продукта/core/run_store/предыдущие тесты/launcher не изменялись. Все реальные `.ultra`, `Чат_pro`, `Чат_Pro_01` использовались только для hash readback, не для tests. Приватные сообщения не скопированы в пакет. Настройки открытого Obsidian не записывались агентом и не восстанавливаются поверх текущих значений. Фактический итог — `user_data_readback.json`, `package_readback.json`.

`launch_config.json` active=standard; target `web_alarm.server`. Launcher/профиль не переключались, пользовательский Web Alarm не останавливался/не перезапускался, стандартный порт не занимался новым сервером. Тестовые HTTP-fixtures выбирали свободный port 0. Визуальная зелёная STANDARD-проверка — NOT RUN; отсутствие переключения подтверждено исходными SHA.

## DOC IMPACT / передача WEB22

Координатору после независимого review: обновить фактические статусы `FOLLOWUP-WUA-P9-AUDIT-PATH-001` и `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001` по новым воспроизведениям; для второго теперь есть доказанный дефект sequences, а не только verification gap. P9 bounded source/index acceptance не отменяется, полный RUN writer не объявляется безопасным. Сохранить Stage3 OPEN и все NOT RUN, назначить отдельный prerequisite repair; затем новое продолжение Stage3. Указать точные local source hashes до публикации, не выдавать task reference SHA за проверенный Git.

БЛОКИ 2–4, история №001 и общие №05/06/34/40 не редактировались. Self-check не является независимым verdict. Копируемый итог для WEB22 — `handoff_to_coordinator.txt`; прямого обращения к веб-координатору/вызова другой LLM не было.

## Штатный finish

После готового PARTIAL-пакета выполнен предусмотренный TASK `python -B tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id CODEX-WUA-CHAT-S3-TURN-RECOVERY-001 --no-chat-amendment --apply --headless`. Новых chat-only поправок к постановке не получено. Это попытка сдачи локальной диагностической итерации, не завершение Stage3.

**Итог: NO ROTATE / NO_TASK_ID, exit 3**, на этапе check. В БЛОКЕ 1 ID записан строкой `# TASK ID: CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`, а `tools/task_slot_rotate.py:67,185–210` распознаёт объявление с backticks и без Markdown heading prefix. Наличие правильного ID в аргументе команды не обходит проверку исходной постановки. Apply/readback ротации не выполнялись, новый `handoff_task.md` скриптом не создан. Карточка полностью совпадает с исходной: SHA `dad9380b0b4ada7a421298eed7ebb6d20c132d08aef747f835ab53f54270a73b`, 50479 bytes. Её точные bytes и полная постановка сохранены в `before/Документация/000_Задачи Codex.md.source.txt`.

В scope карточка и инструмент read-only. Не добавлялись/не переписывались строки ID ради обхода; БЛОКИ 1/1.1 и прежний snapshot остались на месте. `evidence/finish.json`, `finish_execution.json` и `card_readback.json` фиксируют отказ/сохранность. Права Windows и атомарный writer не менялись; до операции записи этот запуск не дошёл.

Пользователю для отдельного разрешённого исправления формата: заменить только объявление ID на `**TASK ID:** ` с этим же ID внутри backticks, сохранив всю постановку; готовая строка — `slot_format_request.txt`. Затем повторить **тот же штатный finish**, без ручного переноса. Это административный blocker сдачи слота, отдельно от технических Run Store blockers.

Финальный readback: 586 файлов `.ultra`, 9 `Чат_pro`, 6 `Чат_Pro_01` — все 601 history-файл совпали; добавлений нет. Из 10 файлов `.obsidian` изменялся только `workspace.json`, агент его не записывал и не откатывал. Все 14 существовавших кодовых/тестовых/launcher/instrument файлов из baseline совпали побайтово; карточка также неизменна. `evidence/package_readback.json`, обновлённый manifest.
