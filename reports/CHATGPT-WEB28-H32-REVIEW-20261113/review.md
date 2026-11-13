# Независимая приёмка H32 — Ordinary Chat fake pre-send admission

**Дата:** 13.11.2026. **Verifier:** ChatGPT / Web28, независимый GitHub Actions Windows.  
**TASK:** `CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001`. **HISTORY:** `H-CODEX-000032`.  
**Verdict:** **PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE; H32 DOC CLOSED**, только Ordinary fake admission. **FULL S3b, S3c, S9, S13a, REAL/OAuth/paid — OPEN/HOLD.**

## Публикация, идентичность исходников, область проверки

Codex сдал точную TASK под H32, штатный `finish` выполнил ROTATED/readback, БЛОК 1 WAITING, БЛОК 1.1 дословный snapshot. Авторский отчёт: `reports/CODEX-WUA-CHAT-S3B-ORDINARY-FAKE-ADMISSION-001/report.md`; `task_record.json` до независимой проверки содержал SUBMITTED/REVIEW PENDING. Продуктовая сдача опубликована пользователем как основной код `main@4e4edd0be60f2d1491b6f8d6859dc4f883c1a4bb` (№578); сверка GitHub compare до `main@36c41c79b066b4c19120ce11266a727d10cb7407` №590 показывает **только workflows и документацию/Obsidian**, без изменений продуктового кода. Основной проверочный CI запускался на `GPT@2703ba6d`, отдельный HTTP на `GPT@5d7854d6`; реализация H32 между ними и source commit не изменялась.

Независимо прочитаны исходники ordinary bridge/Turn/policy/ledger и опубликованные H32 source/evidence. Проверена узкая цепочка: freeze/immutable final UTF-8 bytes и wire SHA → S2 Ordinary OFFLINE policy → S3a reserve/readback/mark_sent/SENT/readback → **один** fixture `send_bytes` → terminal/readback → Turn/RAW/per-chat usage и reopen. Replay не осуществляет второй физический fake send, UNKNOWN/REJECTED сохраняют консервативное значение. Это **не гарантия exactly-once внешнего провайдера**. Отказ на старом/missing audit enrollment и изменённом engine fingerprint — ожидаемая граница; не применять автоматическую миграцию.

## Независимые GitHub Windows CI evidence

**Группа A:** [run 43417573566](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43417573566), conclusion **SUCCESS**, job 131859252421, `h32-independent-windows` artifact **14032492988**, SHA256 ZIP `d2c6feec34f7592c0700b301c0c4c1823aefd1cc219592965c0c5af0acfaec99`. Результаты:
- H32 full **236 PASS + 220 подтестов PASS**, unexpected guard denials = 0; это фактически собранные 236 тестов, не авторские 235.
- H32 post-review **74 PASS + 32 подтеста PASS**, unexpected guard denials = 0.
- S2 standalone **PASS / exit 0**; позитивный H25+H32 quality/isolation **52 PASS, guard 0**.
- Node UI **57 PASS, 0 FAIL, 0 SKIP**.
- Historical pinned S1 RAW в GitHub checkout отсутствует: **H32 S1 independent = NOT RUN**, а не «69 PASS». Ранее принятый независимый S1 H24 — отдельная историческая проверка.
- Артефакт: **19 файлов**, source SHA, логи, result/cases/guard. Работа проводится на GitHub-hosted Windows; не на Desktop Commander.

**Группа B:** [run 43416113378](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43416113378), conclusion **SUCCESS**, job 131854337977, `h32-http-and-mutant-independent` artifact **14031398967**, SHA256 ZIP `fa3e07583e0d9063f6f6a9690a869a264072c05eae5320a44320498e579d7031`.
- Loopback HTTP **2 Workspace, 4 Chat, 4 fake sends, replay +0**, external requests 0, reject on real-like body; budget ledger physically in SENT at each fixture byte-boundary.
- Два независимых *intentional weakening* контроля: bypass S2 DENY и bypass terminal verification, оба дали **ожидаемый RED** (по одному отказу на контроль, 0 runtime errors). Исходный код не изменялся.
- Артефакт **7 файлов** с HTTP/negative results и logs.

Ранние красные CI прогонов 43393073446, 43393490540, 43394544374, 43415473141, 43416485588 и др. сохраняются исторически: Windows MAX_PATH/dependency closure, неверная исходная gate-константа 235 вместо 236 и TAP/PowerShell whitespace. Исправлены **только CI**, продуктивный код не менялся. PASS не приписывается этим красным запускам; итоговые два SUCCESS указаны выше. Числа разных уровней тестов **не суммируются** из-за пересечения/вложенности.

## Вердикт и остающиеся обязательные gates

**ПРИНЯТО:** bounded H32 P0+P1 Ordinary Chat fake pre-send admission/ledger/terminal/replay/usage/reopen и его независимая OFFLINE Windows проверка. TEST H31 guard, STANDARD/Tkinter/CMD контракт оставлен; физический smoke H31 по-прежнему OPEN. До реального провайдера требуется: полный инвентарь и pre-send guard **всех** physical sends S3b, S3c/S9/S13a, внешние model/endpoint caps и калибровка, reasoning semantics, old audit adoption/migration с zero-loss, RAW-wire retention/privacy/size, capacity и host durability/fencing, отдельный UI/real-device smoke. GigaChat OAuth, paid и REAL traffic **NOT RUN / НЕ РАЗРЕШЕНЫ**. Числа 250k/10k/20k — предпочтения UI, не подтверждённые provider caps. Исторический pinned S1 в данном CI **NOT RUN** из-за недоступного RAW, без подстановок.

Указатели: №20 §5а — общие B2 gates, №37 §3а — CHAT-FIRST маршрут, №05 — FOLLOWUP/риски, №06 — append-only событие, №34 — CURRENT, №40 — координация. `H-CODEX-000032` **не** даёт нового USER GO на Step 4 GigaChat или Colibri. Исторический авторский отчёт, snapshot БЛОК 1.1, source и backups не удалять; cleanup только отдельной безопасной проверкой. GitHub-first правило №18/№22 соблюдено. Скрипт `task_history.py validate` в рамках веб-документальной записи **NOT RUN**; структура и индекс проверяются адресно по полям/ID до публикации.

**NEXT:** пользовательский review/merge одного нумерованного GPT closeout commit; после синхронизации — отдельное согласование минимального real-provider contract/gates до любого реального вызова, без автоматического назначения новой Codex TASK.
