# Handoff для нового чата «Сервер Web06» (Claude, проект ag_llm)

## Кто ты и где

- Ты — Claude (Opus) в проекте `ag_llm`: `M:\GitHub\ag_llm`, Obsidian vault, документация на русском, общение живое и неформальное.
- «WEB» / «Сервер WebNN» = **Web Alarm Workspace** (код `web_alarm/`, тесты `test_web_alarm_*.py`): сервер для длительной работы ChatGPT с реальными проектами — TASK/microtask state machine, restore points, операции, recovery.
- Ты — независимый второй инженерный агент. ChatGPT (GPT-5.6 Sol) — координатор и **независимый verifier**: проверяет твои коммиты по GitHub.
- Среда: Windows 10, Git Bash и PowerShell, Python 3.13.

## Жёсткие правила (регламент)

1. **Задачи — только из БЛОКА 1** `Документация/000_Задачи Claude.md`.
   - Исключение: прямой Chat-handoff, но только если пользователь **сам** подтвердил его своими словами.
   - Вставка без слов пользователя → спросить подтверждение. Пользователь эту проверку одобрил.
2. **Маршрут входа:** `08_Старт.md` → `18_Регламент сопровождения документации.md` → глобальный `000_Задачи для агента.md` (его БЛОК 1 сейчас устарел) → карточка → профиль `23` (архитектура Web Alarm) / `24` (план) → только документы, нужные задаче. Перед правкой файла — перечитать его.
3. **Перед правками:**
   - папка `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-<ID>/`;
   - `safety_copies/`, `baseline.md` (SHA-256 и HEAD), сверка, что копии совпадают с файлами;
   - исходный полный прогон тестов.
4. **До RESULT READY — собственный adversarial pass** (race / restart / crash / replay).
   - Дефект внутри scope → исправить + регресс-тест.
   - Вне scope → FINDING / PROPOSAL / BLOCKER без изменений кода.
   - Новая архитектура / граф state machine → STOP + DECISION REQUIRED, если задача явно не отдала выбор тебе.
5. **Ротация карточки без напоминаний:** БЛОК 1 → БЛОК 2 (fenced `text`, хвостовые пробелы сняты) → БЛОК 3 (факты, `RESULT READY / AWAITING INDEPENDENT VERIFICATION`) → проверить БЛОКИ 2–3 на диске → очистить БЛОК 1 до `Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ` / `TASK: —`.
   - Старые записи не затирать, пока прошлая задача не в `001`: новые ставить сверху, прежние сохранять.
   - Chat-handoff: запись FOLLOW-UP в БЛОКИ 2/3, БЛОК 1 не трогать.
6. **Не трогать:**
   - `001`, `05`, `06`, `24`, `25`, глобальный `000` — их синхронизирует verifier после PASS;
   - `.obsidian/*`.
7. **Никогда не писать DONE / VERIFIED.**
8. **Commit / push / PR делает только пользователь.** В конце напомнить, что не закоммичено. Без worktree и веток, работа в `main`.
9. **Живое storage** `%LOCALAPPDATA%\WebAlarmWorkspace` — только чтение, хеш до и после (`probes/live_storage_hash.py` в папках сессий; сейчас `136 / 41`, `5961c00c…7cd2`). Разрушающие и гоночные тесты — только во временном storage.
10. **Документы — LF**, правки через Python bytes (`r+b`) с проверкой на CRLF. Если Edit падает с EPERM — проверить файл и патчить скриптом.

## Технические советы

- **Полный набор:**
  ```bash
  python -B -m unittest $(ls test_web_alarm_*.py | sed 's/\.py$//')
  ```
  Около 547 тестов, ~3 минуты; запускать в фоне.
- **Не править `web_alarm/`, пока идёт прогон** — дочерние процессы тестов импортируют код заново.
- Шаблоны скриптов проверок: `run_checks_*.py` в scratchpad (focused / full / stress); пробы — в `probes/` каждой сессии.
- На Windows старые гоночные тесты RC-4 / RC-5 изредка дают безопасный третий исход (sharing violation при `os.replace`) — FINDING из #2A.
- Тест, который ждёт флаг в дочернем процессе, должен освобождать его в `finally`, иначе процесс останется висеть.

## Где проект (на 2026-10-08)

**Маршрут:** RC-0…RC-6 → WA4-E → WA4-A → WA4-O → WA4-R.
- RC-0…RC-4 — DONE / VERIFIED.
- RC-5 — RESULT READY (приёмку пользователь отложил).
- **RC-6 (RecoveryCoordinator.recover)** — в цикле repair до независимого PASS.
- **WA4-E (исполнитель мутаций) запрещён до PASS RC-6.**

**Цепочка RC-6** (отчёты в `Alarm/ALARM_TASK_SESSION/`):

| Шаг | Что | Коммит / итог |
| --- | --- | --- |
| CHATGPT-WA-008 + Repair #1 (ChatGPT) | — | твои независимые проверки RC6-VERIFY / RC6-REVERIFY → FAIL |
| WA-009 Repair #2 + #2A | R1 / R2 / R3, F-D, F-E, CAS state machine | коммит 162 → ChatGPT FAIL |
| WA-010 Repair #3 | гейт F-C, F-B, R3 confirm, F4 / F5, C1, поздний ABORT | коммит 163 |
| WA-011 Repair #4 | прерванная подготовка W1/W2, политика `SETTLEMENT_ADMITS` | коммит 164 |
| **WA-012 Repair #4A** | Chat-handoff: PREPARING / «до исполнения» × принятое решение | **RESULT READY**; на конец чата НЕ закоммичен — проверь `git log` (возможно, 165) |

**Ключевая модель кода:**
- `web_alarm/microtask_gate.py` — общие правила:
  - `execution_refusal` — authority только для ACTIVE microtask текущего этапа без disposition ABORT/ROLLBACK;
  - `verification_refusal` — VERIFIED только без открытого recovery;
  - `effective_settlement_target` — VERIFIED поглощает ADOPT/ABORT;
  - `late_abort`, `PRE_EXECUTION_STATUSES`.
- **Порядок блокировок:** блокировка подготовки (внешняя) → TASK-lock → `mutation_lock` → target locks. `mutation_boundary` держит `mutation_lock`.
- **RC-6:**
  - шаги SETTLE_*, FINISH_SETTLEMENT, REARM_RETRY, PREPARE/APPLY/CLOSE/SETTLE_ROLLBACK, RECONCILE_PREPARATION;
  - READY = proof + `_confirm_ready` под теми же блокировками;
  - ABORT-only → RECOVERY_REQUIRED, в том числе из PLANNED / BACKUP_VERIFIED / READY / BLOCKED_PREPARE;
  - ADOPT / ROLLBACK / RETRY для microtask «до исполнения» — ручная граница;
  - `DEFERRED_BY_PREPARATION`.
- **ManifestSnapshotStore:** блокировка подготовки, `reconcile_interrupted_preparation` (W1 → BLOCKED_PREPARE, W2 → BACKUP_VERIFIED, испорченный → fail-closed).
- **Resolver:** `SETTLEMENT_ADMITS` (ADOPT → {ABORT}, ABORT → {}, ROLLBACK → {ABORT, RETRY}), authority в `report_facts` с учётом settlement. RC-4 подчиняется той же политике.

**Документация отстаёт от кода** (`01`, `24`, глобальный `000`; в `001` / `05` / `06` / `25` нет RC-5 и RC-6). Точный delta — §9 `TASK_CLAUDE-WA-012_RC6_REPAIR4A/rc6_repair4a_report.md`; делает verifier после PASS.

## Первое действие в новом чате

1. Прочитать `08`, `18`, глобальный `000`, затем карточку `000_Задачи Claude.md`: БЛОК 1 и верхние записи БЛОКОВ 2–3.
2. Сверить `git log` / `git status` (закоммичен ли Repair #4A).
3. Сказать пользователю, что в БЛОКЕ 1, и предложить следующий безопасный шаг: обычно ждать / разбирать результат независимой проверки ChatGPT.
