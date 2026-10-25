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

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА


# 🟨 Строгая политика допуска MCP-брокера — offline реализация и негативные тесты

**TASK ID:** `CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001`

**ARCH CLASS:** Web Alarm Ultra / External AI Integration / STRICT_V2RAY_BROKER / Security Admission

Уважаемый агент 007 (Codex)!

Приглашаем вас выполнить следующую инженерную задачу проекта `ag_llm / Web Alarm Ultra / ChatGPT MCP`.

## 1. Главная цель

Реализовать и проверить строгую **offline admission-policy** для будущего защищённого MCP-брокера.

Политика должна запрещать переход к использованию сетевого движка, если конфигурация не соответствует требованиям безопасности либо её соответствие нельзя проверить.

Это практическая задача по существующим Python-контрактам и тестам, а не новое общее исследование sing-box.

**Основной принцип: неизвестное или недоказанное состояние = BLOCKED, никогда не DIRECT и не автоматическое разрешение.**

## 2. Исходная база

Перед началом убедиться, что пользователь перенёс документационный closeout из ветки `GPT` в `main` и синхронизировал локальную рабочую копию.

Координаторский source reference для документации: `GPT@37ef710cf0ba34f4988cba46a28595d6ce7801a5`.

Git/GitHub исполнителю запрещены без отдельного USER GO. Сверку опубликованной ревизии при необходимости запросить у пользователя или координатора.

**Адресная матрица чтения:**

|Файл|Раздел|Назначение|
|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, БЛОК 1, БЛОК 4|Обязательно|
|`Документация/08_Старт.md`|`DOC-TASK-HANDOFF-USER-01@1`, приоритетные права|Обязательно|
|`Документация/34_TACTICAL_CONTEXT.md`|`WEB_12 / CURRENT`|Обязательно|
|`Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|`STRICT_V2RAY_BROKER`, §7.6–7.7|Обязательно|
|`Документация/36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB, TEST-ENG, TEST-COV, TEST-EXEC, TEST-QA, TEST-EVID, TEST-SCOPE|Обязательно|
|`Документация/36.2_Профиль тестирования Web Alarm Workspace.md`|Применимые offline/Windows test requirements|Адресно|
|`Документация/18_Регламент сопровождения документации.md`|DOC-GIT, DOC-LOCAL-REPORT-HANDOFF, DOC-TASK-CLOSEOUT-OWNER, DOC-TASK-READ-SCOPE|Адресно|

Технические исходные материалы:

- `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/` — принятый WEB_12 bounded source review, особенно `source_callgraph.md`, `strict_route_gap_matrix.md`, `amendment_01/report.md`.
    
- `integrations/wua_chatgpt_mcp/broker.py`
    
- `integrations/wua_chatgpt_mcp/security_contract.py`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.synthetic.example.json`
    
- `integrations/wua_chatgpt_mcp/tests/broker_suite.py`
    
- `integrations/wua_chatgpt_mcp/singbox_source_review.py` — read-only source reference.
    

Не читать автоматически весь архив `001` или большие документы без адресной необходимости.

## 3. Обязательные проверки строгого допуска

### A. Authentication / credentials

Для будущего strict profile:

1. Отсутствующие или пустые `users` должны приводить к отказу в допуске.
    
2. Конфигурация без доказанного обязательного механизма authentication не может считаться готовой.
    
3. Проверить, что собственные diagnostic/error outputs не раскрывают пароли, `Proxy-Authorization` и credential material.
    
4. Опубликованные сведения об upstream-утечке ошибок должны оставаться отдельным **SECURITY BLOCKER**, пока безопасность соответствующей runtime-границы не доказана.
    

Не изменять исходники стороннего `sing` и не заявлять, что локальная фильтрация Python устранила все ошибки upstream.

### B. Маршрут и отказ от DIRECT

Строгий admission должен отвергать:

- DIRECT и любую неутверждённую fallback-схему;
    
- второй прокси, load balancing или неизвестный outbound;
    
- неутверждённые DNS, UDP, IPv6, UoT и фоновые соединения;
    
- неоднозначный endpoint, host/port или конфигурацию;
    
- неподтверждённый сетевой движок и ownership;
    
- незадекларированные изменения политики после preflight.
    

Синтетический договор с корректной структурой **не равен** разрешению на сетевой запуск.

### C. HTTP CONNECT

Разделить три события:

1. HTTP CONNECT принят обработчиком.
    
2. Маршрут разрешён строгой политикой.
    
3. Реальный исходящий socket принадлежит разрешённому брокеру и идёт к разрешённому upstream.
    

Эти события нельзя считать одним доказательством.

Для целевой CONNECT-only политики неопознанные методы, Upgrade, произвольный HTTP и назначения вне разрешённого контракта должны приводить к отказу либо к явно сохранённому BLOCKED до появления проверяемого oracle.

Не писать собственный HTTP-парсер вместо Go standard library.

### D. JSON / configuration admission

Определить и проверить строгие правила:

- один канонический защищённый источник конфигурации;
    
- запрет duplicate keys и неутверждённых unknown fields;
    
- отказ от неполного, неоднозначного или конфликтующего ввода;
    
- запрет неутверждённых merge/reload/environment overrides;
    
- явный DENY вместо небезопасных значений по умолчанию.
    

Использовать существующий parser/validator pipeline. Не создавать параллельную систему конфигурации.

## 4. Реализация

Предпочтительное решение — небольшое расширение существующих `broker.py` / `security_contract.py` и существующих тестов.

Если разделение **структурно корректен** и **допущен к будущей эксплуатации** требует двух статусов, реализовать их явно.

Не разрушать историческую валидность синтетического fixture: он может оставаться `BROKER_PROFILE_STRUCTURALLY_VALID`, одновременно имея `STRICT_ADMISSION_BLOCKED`.

Любой результат по-прежнему обязан содержать:

`can_apply=false`

`can_start_tunnel=false`

`install_uninstall=BLOCKED`

Реальный запуск запрещён независимо от успешности offline-проверок.

## 5. Разрешённый write scope

Минимально необходимые изменения:

- `integrations/wua_chatgpt_mcp/broker.py`
    
- `integrations/wua_chatgpt_mcp/security_contract.py`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json`, только если действительно требуется совместимое уточнение
    
- `integrations/wua_chatgpt_mcp/tests/broker_suite.py`
    
- адресная новая тестовая часть внутри существующего `integrations/wua_chatgpt_mcp/tests/`, только если переиспользование старого suite неудобно и обосновано
    
- `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/**` для отчёта, manifest и безопасных evidence.
    

Никаких других изменений без отдельного пользовательского разрешения.

**Запрещено:** Git/GitHub, live Windows, WFP, firewall, Windows accounts, proxy/v2rayN, DNS, работающий sing-box/V2Ray, движок, Go install/build, tunnel, реальное сетевое испытание, production Web Alarm и изменение карточек/001/общей документации.

Новых сетевых скачиваний не выполнять.

## 6. Тестирование

Нужны реальные offline проверки Python, а не только source anchors.

Сначала сохранить исходные тесты и результаты, затем показать негативные RED/REJECT сценарии и итоговые PASS. Минимальная матрица:

1. Нет users / пустой users.
    
2. Неверный или отсутствующий credential reference.
    
3. Секрет в ошибке или диагностике.
    
4. CONNECT без подтверждения downstream.
    
5. Plain HTTP / Upgrade при CONNECT-only.
    
6. Неверный destination, порт и незадекларированный IPv6.
    
7. DIRECT, fallback, secondary proxy.
    
8. DNS/UDP/UoT/background egress.
    
9. Duplicate JSON keys, unknown field, null/default ambiguity.
    
10. Merge/reload/environment override.
    
11. Повторная подмена конфигурации после проверки.
    
12. Попытка изменить `can_apply` или `can_start_tunnel` входными данными.
    

Для каждой проверки указывать правильный отказ и его конкретный код. Нельзя считать любое произвольное исключение успешным негативным тестом.

Добавить адресные mutant/negative controls, при которых ослабление обязательной проверки обнаруживается тестами. Сохранить первый FAIL и все исправления оракулов.

Не подменять недостающие native security доказательства Python-симуляцией.

## 7. Критерии результата

**PASS в пределах offline admission**, если:

- реализована одна переиспользуемая строгая admission-policy;
    
- небезопасные и недоказанные входы отвергаются;
    
- тесты фиксируют фактические отказы, а не только наличие исходного кода;
    
- опубликованы source/test hashes, результаты, негативные сценарии и независимые ограничения;
    
- старые применимые проверки не сломаны;
    
- все activation gates остались закрыты.
    

**PARTIAL**, если часть admission требований можно определить, но доказать их нельзя без Go/native/OS среды.

**BLOCKED**, если дальнейшее движение потребует недоступного исходника, запрещённого сетевого действия или нового USER GO.

Техническая сдача:

- `report.md` — полный factual результат и MANUAL ENGINEERING REVIEW;
    
- `manifest.json` — exact paths, bytes, SHA-256;
    
- `admission_matrix.md` — критерии допуска, отказа и остаточные blockers;
    
- `checks.json` и sanitized `runs/` — команды, counts, exit codes, исходный FAIL и финальные результаты;
    
- `DOC_IMPACT.md` — предложения для №19/34/06, без самостоятельного редактирования.
    

**После выполнения:** пользователь публикует отчёт и код на GitHub. WEB_12 независимо проверяет результат. Исполнитель не очищает БЛОК 1, не ротирует БЛОКИ 2–4/001 и не объявляет самостоятельно `VERIFIED`.

**Главная цель:** получить практический, тестируемый механизм, который не позволит по ошибке принять небезопасную сетевую конфигурацию за разрешённую, сохранив все настоящие OS/WFP/MCP-gates для следующих задач.

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Скользящее окно последних пяти TASK. Полный архив — [[001_История выполненных задач Codex]].

- **2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — exact sing module dependency source; Codex 51/51 offline, WEB_12 87/87 manifest and 6/6 official source; **TERMINAL PARTIAL / independent bounded review accepted**, native/Chat NOT VERIFIED.
- **2026-10-24 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — upstream sing-box v1.13.4 source/default DIRECT/DNS/UoT; WEB_11 bounded source acceptance, no native.
- **2026-10-24 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — local embedded sing-box static snapshot; WEB_11 bounded acceptance, binary provenance/native pending.
- **2026-10-24 / CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — synthetic disabled broker/negative preflight; WEB_11 bounded offline acceptance, engine/native BLOCKED.
- **2026-10-24 / CODEX-WUA-0-MCP-NOTCP-NPFS-001** — STDIO/NPFS synthetic relay/gateway; independent bounded source result, cross-SID/WFP/real Chat NOT VERIFIED.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001** — 1 GO/ZIP (310819 bytes raw SHA `dfb3b8c7…`), h1 reconstructed from published 322 SHA, Codex 30/30→49/50 FAIL preserved→50/50→51/51, WEB_12 independent 87/87 manifest, 6/6 upstream files and 33/33 locators. **TERMINAL PARTIAL**. Empty users auth disabled, credential logging, CONNECT 200-before-route, JSON/defaults/conditional egress; real C/B WFP/Chat NOT VERIFIED. `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/report.md`.
- **CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001** — Codex 30/30; WEB_11 bounded; default DIRECT, DNS, UoT, conditional egress. `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/report.md`.
- **CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001** — Codex 44/44, WEB_11 bounded static, no installed EXE attestation. `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/report.md`.
- **CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001** — Codex 33/33 broker, 63/63 MCP, 24/24 security pure checks; native/WFP BLOCKED. `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/report.md`.
- **CODEX-WUA-0-MCP-NOTCP-NPFS-001** — Codex 24/24 NPFS, 63/63 MCP, 24/24 security; cross-SID/WFP/Chat NOT VERIFIED. `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/report.md`.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА / VERIFIER
---

**Verifier:** WEB_12 / ChatGPT, Codex READ-ONLY. All historical verdicts in №06.

## 1. Последний вердикт — 2026-10-25 / CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001 / amendment01

**TERMINAL PARTIAL / INDEPENDENT BOUNDED SOURCE & EVIDENCE ACCEPTED**, `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; user explicitly approved terminal PARTIAL closeout, not full security approval.

Codex 007: exact source-only `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`; one GET via explicitly approved HTTP CONNECT according to agent audit, 0 redirects/fallback, 322 module files, ZIP raw SHA-256 `dfb3b8c7cbc603602c6cf453161d319209e5610477e1118354dd449bd9409659`, Go module h1 `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`. Baseline 30/30, first RED 49/50 (Windows ZIP name normalization; preserved), intermediate 50/50, final **51/51 PASS** (11 source +19 pure +21 dependency), per Codex logs; not independently rerun on Windows.

WEB_12: `main@257084ae6e8b7e81d82f1987a80ac2bc5e67fb34`; **87/87** published manifest paths bytes+SHA independently matched (LF/CRLF-aware); **6/6** independently fetched official `SagerNet/sing@ed51f65fbfde` source files and **33/33** locators match; Go module h1 recomputed from **published SHA values of 322 members**, not independently from original ZIP. Stored FAIL/final result and tests inspected. Physical egress/installed executable/ZIP itself, native Go/Windows/WFP, C/B SIDs/sockets, no-DIRECT proof and ordinary ChatGPT MCP E2E **NOT VERIFIED**.

Source risks: `users=[]` disables proxy authentication; 407/error logs can expose username/password or `Proxy-Authorization`; CONNECT sends `200` before dial/route; HTTP Upgrade/plain alternatives and X-Forwarded-For source override; URL-safe-vs-standard Basic Base64 ambiguity and ignored port-parse error; permissive JSON duplicates/null/case/merge/reload; prior default DIRECT, local DNS/UoT/optional other egress; Go stdlib/x/sys source/native behavior incomplete. No proven native bypass asserted. `engine.family=V2Ray` unchanged, `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`; no install/engine switch/proxy/system activation.

Full report `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/amendment_01/report.md`, manifest `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/manifest.json`; pinned complete task in personal 001. No permission to enable/alter engine, Windows, proxy, WFP, local identities, hosted tunnel, ordinary ChatGPT connection or network route.

## 2. Предыдущий — WEB_11 / CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001

**PARTIAL / INDEPENDENT BOUNDED SOURCE REVIEW ACCEPTED**, `main@e0c89b3536cb030edc4fa905a8e00f1047788c4c`, 76/76 paths, 7/7 selected hashes, Codex 30/30 offline, native NOT RUN. Missing sing module source was historical state later narrowed by WEB_12.

## 3. Позапрошлый — WEB_11 / CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

**PARTIAL / BOUNDED STATIC-SNAPSHOT ACCEPTED**, `main@bc0a1be97e7a44a0869310e6961e77ff6c841073`, 70/70 paths, 10/10 hashes, Codex 44/44, native NOT RUN.

---

**Status:** source-only partial, not production. Full earlier NPFS/broker independent verdicts remain permanently archived №06; B1 waiting only after user-approved terminal closeout.
