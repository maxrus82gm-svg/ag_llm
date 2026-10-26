# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**Приоритет USER GO 2026-10-24:** в этой персональной карточке БЛОК 1 и БЛОКИ 2–4, а также личный архив `001` обновляет ChatGPT-координатор **только после** пользовательской публикации и верификации/решения terminal BLOCKED. Локальному исполнителю запрещено изменять любые БЛОКИ карточки, `001` или самостоятельно запускать ротацию. Отчёт/manifest/evidence в разрешённой папке сохранять обязательно; до приёмки БЛОК 1 остаётся за текущей TASK. Источник: `DOC-TASK-CLOSEOUT-OWNER-01@1` (18); старые правила самоличной ротации более не действуют.

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Codex]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила и статусы внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID, никогда автоматически целиком.


- **`DOC-TEST-LIFECYCLE-01@1` (18) — длительные тесты и честная сдача.** Не выдавать копируемый финальный результат или `RESULT READY` до окончания обязательных тестов. Если управление возвращено до их окончания, начинать сообщение с `# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ`; сообщить TASK ID, проверенный статус и как возобновить. Черновой `report.md` помечать `DRAFT`, не обещать автоматического пробуждения без доказанного транспорта. Перед технической сдачей проверить exit code, итоговый файл, изоляцию, manifest и evidence; архив/ротацию выполняет только координатор после приёмки; при FAIL/BLOCKED сообщить факты, а не объявлять PASS.
- **`DOC-VERIFIER-BLOCK4-01@1` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- **Перед TASK / `DOC-TASK-READ-SCOPE-01@1`:** собственные Правила, активный БЛОК 1 и относящийся БЛОК 4 (READ-ONLY), затем указанные в TASK актуальные разделы `08_Старт`, `34_TACTICAL_CONTEXT`, `01`/профиль темы, `36/36.1/36.2` (Web Alarm) или `36.3` (Ultra). Координатор даёт матрицу `файл → точный раздел/Rule-ID → зачем → обязательно/условно/полностью`. Весь глобальный `000_Задачи для агента` и весь `18` не читать механически; при пробеле/конфликте прав, security или отчётности требуется конкретное нормативное правило `18` вместе с зависимостями. Обязательные правила остаются в силе, Git-права не появляются. Codex приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Обязательная отчётность внутри проекта (`rule-ref:DOC-LOCAL-REPORT-HANDOFF-01@1`, 18).** По каждой TASK — в том числе PARTIAL, FAIL, BLOCKED и исследовательской — всегда сохранять полный factual `report.md`, manifest и необходимые безопасные evidence по разрешённому относительному пути внутри локального `ag_llm`, обычно `reports/<TASK-ID>/`. Итоговые файлы нельзя оставлять только во внешнем TEMP/кэше или в пути, исключённом `.gitignore`; при исключении сохранить очищенную публикационную копию в допустимой части проекта и отметить недоступный оригинал. Не публиковать секреты и приватные raw-логи. Git-коммиты/публикацию обычно делает пользователь; Codex не использует Git/GitHub и не имеет постоянного права самостоятельно отправлять сообщения в ChatGPT без конкретного USER GO для TASK/AMENDMENT. Допускаются временные изолированные пробы и минимальные технические файлы, но не вместо обязательного итогового отчёта.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- **Ротация и архив (USER GO 2026-10-24):** Codex сохраняет только техническую сдачу (`report.md`, manifest, evidence, точные проверки). Запись в персональный `001`, окно из пяти кратких TASK/итогов в БЛОКАХ 2–3, независимый БЛОК 4 и закрытие БЛОКА 1 выполняет ChatGPT-координатор после независимого review. Старый порядок самостоятельной ротации отменён; при ошибке архивирования — `CARD CLOSEOUT BLOCKED`, без очистки.

---

> **USER FREEZE / 2026-10-25 — HISTORICAL, MCP STILL PAUSED.** Старый статус CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001 (independent acceptance OPEN / USER HOLD) хранится в №39, №06 и личном архиве. Он не становится VERIFIED из-за принятия независимой Astra rev2. Ветка Desktop MCP/Tunnel/V2Ray/WFP остаётся FROZEN. Текущий независимый bounded PASS касается только ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001; новой implementation TASK не назначено.

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

**Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ / NO EXECUTOR TASK ASSIGNED.** `ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001` закрыта по независимому `PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW` WEB_14 26.10.2026. Полный исходный БЛОК 1 без сокращений, история двух редакций, source/review SHA и вердикт сохранены в персональном `001_История выполненных задач Codex.md` и №06. Сама аналитика — `PROPOSAL / AWAITING USER APPROVAL`.

Новое БЛОК 1 готовит ChatGPT **только текстом в чате**, вручную назначает пользователь **после GPT → main merge и локальной синхронизации**. Никакой автоматической WUA-2A, Claude, live GigaChat или разморозки Desktop MCP. Учитывать параллельный LLM15/WA4-R.

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — rev2 Astra after Sol 6.1 rev1; 30/30 published source pins SHA/size independently checked at №436, R2-01…R2-08 source/reasoning review. **WEB_14 PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW**, Windows/live NOT RUN; roadmap awaits user approval.
- **2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — admission policy inside existing broker/security pipeline; Codex 52/52 offline, 51/51 regression (19 overlap), 7/7 mutants, WEB_12 independent 53/53 manifest; **PASS / BOUNDED OFFLINE ACCEPTED**, native/WFP/Chat NOT VERIFIED.
- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — source-only exact sing dependency; Codex 51/51, WEB_12 87/87, six upstream files and 33 locators. **TERMINAL PARTIAL**, native blocked.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — source-only sing-box v1.13.4, defaults DIRECT/DNS/UoT; WEB_11 bounded source accepted, native not run.
- **2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — embedded sing-box local snapshot, WEB_11 bounded, installed executable not attested.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — architecture rev2 `Документация/Дополнительная аналитика Астры.md`, `main@900f107fc89b3ca9e80e4f66b34ab0c9f4b32c30`, 137301 bytes, SHA256 `7cf81d95be92924dd62a6eb1e623882dd2fa69359c9e31032c19a35ee185d3f5`; independently source 30/30 pinned №436 and eight R2 corrections accepted; no runtime/CI/API. WUA-2A **NOT ASSIGNED**; frozen B1 archived verbatim in Codex 001.
- **CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — new `strict_preflight`, separated structural vs strict policy statuses; controller-owned canonical/source pins, opaque auth refs, CONNECT-only exact destination and deny DIRECT/fallback/secondary/DNS/UDP/UoT/IPv6/merge/reload. Codex 52/52 offline, 51/51 overlapping compatible tests, 7 mutants caught, preserved RED 19/21, WEB_12 53/53 manifest SHA. **OFFLINE PASS only**, upstream credentials in 407/error logs still SECURITY BLOCKER. Real C/B SID/NPFS, WFP, secret-store and ChatGPT E2E NOT VERIFIED. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md`.
- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — WEB_12 terminal bounded source-only PARTIAL, 87/87 files and 6/6 upstream SHA/33 locators; no native/real egress. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — WEB_11 bounded 30/30 Codex, sing-box defaults DIRECT/DNS/UoT/other conditional route risks. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.
- **CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — WEB_11 bounded snapshot, Codex 44/44, actual engine attestation/native not run. `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Verifier:** WEB_14 / ChatGPT. Codex — READ-ONLY. Полная история №06 и Codex 001.

## 1. Последний вердикт — WEB_14 / 2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001 (rev2)

**PASS / INDEPENDENT BOUNDED ARCHITECTURAL SOURCE REVIEW.** `main@900f107fc89b3ca9e80e4f66b34ab0c9f4b32c30` (№438) and all **30/30** source manifest SHA-256/size checked independently on `main@7924d7653e896e3fe110e7d67162730a9b7e857d` (№436), with CRLF reconstruction for server.py, ultra_ui.py, task_planner.py, web_alarm/ui.py. Report 137301 bytes / SHA256 `7cf81d95be92924dd62a6eb1e623882dd2fa69359c9e31032c19a35ee185d3f5` previously independently sealed by WEB_13. Reviewed R2-01…R2-08 by concrete source: identity/bounded reads, chat usage and nullable technical tb, fixed message IDs/recovery, legacy terminal failure assistant RAW, missing ordinary Chat B2 route, bounded owner/locks, shared request transport, physical attempt vs Turn cancellation/UNKNOWN usage. No blocking analytical contradictions. Added future negative-test recommendation: RAW filename/message_id equality and duplicate message IDs.

**Independently checked:** source/content/reasoned architecture. **NOT RUN:** Windows CI and visuals, real reparse/concurrency/TOCTOU/restart, real provider/OAuth/live/paid API. EVM independent Windows/visual, WA4-R, B2 S1/S2 Chat route and S3a/S3b, security/history read gate, Turn implementation and actual roadmap approval **OPEN**. Analysis accepted, proposal NOT APPROVED, implementation NOT STARTED. No next task assigned.

## 2. Предыдущий — WEB_12 / 2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**PASS / BOUNDED OFFLINE SOURCE & EVIDENCE**, `main@6456d669a8a804ddd75a0dbca242782c18d914da`, 53/53 manifest, agent-reported 52/52 tests + 51/51 regression (19 overlap), 7/7 mutants; Windows/WFP/no-DIRECT/ChatGPT MCP E2E NOT VERIFIED, upstream error/credential leak SECURITY BLOCKER. Detailed history №06.

## 3. Предыдущий — WEB_12 / 2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001

**TERMINAL PARTIAL / BOUNDED SOURCE**, `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`, 87/87 manifest, 6/6 upstream selected files, 33/33 locators; no native/network/WFP, Desktop MCP/tunnel FROZEN. Detailed history №06.

---

**Статус карточки:** задача Astra закрыта в пределах source-only аналитики, БЛОК 1 ожидает назначения пользователем. Frozen Desktop MCP/old independent open checks не закрывались, implementation GO не выдавался.
