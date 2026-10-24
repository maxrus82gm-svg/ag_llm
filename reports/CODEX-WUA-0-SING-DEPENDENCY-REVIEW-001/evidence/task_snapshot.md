
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

