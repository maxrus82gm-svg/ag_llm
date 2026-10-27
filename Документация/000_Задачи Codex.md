# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**`rule-ref:DOC-WUA-LAUNCH-01@1` / решение пользователя 2026-10-27 / запуск Ultra:** один постоянный `Start_WebAlarm.bat`. По умолчанию **зелёный STANDARD** на штатный `web_alarm.server` и проверенное постоянное хранилище; при назначенном временном перенаправлении **красный TEST** с TASK ID и фактической целью. Автор TEST-переключения обязан вернуть и проверить STANDARD по завершении; **перед следующей TASK** любой исполнитель/координатор проверяет `Launcher mode`, при TEST возвращает стандартный target до старта, при невозможности — `RESTORE_BLOCKED`, без ложной зелёной метки. Только согласованный scope; никаких вторых пользовательских BAT, несанкционированных чтений/записей реальных Workspace или ослабления прав. Реализация launcher и native Windows/visual пока NOT VERIFIED; полное определение — №18. **Это организационное правило, не новая постановка в БЛОК 1.**


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

**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.** Задача `ASTRA-WUA-37-ROADMAP-REVISION-001` закрыта по независимой документационной приёмке WEB_14. Полная постановка сохранена в `[[001_История выполненных задач Codex]]`, проверена до очистки БЛОКА 1.

**Важно:** №37 остаётся ПРОГРАММОЙ-КАНДИДАТОМ до USER PLAN APPROVAL; V-13/B2 и новые implementation TASK не разрешены. Новую задачу сюда вручную вставляет только пользователь. MCP №39 FROZEN.

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-26 / ASTRA-WUA-37-ROADMAP-REVISION-001** — документ №37, 0–7, H01–H23, R01–R11; independent bounded DOCUMENT PASS, 9/9 artifact hashes; программа ожидает USER PLAN APPROVAL.
- **2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — rev2 Astra after Sol 6.1 rev1; 30/30 published source pins SHA/size independently checked at №436, R2-01…R2-08 source/reasoning review. **WEB_14 PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW**, Windows/live NOT RUN; roadmap awaits user approval.
- **2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — admission policy inside existing broker/security pipeline; Codex 52/52 offline, 51/51 regression (19 overlap), 7/7 mutants, WEB_12 independent 53/53 manifest; **PASS / BOUNDED OFFLINE ACCEPTED**, native/WFP/Chat NOT VERIFIED.
- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — source-only exact sing dependency; Codex 51/51, WEB_12 87/87, six upstream files and 33 locators. **TERMINAL PARTIAL**, native blocked.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — source-only sing-box v1.13.4, defaults DIRECT/DNS/UoT; WEB_11 bounded source accepted, native not run.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **ASTRA-WUA-37-ROADMAP-REVISION-001** — `main@d15d026bf17c1184a004f8891186c0ea02f8887e`, №37 SHA256 `dd2520691cbddbe68157775b42c0373fa3a4009de4b93f008f60ceb180e1df45`, manifest `5cf52fb16438f59f798b633ea0a3f4d8a8456d892b7772e71d0408477b80ed34`, independent 9/9; авторские 21/21 не перезапускались, no runtime/CI/live; B2 V-13 unresolved.
- **ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001** — architecture rev2 `Документация/Дополнительная аналитика Астры.md`, `main@900f107fc89b3ca9e80e4f66b34ab0c9f4b32c30`, 137301 bytes, SHA256 `7cf81d95be92924dd62a6eb1e623882dd2fa69359c9e31032c19a35ee185d3f5`; independently source 30/30 pinned №436 and eight R2 corrections accepted; no runtime/CI/API. WUA-2A **NOT ASSIGNED**; frozen B1 archived verbatim in Codex 001.
- **CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001** — new `strict_preflight`, separated structural vs strict policy statuses; controller-owned canonical/source pins, opaque auth refs, CONNECT-only exact destination and deny DIRECT/fallback/secondary/DNS/UDP/UoT/IPv6/merge/reload. Codex 52/52 offline, 51/51 overlapping compatible tests, 7 mutants caught, preserved RED 19/21, WEB_12 53/53 manifest SHA. **OFFLINE PASS only**, upstream credentials in 407/error logs still SECURITY BLOCKER. Real C/B SID/NPFS, WFP, secret-store and ChatGPT E2E NOT VERIFIED. `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/report.md`.
- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — WEB_12 terminal bounded source-only PARTIAL, 87/87 files and 6/6 upstream SHA/33 locators; no native/real egress. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — WEB_11 bounded 30/30 Codex, sing-box defaults DIRECT/DNS/UoT/other conditional route risks. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

**Verifier:** WEB_14 / ChatGPT; Codex READ-ONLY. Полный архив №001 и журнал №06.

## 1. Последний вердикт — WEB_14 / 2026-10-26 / ASTRA-WUA-37-ROADMAP-REVISION-001

**PASS / INDEPENDENT DOCUMENT & BOUNDED ARCHITECTURAL REVIEW.** Астра / Codex, результат `main@d15d026bf17c1184a004f8891186c0ea02f8887e`: №37 переработан в программу из восьми этапов 0–7, 23 изменения истории H01–H23 и 11 групп рекомендаций R01–R11. **WEB_14 independent PASS / DOCUMENT & BOUNDED ARCHITECTURAL REVIEW.** SHA256 №37 `dd2520691cbddbe68157775b42c0373fa3a4009de4b93f008f60ceb180e1df45` (71042 байта), manifest CRLF `5cf52fb16438f59f798b633ea0a3f4d8a8456d892b7772e71d0408477b80ed34`. Независимо сверены 9/9 артефактов по SHA256/размерам (четыре CRLF восстановлены), исходный №37 с прежней ревизией, кандидат с опубликованным текстом; без блокирующих противоречий в общем Python-ядре, RAW/Turn/RUN/TASK, бюджете, полномочиях Web Alarm и WA4-R. Авторские 21/21 документных проверок независимо не запускались. Windows/UI/runtime/live/paid/CI NOT RUN. №37 остаётся **ПРОГРАММА-КАНДИДАТ / USER PLAN APPROVAL PENDING**, отложенный B2 V-13 Ordinary Chat требует отдельного решения пользователя, исторический RT-002 и MCP freeze №39 не изменены.

**Не является:** USER PLAN APPROVAL, S3a/S3b implementation PASS, EVM Windows/visual PASS, разрешением paid GigaChat, изменением V-13 или запуском первого этапа. Новую TASK пользователь не назначал.

## 2. Предыдущий — WEB_14 / 2026-10-26 / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001

**PASS / BOUNDED ARCHITECTURAL SOURCE REVIEW**, source pins 30/30 at №436 and eight R2 corrections. Нет Windows/production/live.

## 3. Предыдущий — WEB_12 / 2026-10-25 / CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**PASS / BOUNDED OFFLINE SOURCE & EVIDENCE**, native Windows/WFP/ChatGPT Desktop E2E not verified.

---

**Статус:** БЛОК 1 ожидает нового поручения; план №37 требует решения пользователя.
