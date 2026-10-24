## 3. CHATGPT ↔ ULTRA VIA PLUGIN / MCP

Это отдельная архитектура, где инициатором interaction является внешний ChatGPT или integration environment.

```text
ChatGPT
↓
Plugin / Connector / MCP-compatible integration
↓
Ultra Integration Adapter
↓
Server-owned commands / tools
↓
Ultra Runtime
```

Эта схема не означает, что Ultra скрыто вызывает web ChatGPT как API. Она не использует browser scraping, Selenium или Chrome DOM automation и не является обходом normal OpenAI API.

Возможные будущие операции:

- получить список Workspace;
- получить summary выбранного RUN;
- получить Audit export;
- прочитать конкретный RUN record;
- запустить TASK;
- получить status TASK/RUN;
- получить bounded diagnostics;
- запросить Planner / Executor / Dredd evidence.

Все write/action tools проходят Ultra server permission и safety lifecycle. Plugin не получает прямой raw filesystem access в обход runtime.



## 4. SECURITY BOUNDARY

External AI не владеет напрямую:

```text
.ultra internal storage
permissions
backup
Run Store
TaskLifecycle
verification state
```

Integration Adapter должен быть narrow, typed и server-owned. До production нужны authentication, authorization, transport security, scope control, rate limits, timeouts, audit, cancellation и explicit dangerous-action policy.



## 5. LOCALHOST / REACHABILITY

Возможность web ChatGPT напрямую обращаться к localhost Ultra не доказана и остаётся **OPEN RESEARCH QUESTION**. Перед реализацией нужно установить:

- какой transport поддерживает выбранный официальный plugin/MCP environment;
- требуется ли remote или relay endpoint;
- как выполняется authentication;
- доступен ли local connector / desktop bridge;
- какие ограничения платформы действуют на момент реализации.

Нельзя заранее утверждать, что API key не нужен: это определяется выбранным официальным integration path.



### 7.1. FUTURE — сетевые режимы ChatGPT MCP и мастер подключения (решение пользователя 2026-10-20)

**Архитектурная цель, НЕ реализована и НЕ разрешает развёртывание.** Web Alarm Ultra — переносимая мультимодельная платформа: разные люди подключают собственные LLM/API, локальные модели, CLI/агентов и MCP-инструменты через поддерживаемые адаптеры. Каталог и «Проводник» из раздела 7 должны разделять (а) выбор и официальную авторизацию внешнего ChatGPT → Ultra MCP/plugin, (б) выбор сетевого маршрута, (в) разрешения на конкретные операции Ultra. Обратное направление Ultra → LLM/OpenAI как model provider — **другая интеграция** (документ 11), а MCP-сервер инструментов сам по себе не является LLM-провайдером.

**Планируемые профили (не список готовых функций):**

| Профиль | Назначение и ограничения |
| --- | --- |
| `DIRECT_ALLOWED` | Прямой сетевой путь только при явном выборе пользователя, если политика организации и официальный transport это допускают. Никогда не аварийный fallback из строгого профиля. |
| `APPROVED_PROXY` | Согласованный корпоративный или иной доверенный прокси; возможности, аутентификация и безопасность отдельно проверяются для конкретной среды. |
| `STRICT_V2RAY_BROKER` | Текущая цель WUA/Codex: две отдельные неадминистративные Windows identity `wua-client` и `wua-broker`, точные SID/WFP-ограничения, выделенный брокер через V2Ray к разрешённому upstream; **никакого DIRECT, обхода через другие прокси или тихого ослабления защиты**. При недоступности брокера/V2Ray/WFP или недоказанной границе — fail-closed / BLOCKED. |

V2Ray нужен **для выбранного текущего строгого профиля**, а не для MCP вообще. Две Windows-учётные записи — пока архитектурный кандидат именно строгого профиля, не обязательная часть остальных режимов и не доказательство безопасности сами по себе. Ограничения технических SID не защищают всю Windows или обычный пользовательский ChatGPT Desktop; безопасность его процессов оценивается отдельно. Для hostile child/T2 может понадобиться более сильная граница. WFP/IPv4/IPv6/DNS/IPC/loopback port ownership/boot failure/действительный egress V2Ray остаются непроверенными, а Install/Uninstall — BLOCKED.

**Целевой UX внутри Ultra:** открыть каталог интеграций → выбрать «ChatGPT: внешнее MCP-подключение» → проверить официально доступный вариант связи/поддерживаемые возможности → выбрать сетевой профиль → увидеть точный план локальной установки, системных/сетевых изменений, разрешений и рисков → отдельно подтвердить административные действия → запустить настройку/проверки → получить подтверждённый статус либо безопасный отказ/откат. Для строгого режима допустима кнопка «Настроить MCP и брокер»; до доказанной изоляции она не должна разрешать реальную установку. Нельзя без отдельного USER GO менять рабочие учётные записи, WFP, firewall, V2Ray, маршруты и службы или нарушать работу существующей Windows.

**Авторизация личного ChatGPT:** Ultra не должна запрашивать обычный пароль от ChatGPT, хранить его в TASK/логах или передавать агенту. Использовать только официальный способ, действительно поддерживаемый конкретным каналом интеграции на момент реализации (OAuth/browser/device flow или иной подтверждённый механизм); секреты — в платформенном хранилище, агент получает только безопасный статус/opaque handle. Подписка и вход в ChatGPT Web/Desktop **не гарантируют** API/MCP-доступ. Прямое Web ChatGPT → localhost, desktop bridge, transport и реальный E2E пока остаются OPEN, `HOSTED_TUNNEL_ON_HOLD_BY_USER` неизменен.

**Инженерная граница:** текущий `CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001` — offline Discovery/Plan/static Verify/rollback planner, не готовый системный установщик. Следующий этап Codex должен отделять transport/профили от проверяемого security backend строгого режима. Реальные Windows-пробы только в отдельно подтверждённой лаборатории и по отдельному разрешению. Это уточнение **не назначает Codex задачу автоматически**.

Состав команды и назначения моделей описывает [[11_Мультимодельная архитектура и назначение LLM]]; Program/Stage, permissions и recovery — `23_Архитектура Web Alarm Workspace.md`. Это ориентир будущего onboarding, а не новый CURRENT stage и не разрешение на немедленную установку/изменение подключений.




### 7.2. FUTURE — независимые границы MCP transport, reachability и egress (архитектурная сверка 2026-10-20)

Нельзя называть одним «MCP-подключением» три технически независимых вопроса:

1. **Канал вызова инструментов:** какой официальный клиент ChatGPT и поддерживаемый им transport реально способен вызвать Ultra MCP tools (например локальный процесс или поддерживаемый удалённый endpoint); отдельно подтвердить способ регистрации, аутентификации, версии протокола и фактические capabilities. Наличие MCP-сервера на ПК ещё **не доказывает**, что конкретный обычный ChatGPT Web/Desktop способен к нему обратиться.
2. **Достижимость endpoint:** локальный `localhost`, удалённый сервер или разрешённый relay требуют разных механизмов. Исходящий V2Ray-брокер **сам по себе не публикует локальный MCP endpoint** и не даёт облачному ChatGPT входящего доступа; нельзя незаметно запускать публичный tunnel, открывать порты либо отключать firewall. `HOSTED_TUNNEL_ON_HOLD_BY_USER` сохраняется. Для любого будущего внешнего endpoint отдельно проектируются TLS, client authentication, ограниченные полномочия, отзыв доступа и защита от повторов.
3. **Политика исходящей сети (egress):** `DIRECT_ALLOWED`, `APPROVED_PROXY` и `STRICT_V2RAY_BROKER` описывают **конкретный контролируемый процесс/сетевой маршрут**, а не способ «подключить ChatGPT» и не сеть облачных процессов ChatGPT. Windows SID/WFP могут ограничивать только охваченные доказанной политикой локальные процессы; это не защита всей ОС, браузера, обычного ChatGPT Desktop или удалённого облака.

Профиль явно привязывается к connection identity, фактическому процессу/операции и выбранному route. Запись конфигурации, успешный `ping` MCP и успешный тест V2Ray — **три разных вида evidence**; ни один по отдельности не доказывает end-to-end безопасность. Для строгого профиля нельзя менять route на DIRECT/другой proxy, отключать защиту, переиспользовать credentials или расширять scopes при сбоях: статус `BLOCKED`, без скрытого fallback. Переключение профиля — новое явное решение пользователя с повторной проверкой границ. Для иных профилей поведение при отказе также определяется явной policy, а не неявным обходом выбранного маршрута.

**Отдельные критерии подтверждения перед реализацией:** (а) read-only `ping` и синтетический `read_context` из действительно выбранного обычного ChatGPT-клиента, включая client identity и audit; (б) независимое доказательство reachability и auth для фактического transport; (в) в изолированной Windows-лаборатории негативные тесты egress для охваченных SID/процессов: IPv4/IPv6, DNS, loopback/IPC, listener ownership, перезапуск, отказ брокера/V2Ray/WFP и отсутствие прямого выхода; (г) только после этих проверок — отдельное решение пользователя об установке или production E2E. Недоказанное остаётся `UNVERIFIED / BLOCKED`, а не «работает».

**Мультимодальные данные:** MCP tool capabilities и модальности LLM — разные признаки. Любая будущая передача изображений, звука или других вложений через интеграцию требует отдельно проверенного transport, typed payload, scope, ограничения размера, provenance и правил приватности; одного `MODEL ASSIGNMENT` недостаточно. Каноническая терминология — документ 11, голосовое ASR — документ 12; возможное отображение этих типов в Blueprint LLM пока только тема будущего согласования.




### 7.3. CURRENT — ограниченная независимая приёмка offline WFP и Windows Lab Gate (2026-10-21)

**Evidence source:** `main@fd908cd0fff0abe5ab91b270f89cd1f5933f4192`, `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/` и `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/`. Предыдущий WFP backend принят WEB_11 **только как OFFLINE source/build/test candidate**: native WFP enforcement/Windows isolation/rollback/live MCP остались `NOT VERIFIED / BLOCKED`.

**Windows Lab Gate — WEB_11 INDEPENDENT BOUNDED ACCEPTED (документально-кодовая проверка):** опубликованный пакет — 215 из 215 manifest-путей существуют; независимо пересчитанные SHA-256 **13/13** выборочных ключевых текстовых исходников, тестовых результатов и отчёта совпадают. Сопоставлены тесты, подписанная synthetic-positive фикстура, genuine red 50/51 и итоговый 52/52 PASS **по сохранённым результатам Codex**; mutation controls NIC и synthetic-trust приводят к ожидаемым 2 и 1 FAIL. Независимый повторный Windows-run **NOT RUN** (подключённого lab host нет), поэтому counts не обозначают independently rerun tests.

**Реальное состояние:** `gate_results.json` — **I01–I12: 12/12 BLOCKED**, `LAB_PLATFORM_NOT_PROVISIONED`, `HOST_CONFIG_PROOF_PENDING`, `GUEST_ISOLATION_PROOF_PENDING`, `NATIVE_WFP_EXECUTION_BLOCKED`. Для настоящей машины готовый Hyper-V/lab VM/licensed offline Windows media не подтверждены. `source/lab_gate.py` валидирует подписанное evidence и имеет исключительно data-only план, `native_execution_allowed=false`, `vm_changes_allowed=false`, `can_apply=false`; настоящая изоляция не доказана. Подписи свидетельствуют о происхождении заявленных фактов, **не об истинности host/guest sensors или физическом containment**.

**NEXT / HOLD:** пользователь должен отдельно выбрать уже подготовленный lab host и легитимное offline media; далее нужен индивидуальный USER GO на создание/controlled baseline boot disposable VM после точного host-specific review, а потом отдельный USER GO на native WFP только после I01–I12/negative controls, independent observer и recovery proof. На рабочей Windows ничего не устанавливать, не включать Hyper-V, не менять WFP/V2Ray/firewall/сеть; старые `Install/Uninstall BLOCKED`, `CanApply=false` и `HOSTED_TUNNEL_ON_HOLD_BY_USER` не изменены. ChatGPT Desktop ordinary-chat MCP E2E и route строго через V2Ray по-прежнему `NOT VERIFIED`. Документ фиксирует результат проверки, **не санкционирует новый исполнительный TASK или активацию**.



### 7.4. CURRENT — проверенные offline MCP NPFS и выделенный broker (2026-10-24)

**NPFS:** `CODEX-WUA-0-MCP-NOTCP-NPFS-001`, source `main@1147d283674f60ad94dd0be4b26f49e751523669`: independent WEB_11 GitHub source/evidence read, **1404/1404** published paths, **10/10** selected hashes; Codex stored 24/24 NPFS, 63/63 MCP, 24/24 security, independently rerun Windows NOT RUN. Local path: MCP SDK ↔ STDIO C# relay (no Python asyncio on C) ↔ local authenticated Windows Named Pipe ↔ U server-owned MCP SDK/synthetic WebAlarmApi. Finite observation ≠ permanent OS no-network; cross-SID, WFP, real U authority not demonstrated.

**V2Ray broker offline:** `CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001`, source `main@1324f544c7d3fef6c0a80bf71f7460f372f6950d`: independently confirmed **617/617** manifest paths and **12/12** selected hashes; Codex saved 33/33 broker, 63/63 MCP and 24/24 security results, Windows rerun by verifier NOT RUN. Disabled v1 schema/preflight and single-process Python CONNECT/egress loopback fixture exercise fail-closed DIRECT/owner negative oracles; it is not a native V2Ray executable or real B-owned SID socket. Codex initial failures preserved. `can_apply=false`, `can_start_tunnel=false`.

**F2 and native gates:** historical v2rayN used sing-box.exe, not a confirmed V2Ray Core. `ENGINE_VERSION_SOURCE_BLOCKED`, `ENGINE_CONFIG_COMPATIBILITY_BLOCKED`: exact source/version/config behavior unknown. Real B egress owner, C/B identity, WFP IPv4/IPv6/DNS/IPC, protected credentials, secure MCP tunnel and ordinary-chat tools remain NOT VERIFIED/BLOCKED; `HOSTED_TUNNEL_ON_HOLD_BY_USER`. No B-wrapper → host-user SOCKS equivalence and no DIRECT fallback. Next obtain bounded read-only locally approved exact engine metadata and decide sing-box vs V2Ray with user; host-native tests only after isolation and separate GO. No runtime/Windows changes approved. Permanent verdicts in 06 and Codex B4.


