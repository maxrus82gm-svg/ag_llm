# Оперативная память проекта — №34

**Срез 26.11.2026 / WEB35.** Основание: опубликованный WUA main `2c0632a514ffbdecaf4cc628e5ba4f58acef48ea` (merge H46 и документации №676), H46 рабочий source `1457ba433b4b24a61c4cc374b77587af5e2ef12b`; H45 source `eb2c0a8967694712c8db0f1467331f52b224fe79`, прежний main `861c7df4f48704eb9874a0bdaa0f30f6547ce21d`. История сохранена в immutable Git; текущий статус отделён от прежних заголовков. Не новый технический PASS или release.

### Цель и ближайший приоритет

Студия Нейрополис (Web Alarm Ultra, `ag_llm`) — единая рабочая среда: Личные чаты и необязательные Workspace, общий Python Core, независимые от модели Chat/RAW/Turn/Run, сохранённая история, EVM, выбор облачных и локальных LLM. Клиент/Manager (Colibri Ultra, `local_LLM`) управляют распределёнными вычислительными узлами. №43 (Blueprint LLM / Конструктор) утверждён как последующее направление. Не создавать второе ядро, дублирующий sender, менеджер или отдельную историю. Текущий приоритет владельца: настоящие локальные модели в обычном чате, первая итерация — каталог в EVM, затем реальный потоковый ответ. Инженерный UI-редизайн и общий Workspace budget отложены, не закрыты.

### Текущая задача / разделение ответственности

H46 / `H-CODEX-000046` / `CODEX-WUA-COLIBRI-REAL-CATALOG-001`, source №676 (owner working commit 1457ba433b4b24a61c4cc374b77587af5e2ef12b), published main `2c0632a514ffbdecaf4cc628e5ba4f58acef48ea`; штатный finish ROTATED, readback OK, БЛОК 1 WAITING / 1.1 H46, review NOT VERIFIED. Автор: Python 98 PASS + 210 subtests, JS 210, S1 69, S2 73 (450 основных тестов; не складывать подтесты с основными), оба CMD isolated PASS; 0 реальных Bridge/Manager/model/paid calls. Первый параллельный loopback HTTP WinError10053 в H45 write-capability test, 97 passed + 1 error, последовательный полный повтор PASS без изменения кода/теста; причина не доказана. Независимое чтение GitHub подтверждает два GET и отсутствие execution methods в ReadOnlyColibriTransport, запрет POST/body до I/O, отдельную привязку в launcher, READ_ONLY clear allowed_operations, enabled_local_targets empty, известные цели UNKNOWN на обрыве, H45 UNKNOWN/LOCAL_CATALOG_ONLY без ложного зелёного; существующий OFFLINE TEMP gate и обычный запуск сохранены. Independent runtime/Windows CI/real catalogue NOT RUN. Отчёт `reports/CODEX-WUA-COLIBRI-REAL-CATALOG-001/report.md`, tests.md, manifest.json, finish.json, task_record.json; событие EVT-WUA-H46-SOURCE-REVIEW-20261126. Координатор сам анализирует через GitHub; Codex получает конкретные функции/файлы и проверки вместо архивов, обязательные guards сохраняются. Нового назначения нет. Colibri baseline `8df5b5ec5cb363b1ad522516865fc7f4d2a8ebbe`, Bridge v1.0.0 (OpenAPI e578c496aee64ccd0dba1279000e7e0ab12a764a, SSE e39b255f539ce69d21e263f0e7943bd7d9fa112a).

Реализован READ_ONLY в `colibri_bridge_transport.py`, `ultra_connections.py`, `launcher.py`, `model_cards.py`, `ui.py`, адресных тестах и точных S1 fingerprints (`rt002_multimodel_reconciliation.json`). Не изменены ordinary_provider.py / colibri_turn.py / turn_service.py, CMD и контракты; генерация/диагностика локального чата закрыты. Кэш каталога только в памяти процесса; при обрыве видны прежние UNKNOWN, после перезапуска память каталога не гарантирована. Смена origin/launch_identity требует новой явной привязки. READ_ONLY включается только парой --colibri-readonly-profile и --colibri-bridge-id вместе с --standard; без аргументов штатный STANDARD неизменен. Не принимать уже запущенный STANDARD за READ_ONLY. Указанная в отчёте команда — будущий согласованный запуск, не автоматическая активация. Следующая точка: fresh LOCAL-PLAN-01, независимый scoped review, согласование с владельцем и Colibri установленного Client/Bridge, owner/ACL (включая компоненты пути и остаточный TOCTOU проверки по имени), ожидаемых bridge_id/launch_identity/origin, read permission и отдельного idle active+queued evidence. M1-10 только GET health/models после отдельного OWNER GO, затем GUI EVM, никакой генерации или платных вызовов. Не назначать генерацию до результата.

### Облачный чат / H44 и H45

H44 `CODEX-WUA-EVM-PERSISTENT-CONNECTION-001` / `H-CODEX-000044`, #674 b7fb60c71f4454ad15d082dea80be2246bab9ea5. OWNER LIVE RESTART BOUNDED PASS 26.11: после одноразового явного EVM Connect разрешение и даты сохранились, первая обычная отправка после полного перезапуска дала реальный ответ без ручного reconnect. Тогда шесть карточек были orange до первой отправки; это исходный дефект, исправление H45 ниже. Автор H44 PARTIAL; 244 Python/1 skip, 14 repeated consent, S1 69/69, S2 73/73, JS 207/207, Chromium bounded PASS. Не доказаны 6 новых inference после restart, full TEST write, независимый CI, весь release. Отчёт `reports/CODEX-WUA-EVM-PERSISTENT-CONNECTION-001/report.md`, история `EVT-WUA-H44-OWNER-RESTART-20261126` / №06.

H45 `CODEX-WUA-EVM-GLOBAL-INDICATORS-001` / `H-CODEX-000045`, опубликованный source #675 eb2c0a8967694712c8db0f1467331f52b224fe79 (предшествующий merge main 861c7df4). Штатный finish: ROTATED, check/dry-run/apply/readback OK, B1 WAITING, 1.1 H45. Автор RESULT READY / OFFLINE: 121 Python PASS, 1 skip, 1 deselected (permanent TEST full write), 209 JS, S1 69/69, S2 73/73; isolated Chromium defaults/save/F5/reset/pinned/favorite/counter, оба CMD launch/exit; 0/0/0 REAL OAuth/catalog/inference. OWNER GUI: после полного перезапуска без отправки все 6 галочек зелёные, настройки 20/27/30 видны и сохранились после F5, индивидуальное поле срока удалено. Владелец отказался повторять вручную изменение порогов/сброс; значения оставлены default, это NOT RUN для ручной проверки, не FAIL. Независимое чтение `standard_live.py` (25–130), `ordinary_provider.py` (286–356, 597–619), `gigachat_runtime.py` (check), `model_cards.py` (489–548, 612–670), `test_web_alarm_persistent_connection.py` (97–138) подтверждает проектную логику, не является независимым запуском. OWNER GUI BOUNDED PASS / SOURCE REVIEW BOUNDED; независимый Windows CI/двухмониторный UX/full TEST write/REAL H45 NOT RUN. Нового live ответа именно после H45 владелец ещё не подтвердил; H44 реальный ответ относится к H44. Оба технических closeout остаются OPEN. `reports/CODEX-WUA-EVM-GLOBAL-INDICATORS-001/task_record.json`, `report.md`, `tests.md`, `finish.json`, событие `EVT-WUA-H45-OWNER-GUI-SOURCE-20261126`.

Семь состояний EVM: GREEN <20 дней; YELLOW 20–26; ORANGE 27–29; RED_CLOCK >=30 (устаревшее подтверждение, не отказ); RED_CROSS установленная ошибка; GRAY отключена; UNKNOWN нет подтверждения/неизвестный результат. Общие строго возрастающие положительные целые пороги, конфиг и сброс, одна серверная проекция на EVM/избранное/pin/external/chat/counter. Дата последнего подтверждённого ответа отдельная у каждой модели; одна модель не обновляет даты соседей. Дата в списке чатов — последняя сохранённая RAW. Давность не блокирует отправку. Сохранённое пользовательское ALLOWED не имеет таймера 24h: `standard_live.py` исключает expires_at/grant_id из consent binding; суточный `LIFETIME_SECONDS=86400` — только runtime grant. Истечение -> RESTORE_REQUIRED -> явный обычный Send восстанавливает session и при необходимости OAuth; F5/launch не вызывают платные проверки, повтор Turn не повторяет inference. Реальные guards сохраняются: отзыв разрешения, смена реквизитов/хоста/политики, TLS, scope, ledger/UNKNOWN, идемпотентность, provider caps. Не удалять 24h механизм технического допуска, не обещать живую работу при реальном отказе. Программный тест истечения автором пройден; независимый повтор OPEN, не ждать сутки.

### Colibri / WUA-COLIBRI-BRIDGE-001

Целевая цепь: Studio backend -> один явно разрешённый loopback Client Bridge -> Client -> существующие Manager/слоты/модели. Studio владеет EVM/Turn/RAW/Workspace/history/context/tools/permissions, Client — маршрутизацией и контролем Manager. Браузер не получает Bridge токен/путь и не обращается к Manager напрямую. Colibri producer v1 #107 2d9e7f6fb860fdd53747f4ba75350d15bab27877 / #108 883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea, #111 a2796c3a4f452bb7043502c7ef1c4086e0672d6c. WUA #657 проверил 68+22 producer tests и 4 unit/7 loopback fake Manager; реальный установленный Bridge не проверялся. #659/H-CHATGPT-000013 unified Turn backend, #660/H-CHATGPT-000014 existing EVM+ordinary Chrome; cloud→local→cloud один Chat/RAW, сохранение выбора, reasoning/partial через 750ms RUN polling, не native browser SSE. #661/H-CHATGPT-000015 two fake Manager, стабильный target_id, instance_id меняется при restart, disambiguation Manager/slot, Run Store SSE batching (12 пакетов/64KiB, первая часть сразу), 48 fragments 11.562→3.586s fixture, не LLM tok/s. #662/H-CHATGPT-000016 Windows private ACL negative, точный неизменённый PROJECT_CONTEXT_TEMPLATE только пустой маркер; настоящие system/tool directives не подменять и не удалять. #663/H-CHATGPT-000017 OS owner lease и явная orphan reconciliation, UNKNOWN без автоматического retry; #664/H-CHATGPT-000018 interrupted append, evidence-first dry-run и explicit approval, known committed terminal сохраняется, unindexed bytes только после проверки/approval, forged checksum refused, remote engine stop не доказан смертью Studio. Адреса всех этих отчётов — №05/06 и прежний #34 в закреплённой ревизии.

MVP1 остаётся PARTIAL: #665 `CHATGPT-WUA-COLIBRI-MVP1-MATRIX-20261123-001` / H-CHATGPT-000019: 8 scoped OFFLINE PASS / 3 PARTIAL (M1-05 usage, M1-09 broader CI/package, M1-12 joint) / 2 NOT RUN (M1-10 actual HOME read-only, M1-11 real inference/paid cloud). Отчёт и матрица `reports/CHATGPT-WUA-COLIBRI-MVP1-MATRIX-20261123-001/`. #666 H-CHATGPT-000020 full local S1 69/69 with pinned RAW, S2 73/73, D8 1, negatives 5, Python88, JS207; initial WinError10053 retry PASS cause UNKNOWN. #667–669/H-CHATGPT-000021..23 repair Windows sparse long paths, real mcp==2.2.0, original pinned S2 guard; #670/H-CHATGPT-000024 verified exact #669 hosted run 45253916385 job 137970549821 SUCCESS scoped S1 STATIC16, S2 73, D8 1, negatives5, HTTP36, JS207. Broad general smoke 45251979686 checkout failure and full historical S1 RAW hosted/packaging remain OPEN. No new hosted run H45 asserted. #671 `CHATGPT-WUA-COLIBRI-M1-10-READINESS-20261124-001` / H-CHATGPT-000025 source-only readiness and handoff: GET health/models do not expose active+queued, READY != idle. Installed HOME version/ACL/identity/occupancy must be checked separately. M1-10 HOLD/NOT RUN, separate exact OWNER GO after trusted read-only idle evidence; no scan/fallback, only protected discovery/token, IPv4 loopback, no redirect/proxy, expected bridge_id+launch_identity. M1-11 separate permission, M1-12 joint acceptance, no MVP2. `reports/CHATGPT-WUA-COLIBRI-M1-10-READINESS-20261124-001/`.

Future real generation must use existing unified Turn/RAW/Run Store and stable target identity, separate REAL vs OFFLINE provenance, real approved registry/storage scope, preserve no resend on UNKNOWN, cancel ACK ≠ remote stop, actual usage nullable/derived explicitly. No direct Manager fallback or copied credentials, no silent removal of real context. Installed Colibri source/disk != loaded runtime; recent Colibri source includes CPU/CUDA work and owner GUI, not proof of current idle or Bridge activation. Colibri tactical source `local_LLM@8df5b5ec5cb363b1ad522516865fc7f4d2a8ebbe`, Documents/13 and 18. No change to its repo, no model start/stop/restart.

### Новые требования владельца 26.11 — EVM и статистика

Проектный документ `Документация/Локальные LLM — подключение и статистика.md`: вручную подключается Client, автоматически каталог всех Manager/LLM; сохранение привязки, обновление/отключение, человеческая инструкция. Colibri coordinator отвечает за постоянную накопительную базу на каждом Manager, серии model/CPU-CUDA/config/host, Client realtime projection. Studio: LIVE tok/s при генерации, AVG при idle/stop, stale/unknown честно. SQLite — предложение; согласовать контракт до изменения v1. Не блокирует H46/M1-10. LOCAL-PLAN-01 прочитан на HOME SHA b215ef9882542d5e38590965b8635b8c8039320eaf87f7626f9c7137c97831ee; M1-10 HOLD, план не менялся.

### Shared local plan / coordination gate

Единственный актуальный общий план: [[34.1_Общий план развития WUA и Colibri]]. Last confirmed WUA plan read before H45 task: SHA256 b215ef9882542d5e38590965b8635b8c8039320eaf87f7626f9c7137c97831ee, archive 1071b531a3985ecb08d474651f73cedaf5aeb73cec1108b19daf764848fb4102; Colibri Documents/18 reports own 26.11 00:49:45+05 read same SHA, WUA IN_PROGRESS / COLIBRI SUBMITTED / M1-10 HOLD. Это историческая сверка, не новое чтение физического №34.1 координатором. В этой GitHub-only сверке fresh LOCAL-PLAN-01 NOT RUN; не объявлять GO/ACCEPTED, не менять общий этап, не назначать новые задачи, пока владелец не подтвердит актуальный gate. Каталогная задача H46 уже сдана и опубликована; не ретроактивно утверждать PLAN_READ. Перед следующей TASK, значимым результатом, сменой чата/этапа обязательны fresh helper read на HOME по №08/18; отсутствие = STOP для этих действий. WUA изменяет только свою часть через CAS helper, Colibri свою, архив после двух ACCEPTED. Пользователь обсуждал перенос общего плана в GitHub; **действующее LOCAL-ONLY пока не отменено**, никакого принудительного add или копии.

### Открытые продолжения, которые нельзя потерять

- FOLLOWUP-WUA-H44-EVM-INDICATORS-001 -> H45, основной дефект исправлен по owner GUI, independent technical OPEN. FOLLOWUP-WUA-H44-VERIFY-001 -> авторский expiry regression в H45, независимый Windows CI/expiry/negative/TEST guard OPEN. Обновить H44/H45 независимым review только на точной ревизии. Не запускать новые paid проверки автоматически.
- FOLLOWUP-WUA-H44-EVIDENCE-HYGIENE-001: исторический cmd.stdout.txt overwritten, прежний кандидат #568 78a8f5f0277f35228c66d4f199dc2024562fc1a9; restore only expected SHA256 d7a488d104855196ca95e4023060e5d082e4836de18f3c3cad5b33916dec9347; текущую повреждённую копию сохранить. Три отмеченных tracked .ultra файла в #674 и новый `Чат_pro_02/привет.txt` в #675 требуют provenance и решения владельца; не удалять локальную историю и чужие данные. Отдельно от Bridge.
- FOLLOWUP-WUA-H45-UI-COPY-001: `web_alarm/ui.py:723` содержит старую подпись «срок актуальности меняет только границу между ✓ и !» в профиле, где поле уже удалено. Подтверждено source и owner GUI; отдельная мелкая правка UNASSIGNED; не включать самовольно в preflight.
- Старые OPEN: H41/H42 S2/Tcl independent, окна multi-monitor/topmost/Snipping Tool causal link UNKNOWN, H42 UNKNOWN stale settings-version race hypothesis; H43 legacy second ACTIVE and instance GUI; GigaChat shared registered Workspace repair independent/owner multi-Workspace REAL open, damaged/unknown ledger refused; H36 historical review source SHA drift, task_history render WinError5 and Windows EOL mismatch; P9/Run Store audit path/single writer and Tk readers P1–P6; clean Windows portability and S3b/S3c/S9/S13a/B2/WA4-R gates, freeze MCP/V2Ray/WFP №39 unchanged. Full queue №05 is authoritative, do not replace it with this selection. No silent closure of historical tasks.
- H44/H45 full permanent TEST write blocked by existing guard for .ultra inside repo; fixture-level PASS and CMD launch/exit do not resolve this. Do not weaken guard. Source GigaChat consent/expiry checks are bounded, no new live or paid calls by coordinator.
- UI shell redesign (common left navigation / four sections, existing graph geometry), Blueprint №43, usage/cost refinements and broader local model integration are future separate scopes. Do not interleave with M1-10 preflight.

### Operating rules / project continuity

Two permanent starts: `Start_WebAlarm_Standard.cmd` (localhost default 8765; own persistent Workspace/chat/history/preferences), `Start_WebAlarm_Test.cmd` (red isolated OFFLINE TEST fail-closed, no fallback to STANDARD). Separate Tk `Start_Ultra.cmd` untouched, old BAT empty, no third user launcher automatically. Per-chat model preference, history and draft independent of availability; EVM off disables sending but preserves chats even if all models disabled. No artificial trial quotas; provider and agreed budget/storage safety remain. Read exact owner-approved source at task start, no full archive dumps. Codex executes local source/tests only, Git/GitHub prohibited unless separately permitted. Coordinator GitHub-first, Desktop Commander only when unique documented local gate/check is required. TASK three blocks: complete assignment with literal **TASK ID:** followed by ID in backticks; short activation; plain explanation. User inserts between markers; preflight before launch; finish emits HISTORY ID + snapshot + record; no manual rotation. One logical task one numbered atomic GPT commit; user merges main. Do not duplicate numbering when user and coordinator publish concurrently. No background paid checks or independent PASS from author report. Preserve all old TASK/FOLLOWUP IDs. №34 refreshed on material result without endlessly appending old chronology; №40 one current line per direction; №05 full queue and all registered history; №06 append-only; №001 10-row window and exact records. Before chat handoff read №08/000/34/40/05/short №001, source-specific reports as necessary, and shared plan gate.

WORKSPACE-ISOLATION-01 #673 `CHATGPT-WUA-WORKSPACE-ISOLATION-20261124-001` / H-CHATGPT-000026: 14 listed objects/129 files verified SHA+size, moved to ignored project subtrees, no deletion. Worktree UI_TEST_651 #670 relocated under _ultra_agent_test, preserved .venv, before/after fake HTTP smoke PASS, interactive CMD/browser NOT RUN. New launcher `_ultra_agent_test/Start_WebAlarm_UI_TEST_651.cmd`; prior gate logs -> reports/_local/<unchanged-name>, backups/cards -> Backups/<unchanged-name>. Canonical map `reports/CHATGPT-WUA-WORKSPACE-ISOLATION-20261124-001/report.md`. All new local artifacts under ag_llm, not M:\GitHub root; no forced tracked cleanup, no live storage move, no secret export. Exact previous historical revisions and evidence remain.

### Current evidence locators and next

H46 record/report/tests/finish and source above. H45/H44 original reports preserved; №40 coordination, №05 permanent FOLLOWUP, №06 EVT-WUA-H46-SOURCE-REVIEW-20261126 and EVT-WUA-H45-OWNER-GUI-SOURCE-20261126. Older histories remain addressable. Earlier 74,051-symbol №34 preserved at reports/CHATGPT-WUA-DOC-CONTINUITY-20261117-001/preservation/34_TACTICAL_CONTEXT_before.md, main@70870380fc2828087f785357eeb70c0ac343da9f (#641). NEXT: independent H46 scoped checks; fresh local plan and exact owner preflight GO; real catalogue in EVM M1-10; only then agree separate source task for first real local Turn. H44/H45 acceptance and hygiene OPEN, do not delay source planning unnecessarily. No new activation/stage/merge/live by factual doc update. #08 approved WUA naming «Нейрополис» unchanged; Colibri source records «Неополис» in its own UI, not permission to rename WUA.

**OWNER GO 22.11.2026 — LOCAL-ONLY:** только №34.1 и №34.1.1 исключены из Git точными правилами .gitignore. Единственный экземпляр на HOME в прежнем каталоге WUA. Не добавлять принудительно, не копировать в Colibri, не публиковать снимки этих двух файлов. Резервные копии под общим lock вне репозитория. Остальные исходники, документация, отчёты и helper — штатно через GPT (Colibri: GPT_2_local), владелец Fetch origin → Choose a branch to merge into main → Merge → Push origin. Не использовать stash/reset/checkout для обхода защиты; при dirty overlap остановиться и сохранить/reconcile изменения. Не трогать локальные планы при Git-операциях; при отсутствии файла STOP. Не запускать git clean -x/-X на HOME.

## Сохранённые адреса прежней редакции

Ниже только адреса прежних заголовков; они **не являются текущими указаниями**. Полная неизменённая редакция: [исходный документ](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md), Git blob `f98eef2f0aa649896db6417e7f7e480e2aa66d47`. История и исходные свидетельства остаются доступными по точной ревизии, №05/06 и TASK ID.

## CURRENT 26.11.2026 — H44 / #674 OWNER LIVE RESTART BOUNDED PASS
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L3).

## CURRENT 24.11.2026 — WORKSPACE-ISOLATION-01 / #673 (LOCAL MIGRATION)
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L7).

## CURRENT 24.11.2026 — WUA #671 M1-10 PREPARED / NOT LIVE
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L11).

## CURRENT 24.11.2026 — WUA #670 verified scoped GitHub Actions SUCCESS
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L15).

## CURRENT 24.11.2026 — WUA #669 S2 SHA-pinned guard file in CI sparse checkout
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L19).

## CURRENT 24.11.2026 — WUA #668 hosted CI SDK mcp 2.2.0 requirement
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L23).

## CURRENT 24.11.2026 — WUA #667 hosted CI Windows checkout long-path fix
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L27).

## CURRENT 24.11.2026 — WUA #666 S1/S2/D8 offline closure; hosted CI awaiting result
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L31).

## CURRENT 23.11.2026 — Colibri MVP1 independent acceptance matrix / #665
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L35).

## CURRENT 23.11.2026 — Colibri MVP1 interrupted Run Store / manual review
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L39).

## CURRENT 23.11.2026 — Colibri MVP1 OS owner lease and recovery
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L43).

## CURRENT 23.11.2026 — Colibri MVP1 Windows safety PRE-LIVE
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L47).

## CURRENT 23.11.2026 — Colibri MVP1 readiness / 2 fake Manager / stream batching
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L51).

## CURRENT 22.11.2026 — Colibri MVP1 dynamic EVM + ordinary Chrome
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L55).

## CURRENT 22.11.2026 — Colibri MVP1 unified Turn backend
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L59).

## CURRENT 22.11.2026 — Colibri MVP1 transport baseline
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L63).

## CURRENT 22.11.2026 — нижние раскрыватели
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L71).

## CURRENT 22.11.2026 — sidebar inline / disclosure
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L75).

## CURRENT 22.11.2026 — OWNER TEST GUI PASS
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L79).

## CURRENT 22.11.2026 — компактный sidebar
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L83).

## OWNER GO 22.11.2026 — межпроектная работа
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L88).

## CURRENT / 18.11.2026 — REGISTERED WORKSPACE GIGACHAT REPAIR IMPLEMENTED; OWNER GUI / CI OPEN
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L94).

## CURRENT / 17.11.2026 — STANDARD OWNER GUI WORKS FOR PERSONAL GIGACHAT; WORKSPACE FAIL; DOC №18
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L102).

## CURRENT / 17.11.2026 — H43 PERSONAL ACCOUNT RECOVERED / OWNER GO / REAL MODEL HOLD
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L110).

## PREVIOUS / 17.11.2026 — H43 LEGACY RECOVERY: LOCAL REPAIR PARTIAL / REAL HOLD
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L116).

## CURRENT / 17.11.2026 — H42 SOURCE REVIEW / БЛОК 1 WAITING
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L126).

## Цель и фактическая точка
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L138).

## Последние пять задач и доказательная граница
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L144).

## Наблюдения владельца 17.11 — не выдавать за инженерную независимую приёмку
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L155).

## Что открыто и критерии
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L163).

## Ближайшее продолжение
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L175).

## Навигация и архив
[Исторический фрагмент](https://github.com/maxrus82gm-svg/ag_llm/blob/861c7df4f48704eb9874a0bdaa0f30f6547ce21d/%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B0%D1%86%D0%B8%D1%8F/34_TACTICAL_CONTEXT.md#L181).
