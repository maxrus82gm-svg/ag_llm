# Задачи Claude

**Назначение:** отдельный оперативный handoff для задач, которые передаются Claude Desktop / Claude Code в проекте `ag_llm`.

Общий проектный маршрутизатор координатора (не обязательное полное чтение Claude при каждой TASK): [[000_Задачи для агента]]
Персональная история выполненных Claude TASK: [[001_История выполненных задач Claude]]

## Правила

**Приоритет USER GO 2026-10-24:** в этой персональной карточке БЛОК 1 и БЛОКИ 2–4, а также личный архив `001` обновляет ChatGPT-координатор **только после** пользовательской публикации и верификации/решения terminal BLOCKED. Локальному исполнителю запрещено изменять любые БЛОКИ карточки, `001` или самостоятельно запускать ротацию. Отчёт/manifest/evidence в разрешённой папке сохранять обязательно; до приёмки БЛОК 1 остаётся за текущей TASK. Источник: `DOC-TASK-CLOSEOUT-OWNER-01@1` (18); старые правила самоличной ротации более не действуют.

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Claude]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID.


- **`DOC-TEST-LIFECYCLE-01@1` (18) — длительные тесты и честная сдача.** Не выдавать копируемый финальный результат или `RESULT READY` до окончания обязательных тестов. Если управление возвращено до их окончания, начинать сообщение с `# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ`; сообщить TASK ID, проверенный статус и как возобновить. Черновой `report.md` помечать `DRAFT`, не обещать автоматического пробуждения без доказанного транспорта. Перед технической сдачей проверить exit code, итоговый файл, изоляцию, manifest и evidence; архив/ротация — только после coordinator review; при FAIL/BLOCKED сообщить факты, а не объявлять PASS.
- **`DOC-VERIFIER-BLOCK4-01@1` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Общий Git boundary:** до любых действий применить `rule-ref:DOC-GIT-01@1` из 18. Локальный Claude не вызывает Git/GitHub даже ради `status/diff/log/show` без отдельного конкретного разрешения пользователя; историю и SHA запрашивает через пользователя/ChatGPT-координатора. Прямое чтение и разрешённая правка файлов, offline tests без Git и самостоятельная engineering-аналитика остаются разрешены в пределах TASK. Записи Git в исторических отчётах не дают текущего разрешения.

- **Чтение по TASK / `DOC-TASK-READ-SCOPE-01@1`:** прежде всего собственные Правила, активный БЛОК 1 и относящийся к нему БЛОК 4 (READ-ONLY); актуальные разделы `08`, `34`, архитектура ветки и профиль тестов `36/36.1/36.2` или `36.3` — по точным селекторам/цели из TASK. Весь глобальный `000` и весь регламент `18` без адресной причины не читать; при нехватке/конфликте правил перечитать требуемые определения `18` с `requires`, не отменяя Git-запрет, отчётность, safety и независимую приёмку.
- Здесь фиксируются только конкретные задачи, делегированные Claude.
- Этот файл — операционная карточка Claude, а не замена канонических общих реестров/истории `000/05/06` и профильных документов. Полный общий `000` читает координатор; Claude получает адресные нужные разделы в БЛОКЕ 1 (`DOC-TASK-READ-SCOPE-01@1`).
- Если Claude выполняет значимое изменение проекта, итог после проверки должен быть отражён и в канонической документации проекта по обычным правилам.
- **Обязательный локальный отчёт / `DOC-LOCAL-REPORT-HANDOFF-01@1` (18):** для каждой TASK, включая отрицательные и BLOCKED итоги, сохранить полный `report.md`, manifest и безопасные доказательства внутри `ag_llm`, например в утверждённом `Alarm/ALARM_TASK_SESSION/TASK_<TASK-ID>/` или `reports/<TASK-ID>/`, так, чтобы публикационный комплект не игнорировался `.gitignore`. TEMP/внешние диски — не единственный архив; приватные raw данные не публиковать, а создавать адресную очищенную копию или явный `EVIDENCE NOT PUBLISHED`. Обычно commit/push делает пользователь; Claude без конкретного user GO не использует Git/GitHub и не имеет постоянного канала отправки в ChatGPT. Активные БЛОКИ 1–3 от этого уточнения не меняются.
- До начала mutation-задачи явно указывать scope, запрещённые действия и критерии проверки. Эти границы ограничивают **самовольные изменения**, но не глубину инженерного анализа.
- Claude работает как самостоятельный полноценный инженерный агент, а не только как исполнитель перечисленного чек-листа. Claude и Codex — равноправные независимые агенты, назначение по текущей TASK не создаёт иерархии. Перечисленные tests/acceptance cases — обязательный минимум, не потолок. Перед `RESULT READY` Claude обязан сделать собственный adversarial pass и попытаться опровергнуть решение релевантными race/restart/replay/persistence/ownership/finalization/compatibility сценариями.
- Если неперечисленная проблема найдена внутри текущего scope — Claude сам её проверяет, исправляет и добавляет regression test. Если исправление выходит за scope/этап или требует архитектурного решения — код за рамками не менять; reproduction/evidence/root cause/impact и предложение обязательно вынести в task-report и БЛОК 3 как `FINDING / PROPOSAL / BLOCKER` для решения verifier/пользователя.
- Claude имеет право читать соседний релевантный код и делать безопасные isolated probes/tests ради проверки гипотез. Это не даёт права самовольно запускать следующий этап, менять утверждённый план или расширять production mutation-scope.
- Секреты, токены, cookies, Organization ID и платёжные данные сюда не записываются.
- Технические наблюдения по моделям, лимитам и сети вести в `27_Claude.md`.
- БЛОК 1 — входной активный слот. Пользователь/координатор переносит сюда следующую утверждённую постановку. Claude обязан перечитать БЛОК 1 перед стартом.
- После TASK Claude сохраняет проверенный `report.md`, manifest и evidence и сообщает `RESULT READY / AWAITING INDEPENDENT VERIFICATION` либо честный иной статус. Координатор после публикации и приёмки ведёт `001`, БЛОКИ 2–4 и очищает БЛОК 1 лишь после защищённого архивного readback. При сбое closeout — `CARD CLOSEOUT BLOCKED`.
- Если сессия исполнителя оборвалась, сохраняется текущий БЛОК 1; Claude не чистит его и не возобновляет историю. Координатор при продолжении сверяет уже опубликованный статус и состояние архива перед любым closeout.
- БЛОК 2 — максимум пять кратких TASK, БЛОК 3 — максимум пять кратких итогов с locators. Предыдущие полные БЛОКИ не вкладывать рекурсивно.
- Перед вытеснением любой записи из окна пяти удостовериться, что её полный текст и результат сохранены в `001`. Архив фактических результатов не требует PASS; реестр `DONE / VERIFIED` — только после независимой приёмки.
- Полная постановка TASK может дополнительно фиксироваться в обычном Chat как человеческий резерв/след обсуждения, но каноническим источником исполнения остаётся актуальный БЛОК 1 персональной карточки.
- Claude **не обновляет** БЛОКИ 1–4 и `001`; их, а также VERIFIED-реестр, ведёт координатор после независимой приёмки/явного terminal решения. Полный локальный task-report обязателен.
- **Форма итогового отчёта в Chat.** По завершении TASK (`RESULT READY`, `FOLLOW-UP`, проверка) Claude выдаёт итог одним копируемым блоком кода с меткой `text` — самодостаточным, без рассуждений и хода работы: TASK ID и статус; что подтверждено или найдено; root cause; что сделано; изменённые файлы; проверки с точными числами; findings / PROPOSAL / DECISION / риски; блокеры; documentation impact; путь к полному отчёту; NEXT. Промежуточные сообщения о ходе работы остаются вне блока; после блока — не больше одной-двух строк (например, напоминание о незакоммиченном). Полный отчёт по-прежнему хранится файлом в `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-<ID>/`; блок — его краткая форма для передачи verifier / другому агенту без правок.

---
# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА
---

Статус: НАЗНАЧЕНА / ОЖИДАЕТ ЗАПУСКА ПОЛЬЗОВАТЕЛЕМ
TASK: CLAUDE-WA4-R-TOCTOU-RACE-REVIEW-001
ARCH CLASS: Web Alarm / WA4-R Reliability / Adversarial Race Research
PRIMARY: 36.2; SECONDARY: 23, 24, 25
BASE: main@357a71442cc57a67e5df45d7901401d495409df0 (сверить локальные байты/ревизию с доступным источником через пользователя; Claude без Git)
OWNER: Claude 008 — инженерное исследование. INDEPENDENT VERIFIER: ChatGPT. USER GO: scoped offline adversarial research and safe disposable TEMP probes ONLY.

## 1. Цель

Проверить реальные TOCTOU-гонки между проверкой пути, выбором canonical target, snapshot / precondition / ownership / CAS, фактической записью, post-proof и финализацией Web Alarm. Установить, может ли конкурентный процесс/поток заменить объект (файл, каталог, junction/symlink/reparse) после проверки так, что запись уйдёт не туда, будет затёрт чужой объект, получит ложный VERIFIED или испортит durable recovery/receipt. Не смешивать с уже принятым F-T1 test-harness/TMPDIR fix: этот дефект закрыт bounded Windows CI, а malicious/risk-driven TOCTOU ещё не доказан. Отдельно различать подтверждённую уязвимость, теоретический риск, Windows-specific limitation и ложную тревогу теста.

**Тип TASK: DIAGNOSTIC / DESIGN + bounded OFFLINE PoC.** Не исправлять production/runtime сейчас и не включать rollout. Цель — независимая проверяемая матрица угроз и доказательное решение, нужно ли выдавать следующую узкую repair TASK. Не ждать заранее заданного исхода (FAIL или PASS).

## 2. Входные сведения и чтение по scope

- Свою карточку: Правила + БЛОК 1; БЛОК 4 read-only. Профиль `36.2` и тестовые нормативы `36/36.1` (TEST-DEV/COV/EXEC/QA/FLAKY/EVID/SCOPE), `23` и актуальные WA4-R секции `24/25`; `34` — текущий раздел и актуальный WA4-R. `18` — адресно `DOC-GIT-01@1`, `DOC-TASK-CLOSEOUT-OWNER-01@1`, `DOC-TEST-LIFECYCLE-01@1`, `DOC-TASK-READ-SCOPE-01@1`, `DOC-LOCAL-REPORT-HANDOFF-01@1`.
- Критический код — `web_alarm/mutation_executor.py`, `web_alarm/operation_store.py`, `web_alarm/manifest_store.py`, `web_alarm/snapshot_store.py` (если существует; реальную структуру установить), `web_alarm/workspace_registry.py`, `web_alarm/reconciliation.py`, `web_alarm/transport_event_recovery.py`, `web_alarm/server.py`, `web_alarm/cli.py`, `wa4a_acceptance.py` и соответствующие тесты. Это перечень для *чтения*, не разрешение менять все файлы. Не выдумывать отсутствующие модули/точки entry.
- Из прошлых gate: WA4-E/RC-3 lock/CAS; WA4-R OBSERVE bounded; F1–F4, AUD-02c/04, PWR-01, W3 — отдельные OPEN, не выдавать их за закрытые. Известные non-atomic move/rename и junction/Windows reparse нюансы включить как потенциальные сценарии.
- Точный pinned SHA и конфликт локальных редакций установить до тестов (без Git-вызова от Claude: запросить через пользователя, при несоответствии STOP с evidence).

## 3. Scope и permissions

**READ:** релевантный исходный код и тесты Web Alarm в локальном `ag_llm`, документация по указанным селекторам, текущие guard/runner ограничения.

**WRITE (только согласованные новые файлы):**
- `test_web_alarm_toctou_race_review.py` — необязательный новый standalone test module только для безопасных *изолированных* adversarial probes; если используется, не менять discoverability/CI и не добавлять production changes.
- `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TOCTOU-RACE-REVIEW-001/` — `report.md`, `manifest.json`, `runs/`, `tools/` для воспроизводимых, sanitised proof artefacts, минимальных test helpers. Временные рабочие материалы — только в одноразовом TEMP, без чувствительных путей в публикации.
- Не создавать новый тестовый файл, если probes можно честно провести существующими тестами и сохранить script/evidence в TASK package.

**ЗАПРЕЩЕНО:** менять `web_alarm/*.py`, `wa4a_acceptance.py`, существующие `test_*.py`, CI/workflows, `000/001/05/06/18/23/24/25/34/36*`, настоящий registered Workspace, active TASK/store, архивы чужих задач, системные права/параметры, firewall/V2Ray/MCP, сеть, Git/GitHub (включая read-only) без нового адресного USER GO. Ни production recovery apply, ни реальные destructive writes. Не менять guard ради прохода тестов. Никаких изменений прав symlink/junction на хосте, если это требует admin: пометить NOT RUN и не обходить систему.

## 4. Обязательная матрица исследования

1. **Инвентаризация границ:** реальная цепочка `request → admission → path resolve → snapshot/precondition → target claim & lock → CAS → mutation → post-proof/receipt → VERIFIED/closeout`, отдельно для create/edit/write/delete и двухступенчатых move/rename. Отметить, где filesystem handle/identity защищён, а где проверяется только строковый путь.
2. **Файловый race:** внешняя замена/удаление/восстановление файла между hash/precheck и atomic replace/write; изменение содержимого при сохранении имени; поведение при sharing violation; детерминированный pause/barrier injection, без опоры на многотысячные случайные повторы.
3. **Каталоги и reparse:** rename ancestor, replace directory, symlink/junction swap на Windows, `..\`/case/extended paths; доказать физическое место возможного side effect (file hashes/identity), а не только status `blocked`. Если создать ссылку нельзя — SKIP/UNPROVEN.
4. **Ownership/concurrency:** два независимых процесса и два TASK/operation на том же canonical physical target; claim under lock, stale revision, retry/replay after interrupted write; не игнорировать root guard и no-Git/no-network.
5. **Receipt / recovery:** инъекция сбоя между successful physical mutation и persist receipt/verification; допускается только controlled exception/child process termination в TEMP без системного crash, подтверждение reopen отдельным process; никакого ложного VERIFIED/COMPLETED, blind replay или потери оригинальных доказательств.
6. **Негативный контроль:** искусственно ослабленный oracle или строго тестовая imitation path-swap должен порождать обнаруживаемый FAIL; без proof test может быть INCONCLUSIVE, а не PASS. Отдельно учесть F-T1 CI env `TMPDIR/TEMP/TMP` и не повторить старую ошибку выбора корня.

## 5. Тестовая стратегия

Сначала статический source-to-sink review и минимальные детерминированные PoC с изолированным внешним parent TEMP/inner root. Все дочерние процессы получают согласованный temp-root, где требуется. Каждый сценарий должен иметь pre/post SHA/bytes, процессную идентичность, точку race injection, статус и явно `SIDE EFFECT: NONE/IN-ROOT/OUT-OF-ROOT/UNKNOWN`. Сохранять RED и GREEN лишь при реальном воспроизведении; не называть expected test refusal ошибкой Web Alarm. При возможности — несколько независимых повторений *только* для выявленной нестабильности и bounded full regression; не запускать 989 тестов без причинной необходимости для diagnostic-only research. Нельзя расширять guard или маскировать FAIL.

**Нужные доказательства:** threat matrix (severity/likelihood/reproducibility), precise vulnerable/source line references, target identity/pre/post bytes, Windows/platform limits, parser/runner fail-closed, tests total PASS/FAIL/ERROR/SKIP/NOT RUN, raw local path sanitized, manifest SHA-256/size/EOL. Если обнаружена достоверная опасная ошибка, ограничить probe, зафиксировать минимальный RED и предложить отдельно узкую repair TASK — **не лечить runtime по своей инициативе**.

## 6. Ожидаемая сдача

`Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TOCTOU-RACE-REVIEW-001/report.md` должен включать: архитектурную схему write boundary; audit каждого сценария; reproducible PoC или точные причины NOT RUN; фактические файловые эффекты; negative controls; список findings с `CONFIRMED / RISK / DISPROVED / INCONCLUSIVE`, severity и проверенные инварианты; минимальную рекомендацию по repair/priorities; `DOC IMPACT`; explicit `NO PRODUCTION CHANGE / NO ROLLOUT`. Сохранить sanitized files и manifest. Не вносить найденные факты в общую документацию/личный 001 самостоятельно.

**Самопроверка Claude:** собственный adversarial pass перед итогом; для предупреждений средней/высокой критичности доказательства должны быть перепроверены новым процессом или чётко отмечены как только гипотеза. Не объявлять WA4-R DONE, W3/PWR-01/ WARN/GATEWAY REQUIRED/STRICT принятыми.

**STATUS:** `RESULT READY / AWAITING INDEPENDENT VERIFICATION` — лишь после завершения выбранных обязательных сценариев и readback пакета; `PARTIAL / BLOCKED` с точным NEXT при ограничениях. Если тест ещё работает — красный `ТЕСТЫ НЕ ЗАВЕРШЕНЫ` с реальным состоянием, без преждевременного финального блока.

**Ответ пользователю:** один краткий копируемый блок `text`: TASK ID, итог, матрица, изменения, tests/evidence, risks, рекомендации, report/manifest locator, NEXT. Дальше пользователь публикует на GitHub, ChatGPT проверяет код/evidence и независимый CI и *только потом* заполняет `001`, БЛОКИ 2–4, журнал 06 и актуальный 34, а БЛОК 1 освобождает при успешном closeout. Ни один документный блок не ротировать исполнителем.

## 7. STOP / следующий gate

Без отдельного USER GO не переходить к физическому ремонту, изменению production code, live preflight, security/power-loss gates, rollout. При confirmed HIGH — сохранить исключающий доступ за пределы TEMP тест и немедленно сообщить координатору/пользователю. Итог исследовательской TASK — предложение о следующем минимальном ремонте или evidence-based отказ от него, а не автоматическое решение включить строгий режим.

---
# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Скользящее окно до 5 выполненных TASK; полный архив — [[001_История выполненных задач Claude]]. После шестой задачи самая старая строка вытесняется только отсюда, после архивного readback. Независимый статус не выдумывать.

- **2026-10-24 / CLAUDE-WA4-R-FT1-CI-REPAIR-001** — устранение девяти ошибок независимой Windows-проверки guard (CI #40112070376). Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.
- **2026-10-24 / CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001** — устранение ложных срабатываний guard тестового runner (F-T1) и проверка полноты forensic-архива при повторном восстановлении (`_proven_attempts`). Статус: RESULT READY / AWAITING INDEPENDENT VERIFICATION.
- **2026-10-23 / CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001** — исправление fail-open F-ES-01 / F-ES-02 + REVISE F-ES-03 (2026-10-24) + локальное завершение пакета (SHA-256/manifest/mapping, 2026-10-24) + CHAT-ONLY AMENDMENT: дубликаты `id` в `runs-map.json` (2026-10-24). Статус исполнителя: RESULT READY; независимо (БЛОК 4, 2026-10-24): PASS / BOUNDED OFFLINE VERIFIED.
- **2026-10-21 / CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001** — анонимизация диагностических evidence. Статус: PARTIAL / REWORK REQUIRED.
- **2026-10-20 / CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001** — офлайн восстановление оборванного журнала. Статус: RESULT READY / NOT INDEPENDENTLY VERIFIED.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CLAUDE-WA4-R-FT1-CI-REPAIR-001** — дефект теста, не guard: CI задаёт `TMPDIR`, а `tempfile` берёт его раньше `TEMP`/`TMP`; ребёнок теста наследовал `TMPDIR` и его guard защищал TEMP раннера вместо своего `inner` → 8 «внешних» записей законно `allowed` (внутри TEMP раннера). Исправлен только `test_web_alarm_runner_guard.py` (`TMPDIR` + oracle фактического корня + тест CI-окружения); guard не менялся. RED в CI-окружении = 9 FAIL как в CI; мутанты 9/9 в обоих окружениях. Полный источник: запись в `001` и `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-FT1-CI-REPAIR-001/report.md`.
- **CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001** — F-T1: `Path.resolve()` оставлял префикс расширенного пути при гонке создания каталога (ошибка 3→2) и разрешал удаляемый каталог в `$Extend\$Deleted` → guard снимает только свой префикс и переразрешает `$Deleted`, явные выходы по-прежнему отвергаются; Archive Retry: `tail.bin` и квитанция не проверялись → проверяются, повреждение → REFUSED без записи, отсутствие квитанции допустимо. Мутанты 6/6 + 9/9. Полный источник: запись в `001` и `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-FT1-ARCHIVE-RETRY-001/report.md`.
- **CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001** — F-ES-01/F-ES-02 закрыты fail-closed; REVISE F-ES-03: `--package` = комплект, внутри или вокруг него, через ссылку или жёсткие ссылки → `package-not-independent`, REFUSED; завершение: 201 CRLF-копия прогона не сверялась бы с опубликованным блобом → копии в LF, manifest отказывает при CR, `evidence.json` исправлен; CHAT-ONLY AMENDMENT: `tools/check_package.py` — уникальность `id` в `runs-map`, строгая загрузка JSON (повтор ключа), безопасный `id`, самотест 11/11 DETECTED, пакет CONSISTENT. Полный источник: записи в `001` и `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001/report.md` (§12–14).
- **CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001** — Независимые Linux tests: штатные 38/38 PASS, но 2 подтверждённых fail-open; публикация исторических evidence заблокирована. Полный источник: поиск TASK ID в `001` и task-report проекта.
- **CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001** — Offline inspect/apply, архив до исправления; live storage и production не затронуты. Полный источник: поиск TASK ID в `001` и task-report проекта.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Автор:** ChatGPT, Claude — READ-ONLY. Постоянный архив всех вердиктов — 06. БЛОКИ 1–3 не изменялись.

## 1. Последнее заключение: 2026-10-24 / CLAUDE-WA4-R-FT1-CI-REPAIR-001

**Независимое заключение: PASS / BOUNDED WINDOWS TEST GATE. WA4-R остаётся PARTIAL.** Публикация Claude в `main@6d79fca5b36830b444e43d992a8f4e0d3d124367`; единственный изменённый test source `test_web_alarm_runner_guard.py` SHA-256 `836eb0b1b6bbd1c5a0eca7ba58cd12130f8d093eba0a5b4f81e76f08a69926c0`. Guard `wa4a_acceptance.py`, recovery module/tests не менялись.

- [Focused + evidence](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/40118229965), independent Windows `GPT@f76a4d8879e13d98e646c6300eb4425c7a52a9d2`: **manifest 79/79, source hashes 4/4, 46 tests = 45 PASS/1 SKIP, zero FAIL/ERROR/isolation**, entire job success.
- [Full](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/40117844402), independent Windows `GPT@4cbe2a89356f6f8101123e63feecdd5fa2d5e490`: **full job SUCCESS, 989 = 988 PASS/1 SKIP (8.3 short paths unsupported), 0 FAIL/ERROR/isolation**, artifact `12570496922`. Aggregate run `failure` исключительно из-за первого ошибочного LF-hash oracle в параллельном evidence job: `wa4a_acceptance.py` исторически authored CRLF, Git blob LF. Diagnostic CI исправлен коммитом №417, focused/evidence rerun SUCCESS. Исходники Web Alarm одинаковы между коммитами №415 и №417.
- **Причина девяти исторических CI FAIL:** дочерний тест выставлял только `TEMP/TMP=inner` и наследовал родительский `TMPDIR`; `tempfile.gettempdir()` выбирал root внешнего runner TEMP, а не `inner`. Теперь все три переменные задаются явно и проверяется фактический root guard внутри ребёнка; один новый тест CI-like env. Исторический RED и 9 mutant tests сохранены как **evidence Claude**, не независимый mutation replay.
- **Ограничения:** Claude local full `989 = 987 PASS / 2 SKIP` — иное окружение; независимый Windows full `989 = 988 PASS / 1 SKIP`. Не выполнены adversarial TOCTOU, hardware PWR-01, Linux, production storage, rollout и спорные P1/P2/P3. Никакого общего WA4-R DONE/production GO.

**NEXT:** выбранные пользователем отдельные WA4-R gates; предварительная концепция Workspace Test Control Center для Ultra в 37, без implementation GO. Полное заключение в 06.

## 2. Предыдущее заключение: 2026-10-24 / CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001 + AMENDMENT

**Исторический PASS / BOUNDED OFFLINE VERIFIED:** `main@20ebf607cdb891c13e04c71239247fcbaab090ae`, Windows Actions 40093415722 (69/69, isolation=0), 40093575514 (11/11 negatives). No private TEMP/production claims. Полная исходная запись сохранена в 06.

## 3. Более раннее заключение: 2026-10-21 / CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001

**Исторический PARTIAL / REWORK REQUIRED:** независимый Linux 38/38 PASS, обнаружены два fail-open негативных сценария. Последующий repair отдельно проверен; прежний RED не становится PASS задним числом.
