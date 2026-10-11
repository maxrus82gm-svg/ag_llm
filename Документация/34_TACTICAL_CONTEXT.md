---
aliases:
  - Tactical Context
  - Тактический контекст
---

# 34 — TACTICAL CONTEXT / Живой тактический контекст

**Назначение:** живой оперативный handoff и навигатор решений проекта `ag_llm` для сменяемых ChatGPT/Claude/Codex. Здесь — **текущий статус, границы полномочий, важнейшие проверенные факты и маршрут к подробным источникам**. Не копировать сюда весь архив дебатов, код или полные журналы.

**Каноническая связь:** [[05_Реестр задач]] → **этот документ**. Обычный маршрут: 08 → 000 → 34 → 18 → профиль. **Для INDEPENDENT_PLAN действует раннее исключение BLIND-START из 08: 34 НЕ ЧИТАТЬ до SUBMITTED**, так как ниже он содержит пересказы исходного плана. Координатор доставляет безопасную выборку правил, 28 Planning Input Manifest, решения 32 и соответствующие evidence 31.

**Постоянный координаторский цикл (решение пользователя 2026-10-10):** пользователь распределяет TASK между независимыми Claude/Codex/ChatGPT; ChatGPT при поручении проверки сам открывает синхронизированные GitHub task-cards, отчёты, исходники и evidence, проводит независимую приёмку в назначенном scope и централизованно разносит подтверждённые дельты в 34 / 000 / 05 / 06, текущую архитектуру, профильные планы/журналы и при необходимости другие владельцы. Пользователь не обязан пересылать уже доступный GitHub-отчёт. `RESULT READY` не означает `DONE`; при недоступном evidence сообщить о блокере. Человеческий итог — краткий и понятный, технические доказательства остаются в источниках. Полная матрица — в 18; разрешённый прямой GitHub-коммит в scope порученной работы — по разделу Git документа 08, с сообщением SHA и инструкцией синхронизации.

> **Начальный снимок: 2026-10-09, домашний ПК `DESKTOP-SC96D3U`, репозиторий `M:\GitHub\ag_llm`.** Не принимать дату, HEAD или статус ниже за вечные факты: при каждом входе сверять с актуальным Git, task-card и доказательствами. Доступный Remote ПК не обязательно домашний; всегда выбирать по метке.

**CURRENT 2026-10-11 / ULTRA S0 INDEPENDENT PASS:** ChatGPT independently ran unchanged RT-002 S0 guarded suite via authorized Desktop Commander DESKTOP-SC96D3U (M:\GitHub\ag_llm, Python 3.12.10): **166/166 PASS, 0 FAIL, 0 ERROR, 0 SKIP, 0 isolation violations; exit 0, 110.073 s**. Manifest contains original F01–F04 and all 11 terminal-callback methods. Command `.venv/Scripts/python.exe -B test_rt002_s0_kernel.py`. Original and post-run file hashes equal: server.py SHA-256 `44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54`, test_rt002_s0_repair.py `860f723f4c864deb0fbf6a7699a0ef9b44a29fc6c08038cffb026b36e32fb868`, runner `cf9b1d771e7e83888378108a8a6de1fc8e5bcc6e3673f6fc0b6ec5b1fb821e3b`. Local temporary logfile `C:\Users\REX\AppData\Local\Temp\codex-rt002-s0-baq6h0ex\unittest.log` SHA-256 `c64fc45950b9c387b7cc1486459f5b30a4d13b3f5c49a131733eb79267ed5817` (hash independently reread), `result.json` manifest/observations. This is ChatGPT runtime evidence, not merely Codex-reported 166. **S0 bounded OFFLINE kernel gate: INDEPENDENT ACCEPTED / VERIFIED.** Historic user-operated live R-036/T-036 BLOCKED permission rejection and R-037/T-037 WRITE/READ/EQUALS SUCCESS + Dredd PASS remain separate; no real live destructive callback injection. A synchronous `on_event` can see provisional SUCCESS before corrective BLOCKED; very-late external races and unavailable durable corrective BLOCKED after storage failure remain known limits. No source changes, Git commands, paid models or network calls during guarded suite. **S1 NOT ASSIGNED — separate USER GO/TASK required.** Old 151C/KT3 PARKED/PENDING; S6b/151G gated by S13a. ARCH Ultra 01/13/20/21, not WA 23–25 or Voice 12. Earlier #250/155 and callback-unreproduced notes in dated history below are NOT CURRENT.

## 0. Переход в новый Chat — короткий и самостоятельный

### GitHub Actions — подтверждённый серверный CI, Web Alarm WA4-E (2026-10-11)

**CURRENT / INFRA / VERIFIED, НЕ АРХИТЕКТУРА ULTRA.** Задача и коммит **№256** `f211045d18d30331f6d95c912c140e4d7ad9b647`, PR [№2](https://github.com/maxrus82gm-svg/ag_llm/pull/2) принят в `main`; постоянная ветка `GPT` используется для работы ChatGPT и не удаляется после принятия. Исполняемый файл — `.github/workflows/web-alarm-tests.yml`. Дополнительная документальная фиксация №257 сохранена в 05/06/22/25/34; подробность для будущих чатов дописана отдельно.

**Что уже реально работает:** GitHub Actions запускает Python-тесты в облачном **Windows runner (`windows-latest`), Python 3.12**, без домашнего компьютера, Desktop Commander и live Web Alarm storage. Автоматический запуск настроен при `push` в `GPT` и `pull_request` в `main`, **только если изменены workflow, `web_alarm/**` или `test_web_alarm_*.py`**. В workflow также объявлен `workflow_dispatch` для ручного запуска; отдельный фактический ручной запуск пока не проверялся. GitHub token имеет `contents: read`; секреты не передаются; тесты работают с изолированными временными каталогами. Результаты и логи доступны в GitHub → Actions → `Web Alarm smoke`.

**Пять существующих, не урезанных внутри себя unittest-проверок (но выборка мала):**
1. **STARTED-before-write:** durable статус `STARTED` сохраняется до первой физической записи.
2. **Idempotent replay:** повтор того же operation contract не выполняет физический side-effect второй раз.
3. **Create/delete:** выполнение операций создания и удаления в изолированном test Workspace.
4. **CAS pre-state guard:** если фактическое состояние target изменилось, устаревшая операция не перезаписывает его.
5. **Closed TASK gate:** закрытая или архивная TASK не получает права на новую mutation.

**Реальное evidence, оба запуска SUCCESS:** [push-run 38124155634](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38124155634) — **5/5 OK за 5.631 с**; [PR-run 38124184732](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/38124184732) — **5/5 OK за 3.784 с**. Это именно проверенные логи и результаты, не только наличие YAML.

**Что НЕ доказано этими 5/5:** полный регресс Web Alarm, реальные отключения/падения сервера и опасные live mutation, автоматическая проверка Ultra или весь UI. Прежние **36/36 focused + 643 full OK (1 skipped)** относятся к отдельной независимой проверке WA4-E на домашнем ПК 2026-10-09, **не** к GitHub Actions. Эти пять тестов дают быстрый предохранитель на затронутых путях, но не заменяют полный регресс и independent acceptance. Важно: изменение только Markdown не вызывает автозапуск из-за `paths`-фильтра; после изменения кода сверять именно новый run, а не прежний PASS.

**Маршрут нового Chat:** `08_Старт.md → 000_Задачи для агента.md → этот 34`; при необходимости посмотреть команды, фильтры и эксплуатационные ограничения в `22_Техническая информация.md`, историю доказательств в `06` и профильный журнал `25`. Следующая возможная **отдельная согласованная CI-задача** — расширить тесты до focused/full при сохранении изоляции. WA4-A, WA4-O/R и Ultra RT-002 S1 от появления CI автоматически **НЕ НАЗНАЧАЮТСЯ**. Архитектурные инварианты Web Alarm остаются в 23, план — в 24; работающий CI не является runtime-функцией Ultra.


**Достаточная команда нового пользователя:** «Прочитай документ Старт». Подключённый GitHub репозиторий: `maxrus82gm-svg/ag_llm`, папка `Документация/`. Обычный маршрут: `08_Старт.md → 000_Задачи для агента.md → 34_TACTICAL_CONTEXT.md → 18_Регламент сопровождения документации.md → 01_Архитектура и текущее состояние.md → персональная карточка/профиль по теме`. Контекст старого чата не нужен; **статусы всегда сверять с GitHub HEAD** и текущими файлами. `INDEPENDENT_PLAN` — исключение со слепым стартом из 08; этот 34 ему до SUBMITTED не показывать.

**Роль ChatGPT:** координатор общей документации и независимый verifier **по пользовательскому поручению**. При новой Claude/Codex TASK выдаёт **два блока в чате**: полная постановка для БЛОКА 1 и короткий launch message; **личный БЛОК 1 вставляет и контролирует пользователь** (`DOC-TASK-BLOCK1-01@1` в 18). Во время работы исходный БЛОК 1 не переписывать, минимальные дополнения — в чат исполнителя с сохранением trace, после factual result исполнитель безопасно ротирует 1→2/3. ChatGPT изменяет общий 000/05/06/34 в scope поручения, **не** личную карточку агента без отдельного запроса. Codex/Claude сами не используют Git/GitHub без разрешения и запускаются только пользователем; текущие карточки и HEAD всегда сверять.

**Обязательная пользовательская синхронизация:** после успешной прямой публикации GitHub-изменений ChatGPT выводит отдельным крупным заметным сообщением **«🟢 ПРИМИ МОИ ИЗМЕНЕНИЯ ИЗ GITHUB»**, указывает `main/HEAD SHA` и `GitHub Desktop → Fetch origin → Pull origin` по `DOC-GITHUB-HANDOFF-01@1` (в 18). Не заявлять `SYNCED LOCALLY` до подтверждения. При подозрении на dirty/conflict состояние предупредить, не советовать принудительную перезапись. Локальную синхронизацию делает пользователь, не ChatGPT.

## 1. Что сейчас происходит

- **HISTORY, superseded by CURRENT 166/166 verification above — Ultra / RT-002 B2 S0 repair submitted (#250, 2026-10-10):** базовая S0 (#247) дала четыре HIGH / две причины и остаётся историческим FINDINGS. Codex выполнил отдельно разрешённую `CODEX-RT002-S0-REPAIR-001` и пользователь опубликовал №250: `server.py`+`run_store.py`+`audit_storage.py`, тесты. Codex-reported **155 PASS, 0 FAIL/ERROR/SKIP, guard=0**; независимый GitHub source/test review подтверждает направленность исправления F01–F04, **НЕ подтверждает независимый runtime PASS** (оба Remote Desktop offline). **Additional open review probe:** при `run_finished(SUCCESS)` внешняя `on_event` вызывается после последней проверки outcome, до возврата SUCCESS — требуется адресно проверить corruption/source-drift в этом callback. Статус REPAIR **RESULT READY / AWAITING FINAL INDEPENDENT VERIFICATION**, S0 acceptance и S1/S2/151G не разблокированы. 151C/КТ-3 PARKED/PENDING; отдельная UX STOP кандидат, не стартовал.


- **ChatGPT-DOC-RT-20261010-001 / Architecture adoption:** по прямому поручению пользователя внедрён пакет Astra 28.1 v2.1 в общие правила и две оболочки: запрет Git, Rule-ID/retrieval, Document Change Impact, RT input/sealing/cleanup, 33 planning modes, статусы 32/35. **RESULT READY / AWAITING INDEPENDENT VERIFICATION** (не DONE); остались реальные ограничения: untracked raw-audit retention перед будущей очисткой, отсутствие автоматического resolver/серверного enforcement blind-mode, ещё не пройденная визуальная проверка Obsidian Graph. Работы Ultra/Web Alarm этим пакетом не запускались.


- **Ultra / Codex App Server (2026-10-10):** уточнён документ `19`: для будущей глубокой интеграции Codex как агента предпочтительно исследовать **Codex App Server (локальный JSON-RPC)**; `codex exec` — упрощённый одноразовый путь. OpenAI объявила deprecated только режим **`codex mcp-server`** (Codex-as-MCP-server), **не протокол MCP в целом** и не использование MCP-инструментов в Codex. Зафиксированы server-owned permissions, TASK/thread identities, запрет несанкционированных Git-операций, feasibility/Windows checks. **CONCEPT / NOT IMPLEMENTED**, реальный локальный runtime не менялся.
- **Ultra / Claude integration (2026-10-10):** в профильном документе `19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md` дополнена концепция трёх раздельных путей: Ultra → Claude Messages API как LLM; Ultra → локальный Claude Code CLI / Agent SDK как agent backend; Claude → Ultra через ограниченный MCP tool server. Рассмотрены app/sidecar, discovery, auth, network/permissions, независимые планировщики и feasibility gates. **FUTURE / NOT IMPLEMENTED**; код, настройки, runtime и работа локальных агентов не изменялись.
- **RT / архив архитектуры:** предложение Astra 28.1 v2.1, принятые регламенты 18/28/33 и история внедрения №199–233 сохранены в своих документах. Для обычной Ultra TASK достаточно утверждённого B2 и канонического 20 §5а; полный RT-протокол читать адресно, если возник конкретный спор или новый Круглый стол.

- **Основная активная ветка:** WEB-02 / Web Alarm Workspace, устойчивое выполнение TASK, recovery и будущий контролируемый mutation gateway.
- **Подтверждённая точка:** Recovery Closure RC-0…RC-6 — `DONE / VERIFIED`. RC-5 / `CLAUDE-WA-016` — независимо принято (commit `d53ec14`; 60/60 targeted, 593 full OK, 1 skipped). F-5/F-6 / `CLAUDE-WA-017` — независимо принято (commit `c7681c38`; 17/17 targeted, 607 full OK, 1 skipped).
- **Последняя independently verified WEB-02 TASK:** `CLAUDE-WA-018` / WA4-E — **DONE / VERIFIED** (ChatGPT reviewed commit `a142817b33964691584aadbd6ea6464779df1815`, independent 36/36 focused + 643 full OK, 1 skipped, exit 0, 2026-10-09; same GitHub source/test blobs confirmed 2026-10-11). Server-owned `web_alarm/mutation_executor.py`, HTTP mutations and CLI mutate; move/rename are two tracked non-atomic operations. Next candidate `WA4-A` requires separate USER GO; WA4-O/WA4-R not started. Claude report remains in `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA-018_WA4E_EXECUTOR/wa018_report.md`.
- **RT-002 / Круглый стол — завершённая стадия принятия архитектурных решений:** синтез 31 SEALED, вердикт 32 APPROVED, Codex REVIEW-1 в 33.1 SEALED, итоговый B2 (33.3, immutable №242) **USER PLAN APPROVED**, перенесён в каноническую программу **20 §5а**. Круглый стол существует как сохранённый отдельный процесс в 28–35, но **не является текущей задачей**; не перечитывать дебаты на каждом старте. Остались только реальные инженерные TASK S0→… и ограничения из B2. Главная доказанная проблема R-031 — повтор больших READ в контексте; source/evidence 31/21.
- **Ultra / TASK 151C:** `CODEX-ULTRA-151C-RECOVERY-001` **PARKED / снята с активной очереди по решению пользователя 2026-10-10**. Её factual recovery результат остаётся `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, КТ-3 PENDING, **не DONE**; историческая полная версия БЛОКА 1 в GitHub `main@27ddda0162959f23fabf92ea80a9a58006af93fc` персональной карточки Codex, другие старые результаты в БЛОКАХ 2–3 сохранены. 151C не перезапускать и отдельно не принимать сейчас; reviewer обязан оценить конфликт T0/151C и безопасную ревизию плана.
- **DOC-034 / граф Obsidian:** `CODEX-DOC-034-GRAPH-001` — **RESULT READY / AWAITING INDEPENDENT VERIFICATION**; визуальный PASS графа ещё не установлен. Сохранять **одного уникального wiki-соседа — 05**; другие файлы упоминать без wiki-связей. Ранние слова «commit/push не выполнялись» — исторический снимок до новых GitHub-коммитов, не текущий статус.

- **ULTRA UX / внеочередной кандидат (НЕ НАЗНАЧЕН):** после S0 рассмотреть `ULTRA-UX-STOP-001` — видимая кнопка **«Остановить генерацию»** во время текущего RUN. Отдельная от shutdown приложения/rollback: пользовательский сигнал прерывает ожидание/LLM attempt при технической возможности и гарантированно прекращает **дальнейшие** автоматические LLM sends, stages и mutation; сохраняет evidence, завершает RUN статусом INTERRUPTED/CANCELLED, не SUCCESS. Уже отправленный запрос может тарифицироваться и остаться UNKNOWN. Реализовать с async cooperative cancellation, защитой от race/double click, permission wait, UI responsiveness; mock GUI+transport tests. **Это backlog в 05/34, не часть неизменяемого B2 и не изменение текущей S0.** При фактическом назначении проверить сложность/связь с будущим pre-HTTP budget guard и user approval отдельной TASK.

## 2. Ограничения и открытые вопросы

- Закрытая TASK не должна получать mutation authority; любая запись — только после server-owned gates. `WA4-E`: STARTED должен быть persisted под TASK-lock **до первой physical mutation**; replay не должен удваивать side effect.
- **Открыто, без самостоятельного закрытия:** F-1 / F-3; legacy ownership claim у closed TASK без mutation authority; кратковременные Windows sharing violations / открытый handle; косметика server task listing. Не смешивать с завершённым F-5/F-6.
- Для Windows checkpoint: FAILED rebuild может означать MISSING/STALE, но **никогда ложный VALID**. Успешный REBUILT обязан иметь валидный checkpoint.
- Пользователь делает `commit/push`, если явно не делегировал это. Не переписывать чужие локальные изменения; не трогать live storage при тестах без специальной разрешённой процедуры.
- Для ChatGPT Remote — штатный `ALARM_TASK_SESSION` и recovery reconciliation; для локальных Claude/Codex **не навязывать** Remote-only журналы и safety copies.
- Не путать этот документ с `.ultra/project_context.md` или библиотекой контекстов 14–16: сам по себе он **не подмешивается** в модельный runtime prompt.

## 3. Git и среда — снимок, перепроверять

- **Правильный компьютер:** `DESKTOP-SC96D3U`, путь `M:\GitHub\ag_llm`; альтернативный подключённый ПК не считать нужным по признаку доступности.
- **GitHub baseline (2026-10-10, до этой редакции):** пользовательский №199 = `74805da3f376fb4730b16b66d841cc29c9567985`; законченная документационная серия №200–233, последнее предыдущее изменение 18/08 — коммиты №234 `4627c2f` и №235 `a093183`. Текущий HEAD после этой записи ОБЯЗАТЕЛЬНО перечитать из GitHub; локальный GitHub Desktop/Fetched/Pulled state **не подтверждён**.
- Git/файлы, реальные статусы `TASK` и проверенное evidence первичны; при противоречии править этот снимок после reconciliation, не наоборот.

## 4. Карта чтения — брать только по потребности

| Зачем | Источник |
| --- | --- |
| Начать новый Chat / восстановить маршрут | `08_Старт.md`, затем `000_Задачи для агента.md` и этот файл |
| Проверить статусы и зависимости TASK | [[05_Реестр задач]] |
| Правила исполнения и документации | `18_Регламент сопровождения документации.md` |
| Общая текущая архитектура | `01_Архитектура и текущее состояние.md` |
| Web Alarm — утверждённые инварианты | `23_Архитектура Web Alarm Workspace.md` |
| Web Alarm — этап, критерии, NEXT | `24_План реализации Web Alarm Workspace.md` |
| Web Alarm — независимая история и аудит | `25_Журнал Web Alarm Workspace - выполненные задачи и аудит.md` |
| Общий append-only журнал | `06_Журнал выполнения и отчёты.md` |
| Claude / Codex / ChatGPT — точная постановка и результат | `000_Задачи Claude.md`, `000_Задачи Codex.md`, `000_Задачи ChatGPT.md`: БЛОКИ 1–3; верить фактической записи/её status, не историческому пересказу |
| RT-002 — решение и его основания | `28` — правила и закрытый gate; `31` — полный синтез из 29, 29.1, 30, 30.1 с доказательствами, ошибками и разногласиями; `31.1/31.2` — аттестация PASS; `32` — **уже утверждённый** вердикт и Decision Record |
| RT-002 — исполнение после PLAN APPROVAL | #252 S0 REPAIR independently verified by ChatGPT: guarded 166/166 PASS, exit 0, 0 guards; FULL report 21, code #254. S0 offline ACCEPTED; NEXT S1 awaits USER GO/TASK. Old 151C/KT3 PARKED/PENDING, 151D/E deferred, S6b blocked until S13a. |
| RT-002 — первоисточники по необходимости | `29/29.1/30/30.1` — адресно, если 31 не даёт точной исходной формулировки или доказательства; не заставлять читать весь архив без причины |
| Независимая приёмка результата 151C / КТ-3 | **PARKED пользователем**, сейчас не текущая TASK. Исторические материалы `000_Задачи Codex.md` до нового назначения доступны в `main@27ddda0162959f23fabf92ea80a9a58006af93fc`; профили 13/20/21 и код для адресной проверки Codex REVIEW. Не объявлять DONE. |
| Аварийное восстановление удалённой TASK | `Alarm/ALARM_TASK_SESSION/00_INSTRUCTION.md` и соответствующая `TASK_*/session.jsonl` |

Не читать все файлы по привычке. Выбрать PRIMARY PROFILE и нужные вторичные документы по текущей TASK.

## 5. NEXT SAFE ACTION

1. **RT-002 / CURRENT:** S0 amendment #252 independently verified via Desktop Commander, **166/166 PASS**, 0 guard violations, exit 0; original code unchanged. **S0 OFFLINE ACCEPTED.** NEXT S1 only by user-authorized task; none started. Historical #250/155 context below is superseded by 21; UX STOP proposal not assigned, 151C/KT3 remains pending.
2. **WEB-02:** WA4-E / CLAUDE-WA-018 independently DONE / VERIFIED (36/36 targeted, 643 full OK, 1 skipped). Reconcile profile 23/24/25 and general 000/05/06 after user PR acceptance. NEXT is WA4-A only after new user-authorized TASK, with retained P-2/P-3/P-4/R-1 and two-step move caveat.
3. **DOC-034:** `CODEX-DOC-034-GRAPH-001` ожидает независимой проверки; визуальная проверка Obsidian Graph не заявлена. У 34 должен остаться один wiki-сосед — реестр 05.
4. **Новый чат / GitHub:** вход обычного ChatGPT — `08 → 000 → 34 → 18 → 01 → профиль`. Сверить HEAD и персональные БЛОКИ с GitHub, не полагаться на устаревшие слепки. При выполнении прямых GitHub-записей **обязателен один заметный итоговый призыв «🟢 ПРИМИ МОИ ИЗМЕНЕНИЯ ИЗ GITHUB»** по `DOC-GITHUB-HANDOFF-01@1` (18): SHA, branch, Fetch origin → Pull origin, предупреждение о риске локального dirty/conflict state. До подтверждения пользователя считать лишь `PUBLISHED ON GITHUB`, не `SYNCED LOCALLY`. Не запускать локальные Claude/Codex или Remote без явного поручения.

## 5а. RT-002 — завершённое планирование, актуальный инженерный маршрут

**Не текущий Круглый стол.** Все раунды и альтернативы сохранены в 28–35: 31 синтез SEALED, 32 решение APPROVED, 33 исходный план, 33.1 Codex REVIEW SEALED, 33.3 B2 exact approved, вход в реализацию **20 §5а**. Ссылка на эти документы — навигация и история; **не пересылать агенту полный круглый стол автоматически**. Для нового слепого планировщика (INDEPENDENT_PLAN) по-прежнему исключение из 08: этот 34 до собственной SUBMITTED читать нельзя.

**Ключевые обязательства B2 (см. 20/33.3, не дублировать их здесь):** R-031 — файловый RUN, а не «700k на приветствие»; большие READ повторялись 11 раз, вызвав разрастание контекста. До 151G — server pre-HTTP budget по всем LLM routes, два отдельных cap (full READ и serialized request), честный UNKNOWN/резерв и видимый человеку UI. Независимо проверять correctness/freshness/Final Audit; старые 151C/КТ-3 **PARKED/PENDING**, deferred 151D/E/F/H/I не получать ложный PASS. **S13a independently ACCEPTED перед S6b/151G.** Все A1…A8 offline + полноценное GUI/мониторное подтверждение по этапам, live только по отдельному USER GO.

**CURRENT 2026-10-11:** S0 / RT-002 B2 independently OFFLINE VERIFIED — ChatGPT reran guarded 166/166 PASS, exit 0, guard 0. This unblocks consideration of S1, but **S1 NOT ASSIGNED** without separate USER GO/TASK; S6b/151G still BLOCKED until independently accepted S13a + S6a. Remaining provisional SUCCESS/callback limits are recorded in 13/21. Historical #250/155 was superseded, not erased. Separate `ULTRA-UX-STOP-001` remains PROPOSED / NOT ASSIGNED.

**Открыто:** реальная экономия при неизменной решаемости/negative evidence, raw RUN retention, source token accounting, локальные GUI проверки и пределы будущей cancellation semantics. Их сверять по конкретной TASK/13/20/21, а не по архивной дискуссии. Обновления контекста — минимальной дельтой; immutable 31/33.3 не редактировать ради сокращения.

## 6. Обязательное сопровождение — DELTA, а не переписывание истории

**Команда пользователя «контекст», «тактический/оперативный контекст», «обнови контекст» (в рамках ag_llm):** прочитать **34** после обычного 08→000, сверить с GitHub и профильными владельцами, внести только обоснованную дельту и убрать фактически устаревшее. Если изменений нет — сообщить. Для blind-планировщика 34 запрещён до разрешённого reveal. Не создавать вместо 34 новый «контекстный» документ без отдельного запроса.

**На входе каждой значимой TASK:** прочитать документ и сверить текущий scope, Git и статус. Не объявлять записанное автоматически доказанным. Перед изменениями решить, что из контекста устарело.

**На выходе каждой TASK / после значимого решения:** обновить только изменившиеся поля — текущий фокус, подтверждённый результат, открытые вопросы, следующий безопасный шаг, нужный маршрут чтения и актуальный рабочий снимок. Обновлять и при переносе работы в другой чат/агента. Этот шаг — обязательная часть документационного closeout, включая documentation-only TASK.

**Редактирование без потери ориентиров:** обновлять ложные CURRENT-статусы и удалять только действительно утратившие смысл оперативные подробности. **Не чистить важную старую информацию механически после каждой TASK:** подтверждённые вехи, принятые архитектурные решения, открытые риски и маршрут последующих этапов могут оставаться кратко, пока полезны для нового чата. При уходе детали из 34 сначала убедиться, что её смысл сохранён у канонического владельца (`05/06/23/24/25` и другие профили); при необходимости оставить одно предложение со ссылкой на источник. Разрешено временно хранить *немного больше* сведений для сложного handoff; полный архив — в `06/25` и task-отчётах. Не копировать длинные log/diff, исходники, секреты или полную переписку.

**Контракт доказательств:** различать `CONFIRMED / AWAITING VERIFICATION / PROPOSAL / DEFERRED`. Ни один агент не повышает статус до `DONE / VERIFIED` без принятой независимой проверки. Если возникло противоречие с `000/05/23/24/25`, сначала установить источник истины и синхронизировать документацию; этот файл не переопределяет authority.

**Граница автоматизации:** это дисциплина сопровождения документов при работе агентов, **не фоновый процесс**. Между задачами и закрытыми чатами файл самостоятельно не меняется.

## 7. Последний тактический handoff

- **2026-10-10 / граница Git локальных агентов:** по решению пользователя правило `DOC-GIT-01@1` внесено в 18, устаревшие постоянные разрешения Git в 18 и персональных инструкциях Codex/Claude исправлены. Самостоятельные Git/GitHub-операции локальных агентов запрещены, включая чтение истории, кроме отдельного явного разрешения. При необходимости локальный агент запрашивает историю у пользователя/внешнего координатора; исторические результаты/отчёты остаются без исправлений. Проверка полноты внедрения — в независимой приёмке.
- **2026-10-10 / архитектурное сохранение:** концепция Claude API / Claude Code CLI / Agent SDK / MCP, app/sidecar и контракта будущей автоматической координации дополнена в 19 и отражена в краткой карте 01. Это только FUTURE; собственные рабочие среды Claude/Codex, текущие TASK, права и existing Ultra runtime не менялись.

- **2026-10-10 / протокол координации и документации:** пользователь подтвердил прямое GitHub-чтение/адресную запись ChatGPT в порученных задачах и их documentation closeout. Обязателен самостоятельный поиск доступных карточек/отчётов по команде «проверь агента», независимая проверка перед DONE, распределение фактов по 34/000/05/06/профилям, краткий человеческий отчёт и сохранение значимых старых ориентиров 34. Это правило процесса, а не объявление находящихся в проверке TASK завершёнными.
- **2026-10-10 / RT-002 — сохранённая история:** предыдущие снимки этапов 31/32/33, исходный план и SUBMITTED REVIEW доступны в 28–35 и GitHub №199–245; текущая стадия — **B2 APPROVED и S0 USER ASSIGNED**, не DRAFT/EMPTY. Детальная хронология, seal, hash и reason matrix хранятся по своим владельцам, а не здесь.
- **Правило повторного использования Круглого стола:** отдельные RT-процедуры 28/31/32/33/33.1/33.3 существуют и доступны; новый RT не наследует автоматически старые решения, provenance, статусы и контекст. Не показывать старые CURRENT-поля как актуальные для текущей Ultra TASK.
- **Очистка устаревшего:** прежние длинные handoff-записи с `32 DRAFT / 33 EMPTY / commit not done` удалены **только из живого 34** как устаревшие, не из Git history или документов-первоисточников. Не использовать их в качестве текущих инструкций.
