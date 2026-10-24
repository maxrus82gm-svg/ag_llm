# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Codex]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила и статусы внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID, никогда автоматически целиком.


- **`DOC-TEST-LIFECYCLE-01@1` (18) — длительные тесты и честная сдача.** Не выдавать копируемый финальный результат или `RESULT READY` до окончания обязательных тестов. Если управление возвращено до их окончания, начинать сообщение с `# 🔴 ТЕСТЫ НЕ ЗАВЕРШЕНЫ — ЗАДАЧА В РАБОТЕ — ОТЧЁТ ПРЕДВАРИТЕЛЬНЫЙ`; сообщить TASK ID, проверенный статус и как возобновить. Черновой `report.md` помечать `DRAFT`, не обещать автоматического пробуждения без доказанного транспорта. Перед финалом проверить exit code, итоговый файл, изоляцию и evidence, только потом архив/manifest/ротацию; при FAIL/BLOCKED сообщить факты, а не объявлять PASS.
- **`DOC-VERIFIER-BLOCK4-01@1` (18): БЛОК 4 независимого verifier.** БЛОКИ 1–3 прежние; БЛОК 4 — READ-ONLY для исполнителя, его пишет назначенный независимый проверяющий (пока ChatGPT) после фактического review/test. Память — последнее полное заключение + до двух кратких прежних, постоянный архив всех verdict в 06. Новая TASK не обнуляет БЛОК 4. При отсутствии независимого результата — NOT VERIFIED, не PASS.

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- **Перед TASK / `DOC-TASK-READ-SCOPE-01@1`:** собственные Правила, активный БЛОК 1 и относящийся БЛОК 4 (READ-ONLY), затем указанные в TASK актуальные разделы `08_Старт`, `34_TACTICAL_CONTEXT`, `01`/профиль темы, `36/36.1/36.2` (Web Alarm) или `36.3` (Ultra). Координатор даёт матрицу `файл → точный раздел/Rule-ID → зачем → обязательно/условно/полностью`. Весь глобальный `000_Задачи для агента` и весь `18` не читать механически; при пробеле/конфликте прав, security или отчётности требуется конкретное нормативное правило `18` вместе с зависимостями. Обязательные правила остаются в силе, Git-права не появляются. Codex приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Обязательная отчётность внутри проекта (`rule-ref:DOC-LOCAL-REPORT-HANDOFF-01@1`, 18).** По каждой TASK — в том числе PARTIAL, FAIL, BLOCKED и исследовательской — всегда сохранять полный factual `report.md`, manifest и необходимые безопасные evidence по разрешённому относительному пути внутри локального `ag_llm`, обычно `reports/<TASK-ID>/`. Итоговые файлы нельзя оставлять только во внешнем TEMP/кэше или в пути, исключённом `.gitignore`; при исключении сохранить очищенную публикационную копию в допустимой части проекта и отметить недоступный оригинал. Не публиковать секреты и приватные raw-логи. Git-коммиты/публикацию обычно делает пользователь; Codex не использует Git/GitHub и не имеет постоянного права самостоятельно отправлять сообщения в ChatGPT без конкретного USER GO для TASK/AMENDMENT. Допускаются временные изолированные пробы и минимальные технические файлы, но не вместо обязательного итогового отчёта.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- **Новая ротация (USER GO 2026-10-23):** до очистки БЛОКА 1 записать полную TASK, AMENDMENT, factual результат, исходный статус, report/manifest locator в `001_История выполненных задач Codex.md`; проверить чтение и целостность архива. Затем заменить БЛОКИ 2–3 компактным окном пяти последних TASK. Шестая вытесняется только из карточки, никогда из истории. БЛОК 4 — READ-ONLY для исполнителя; БЛОК 1 очищать только после успешного архива. Если запись не удалась — `CARD ROTATION BLOCKED`, ничего не удалять.

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

ОЖИДАНИЕ НОВОЙ ЗАДАЧИ

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Скользящее окно до 5 выполненных TASK; полный архив — [[001_История выполненных задач Codex]]. Независимый статус не выдумывать.

- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — USER GO amendment01: один официальный source ZIP получен, bounded source review выполнен. Статус: PARTIAL; dependency closure BLOCKED; independent NOT VERIFIED.
- **2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — exact local sing-box static snapshot, embedded v1.13.4 claim; no core launch. Статус: RESULT READY; provenance/schema/CONNECT не подтверждены; independent NOT VERIFIED.
- **2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — disabled V2Ray broker contract/preflight и same-process loopback model. Статус: RESULT READY; engine compatibility BLOCKED; independent NOT VERIFIED.
- **2026-10-24 / CODEX-WUA-0-MCP-NOTCP-NPFS-001** — реальный STDIO↔NPFS relay/gateway; current-user auth. Статус: RESULT READY; independent NOT VERIFIED.
- **2026-10-21 / CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001** — local MCP SDK/stdio интеграция; secure tunnel/V2Ray остаются gated. Статус: RESULT READY; independent NOT VERIFIED.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — amendment01 PARTIAL:30/30 (11 source+19 pure), ZIP SHA ecf6cbed… с revision d091826…; native DIRECT/DNS defaults и UoT/hidden paths найдены. HTTP/auth/JSON dependency sing source отсутствует; full strict/WFP/B owner/Chat NOT VERIFIED, tunnel HOLD. Отчёт: `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`; новый append-only amendment locator в amendment_01/evidence/card_rotation.json.
- **CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — 44/44 (25 metadata + 19 pure broker), hash/capability mutants обнаружены; exact sing-box hash совпал с 17.10, embedded v1.13.4/Go1.25.8/d091826… только claims. Engine selection PENDING USER; provenance/schema/CONNECT/B egress/WFP/Chat NOT VERIFIED, tunnel HOLD. Полный отчёт: `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/report.md`; полная TASK/factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).
- **CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — 33/33 broker; регрессия 63/63 MCP и 24/24 security; DIRECT/owner mutants обнаружены. Engine version/source/config BLOCKED; B identity не создана; B egress/V2Ray/WFP/ordinary Chat NOT VERIFIED, tunnel HOLD. Полный отчёт: `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/report.md`; полная TASK и factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).
- **CODEX-WUA-0-MCP-NOTCP-NPFS-001** — 24/24 NPFS, регрессия 63/63 MCP и 24/24 security; TCP/peer mutants обнаружены. Cross-SID/WFP/B V2Ray/ordinary Chat NOT VERIFIED, tunnel HOLD. Полный отчёт: `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/report.md`; полная TASK и factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).
- **CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001** — 63/63 локальных MCP и 24/24 security-тестов по evidence исполнителя; настоящие WFP, V2Ray, две identities, ChatGPT E2E не подтверждены. Полный источник: поиск TASK ID в `001` и task-report проекта.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Verifier:** WEB_11 / ChatGPT. Codex — READ-ONLY. Полная история приёмки в `Документация/06_Журнал выполнения и отчёты.md`.

## 1. Последнее заключение — 2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001 / amendment01

**PARTIAL / INDEPENDENT BOUNDED SOURCE REVIEW ACCEPTED**, source `main@e0c89b3536cb030edc4fa905a8e00f1047788c4c`. WEB_11 независимо проверил **76/76** перечисленных manifest paths, **7/7** выбранных SHA-256; рассмотрел новый checker, 11 тестов, source locators, download/source-tree/rotation receipts и отчёт. Codex-run **30/30 PASS** (11 source + 19 pure regression), независимый Windows/Go run NOT RUN; external ZIP **1,013** source files and its SHA-256 `ecf6cbedda4c35073656c902722b74daaf9fb89bb6f52de9ed0bdfd3a7729c1c` — локальный receipt Codex, **не независимый пересчёт ZIP**. Сам WEB_11 адресно прочитал официальный `SagerNet/sing-box@d09182614c7778c1e0f51d990635c5d4249c437e` `go.mod`, `box.go`, `adapter/outbound/manager.go`, `protocol/http/inbound.go`, `route/route.go`, `common/uot/router.go`, `cmd/sing-box/cmd_run.go` через GitHub connector. Подтверждены exact dependency `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`, потенциальный default DIRECT при отсутствии явного outbound, HTTP delegated parser/auth, UoT logical packet routing и merge/reload path. Это **bounded code findings**, не доказательство реального working profile. Негативные проверки source tripwire — по evidence Codex, Go/engine/native tests NOT RUN.

**OPEN:** внешний source dependency `sagernet/sing` пока не исследован; HTTP CONNECT/auth/JSON closure BLOCKED; native strict route, owner SID, WFP, installed EXE authenticity, hosted tunnel и ordinary ChatGPT E2E NOT VERIFIED. `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`. NEXT: получить ровно version-pinned **source-only** `sagernet/sing` dependency под отдельным разрешением пользователя; затем минимальная source compatibility review и решение о выборе engine. Полное заключение в 06.

## 2. Предыдущее заключение — 2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

**PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED**, `main@bc0a1be97e7a44a0869310e6961e77ff6c841073`. Independently **70/70** manifest paths и **10/10** SHA-256; Codex-run **44/44** (25 new, 19 pure regression), two metadata mutants detected. Actual `sing-box.exe` SHA-256 from local inventory `ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3` matches historical snapshot; embedded v1.13.4 / Go1.25.8 / VCS d091826… agrees with official GitHub tag commit but does **not** attest installed binary. Windows independent tests NOT RUN. Full verdict in 06.

## 3. Позапрошлое заключение — 2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001

**PARTIAL / BOUNDED OFFLINE ACCEPTED**, `main@1324f544c7d3fef6c0a80bf71f7460f372f6950d`. Independently **617/617** paths и **12/12** selected hashes; Codex broker **33/33**, MCP **63/63**, security **24/24**, independently Windows NOT RUN. Synthetic strict broker, no native V2Ray/WFP. Full verdict in 06.

---

**Status:** not PRODUCTION VERIFIED. Old NPFS and Lab Gate verdicts remain archived in 06. B1–B3 untouched, hosted tunnel HOLD.
