# CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001

**2026-10-24 / Codex 007 — RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.**

Текущий v2rayN действительно связан с **sing-box.exe**. Статически прочитанный файл имеет SHA256 **`ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3`**, 44,773,888 bytes, PE32+ AMD64. Хеш точно совпал с историческим наблюдением 17 октября. Встроенные Go metadata заявляют **sing-box v1.13.4**, Go **go1.25.8**, source revision **`d09182614c7778c1e0f51d990635c5d4249c437e`**. Это идентификация конкретного локального файла и его build claims, **не проверенное соответствие официальному release/source**.

FileVersion/ProductVersion/CompanyName/OriginalFilename/ProductName отсутствуют. В PE нет встроенной Authenticode certificate table. Catalog signatures/цепочки доверия/издатель не проверялись: никаких сетевых signature/revocation запросов. Ни core, ни `--version` не запускались. Working profile, command line, subscription, credentials и process memory не читались.

## Факты и пределы идентификации

Через локальный filtered `Win32_Process` metadata query получены v2rayN PID2012 и его sing-box child PID21976; прочитан только exact executable path. Путь связан с сохранённым `ENGINE_BINARY_01` через SHA256 нормализованной строки. Публичный receipt не содержит raw path. Read-only binary inventory проверяет local fixed drive/reparse attributes, размер, file identity/mtime до/после чтения. Результаты: `evidence/binary_snapshot.json`, `inventory_receipt.json`, `process_link.json`.

Это не доказательство, что байты ранее загруженного image в памяти полностью совпадают с файлом на диске; память не исследовалась. Имя v2rayN не является именем core. Go module path `github.com/sagernet/sing-box` и current child basename подтверждают семейство на уровне согласованных metadata claims, но могут быть подделаны вместе с бинарником. Официальный digest/signature и matching release source отсутствуют в разрешённых материалах.

Проверены только пять exact adjacent source/doc candidates: `go.mod`, `go.sum`, `README.md`, `LICENSE`, `config.schema.json` — отсутствуют. Это не поиск по диску и не утверждение, что исходников нигде нет. Рабочий `config.json` и соседние пользовательские данные не открывались. Новый V2Ray Core path/release не предоставлен; его присутствие по всему компьютеру не исследовалось.

## Результат source/schema и сравнения

HTTP CONNECT inbound, route defaults, одно encrypted upstream R:Q, отсутствие DIRECT/fallback/скрытых DNS/UDP/IPv6/health/telemetry/companions у **настоящего** sing-box v1.13.4 остаются **UNVERIFIED**. Build tags/dependency names показывают включённые компоненты сборки, но не доказывают, какие функции активны и какие сетевые пути отключены. Для V2Ray Core нет разрешённого конкретного release/source/schema; его возможности также не выдаются за проверенные по памяти модели.

Техническое сравнение — `singbox_vs_v2ray.md`. Сейчас нет доказанного технического основания менять engine только из-за названия «V2Ray». Рекомендация с высокой уверенностью по порядку работы: **сначала source-only review подлинного локального bundle существующего sing-box v1.13.4/revision d091826…**, сохраняя выбор engine за пользователем. Уверенность в его strict CONNECT compatibility — недостаточная; никакого deployment recommendation пока нет.

Существующий broker schema требует `engine.family=V2Ray`. Новый metadata gate обнаруживает два отдельных конфликта: при выборе V2Ray — `ENGINE_FAMILY_MISMATCH`; при гипотетическом выборе sing-box — `EXISTING_CONTRACT_ENGINE_MISMATCH`. Даже ручная подмена family в старом contract отвергается старым validator. Этот конфликт не означает, что sing-box технически неспособен работать как B-owned broker; он означает, что автоматической смены одобренного контракта нет.

## Реализованный код и проверки

Добавлены только `integrations/wua_chatgpt_mcp/engine_snapshot.py` и `tests/engine_snapshot_suite.py`. Первый — bounded PE32+/inline Go build-info metadata reader и gate evaluation; никаких loaders/installers/native config generators. Второй — offline тесты с inert byte fixtures и negative/mutation oracles. Повторно используются `common` и существующий `broker.preflight/security_contract`; второй broker stack не создан. Прежние код/config/NPFS/WFP не менялись.

**44/44 PASS, 0 FAIL/ERROR/SKIP:** 25 новых metadata tests и 19 прежних pure broker contract tests. Финальный run — `runs/suite-20261024-175139-adb7977b/result.json`. Проверены pin/version swap, malformed/truncated PE/Go, schema mismatch, неизвестная версия, fake source/capability/signature/owner claims, engine-family mismatch, неправильные endpoint/DIRECT/fallback/default/second proxy. Две code mutations дали по одному ожидаемому inner FAIL и обнаружены: удаление inventory pin guard и доверие fake capability. Это синтетические metadata controls, не системные эксперименты.

Начальный прогон тоже 44/44 PASS, сохранён отдельно. Manual review нашёл test gap: duplicate-module fixture меняла длину файла и могла отказать на PE bounds вместо нужного oracle. Final regression сохраняет длину и требует точный `GO_DUPLICATE_MODULE`; зелёная первичная попытка не выдана за покрытие этой ветви. Неожиданных initial FAIL/ERROR в этой TASK не было. Точные IDs, counts, mutation evidence — `checks.json`, `tests.md`.

Новые тесты запрещают socket и child process creation Python audit hook. Это дополнительный контроль нашего pure Python runner, не OS containment. Два прежних broker tests с loopback/subprocess и весь route/native/SDK E2E здесь **NOT RUN**. Старые 33/63/24 — исторические результаты предыдущей TASK, не текущие повторные прогоны. Нативные core/network/WFP tests в этой TASK: **0**.

## Статусы

```text
ENGINE_BINARY_IDENTIFIED — точный файл, static metadata / embedded claims
ENGINE_RELEASE_PROVENANCE_BLOCKED
ENGINE_NATIVE_CONFIG_SCHEMA_BLOCKED
STRICT_CONNECT_COMPATIBILITY_UNVERIFIED
ENGINE_SELECTION_PENDING_USER
B_IDENTITY_NOT_PROVISIONED
B_EGRESS_OWNER_NOT_VERIFIED
WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER
ORDINARY_CHATGPT_E2E_NOT_VERIFIED
can_apply=false; can_start_tunnel=false; native_config=null
```

Подлинного versioned native schema нет, поэтому настоящая disabled native configuration не генерировалась и её structural validation **NOT RUN / BLOCKED**. Положительные JSON-флаги, совпадение hash или version claim не повышают реальные gates. Реальный F2 — один B-owned process владеет CONNECT и actual remote socket — по-прежнему не подтверждён. Системные SID/WFP, DNS/IPv6, pre-existing flows/observer loss и credentials остаются отдельными gates.

## Сохранность и handoff

Контрольный список из **95 предыдущих файлов** сохранён в `evidence/initial_state.json`; итоговая сверка — `evidence/final_integrity.json`. Core только читался, штатный v2rayN/sing-box не останавливался и не перенастраивался. Accounts/ACL/WFP/Firewall/BFE/services/proxy/DNS/VPN/network/hosted tunnel не менялись; downloads/Git/GitHub operations: 0. Это не утверждение об отсутствии фонового трафика чужих работающих приложений.

Независимый прошлый verdict WEB_11 прочитан в собственном B4: PARTIAL / INDEPENDENT BOUNDED OFFLINE ACCEPTED, 617 paths/12 selected hashes; independent Windows run NOT RUN. GPT#402 и coordinator SHA — предоставленные ссылки, не локально проверенная Git-история. Для этой TASK независимой приёмки ещё нет.

DOC IMPACT: общие 18/19/34/37 не правились. Предложение WEB_11: добавить static sing-box build claim v1.13.4/go1.25.8/d091826… и совпавший historical hash, сохранив provenance/schema/CONNECT/real B ownership BLOCKED. В актуальном 18 есть уточнение ротации согласно личной карточке; применяется compact five + append-only 001. Ссылка `DOC-VERIFIER-BLOCK4-01@1` в собственных правилах устарела относительно текущего @2; в этом scope правила карточки не редактируются, B4 сохраняется целиком.

Штатная ротация выполняется после сохранения report/manifest; receipt — `evidence/card_rotation.json`. Старые 001 bytes не читаются и не переписываются, сверяется только новая запись, B4 сохраняется побайтно. Следующее **решение пользователя**, а не operational GO, сформулировано в `next_user_decision.md`. Комплект готов для пользовательской публикации и передачи WEB_11.

Фактический результат ротации: **CARD ROTATION VERIFIED**, добавлено/сверено **22,102** новых байт, старых байт архива прочитано/переписано **0**. B1 `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`, B2/B3 по пять кратких записей; B4 SHA256 до/после **`608c49b5be482fc6c7ccb7db2c5898bf8c6f9143fbf1d2c02a1c14f4e9fbb089`**. Это административное завершение offline-исследования, не независимая приёмка native/security gates.
