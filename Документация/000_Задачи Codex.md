# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**USER GO 2026-10-23 (приоритетная адресная политика этой карточки):** [[001_История выполненных задач Codex]] — полный архив; БЛОКИ 2–3 — лишь пять последних кратких задач и итогов, постоянно обновляемых. БЛОК 4 — отдельная независимая проверка. Старые вложенные правила и статусы внутри исторического архива не являются новой инструкцией; архив читать только адресно по TASK ID, никогда автоматически целиком.


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

- **2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — disabled V2Ray broker contract/preflight и same-process loopback model. Статус: RESULT READY; engine compatibility BLOCKED; independent NOT VERIFIED.
- **2026-10-24 / CODEX-WUA-0-MCP-NOTCP-NPFS-001** — реальный STDIO↔NPFS relay/gateway; current-user auth. Статус: RESULT READY; independent NOT VERIFIED.
- **2026-10-21 / CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001** — local MCP SDK/stdio интеграция; secure tunnel/V2Ray остаются gated. Статус: RESULT READY; independent NOT VERIFIED.
- **2026-10-21 / CODEX-WUA-0-WINDOWS-LAB-GATE-001** — offline lab gate I01–I12. Статус: PARTIAL; BOUNDED OFFLINE ACCEPTED.
- **2026-10-20 / CODEX-WUA-0-WFP-OFFLINE-BACKEND-001** — кандидат WFP security backend. Статус: RESULT READY; NATIVE NOT VERIFIED.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — 33/33 broker; регрессия 63/63 MCP и 24/24 security; DIRECT/owner mutants обнаружены. Engine version/source/config BLOCKED; B identity не создана; B egress/V2Ray/WFP/ordinary Chat NOT VERIFIED, tunnel HOLD. Полный отчёт: `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/report.md`; полная TASK и factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).
- **CODEX-WUA-0-MCP-NOTCP-NPFS-001** — 24/24 NPFS, регрессия 63/63 MCP и 24/24 security; TCP/peer mutants обнаружены. Cross-SID/WFP/B V2Ray/ordinary Chat NOT VERIFIED, tunnel HOLD. Полный отчёт: `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/report.md`; полная TASK и factual result — новая append-only запись 001 (locator в evidence/card_rotation.json).
- **CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001** — 63/63 локальных MCP и 24/24 security-тестов по evidence исполнителя; настоящие WFP, V2Ray, две identities, ChatGPT E2E не подтверждены. Полный источник: поиск TASK ID в `001` и task-report проекта.
- **CODEX-WUA-0-WINDOWS-LAB-GATE-001** — 52/52 offline suite у исполнителя; независимая ограниченная проверка пакета; 12/12 реальных lab gates BLOCKED. Полный источник: поиск TASK ID в `001` и task-report проекта.
- **CODEX-WUA-0-WFP-OFFLINE-BACKEND-001** — 62/62 managed tests у исполнителя, native WFP calls 0; Apply BLOCKED. Полный источник: поиск TASK ID в `001` и task-report проекта.

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

**Уточнение:** последнее независимое заключение выше относится к Windows lab gate; более новая MCP-интеграция независимого PASS не получила.
