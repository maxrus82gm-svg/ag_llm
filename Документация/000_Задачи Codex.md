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

# 🟨 Исходники sing — завершение проверки HTTP CONNECT/auth/JSON

**TASK ID:** `CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001`

Уважаемый агент 007 (Codex)!

Приглашаем вас выполнить следующую ограниченную инженерно-исследовательскую задачу проекта `ag_llm / Web Alarm Ultra / ChatGPT MCP`.

## 1. Цель

Получить и исследовать исходный код зависимости `github.com/sagernet/sing`, используемой sing-box v1.13.4, чтобы завершить ранее заблокированную проверку HTTP CONNECT, proxy authentication и JSON/config handling.

**Точная зависимость:**

- Module: `github.com/sagernet/sing`
    
- Version: `v0.8.3-0.20260315153529-ed51f65fbfde`
    
- Ожидаемый Go module ZIP checksum из `go.sum`: `h1:RNQzlpnsXIuu1HGts/fIzJ1PR7RhrzaNlU52MDyiX1c=`
    
- sing-box: `v1.13.4`, upstream revision `d09182614c7778c1e0f51d990635c5d4249c437e`
    

Продолжить доказательную базу `CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/amendment01`, не повторяя её приёмку и не объявляя ранее установленные факты неподтверждёнными без новых противоречащих данных.

**Исходное состояние:** независимый WEB_11 verdict — `PARTIAL / BOUNDED SOURCE REVIEW ACCEPTED`, 76/76 paths, 7/7 selected hashes, Codex 30/30 tests; independent Windows/Go NOT RUN. Предыдущая задача уже архивирована.

## 2. Границы разрешения

Сначала проверить факт отдельного USER GO на **один точно указанный source-only download**. Формулировка данной задачи без этого разрешения не даёт права на сетевую загрузку.

Если GO отсутствует, не скачивать архив и не заменять его другим пакетом. Разрешается подготовить read-only план и завершить зависимую операцию статусом `BLOCKED / DOWNLOAD_GO_REQUIRED`.

После отдельного GO разрешается:

1. Получить один официальный version-pinned Go module source ZIP, предпочтительно через `https://proxy.golang.org/github.com/sagernet/sing/@v/v0.8.3-0.20260315153529-ed51f65fbfde.zip`.
    
2. Использовать только уже существующий разрешённый пользовательский HTTP CONNECT proxy path. Предыдущий проверенный для загрузки endpoint — literal `127.0.0.1:10808`; перед использованием проверить его актуальность без изменения настроек.
    
3. Строго запретить DIRECT fallback, обход через системные proxy settings, неутверждённые промежуточные прокси и автоматическое повторение через другой маршрут.
    
4. Сохранить ZIP и проверяемую распаковку в новом изолированном source-only каталоге вне `ag_llm`, не перезаписывая предыдущий sing-box archive.
    
5. Выполнить только статические исследования и изолированные pure/source тесты.
    

Если происхождение, маршрут или целостность источника нельзя подтвердить — STOP/BLOCKED, без попытки обойти ограничение.

## 3. Абсолютные запреты

- Не изменять рабочую Windows, системные или пользовательские proxy settings, v2rayN, sing-box, VPN, routing, firewall и WFP.
    
- Не создавать, удалять и не перенастраивать `wua-client` (C) и `wua-broker` (B).
    
- Не запускать, не устанавливать, не собирать и не обновлять сетевые движки, Go dependencies или native services.
    
- Не выполнять Go-команды, которые могут неявно скачать/установить модули, запустить сборку либо сетевой runtime.
    
- Не создавать listener, не посылать тестовые CONNECT-запросы во внешнюю сеть и не выполнять DNS probes.
    
- Не менять `engine.family=V2Ray`, `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`.
    
- Не активировать Secure MCP Tunnel, MCP external endpoint, hosted services, production route или обычный ChatGPT E2E.
    
- Не использовать Git/GitHub даже read-only из локального Codex без отдельного пользовательского GO. Не запускать commit/push.
    
- Не редактировать персональную карточку Codex (БЛОКИ 1–4), личный архив `001` и общую документацию.
    

## 4. Адресная матрица чтения

|Источник|Раздел|Причина / уровень|
|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, БЛОК 1, БЛОК 4|Обязательно; БЛОК 4 read-only|
|`Документация/08_Старт.md`|Актуальный старт, границы ролей и тестов|Адресно, обязательно|
|`Документация/34_TACTICAL_CONTEXT.md`|`WEB_11 → NEXT MCP CHAT`, `WEB_11 sing-box source review`|Полностью соответствующие разделы|
|`Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|§7.1, §7.2, §7.4, §7.6|Обязательно|
|`Документация/01_Архитектура и текущее состояние.md`|External integrations и ограничения проекта|Адресно|
|`Документация/18_Регламент сопровождения документации.md`|`DOC-GIT-01@1`, `DOC-PARALLEL-01@1`, `DOC-LOCAL-REPORT-HANDOFF-01@1`, `DOC-TASK-CLOSEOUT-OWNER-01@1`, `DOC-TEST-LIFECYCLE-01@1`|Применимые определения вместе с `requires`; при конфликте|
|`Документация/36_Единая архитектура тестирования.md`|Разделение тестовых областей, доказательность|Адресно|
|`Документация/36.1_Обязательный регламент тестирования для LLM.md`|`TEST-COLLAB`, `TEST-ENG`, `TEST-COV`, `TEST-EXEC`, `TEST-QA`, `TEST-EVID`, `TEST-SCOPE`|Обязательно|
|`Документация/36.2_Профиль тестирования Web Alarm Workspace.md`|Актуальные инварианты и изоляция|Адресно|
|`reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/`|`report.md`, `amendment_01/` и относящиеся source locators|Обязательно, без повторной приёмки|

Дополнительное правило: архитектурная экономия. Переиспользовать существующие validators, source-review mechanisms и test helpers. Не создавать второй broker, дублирующий Go parser, отдельный конфигурационный framework или лишние абстракции.

## 5. Программа исследования

### Этап A — происхождение и целостность

После GO:

1. Получить единственный точный модульный архив.
    
2. Зафиксировать URL, redirect chain, дату, размер, SHA-256 ZIP, разрешённый proxy route и фактические ограничения downloader.
    
3. Проверить module path/version, структуру архива, duplicate/case collisions, опасные пути, traversal, symlink/reparse cases, CRC и отсутствие записи вне разрешённого каталога.
    
4. Отдельно проверить ожидаемый `h1:` по алгоритму **Go module ZIP checksum**, а не сравнением его с raw SHA-256 ZIP. Если корректная offline-проверка невозможна — `CHECKSUM_UNVERIFIED`.
    
5. Связать импортируемые API с сохранённым sing-box v1.13.4 source snapshot. Любую недостающую transitively required dependency фиксировать отдельно, не загружая автоматически.
    

Сохранить проверяемый receipt и tree manifest. Оригинальный ZIP/source tree не помещать в публичный репозиторий.

### Этап B — HTTP CONNECT

По реальным определениями функций и call graph установить:

- где читается HTTP request и распознаётся метод CONNECT;
    
- как определяется authority, host, port, target и IPv4/IPv6 destination;
    
- какие authentication checks выполняются до открытия upstream connection;
    
- какие ошибки, malformed requests, unsupported methods и early EOF приводят к отказу;
    
- возможен ли альтернативный HTTP, SOCKS, tunnel, packet или redirect path;
    
- где завершается parsing и начинается dial через sing-box outbound/route.
    

Для каждого критичного утверждения указать исходный файл, функцию и точные строки. Не считать наличие обработчика CONNECT доказательством соблюдения всей строгой политики.

### Этап C — authentication и JSON

Исследовать:

- реальную модель proxy authentication: credentials, отсутствующий/неверный auth, ошибки проверки и отказ доступа;
    
- риск обхода authentication через альтернативные handlers;
    
- обработку JSON/options, неизвестных полей, невалидных типов, пустых и null-значений;
    
- duplicate keys и допустимые неоднозначные варианты, если они существенны для контракта;
    
- применение defaults, объединения нескольких файлов, reload и возможной смены policy после reload;
    
- границу между библиотекой `sagernet/sing` и собственным конфигурационным кодом sing-box.
    

Отдельно обозначить всё, что остаётся за пределами полученного исходного дерева.

### Этап D — строгий маршрут и негативные сценарии

Сопоставить реальный source call graph с целевым `STRICT_V2RAY_BROKER`.

Проверить исходниками, какие условия необходимы для:

- default-deny при пустой, неполной или неподходящей конфигурации;
    
- отсутствия DIRECT, неутверждённого secondary proxy или fallback;
    
- единственного разрешённого пути через B-owned broker к утверждённому upstream;
    
- запрета нежелательных UDP/UoT, DNS и иных дополнительных egress paths;
    
- fail-closed при ошибках auth, CONNECT, outbound, group selection, resolver, health checks, config merge/reload и недоступности upstream.
    

Разделить выводы на `SOURCE CONFIRMED`, `CONDITIONAL`, `UNVERIFIED`, `BLOCKED`.

Ни один source finding не должен объявляться доказательством SID/WFP, process ownership либо реального трафика.

### Этап E — source tests

Проверить возможность адресно расширить существующий `singbox_source_review.py` и `singbox_source_review_suite.py`, не создавая второй анализатор.

Требуются релевантные pure/source negative controls: повреждение source pin, несовпадение module hash, пропуск проверки auth, изменение критичного parser/route anchor, допуск DIRECT и неизвестного default path. Мутации — исключительно во временных копиях данных/фикстур.

Сохранить исходные RED/FAIL, итоговые PASS/FAIL/ERROR/SKIP, команды, exit codes, test collection, ограничения и объяснения оракулов.

Не запускать native Go и не подменять его симуляцией. Для непроверяемых семантических сценариев указать `TEST GAP`, а не искусственный PASS.

Включить `MANUAL ENGINEERING REVIEW`: просмотренные ветви, альтернативы, edge cases, неизвестные и остаточные риски.

## 6. Write scope и сохранение

**Разрешено:**

- `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/**` — новый итоговый пакет, manifest, sanitized evidence, source map и результаты.
    
- `integrations/wua_chatgpt_mcp/singbox_source_review.py` — только если действительно требуется минимальное расширение существующего source validator.
    
- `tests/singbox_source_review_suite.py` — только соответствующие pure/source regression и negative tests.
    
- Новый изолированный каталог source-only ZIP/tree вне repo, без перезаписи предыдущего содержимого.
    

Остальные source, runtime, config, tests, runners, CI, документация, карточки и личные архивы — READ-ONLY.

Любое расширение write scope требует отдельного USER GO.

## 7. Критерии сдачи

**PASS в пределах source-review**, если точная версия получена и проверена, критичные HTTP CONNECT/auth/JSON paths изучены с locators, выполнены разрешённые тесты, нарушения маршрута явно раскрыты, а все open gates сохранены.

**PARTIAL**, если исходники проверены, но поведение условно зависит от других неполученных зависимостей либо не может быть доказано без native tests.

**BLOCKED**, если нет USER GO на download, отсутствует разрешённый строгий proxy route, не доказаны версия/целостность либо для продолжения нужны запрещённые действия.

Сдать:

- `report.md` — итог, таблица source findings, `MANUAL ENGINEERING REVIEW`, статусы и NEXT;
    
- `manifest.json` — фактический список сохраняемых артефактов и hashes;
    
- `source_provenance.json` — источник, version, module checksum, архивные проверки;
    
- `source_callgraph.md` — HTTP CONNECT/auth/JSON и связь с sing-box;
    
- `strict_route_gap_matrix.md` — что подтверждено, что запрещать, что остаётся недоказанным;
    
- `tests/` или `runs/` — sanitized evidence выполненных проверок;
    
- `DOC IMPACT / SHARED DOC DELTA` — предложения для №19, №34, №06 без их изменения.
    

Отчёт и доказательства сохранять в неигнорируемой части `ag_llm`. Не публиковать ZIP, секреты, credentials, полные приватные raw-логи или неочищенные данные хоста.

До завершения обязательных проверок не объявлять `RESULT READY`. При длительных тестах соблюдать `DOC-TEST-LIFECYCLE-01@1`. При блокировке честно указывать её причину.

**Завершение:** `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, `PARTIAL` либо `BLOCKED`. Не объявлять самостоятельный `DONE / VERIFIED`.

Персональную карточку, БЛОК 4 и архив `001` не менять. После пользовательской публикации независимую приёмку и централизованное закрытие выполнит ChatGPT-координатор.

**Итоговая цель:** представить пользователю доказательную матрицу и рекомендацию для последующего выбора sing-box либо V2Ray Core. Самостоятельно выбирать или переключать движок запрещено.

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
