# CODEX-WUA-0-NATIVE-EGRESS-GATE-001

**WUA MCP — Native Egress Isolation & V2Ray-Only Gate**
Codex 007 · 18 октября 2026 · Asia/Yekaterinburg · координатор WEB_10.

**Исследование: PARTIAL / RESULT READY. Настоящий native gate: BLOCKED.**
**LOCAL ONLY / GITHUB NOT YET VERIFIED.** Подготовлены проверяемая схема,
карта рисков, новые offline evidence и условия следующего этапа. OS boundary
не установлен/не доказан; отдельного USER GO на native execution нет.

## Обязательные итоговые статусы

```text
SOURCE AUDIT PARTIAL
NATIVE EGRESS MAP PARTIAL
WINDOWS ISOLATION DESIGN PARTIAL
OS-ENFORCED EGRESS ISOLATION NOT VERIFIED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

**SOURCE PACK BLOCKED.** Разрешение на исследование этой TASK не является
разрешением запускать native EXE. Никаких реальных ключей/tunnel IDs, hosted
endpoints, OpenAI/Cloudflare/внешних DNS/IP подключений исследуемой цепочки.

## 1. Вход, scope и provenance

Текущий БЛОК 1 действительно содержит новую утверждённую TASK; card SHA на входе
`7d2e8a1ef2d5943cc2e289aacaa5a4075d37d0f68cd65fc1c1fbf3cb79328576`.
Полная постановка сохранена в `assignment.md`. Историческая проблема чужой задачи
в карточке не исправлялась/не восстанавливалась этим агентом.

Прочитаны route 08→000→34→18→01, персональная карточка, профильные 19/23/36/36.1/
36.2/37, AM05–AM07 и текущие независимые выводы WEB_10. 17 адресных нормативных
definitions/contract/source hashes — `rules_read.json`. Предыдущие 19/19, 5/5,
36/36 suites **не повторялись**. Hash-pinned AM07 fixtures импортированы только
для **новых** chain-lease/attempt-oracle tests, старые TestCase не запускались.

В 34/19 WEB_10 записал bounded independent AM07 review опубликованного
`e6724b15e1191c5f49ad2eb9ca6245208cdda157`: 32 manifest paths + manifest,
13/13 sampled byte/SHA checks, reference accepted with open risks, без своего
Windows rerun. Это локально прочитанные coordinator statements, не собственный
GitHub read Codex. Excerpts/hashes — `coordinator_findings.json`.

Запись только в `reports/CODEX-WUA-0-NATIVE-EGRESS-GATE-001/`. Сеть, V2Ray/sing-box,
Windows firewall/DNS/TUN/routes/proxy/permissions, launcher, остальные TASK,
Claude/LLM12/production и предыдущие отчёты не менялись.

## 2. Gate A — источник и карта настоящей цепочки

`native_egress_map.md` задаёт для каждого пути: **инициатор → endpoint → transport
→ proxy-policy source → возможный bypass → требуемый запрет → уровень evidence**.
Охвачены main/secret control-plane, MCP HTTP/startup/binding/STDIO child, OAuth,
Harpoon, proxy-health, DNS, redirects/retries/reconnect/defaults/overrides,
Cloudflared, неизвестные children/IPC brokers, adapter, V2Ray remote broker,
локальный WUA API и отдельный frontend ChatGPT.

Разделены три вещи:

1. Official tag v0.0.16 → commit
   `5f99daabd4aa4a77049e6d81d54a0d8c18335397`, по exact-tag source review WEB_10:
   explicit HTTP/HTTPS-only parser, fixed transport Proxy, global/component
   layers, proxy в main/secret control-plane/HTTP MCP, отдельный Cloudflared child.
   Это **SOURCE VERIFIED BY COORDINATOR**, не новые собственные source bodies.
2. Локальный Windows EXE SHA-256
   `4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`, сохранён
   побайтно. Commit literal ≠ reproducible build attestation. EXE не исполнялся.
3. Official runtime-source tar.gz с expected SHA-256
   `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0` локально
   не найден. `source_pack_search.json`: **SOURCE PACK BLOCKED**; загрузок/обходов
   Git/API/raw-content/pip/npm/go mod не было. Точный список необходимых файлов
   и dependencies указан в карте.

Поэтому full native graph/source→EXE proof — **BLOCKED**, полная карта PARTIAL.
Не обещается process-wide direct deny одним proxy setting. Наличие символов или
отдельного fixed HTTP callback не распространяется автоматически на все
resolvers/clients/children/дополнительные transports.

## 3. Gate B — Windows isolation design

Обнаружен новый первичный локальный источник: Windows SDK **10.0.19041.0**.
Прочитаны 22 selectors declarations/constants в fwpmu.h/fwpmtypes.h/fwptypes.h:
ALE_AUTH_CONNECT v4/v6, App ID/user/package, remote address/port/protocol,
BLOCK, transactions/filter add/delete и net-event API. Полные headers не
копировались; paths/hashes/line numbers — `windows_source_evidence.json`.
**Ни один WFP/security mutation API не вызывался.** Это наличие интерфейса,
не доказательство активной политики или её semantics.

`isolation_design.md` разделяет два этапа:

- **Первый native offline gate:** заранее предоставленная disposable Windows VM
  без внешнего NIC/NAT/bridge/gateway/DNS/host relay/integration escape channels.
  Все fixtures и потомки внутри. Не только guest route list, а независимая
  attestation реальной hypervisor boundary. Отдельный USER GO после review.
- **Возможная рабочая цепочка:** authenticated scope и default-deny для root,
  adapter, WUA child и всех descendants; только точные directed loopback edges;
  отдельно подтверждённый broker→approved remote route. Это WFP candidate,
  не installer и не выполненная Windows policy.

Существенные открытые условия:

- App-path/PID-only rule нельзя считать деревом процессов; shared Python и другой
  child EXE требуют OS-derived scope, birth-time containment и generation identity.
- `FWPM_SESSION0.processId` — engine session metadata, не готовое child-tree rule.
- Loopback:* слишком широко; даже fixed port требует trusted receiver identity:
  broker может умереть, другой процесс занять порт. Snapshot PID не atomic binding.
- Controller/BFE/session/callout failure не должен убрать deny, пока scope жив;
  active flows нужно отозвать отдельно от запрета новых connects. Header flags
  не доказывают безопасный crash/rollback/order/arbitration.
- Client-side restriction не доказывает, что sing-box не выберет DIRECT/local DNS.
  Нельзя превратить broker exception в разрешение ему любого remote egress.

Точный **контракт будущего rollback** описан: freeze admissions → close/reap
только owned scope → подтвердить отсутствие живых members/flows → удалить/
восстановить только manifest-owned keys/state → readback. При cleanup failure
deny сохраняется. Никаких reset всей Windows firewall/сервисов/чужих правил.
Backend-specific executable rollback пока не может быть безопасно выписан:
installer/backend не выбран и не разрешён. Сейчас OS mutations для отката **0**.

Read-only inventory: Windows 10.0.19045; BFE Running, Sandbox EXE отсутствует,
команды Hyper-V/VM/container не найдены в bounded inventory; optional states
сохранены численно. Это не exhaustive proof отсутствия всех VM на компьютере.
Готовой **attested** среды не установлено. Design **PARTIAL**, OS isolation
**NOT VERIFIED**; ни VM, ни feature, ни driver/security profile не создавались.

## 4. Gate C — HTTP/SOCKS5 и рабочий V2Ray

`proxy_options.md`: уже существующий **attested HTTP/mixed inbound предпочтительнее**
адаптера по числу компонентов. AM07 adapter — CONNECT-only synthetic reference,
не general forward HTTP proxy и не native policy. Если требуется отдельный adapter,
его расширение/installation/real destinations нужны по отдельному scope.

Текущий snapshot: V2RayN PID 18032 → sing-box PID **19124**, listen
**127.0.0.1:10808 и :10813**. Запрошенный 10808 принадлежит sing-box; на 10814
в all-listener snapshot ничего не найдено. AM07 10814/PID27008 — история, не
вечная конфигурация. Причина/автор смены процесса/порта не устанавливались.

ExecutablePath/CommandLine снова недоступны через разрешённый CIM read; loaded
config/cwd/HTTP-mixed/DNS/DIRECT/outbound **NOT VERIFIED**. GUI-настройки за active
config не приняты. Live listener/DNS/CONNECT/HTTP probes **0**. Первый snapshot
сохранён; collector повторно прочитал inventory только для добавления отдельного
all-listener ответа по requested 10808/10814.

## 5. Gate D — новые безопасные offline evidence

Новая проверяемая гипотеза: **отказ до API, реально заблокированная попытка API
и успешный обход control-model должны различаться; утрата lease должна закрывать
tracked connections и запрещать следующие root/child attempts**.

`egress_reference.py` — synchronous helper **без OS backend/native launcher**.
Логические identity tuples/child registry — model data, не реальные Windows
токены/PID security. Один configured literal-loopback endpoint, explicit state
READY/TRIPPED/CLOSED; нет environment routing, resolver, fallback или reconnect.

Фактически исполнялось:

```text
Python 3.12.10 x64 / Windows 10.0.19045
22 collected / 22 executed
22 PASS / 0 FAIL / 0 ERROR / 0 SKIP — exit 0, один запуск
18 socket.connect attempts: 17 allowed own-loopback, 1 expected Python guard deny
1 subprocess.Popen attempt: expected Python guard deny before CreateProcess
2 expected guard denials / 0 unexpected
0 fixture errors / 0 remaining ports / 0 worker leaks
0 test-probe child processes / 0 native tunnel-client / 0 cloudflared runs
```

Новые cases охватывают missing/invalid endpoint, hostname без resolver call,
owned-but-unapproved port, unavailable endpoint, SOCKS refusal/timeout/disconnect/
malformed method, lease/monitor loss и закрытие tracked socket, no env/NO_PROXY
renewal, unknown/approved model child, generation reuse/bool trap, UDP/v6 config
refusal, actual API-denial controls и intentional own-loopback orphan detection.

**Три различных oracle результата:**

1. `REFUSED_BEFORE_DIAL`/`CHILD_REFUSED_NOT_CREATED` + ноль API events:
   helper вообще не вызывал dial/create. Источник проверен, DNS API не вызывался.
2. Connect audit event к собственному запрещённому loopback port, затем Python
   guard exception, origin peer отсутствует: **ATTEMPT_BLOCKED_BY_PYTHON_GUARD**,
   не OS verdict. Fake Popen также замечен и остановлен; local CPython source
   hash/line ordering подтверждает audit **перед** CreateProcess. Native child 0.
3. Разрешённый только как quality control raw connect к своему echo origin
   действительно состоялся, но без operation ID модели; oracle его обнаружил
   и trip зафиксирован. Это показывает, почему отсутствие строки в ledger не
   означает отсутствия попытки и почему helper не является OS boundary.

Audit API events **19** = 18 socket + 1 Popen; actual connect trace roles driver14,
SOCKS fixture4. Один allowed orphan dial намеренно synthetic loopback, не внешняя
проба. Raw orphan socket закрывается harness cleanup, не магически registry
модели; production требует kernel/whole-scope revocation. Python guard не
ограничивает arbitrary native code, что в отчёте не скрывается.

Evidence/source hashes — `attempt01_results.json`; команды/dependencies —
`execution.json`. Предыдущие suites не запускались; использованы только их
синтетические fixtures. Read-only collector отдельно дважды запускал PowerShell
для CIM/SDK inventory; фраза «test child 0» не означает «Windows не создавала
вообще никаких процессов». Секреты/headers/payload/error-message dumps не пишутся.

## 6. Manual review, checks и stop

`manual_engineering_review.md` — собственный adversarial source/security review
сверх pass count. Просмотрены check-before-dial порядок, synthetic identity types,
tracked/untracked resource граница, audit correlation, Popen ordering, fixtures,
scope lifetime, WFP/VM alternatives, PID/port takeover и crash/rollback risks.
Не заявляется kernel proof из Python или право установки из самого design.

`checks.json`: **27 evidence rows = 15 PASS / 6 BLOCKED / 6 NOT RUN**. Это не
27 сетевых тестов; новые 22 cases указаны отдельно. Exact native source, actual
Windows enforcement, real broker remote route и execution authority остаются
открытыми. `native_gate_decision.json`: **BLOCKED**, native executor отсутствует.

`native_test_plan.md` задаёт ordering: exact source → boundary evidence →
independent isolation review → **separate USER GO** → только bounded native
loopback cases. Нарушение scope/child/observer/policy/hash — STOP и сохранение
первого failure; никаких public-IP/DNS canaries и retry к реальным службам.
OS-blocked direct attempt ещё не является native-client fail-closed PASS.

## 7. Сохранность, карточка, DOC IMPACT и публикация

**122/122 защищённых input hashes неизменны** в этой TASK, включая 105 файлов
AM05/AM06/AM07, карточку, нормативные источники, native EXE, launcher/profile и
Codex config. SHA config до/после:
`2a1745afe7818f69f564ea36d58f17adb1653edec9e711e3e1c8f8ee97565aa2`.
Hosted launcher hold `HOSTED_TUNNEL_ON_HOLD_BY_USER` сохранён. Никаких старых
config snapshots не восстанавливалось. Это file-hash proof, не whole-OS network
attestation. Raw private configs/DB не скопированы.

Карточка не ротирована: section 8 TASK ограничивает write_scope **только** этой
report folder, тогда как section 10 ссылается на обычный handoff БЛОКОВ 1–3.
Узкая граница записи сохранена; concrete material для согласованной ротации —
`card_handoff.md` + полная `assignment.md`. Не исправлялась история/чужая задача.

**DOC IMPACT:** общие 19/23/34/36 и остальные нормы/карточки не менялись.
**SHARED DOC DELTA proposal для WEB_10 после review:** новая source/map/design
PARTIAL TASK, 22/22 новых reference cases, Windows SDK declarations прочитаны;
OS/native/remote gates BLOCKED, no activation GO; critical child identity,
port-takeover, controller crash/active-flow and broker-DIRECT gaps сохранены.

`manifest.json` перечисляет весь публикуемый безопасный комплект с SHA/размерами.
Project ignore правила читаются только как обычные файлы; actual Git index/global
excludes/GitHub completeness не проверены. **Git/GitHub операций 0**. Пользователь
публикует только новую report folder, затем передаёт factual result WEB_10 для
независимой проверки. Независимую приёмку/рабочий native запуск не объявляю.

## 8. NEXT

1. WEB_10 independently reviews опубликованные sources/design/evidence по exact
   publication, не превращая reference PASS в native security acceptance.
2. Нужен exact runtime source pack через separately approved protected transfer;
   полный source audit и приоритетный выбор offline-VM boundary. WFP backend,
   child identity/flow/crash semantics требуют дальнейшего scoped решения.
3. Native run — только после proof/review и нового адресного USER GO. Broker
   live loaded policy/remote route, hosted и ordinary Chat остаются отдельными
   поздними gates; сеть/системные политики сейчас менять не требуется/не разрешено.
