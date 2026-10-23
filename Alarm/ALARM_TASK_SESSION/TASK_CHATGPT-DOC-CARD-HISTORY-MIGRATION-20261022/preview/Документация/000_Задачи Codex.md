# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. История: [[001_История выполненных задач Codex]]. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**DOC-AGENT-CARD-HISTORY-01@1:** БЛОК 1 — целая актуальная постановка; БЛОК 2 — не более пяти кратких последних TASK; БЛОК 3 — краткий factual результат последней; БЛОК 4 — только независимая приёмка. Полная история — [[001_История выполненных задач Codex]]. Оригиналы TASK и отчётов — отдельно. Исполнитель не объявляет себе DONE/VERIFIED.


- **`DOC-VERIFIER-BLOCK4-01@2` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- **Перед TASK / `DOC-TASK-READ-SCOPE-01@1`:** собственные Правила, активный БЛОК 1 и относящийся БЛОК 4 (READ-ONLY), затем указанные в TASK актуальные разделы `08_Старт`, `34_TACTICAL_CONTEXT`, `01`/профиль темы, `36/36.1/36.2` (Web Alarm) или `36.3` (Ultra). Координатор даёт матрицу `файл → точный раздел/Rule-ID → зачем → обязательно/условно/полностью`. Весь глобальный `000_Задачи для агента` и весь `18` не читать механически; при пробеле/конфликте прав, security или отчётности требуется конкретное нормативное правило `18` вместе с зависимостями. Обязательные правила остаются в силе, Git-права не появляются. Codex приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Обязательная отчётность внутри проекта (`rule-ref:DOC-LOCAL-REPORT-HANDOFF-01@1`, 18).** По каждой TASK — в том числе PARTIAL, FAIL, BLOCKED и исследовательской — всегда сохранять полный factual `report.md`, manifest и необходимые безопасные evidence по разрешённому относительному пути внутри локального `ag_llm`, обычно `reports/<TASK-ID>/`. Итоговые файлы нельзя оставлять только во внешнем TEMP/кэше или в пути, исключённом `.gitignore`; при исключении сохранить очищенную публикационную копию в допустимой части проекта и отметить недоступный оригинал. Не публиковать секреты и приватные raw-логи. Git-коммиты/публикацию обычно делает пользователь; Codex не использует Git/GitHub и не имеет постоянного права самостоятельно отправлять сообщения в ChatGPT без конкретного USER GO для TASK/AMENDMENT. Допускаются временные изолированные пробы и минимальные технические файлы, но не вместо обязательного итогового отчёта.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- После TASK Codex сохраняет полный БЛОК 1/AMENDMENT и factual report внутри ag_llm, БЛОК 2 пополняет краткой строкой (до пяти TASK), БЛОК 3 — краткий factual результат; только после проверки архивов освобождает БЛОК 1. БЛОК 4 READ-ONLY. 001 и 06 ведёт independent verifier; при сбое ротации CARD ROTATION BLOCKED.

---

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

ОЖИДАНИЕ НОВОЙ ЗАДАЧИ

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КРАТКО)

Подробно — [[001_История выполненных задач Codex]]; оригинал всех прежних блоков — `reports/AGENT-CARD-HISTORY-MIGRATION-20261022/full_000_Задачи Codex.md`.

## CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001 — см. историю
- **Факт из отчёта:** Реализован standalone `integrations/wua_chatgpt_mcp/`: настоящий MCP SDK2 stdio server/client, 4 read tools ping/list_capabilities/read_synthetic_context/get_status, separate authenticated server-owned WebAlarmApi fixture с new owned state, strict JSON/auth/task/replay/hash/nonce/size/time/cleanup; pinned strict profile, diagnostic CLI, disabled versioned…
- **Статус источника:** **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.** Исполнение завершено в разрешённом local/synthetic scope; independent acceptance pending, production BLOCKED.
- **Источник:** `reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001`

## CODEX-WUA-0-WINDOWS-LAB-GATE-001 — см. историю
- **Факт из отчёта:** Созданы executable I01–I12 offline evidence gate, раздельные signed host/guest/review synthetic fixtures с внешним approved-request trust pin, strict JSON/disk/assets/owner/freshness checks, bounded host collector, частичный exact-GUID read-only Hyper-V candidate и 13-step data-only dry-run. Всегда native_execution_allowed=false / vm_changes_allowed=false / can_apply=false.…
- **Статус источника:** **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11.** Исполнение TASK завершено в разрешённом offline scope; независимая приёмка pending.
- **Источник:** `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001`

## CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001 — см. историю
- **Статус источника:** RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_10).
- **Источник:** `reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001`

## CODEX-WUA-0-WFP-OFFLINE-BACKEND-001 — 2026-10-20
- **Статус источника:** RESULT READY / AWAITING INDEPENDENT VERIFICATION (WEB_11).
- **Источник:** `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001`

## CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001 — см. историю
- **Статус источника:** сверить с отчётом / 06

---

# БЛОК 3 — КРАТКИЙ FACTUAL RESULT / HANDOFF

**TASK:** CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001

**Результат:** Реализован standalone `integrations/wua_chatgpt_mcp/`: настоящий MCP SDK2 stdio server/client, 4 read tools ping/list_capabilities/read_synthetic_context/get_status, separate authenticated server-owned WebAlarmApi fixture с new owned state, strict JSON/auth/task/replay/hash/nonce/size/time/cleanup; pinned strict profile, diagnostic CLI, disabled versioned…

**Статус исходника:** **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.** Исполнение завершено в разрешённом local/synthetic scope; independent acceptance pending, production BLOCKED.

**Отчёт:** `reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001`

**Полный архив:** `reports/AGENT-CARD-HISTORY-MIGRATION-20261022/full_000_Задачи Codex.md`. Независимый verdict — БЛОК 4 и 06.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Автор:** независимый ChatGPT, Codex — READ-ONLY. Архив: `Документация/06_Журнал выполнения и отчёты.md`.

## 1. Последнее заключение: 2026-10-21 / CODEX-WUA-0-WINDOWS-LAB-GATE-001

**Вердикт: PARTIAL / INDEPENDENT BOUNDED OFFLINE ACCEPTED**. WEB_11 подтвердил пакет **215/215** путей и **13/13** выборочных SHA-256. Сохранённые **52/52 PASS** — Codex-run evidence, **не независимый запуск Windows suite**; baseline red 50/51, 2 мутанта. Реальный lab I01–I12: **12/12 BLOCKED**; trusted VM/media/изоляция, WFP/V2Ray/native/Chat E2E **NOT VERIFIED**. `CanApply=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`; future provisioning требует отдельного USER GO. Путь: `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/`, WEB_11 в 34, постоянный архив 06.

## 2. Предыдущее заключение: 2026-10-20 / CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001

WEB_10 bounded independent source/evidence: **87** путей по manifest + manifest, **10/10** выборочных SHA-256; real Windows/native install не проверены, installer BLOCKED. История: 06, WEB_10.

## 3. Позапрошлое заключение

Оставлено пустым: без достоверной дополнительной независимой проверки/постоянной записи не заполнять.

---
