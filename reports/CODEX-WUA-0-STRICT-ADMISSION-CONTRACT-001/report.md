# CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001

**Codex 007 / 2026-10-25 — OFFLINE ADMISSION CONTRACT PASS (AUTHOR TESTED). RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12.**

Реализована строгая offline policy в существующем broker/security pipeline. Небезопасные входы получают конкретный отказ; корректный synthetic intent получает `strict_policy_status=VALID`, но всегда `STRICT_ADMISSION_BLOCKED`. Никакой конфигурацией нельзя включить apply/tunnel/install. **Основной набор 52/52 PASS; совместимая source/pure-регрессия 51/51 PASS.** Это Python-контракт и его проверки, **native security NOT VERIFIED**.

## Основание и scope

БЛОК 1 прочитан из собственной карточки; полная неизменяемая постановка сохранена в `evidence/task_snapshot.md`. Пользователь отдельно подтвердил: «Да, main и локальная копия синхронизированы». Coordinator source reference `GPT@37ef710cf0ba34f4988cba46a28595d6ce7801a5` принят как контекст пользователя; Git HEAD самостоятельно не проверялся. Evidence — `evidence/sync_gate.json`. Прочитаны актуальные 08/WEB_12 current/19 §7.6–7.7, адресные правила 18/36.1/36.2 и принятый bounded sing source report/matrix. Прежняя независимая приёмка не повторялась и не переобозначалась.

Изменены только:

- `integrations/wua_chatgpt_mcp/broker.py` — явный строгий статус, canonical/pin admission, безопасные коды и domain-specific mapping отказов существующей schema.
- `integrations/wua_chatgpt_mcp/security_contract.py` — одна функция проверки strict policy и CONNECT metadata, opaque refs, неизменно закрытые activation flags.
- `integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json` — совместимое optional поле admission и формат opaque upstream ref. Исторические null/placeholder значения структурно допустимы, но не проходят strict admission.
- `integrations/wua_chatgpt_mcp/tests/admission_suite.py` — адресный offline selector, повторно использующий 19 pure ContractTests из старого broker suite; новые поведенческие и mutation tests.

Существующий `broker_suite.py` смешивает pure ContractTests и loopback/process Harness. Поэтому создан небольшой offline test entry point в разрешённом tests/, не второй broker/config framework. Старый suite, synthetic example, common parser, sing source validator, runtime и другие тесты не редактировались. Исходные четыре адресных файла сохранены в `source_before/` до правок.

## Реальная policy и интерфейс

API: `broker.strict_preflight(raw_bytes, controller_config_pin, controller_source_pin, request_metadata=...)`. Он использует **существующие** `common.parse` → canonical comparison → broker JSON schema → `security.validate` → `security.validate_admission`. Native HTTP/JSON parser не создавался. Нельзя подставлять pin, заново вычисленный из недоверенного изменённого ввода: expected pins принадлежат контроллеру. После подмены input/source с прежним pin возвращается отказ, без использования старого решения.

Optional admission живёт в том же JSON broker contract:

- Authentication: required=true; один явно заданный protected-reference mechanism; непустой список пользователей, уникальные principals/refs. Только canonical nonzero UUID в opaque `wua-secret-ref:`; inline passwords/headers и неизвестные auth fields запрещены. Upstream ref обязателен и не переиспользует user credential ref. Функция не разрешает ref, не читает store и не получает секрет.
- Configuration: ровно один CANONICAL_JSON source; protected-source declaration; merge/reload/environment_override строго false. Actual B-only filesystem protection этим не доказывается и остаётся blocker. Native permissive JSON не используется как strict admission oracle.
- CONNECT: только CONNECT, без Upgrade/plain HTTP/UoT/background; один явно разрешённый literal IPv4 logical target с integer port1..65535. DNS names, URI, неоднозначные address/port и IPv6 не допущены. Это консервативный будущий subset, не утверждение, что обычный ChatGPT уже совместим с ним.
- Logical CONNECT target **отделён** от physical broker upstream R:Q в integration.route. Совпадение с physical endpoint не становится разрешением на другое logical назначение.
- Existing routing schema продолжает запрещать DIRECT/fallback/secondary/load balancing/host DNS/UDP/IPv6/health/telemetry/companions и неизвестные routing fields. Коды strict refusal выводятся из той же schema; отдельной параллельной route-policy нет.

Три события представлены раздельно:

1. `connect_handler_event=UNTRUSTED_ACCEPTED_CLAIM` либо NOT_ACCEPTED/NOT_OBSERVED — входная metadata, не наблюдение Go handler.
2. `policy_route_allowed=true/false` — только результат локальной offline policy.
3. `real_egress_verified=false` — всегда; Python metadata не доказывает socket/PID/SID/R:Q.

Отсутствующая/malformed metadata не допускается. Настоящие HTTP request bytes не парсятся нашим кодом. Даже утверждение CONNECT200, все approvals=true или правдоподобные engine hashes не дают фактического разрешения. Старый synthetic fixture по-прежнему `BROKER_PROFILE_STRUCTURALLY_VALID`, а строгий статус BLOCKED; отсутствие admission/users отвергается при строгой оценке.

## Секреты и закрытые границы

Own diagnostics содержат только закрытый набор статических rejection codes. Не форматируются ValidationError.message, произвольное exception text, входные usernames, refs, пароли или Proxy-Authorization. При strict rejection удаляется даже contract digest из результата; raw input не журналируется. Неизвестная ошибка превращается в STRICT_INTERNAL_FAILURE (либо fixed structural error), не в str(exc). Это проверено синтетическими markers и отдельным error-echo mutant.

**Это не устранение upstream утечки sing.** Ни third-party source, ни работающий движок не изменялись. `UPSTREAM_SECRET_BOUNDARY_UNVERIFIED` сохраняется обязательным SECURITY BLOCKER вместе с credential-store protection, protected canonical source, CONNECT metadata oracle, engine/source/native config, B owner/WFP/route и hosted/E2E gates. Даже полностью корректный offline intent не может снять их данными.

Любой возвращаемый relevant public decision сохраняет `can_apply=false`, `can_start_tunnel=false`, `install_uninstall=BLOCKED`. Никакого пути реального запуска в новой policy нет. Старый CLI preflight остаётся structural-only и явно маркирует strict NOT_EVALUATED/BLOCKED; он не считает structural validity разрешением.

## Проверки и сохранённый RED

Основная команда: `.\.venv\Scripts\python.exe -B integrations/wua_chatgpt_mcp/tests/admission_suite.py`.

| Attempt | Collection / PASS / FAIL / ERROR / SKIP | Exit |
| --- | --- | --- |
| runs/baseline — до source/test правок | 19 /19/0/0/0 | 0 |
| admission-20261025-134958-2caf5be1 — первый RED | 40 /19/21/0/0 | 1 |
| admission-20261025-135158-dd223945 — первая реализация | 40 /40/0/0/0 | 0 |
| admission-20261025-135342-16add776 — coverage/manual hardening | **52 /52/0/0/0** | **0** |
| source-regression-20261025-135559-d6c08e21 — совместимость | **51 /51/0/0/0** | **0** |

Первый RED не удалён и не переименован в PASS. Он фиксирует отсутствовавший strict API/status на старой реализации, не живую сетевую уязвимость. После реализации первая green40 получена без ослабления expected codes. Добавлены boundary/type/ref-reuse cases и семь executed Python mutants; конечные52 состоят из 19 legacy pure +26 admission tests +7 mutation tests.

Каждый mutant ослабляет конкретный guard в **in-memory копии** Python и должен дать ровно один inner FAIL, ноль ERROR: mandatory auth, merge prohibition, CONNECT-only method, schema/route validation (DIRECT), canonical raw input, controller config pin, secret-safe error output. Все7 обнаружены. Inner expected FAIL не смешивается с outer52 PASS и не является native attack. Исходные code files на диске не мутируются. Evidence `mutant-*.json` содержит trigger/oracle и hashes; raw passwords/рабочие headers не используются.

Совместимая source-регрессия исполнила существующие11 source +21 dependency/archive +19 pure broker tests с output в **новую** TASK. Последние19 пересекаются с основным набором; counts не суммируются как уникальные тесты. Прежние report folders не менялись. Source-anchor tests не выдаются за Go semantics.

Оба offline runners блокируют socket/subprocess audit events; нарушение было бы ошибкой сдачи. Нарушений0. Новые рабочие процессы/listeners не создавались. Старые RouteTests, native/loopback integration tests и два ContractTests с subprocess/listener не исполнялись; remote-schema refusal отдельно проверен без listener новым test. Native tests NOT RUN, а не SKIP/PASS. Никакой full Web Alarm suite не запускался: изменён integration-contract слой, не production Web Alarm.

Source/test hashes, Python/OS context, counts, exit codes, test IDs, skipped selectors и границы guard — `checks.json`, runs/*/result.json/source_pins.json и `evidence/final_integrity.json`. Source hashes — локальная проверка, не Git commit attestation. JSON schema/static syntax проверены, последующие правки source после final runs не выполнялись.

## MANUAL ENGINEERING REVIEW

1. Проверены sync USER acknowledgement, frozen B1, exact write scope, source-before и reusable parser/schema/security contract. Не требовалось читать personal001 или Git. Общие документы и карточка не менялись.
2. Прослежен normal/reject path от immutable raw bytes через parse/canonical/pins/schema до auth/config/CONNECT. Unknown shape не получает default allow; validation exception не раскрывает raw payload. Не создан второй JSON/HTTP parser.
3. Сопоставлены отсутствующий/пустой users, неверные и повторные refs, inline secret fields, непроверенное хранение refs. Корректная форма refs не названа proof их существования/B-only ACL. Утечка upstream остаётся отдельным blocker.
4. Проверены method/Upgrade/plain/UoT/background и строгие literal address/port types. Logical D:port не смешан с physical R:Q. CONNECT acceptance, offline route match и реальное B-owned egress разнесены. Native oracle отсутствует честно.
5. Проверены canonical/duplicate/unknown/null, missing fields, single source и запрет merge/reload/env flags. Это проверка намерения, а не OS proof protected file либо фактического environment процесса. После изменения bytes/source требуется новое совпадение fixed controller pins; cached permission не выдаётся.
6. Просмотрены route schema error mapping и отсутствие дублирующих разрешений. Источник routing restrictions — прежняя schema; добавленные domain codes не печатают schema messages/секретные ключи. Все activation flags остаются false независимо от synthetic evidence/approvals.
7. Проверены реальные triggers/точные refusal codes, in-memory mutant execution, восстановление заменённых test helpers, отсутствие workers/listeners и отдельные run roots. RED40 и inner mutation FAIL сохранены раздельно. Existing fixture/19 pure checks остаются валидными.
8. Остаточные риски: engine integration/adoption этого API, upstream error boundary, real credential store/config ACL, exact Go grammar/JSON/platform behavior, cross-SID/IPC/WFP/actual owner и runtime policy loss. Эти риски не решены Python policy. Долгосрочный caller обязан использовать policy перед engine action и не переосмыслять VALID как разрешение; engine action в этой TASK отсутствует.

## Итоговые статусы / NEXT

```text
OFFLINE ADMISSION CONTRACT: PASS / AUTHOR TESTED
PRIMARY CHECKS: 52/52 PASS; SOURCE/PURE COMPATIBILITY: 51/51 PASS
STRICT_ADMISSION_BLOCKED (including structurally valid synthetic fixture)
UPSTREAM_SECRET_BOUNDARY_UNVERIFIED — SECURITY BLOCKER
NATIVE ENGINE / WINDOWS / WFP / REAL OWNER / REMOTE ROUTE: NOT VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER; ORDINARY CHATGPT E2E NOT VERIFIED
can_apply=false; can_start_tunnel=false; install_uninstall=BLOCKED
CARD / BLOCKS 1–4 / 001 / SHARED DOCS: NOT MODIFIED
NETWORK / DOWNLOAD / GIT/GITHUB / PRODUCTION ACTIVATION: NOT USED
RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12
```

Пользователь публикует код/полный пакет; WEB_12 проверяет exact source/tests/manifest/RED/negative controls. DOC IMPACT для №19/34/06 подготовлен отдельно. Карточка остаётся текущей; ротация/закрытие не выполнялись. Любая engine/credential/native/lab integration, изменение Windows/proxy/WFP или активация tunnel требует отдельного scope/USER GO и настоящего независимого доказательства. Данная сдача не предлагает rollout.
