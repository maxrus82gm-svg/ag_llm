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

**TASK:** CODEX-ULTRA-151C-RECOVERY-001 — TASK 151C / KT-3: Recovery, Independent Code Audit & Closure.
**Приоритет новой границы полномочий (не переписывает историю исполнения):** эта TASK уже получила RESULT READY и не должна запускаться повторно самовольно. Упомянутые ниже в первоначальной постановке `HEAD/history/git diff --check/Git state` описывают прежний baseline, historical evidence и старый тестовый маршрут; для любого нового действия действует `DOC-GIT-01@1`, сведения Git запрашиваются у координатора/пользователя. Не стирать БЛОКИ 2–3 и не переводить КТ-3 в DONE без независимой проверки.

**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION (2026-10-09; USER APPROVED). Исполнитель Codex; независимый verifier и владелец общей документации — ChatGPT.
**Предыдущая задача:** CODEX-DOC-034-GRAPH-001 остаётся в БЛОКАХ 2–3 в статусе RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не стирать и не повышать её статус без проверки. Пользователь явно разрешил запуск новой работы параллельно ожидающей приёмке.

## Цель
Проверить существующую реализацию TASK 151C (Compact Final Audit Packet + Task-scoped Git Evidence / КТ-3), найти оставшиеся реальные дефекты, исправить только подтверждённые в пределах разрешённого Ultra scope, предоставить evidence-backed отчёт для независимой приёмки. НЕ реализовывать с нуля и НЕ объявлять DONE/VERIFIED самостоятельно.

## Источник и baseline
Корень: M:\GitHub\ag_llm.
Важный implementation commit: deef0adc7f1a9b36134c3ed0fd7851c893aae046 (№140 от 2026-10-03).
Актуальные HEAD / рабочую копию / историю после №140 определить самостоятельно на старте; не считать №140 текущим HEAD.
Маршрут: 08_Старт.md → 000_Задачи для агента.md → 000_Задачи Codex.md → 18_Регламент сопровождения документации.md → 01_Архитектура и текущее состояние.md → 13 / 20 / 21.
PRIMARY: 13_Архитектура оперативной верификации и контроля выполнения задач.md.
SECONDARY: 20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md; 21_Журнал качественного перехода - решения, метрики и аудит.md; 03 по необходимости.

## Обязательная аналитика
1. Сверить committed/runtime baseline, TASK 151B freshness, 151C code/verification gaps, актуальную документацию и результаты предыдущих tests.
2. Независимо оценить Final Audit packet: RAW TASK; accepted task plan; active requirements; requirement-to-evidence coverage; mutation receipts; exact verification; freshness source identity; task-relevant conflicting/negative/external/unattributed facts; candidate final; completeness metadata.
3. Убедиться, что Server mechanical completeness fail-closed ДО Dredd и не допускает false PASS.
4. Проверить task-scoped Git: отсутствие workspace-wide diff в default; no-path NOT_APPLICABLE; delete/move/rename, directories, untracked/ignored, path scope, no RUN ownership inference from Git alone.
5. Проверить large outputs / truncated material / deduplication / item+packet budgets, preservation of relevant evidence, run-store reproducibility and source identifiers.
6. Проверить freshness revalidation before/after Final Audit packet and fail-closed on drift.
7. Провести adversarial review сверх уже существующих tests. Найти и устранить только воспроизводимые реальные дефекты Ultra.
8. Проверки offline: targeted regressions; expanded Final Audit/Planner/freshness/Run Store; full unittest; py_compile; UI smoke; git diff --check. Точные числа, failures/skip и ограничения отразить в отчёте.

## Границы / параллельная работа
Claude параллельно работает над Web Alarm WA4-E. Не менять web_alarm/*, профильные 23/24/25, персональную карточку Claude, код/tests/неоткоммиченные изменения Claude. Ultra code targets: server.py, task_planner.py, verifier_runtime.py и соответствующие regression tests.
Общие документы 000 (глобальный), 00, 01, 04, 05, 06, 08, 18, 34 — ТОЛЬКО ChatGPT-координатор. Codex их читает и передаёт proposed changes в DOC IMPACT.
Документы 13/20/21 Codex ведёт исключительно в Ultra scope, не затирая изменения другого автора.
Изоляция рабочей копии приветствуется. Никаких reset/clean/stash/add -A/commit/push/pull, переписывания истории или захвата чужого scope без отдельного разрешения. Не запускать live paid Ultra, R-027/R-031 stress; они относятся к будущей TASK 151G.
Если исправления нельзя безопасно изолировать, STOP before mutation и предложить конкретный безопасный путь.

## Закрытие / отчёт
До любых правок: baseline report + findings + минимальный design. Далее только justified targeted repairs and regression.
Результат: RESULT READY / AWAITING INDEPENDENT VERIFICATION, не DONE. В итоговом отчёте: точные пути и изменения, tests с числами и exit code, оставшиеся риски, Git state, DOC IMPACT, NEXT. Никаких commit/push. Общие документы не редактировать.
Только независимая приёмка ChatGPT может подтвердить КТ-3 DONE. После принятия NEXT = TASK 151D — Server Direct Exact Evidence.

## Baseline report / findings / minimal design — 2026-10-09

**ARCH CLASS:** Quality Transition / Final Audit / Evidence Packaging / Runtime Efficiency.
**PRIMARY PROFILE:** 13_Архитектура оперативной верификации и контроля выполнения задач.md.
**Baseline:** main, a142817b33964691584aadbd6ea6464779df1815 (177). Целевой Ultra implementation остаётся байтово на deef0adc7f1a9b36134c3ed0fd7851c893aae046; после него нет изменений server.py / task_planner.py / verifier_runtime.py и трёх исходных regression modules. На входе изменены .obsidian/graph.json, .obsidian/workspace.json, персональная карточка Codex и глобальный 000; они сохраняются.
**Изоляция:** C:\Users\REX\.codex\worktrees\ultra151c-recovery\ag_llm, от указанного HEAD. Tests/probes используют временный LOCALAPPDATA и запрет внешних socket connections. Live paid Ultra, runtime Web Alarm и R-027/R-031 не запускаются.
**Baseline tests:** проектный .venv Python — 187 tests OK, exit 0 (Final Audit / Planner / freshness / Verifier / Run Store). Первая попытка на системном Python 3.13 дала 4 import errors из-за отсутствующего httpx; это ошибка окружения, затем использован штатный проектный venv без установки зависимостей.
**Подтверждённые findings до code edits:**
1. Первое exploratory read 9 000 bytes усекается без requirement; следующее обязательное чтение того же результата дедуплицируется и обходит completeness: Dredd вызван 1 раз, mock PASS принят, critical_for_success=false.
2. После внешнего изменения большого файла на короткое содержимое freshness повышает generation и получает fresh read; старое усечённое material всё равно ошибочно блокирует Final Audit.
3. Task path target[1].txt включает в реальный Git status также чужой target1.txt: Git интерпретирует filename как pattern.
4. Clipping при лимитах 0–40 bytes возвращает 41-byte marker; при разрыве UTF-8 лимит 42 даёт 44 bytes с replacement character.
5. Failed equals → successful sha256: compact packet теряет failed expected/actual hashes и детали error; source_run_store_record_id отрицательного результата ведёт в tool_started вместо outcome record.
**Минимальный design:** только server.py + соответствующий regression module: literal pathspecs; strict UTF-8 byte limit; mandatory material привязать к текущим source IDs/generation, выделять его до exploratory material, переносить полноту и source ID при dedup; negative exact material и полный outcome хранить с правильной ссылкой Run Store. Freshness, permissions, RAW TASK, Planner contract, paid/live policy и роли не ослаблять.
**Documentation Block:** DOC IMPACT YES — профильные 13/20/21 и эта карточка. CURRENT STATE/ARCHITECTURE IMPACT YES — источники/полнота Final Audit packet; CONTEXT LIBRARY IMPACT NO; REGISTRY/ROUTING IMPACT NO; NEW DOCUMENT REQUIRED NO (кроме необходимого regression test). Общие 000/00/01/04/05/06/08/18/34 — только proposed changes для ChatGPT.
**Предыдущий pending result:** БЛОКИ 2–3 задачи CODEX-DOC-034-GRAPH-001 сохраняются целиком; без independent PASS не перезаписывать их ротацией текущего recovery.

## Factual recovery result — 2026-10-09

**TASK:** CODEX-ULTRA-151C-RECOVERY-001.
**Статус результата:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. КТ-3 остаётся PENDING, приёмка — ChatGPT.
**Изменения:** устранены 8 классов defects: dedup completeness bypass; stale material false block; Git pattern scope leak; UTF-8 byte overrun; потеря negative exact/empty-search facts и неверный Run Store outcome pointer; потеря upstream truncation; directory/Git-state freshness; молчаливое усечение model stage result. Подробная factual запись, воспроизведение и ограничения — в профильном документе 21.
**Design delta после дополнительных findings:** task_planner.py получает optional typed dependency callback без ослабления file-only persistence; полный model stage result сохраняется в task-plan state, explicit audit projection ограничена 8 KiB и fail-closed для required model_result. Все outcome summaries, включая count=0, сохраняются отдельно от preview budget. Права Executor на directory git_diff не расширены. Verifier protocol и 151D не менялись.
**Целевые файлы:**

- M:\GitHub\ag_llm\server.py
- M:\GitHub\ag_llm\task_planner.py
- M:\GitHub\ag_llm\test_final_audit_recovery.py
- M:\GitHub\ag_llm\Документация\13_Архитектура оперативной верификации и контроля выполнения задач.md
- M:\GitHub\ag_llm\Документация\20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md
- M:\GitHub\ag_llm\Документация\21_Журнал качественного перехода - решения, метрики и аудит.md
- M:\GitHub\ag_llm\Документация\000_Задачи Codex.md.

| Проверка | Результат | Exit code |
| --- | --- | --- |
| Baseline: Final Audit / Planner / freshness / Verifier / Run Store | 187 tests OK; 49.067 s | 0 |
| Окончательные targeted recovery regressions | 24 tests OK; 10.682 s; failures/errors/skip 0 | 0 |
| Окончательные expanded Ultra / Audit / Planner / Run Store | 276 tests OK; 62.260 s; failures/errors/skip 0 | 0 |
| Окончательный full unittest discovery | 1000 tests; 395.103 s; failures/errors 0, skipped 1 | 0 |
| py_compile: server, task_planner, verifier_runtime, recovery test | 4/4 PASS | 0 |
| UI smoke: UltraApp construction/update/destroy | 1/1 PASS | 0 |
| git diff --check | PASS | 0 |

Skip: test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed — Windows не разрешает создание symlink; причина отдельно подтверждена. Предварительные regression evidence до repairs: 14 test methods, failures=200 (включая subtests), errors=4, exit 1; отдельный empty-search negative probe: 1 test / 1 failure, exit 1. Эти неудачные проверки сохранены как evidence, а не выданы за acceptance PASS. Системный Python 3.13 дал 4 import errors (нет httpx); штатный проектный .venv использован без установки зависимостей. При подготовке исправлены двухстадийная model_result fixture и имя класса отдельной skip diagnostic; production defects и fixture errors разделены.

Воспроизводимые команды в изолированном LOCALAPPDATA, с запретом внешних socket connections: проектный .venv Python -B -m unittest test_final_audit_recovery; Python -B -m unittest discover -s . -p 'test_*.py'. Raw logs, offline guard, UI/compile probe и source SHA-256 manifest: C:\Users\REX\AppData\Local\Temp\codex-ultra151c-3artJP (файлы *-acceptance3.log, acceptance-source-hashes.json). Full unittest выводит существующие ResourceWarning о temporary directory cleanup и asyncio slow-task warnings; итоговый status OK, failures/errors 0.

**Git / loss check:** HEAD a142817b33964691584aadbd6ea6464779df1815 и index не менялись; commit/push/reset/clean/stash/pull/add -A не выполнялись. Основная копия получила только проверенные целевые deltas с baseline SHA-256 guards. Остальные 1211 tracked files совпадают с baseline, включая исходные пользовательские .obsidian/graph.json и глобальный 000. При финальной сверке .obsidian/workspace.json отличается от стартового SHA-256; агент его не редактировал и не восстанавливал, текущее внешнее изменение оставлено без вмешательства. Web Alarm code/runtime/tests, профили 23/24/25, карточка Claude, общие 00/01/04/05/06/08/18/34 и Alarm не изменялись. Tests используют изолированные synthetic storage / LOCALAPPDATA, новые Alarm artifacts не создавались. Journal history сохранена; БЛОКИ 2–3 предыдущей CODEX-DOC-034-GRAPH-001 сохранены целиком по исключению текущей постановки, recovery не затирает ожидающий приёмки result. Изолированный worktree сохранён для review, без snapshot commit.
**Ограничения:** live paid Ultra / R-027/R-031 не запускались; mock Dredd не является live независимой приёмкой. Token/call savings не измерялись. UI smoke ограничен construction/update/destroy. Concurrent writer внутри физического tool read не стресс-тестировался; best-effort observability при storage failure не менялась.
**DOC IMPACT:** YES; CURRENT STATE / ARCHITECTURE IMPACT YES; CONTEXT LIBRARY IMPACT NO; REGISTRY/ROUTING IMPACT NO; NEW DOCUMENT REQUIRED NO. CANONICAL OWNER 13; AFFECTED DOCUMENTS 13/20/21 + персональная карточка. CONTRADICTION CHECK REQUIRED / PASS; LOSS CHECK PASS. Proposed delta только для ChatGPT: общие 000/05/06/01/34 — текущий recovery result, КТ-3 pending PASS, ограничения/NEXT; обычные текстовые имена, без новых рёбер 34.
**NEXT:** независимая проверка ChatGPT по утверждённой постановке, diff и воспроизводимым tests. Только после принятого PASS — КТ-3 DONE и TASK 151D. 151D не запускалась.


---

# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

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

# БЛОК 3 — FACTUAL RESULT / HANDOFF

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
