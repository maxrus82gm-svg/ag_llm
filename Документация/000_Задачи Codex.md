# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

- Перед TASK: `08_Старт.md` → `000_Задачи для агента.md` → `18_Регламент сопровождения документации.md` → `01` → профиль темы. Кодекс приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать Git, локальный контекст и временные изолированные пробы. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Минимум артефактов.** В Git оставлять только целевые правки, необходимые regression tests и действительно существенные evidence. Полный task-report отдельным файлом только при необходимости для независимой проверки либо при прямом запросе пользователя. Остальные технические детали — во временном окружении Codex.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- После исполнения: сохранить полную утверждённую постановку в БЛОКЕ 2, factual result — в БЛОКЕ 3; только затем очистить БЛОК 1 до ожидания. Канонические журналы обновляются после независимого PASS, не на основании самопроверки Codex.

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

**Статус:** ОЖИДАНИЕ НОВОЙ ЗАДАЧИ

**TASK:** —

---

# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

**TASK:** CODEX-ALARM-CLEANUP-001

**Статус:** разрешена безопасная очистка проверенных дубликатов. Удаление целых исторических TASK-папок требует отдельного согласования.

**Baseline:** GitHub `main`, commit `2c10478291b932ff0c77ef130438adc7470fcd65`.

**ARCH CLASS:** Local maintenance / evidence-preserving Alarm cleanup.
**PRIMARY PROFILE:** `18_Регламент сопровождения документации.md`.
**SECONDARY PROFILE:** `23_Архитектура Web Alarm Workspace.md` — границы защиты runtime snapshots / rollback / receipts.

**Цель:** сократить служебный мусор в `Alarm`, не потеряв историю, уникальные доказательства проверки и возможность восстановления.

**Порядок:**

1. Прочитай `08_Старт.md`, `18_Регламент сопровождения документации.md` и персональную карточку `000_Задачи Codex.md`. Это локальная задача Codex — аварийный протокол Desktop Commander Remote НЕ применять.
2. Проведи инвентаризацию всей папки `Alarm`, включая `ALARM_TASK_SESSION`. Сгруппируй файлы по категориям: уникальные отчёты, исходные воспроизведения, regression tests, дублированные safety copies, временные логи, исторические handoff.
3. Сначала проверь особенно большие сессии `CLAUDE-WA-011`, `012`, `013`, `014`. Сопоставь каждую резервную копию с исходным файлом в соответствующем Git-коммите. Если байтовая идентичность и сохранность в Git доказаны, удаление такого дубликата разрешено.
4. Можно также удалять однозначно повторные промежуточные выводы тестов, если результат уже достоверно сохранён в итоговом отчёте и для воспроизведения ошибки они не нужны.
5. Не удаляй уникальные отчёты, воспроизводящие скрипты, критические доказательства дефектов, архитектурные решения, каноническую документацию, важные handoff и данные runtime Web Alarm. Не удаляй целые TASK-папки без отдельного одобрения.
6. Проверь ссылки из документации и отчётов на кандидатов для удаления. При сомнении — оставляй файл и указывай причину.
7. Не создавай новых safety copies, `session.jsonl`, `context.md`, `history.md` или дополнительных папок в Alarm ради этой очистки. Используй Git и штатный локальный контекст Codex.
8. По завершении выполни `git status`, `git diff --check`, сверь сохранность защищённых файлов. Не делай commit/push.

**Финальный отчёт:** одним копируемым блоком `text`. Укажи количество и объём удалённых файлов, сохранённые обязательные артефакты, список папок, предлагаемых к отдельному удалению, результаты проверок и оставшиеся риски.

**Важно:** цель — уменьшить служебный объём, а не переписать историю проекта или скрыть неудачные проверки.

**DOCUMENTATION BLOCK**

- TASK TOPIC: служебный объём Alarm и сохранность evidence.
- PROFILE DOCUMENTS: `18`; защитные границы `23`.
- CHECK 01: YES — проверить отсутствие влияния на архитектуру и текущий runtime.
- OTHER AFFECTED DOCUMENTS: персональная карточка Codex; ссылки из документации и отчётов на кандидатов.
- AFTER TECHNICAL RESULT: сверить точный diff, byte identity, Git provenance, ссылки и сохранность; сохранить factual result в БЛОКЕ 3; исторические журналы не переписывать.
- REGISTRY IMPACT: NO.
- CONTEXT LIBRARY IMPACT: NO.
- CONTEXT DOCUMENTS: —.

---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

**TASK:** CODEX-ALARM-CLEANUP-001
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**Дата:** 2026-10-08.
**Baseline:** main, 2c10478291b932ff0c77ef130438adc7470fcd65; HEAD и index не изменялись; commit/push не выполнялись.

Инвентаризация всего Alarm, включая hidden/ignored: 1 395 файлов / 23 802 692 байта, 361 папка; ALARM_TASK_SESSION — 1 008 / 17 745 703 байта. Категории по роли: отчётные материалы — 146 / 5 377 085 байт (137 различных SHA-256; 9 групп одинаковых отчётных/snapshot-материалов сохранены); исходные воспроизведения и raw evidence — 427 / 6 627 463; regression tests — 12 / 34 848; safety copies — 554 / 10 890 827; временные выводы/логи/кеши — 214 / 684 158; исторические handoff — 42 / 188 311. Snapshot-материалы внутри этих категорий защищены.

Удалено **450 файлов / 7 445 289 байт (7,45 МБ; 7,10 MiB; 31,3%)** — только tracked .py-дубликаты внутри safety_copies. Теперь Alarm: **945 файлов / 16 357 403 байта**. Папки не удалялись, новые артефакты в Alarm не создавались.

| Сессия (в Alarm/ALARM_TASK_SESSION/) | Удалено | Байты | Source proof |
| --- | ---: | ---: | --- |
| TASK_CLAUDE-WA-011_RC6_REPAIR4 | 70 | 1 091 428 | baseline ce5e1799ab4a08157c779680711bebaf29d686dd |
| TASK_CLAUDE-WA-012_RC6_REPAIR4A | 82 | 1 306 798 | baseline 47e5344ade57aaabca8ed5f782d5eb94f57ad464 |
| TASK_CLAUDE-WA-013_RC6_REPAIR4B | 83 | 1 329 742 | baseline 32bdf9635afcf81a9e6f1090a3bcba54b907c126 |
| TASK_CLAUDE-WA-014_RC6_ABORT_BEFORE_ACTIVE | 84 | 1 368 367 | baseline fb5e6e38c9ff13d43655ea51445fb7fef422cd38 |
| TASK_CLAUDE-WA-010_RC6_REPAIR3 | 79 | 1 192 105 | byte-identical original versions in ancestors of current baseline |
| TASK_CLAUDE-WA-009_RC6_REPAIR2 | 4 | 111 302 | same historical source proof; only unlinked repair2a copies |
| TASK_CHATGPT-WA-008_RC6 | 35 | 703 368 | same historical source proof |
| TASK_CHATGPT-WA-008_RC6_REPAIR1 | 13 | 342 179 | same historical source proof |

Доказательства: все 334 копии WA-011–014 сопоставлены с исходными путями своего baseline; 333/334 полностью идентичны, включая 3 task-card copies. Для всех 529 code safety copies найдены canonical source paths; 528/529 имеют байтово идентичный оригинал в достижимом Git. Из них 78 оставлены из-за конкретных ссылок; удалены 450. Для каждого удалённого файла выполнены raw-byte comparison с оригиналом в Git и с архивной копией в 2c10478: **450/450 + 450/450 PASS**. SHA-256 проверен повторно непосредственно перед удалением, без преобразования окончаний строк. Восстановление возможно из baseline по прежнему полному пути Alarm; исходные версии кода также остаются в истории Git. Git history/objects/index не переписывались.

Защищено: все 945 оставшихся файлов Alarm — SHA-256 945/945 PASS; все 146 отчётных материалов, 90 воспроизводящих .py, 12 regression fixtures, 42 handoff; manifests, snapshot_* и benchmark audit streams; ALARM_TASK_SESSION/00_INSTRUCTION.md и CLAUDE_HANDOFF_Web04.md; все 214 logs/outputs/caches, включая уникальные FAILED/invalid/interrupted прогоны. Никакие runtime snapshots, rollback, payloads, receipts и checkpoints не удалялись.

Оставлены 104 safety copies / 3 445 538 байт: 25 документальных копий/handoff, 78 code copies со ссылками (включая 11 из .obsidian/workspace.json), 1 code version без идентичного оригинала в Git: TASK_CLAUDE-WA-009_RC6_REPAIR2/repair2a/safety_copies/web_alarm__recovery_coordinator.py. Карточка TASK_CLAUDE-WA-011_RC6_REPAIR4/safety_copies/000_Задачи Claude.md.before не совпадает с исходной карточкой на ce5e179; сохранена. Повторные позитивные logs тоже сохранены: различаются timings/incident context и/или на них ссылаются отчёты. В частности full_after_fix_first.txt в WA-014 хранит FAILED (failures=1, errors=1, skipped=1) и сохранён.

Ссылки: проверены 1 073 текстовых файла (tracked documents/reports/code/config + Alarm и документальные safety copies), относительные/полные пути, slash variants и URL encoding; удалённые кандидаты не имеют конкретных ссылок. Live storage не ссылается на удалённые пути. Общие исторические упоминания safety_copies/ сохраняются; папки и baseline.md сохранены, копии доступны из Git.

Проверки: все 361 папки сохранены; 0 новых файлов/папок Alarm; 270 tracked защищённых файлов вне Alarm не изменились относительно контрольных хешей. Web Alarm storage C:/Users/REX/AppData/Local/WebAlarmWorkspace: 136 файлов / 1 080 777 байт, hashes/paths unchanged. .ultra: 512 файлов, hashes/paths unchanged. git status: 450 D, карточка Codex M, внешняя .obsidian/workspace.json M (появилась во время инвентаризации; Codex её не менял). git diff --check: PASS, exit 0; только LF/CRLF notice для внешнего Obsidian-файла. Runtime tests не запускались: runtime и tests не менялись, релевантная проверка — byte preservation и diff scope.

На отдельное удаление предложены только 9 теперь пустых подпапок (относительно Alarm/ALARM_TASK_SESSION/):
- TASK_CHATGPT-WA-008_RC6/safety_copies/m2_pre
- TASK_CLAUDE-WA-010_RC6_REPAIR3/safety_copies/tests и safety_copies/web_alarm
- TASK_CLAUDE-WA-012_RC6_REPAIR4A/safety_copies/tests и safety_copies/web_alarm
- TASK_CLAUDE-WA-013_RC6_REPAIR4B/safety_copies/tests и safety_copies/web_alarm
- TASK_CLAUDE-WA-014_RC6_ABORT_BEFORE_ACTIVE/safety_copies/tests и safety_copies/web_alarm

Целые TASK-папки к удалению не рекомендованы: содержат evidence/handoff и требуют отдельного zero-loss audit + явного согласования.

DOC IMPACT: operational YES — только персональная карточка Codex; CURRENT STATE / ARCHITECTURE / CONTEXT LIBRARY / REGISTRY / ROUTING IMPACT: NO; NEW DOCUMENT REQUIRED: NO; LOSS CHECK: PASS. Канонические 05/06/25 и project-level 000 не переписывались; их подтверждённую историю синхронизирует independent verifier после PASS.

Оставшиеся риски: объём .git не уменьшился (Git сохраняет историю); удалённые копии восстановимы при наличии baseline/его ancestry; untracked .tmp и caches, старые snapshot_* и linked copies намеренно оставлены; пустые папки Git не отслеживает и они могут отсутствовать в будущем checkout; независимая приёмка ещё не выполнена.

NEXT: independent verification текущего diff; отдельно решить вопрос пустых подпапок. Новую runtime TASK не начинать.
