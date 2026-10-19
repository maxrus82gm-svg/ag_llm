# CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001

**RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Codex 007 · 2026-10-19, Asia/Yekaterinburg · independent architecture review
of Claude 008's proposal · ANALYSIS ONLY / LOCAL READ-ONLY.

**Вердикт: принять идею выделенных Windows identities, отклонить достаточность
описанного P1 и не считать P2 готовой гарантией V2Ray-only.** Без VM можно
спроектировать рабочий фоновой MCP-контур с системным ограничением собственных
сокетов. Предложенный отчёт этого ограничения ещё не доказывает. Строгое
требование, включающее DNS, посредников, подмену loopback-получателя и отказы
защиты, существенно сильнее «блокировать внешние сокеты по SID».

```text
ARCHITECTURE REVIEW COMPLETED — CONDITIONAL RECOMMENDATION, NOT DEPLOYMENT GO
OS-ENFORCED EGRESS ISOLATION NOT VERIFIED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

## Основания и уровень доказательности

**[L]** — прочитанные локальные bytes/schema/help; **[C]** — заявление координатора;
**[K]** — известная документированная модель Windows, воспроизведённая по
инженерному знанию; свежие официальные тексты и runtime здесь не проверены;
**[P]** — предлагаемая конструкция/логический вывод; **[N]** — требует отдельного
системного/native доказательства. Наличие константы в SDK не превращает [N] в [L].

Прочитана вся постановка БЛОКА 1 и весь 413-строчный отчёт Claude
`reports/CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001/report.md`, его manifest/supporting
evidence, адресные материалы AM05–AM07, native-egress и offline-VM-preflight.
**9/9** файлов Claude, перечисленных его manifest, совпали по размерам/SHA-256
с локальными bytes; manifest — десятый файл. Это integrity review, не PASS
его архитектуры. Источники и fresh hashes — `inputs_before.json`.

Актуальные 08/000/34/18/01, профиль 19/36/36.1/36.2 сверены адресно. Из 17
нормативных definitions 16 нормализованных текстов совпали с прежним чтением;
DOC-TASK-BLOCK1-01 теперь явно разрешает узкую ротацию после готовых report,
manifest и evidence, включая завершённое исполнение с PARTIAL/BLOCKED.
Правила собственной карточки не переписываются этой TASK.

Последний доступный локальный review WEB_10 в 19/34 относится к offline-VM
preflight и прежним этапам. **Отдельная запись WEB_10 о Claude EGRESS report
по его TASK ID там не найдена.** Конкретное замечание WEB_10 о Block ALL/Allow
взято из утверждённого текущего БЛОКА 1 §4, а не из вымышленного прочитанного
review. Source pin `25f62e33e9e094e1c4613818ce168890863b3431` — [C], Git не сверялся.

Локально прочитаны 9 Windows SDK/CDXML файлов. `windows_static_evidence.json`
сохраняет hashes, селекторы и строки деклараций. CDXML действительно имеет
`LocalUser` string, `Authentication`, `OverrideBlockRules`; **он не документирует
применимость LocalUser к обычному outbound без IPsec или runtime precedence**.
SDK содержит ALE layers, ALE_USER_ID, loopback flag, Block/Permit, persistence
flags и Task Scheduler/process APIs; это declaration evidence. Доступ к одному
подкаталогу `wbem/MOF` при поиске был запрещён; повышения прав/обхода не было.
`firewallapi.mof` оказался WPP trace metadata, не справкой firewall semantics.

Сеть/web lookup/API/Git запрещены и не использовались. Поэтому ниже нет
притворной ссылки на якобы свежепрочитанную Microsoft/sing-box документацию.
Технические выводы [K] сформулированы отдельно от проверок [L]/[N].

## A. Executive Summary

**Второй рабочий стол и вторая Windows не нужны для запуска под другой
учётной записью.** Планировщик или небольшой доверенный service launcher
могут создавать фоновые процессы с другим primary token в этой же ОС [K].
Это решает удобство запуска; само по себе не создаёт сетевую песочницу.

Рекомендуем **одну конкретную без-VM архитектуру-кандидат для T1**: две
стандартные служебные identities, native user-mode WFP policy с непересекающимися
deny predicates, клиенту только один exact loopback TCP endpoint, брокеру только
один согласованный remote TCP endpoint, direct HTTP CONNECT в выделенный
V2Ray/sing-box broker, без промежуточного AM07-адаптера. Loopback-pin и broker-pin
обязательны **с начала**, а не необязательное последующее усиление P1.

Это [P], не установленная политика. Нельзя заявить полное V2Ray-only даже для
T1 до закрытия DNS/service delegation, listener ownership и поведения защиты
при отказе/boot. Для **T2 с произвольным недоверенным кодом** отдельная обычная
учётка недостаточна: она не запрещает все доступные этой учётке RPC/COM/IPC
вызовы. Если T2 обязателен, нужен проверенный более сильный application/IPC
boundary (AppContainer/LPAC с совместимостью) либо изолированный guest с
контролируемым единственным путём. Ни один из них сейчас не доказан.

Отсутствие доказательства не равняется невозможности без-VM решения вообще.
Но исходное категорическое «можно, достаточно identity-jail» следует заменить
на условную инженерную рекомендацию. VM также не объявляется обязательной
для эксплуатации или автоматически защищённой при подключении её к сети.

## B. Verdict по архитектуре Claude

| Тезис Claude / место | Независимая оценка |
|---|---|
| SID вместо PID/EXE, §3/5 | **Согласен с принципом.** Убирает PID reuse/shared EXE из идентификации обычных прямых операций под тем же token. Не доказывает identity всех delegated operations |
| Background account, §14 Q2 | **Практически возможно без desktop switch.** `runas` не основной UX; scheduler/service startup описан в D |
| P1 не V2Ray-only, §10 | **Верно.** Доступ к любому loopback и неприкреплённый к endpoint брокер оставляют обход; P1 нельзя вводить как выполнение главного требования |
| «1–2 статических правила, нет контроллера», §4/5/10 | **Завышено.** Нужны разные family/protocol/address/port predicates, реальная поддержка SID и loopback, broker policy, состояние при boot/failure. Static kernel filters могут не зависеть от жизни installer; это не доказывает поведение при отказе BFE |
| Block ALL + Allow loopback | **Неверная общая конструкция WFAS.** Ordinary allow не является исключением из explicit block [K]. У самого Claude L2 в §5.1 написан как non-loopback complement, что логически лучше; но его работоспособность через LocalUser и P2 не доказаны |
| «SID наследуется всем потомкам», §2/6 | **Только с оговорками.** Обычный CreateProcess primary-token chain — да; alternate-token/impersonation/system-mediated requests требуют отдельного учёта. Смена identity посредника не всегда требует прав администратора вызывающего |
| «Нет DIRECT в config ⇒ не может быть DIRECT», §5.1 L3 | **Недостаточно.** Нужны exact loaded config/version/runtime paths, DNS/bootstrap/override audit и системный broker egress pin |
| R-DNS — только metadata, §6/15 | **Нарушение строгого маршрута.** При T2 DNS names способны переносить данные. Нельзя молча принять такую утечку за допустимую |
| Port owner preflight/poll, §6/13 | **Обнаружение, не prevention.** Проверка до connect имеет TOCTOU; редкий порт не является security control |
| Firewall/BFE failure — только T3, §5/15 | **Неверно исключать все такие отказы.** Сбой/ошибка profile/GPO/provider возможны без злонамеренного администратора. Их надо учитывать в T1 reliability |
| Host own-LAN-IP probe, §11/15 | **Неполный oracle.** Local delivery может классифицироваться как loopback; факт числового адреса вне 127/8 не доказывает покрытие external path. Отсутствие external packets нельзя заранее постулировать вместо независимой границы |
| Sandbox first, §8 | **Допустимый условный lab вариант.** Меньше provisioning, но mapped folders/guest integrations всё равно каналы данных и потенциального relay. Он не доказывает host policy. Не нужно спорить о VM vs Sandbox до выбора конкретного безопасного lab backend |

## C. Главное техническое решение: identities и непересекающийся deny

### C1. Что означает SID-scoped policy

Обозначения: `C` — фактический SID `wua-client`, `B` — другой SID `wua-broker`;
`P` — новый выделенный локальный TCP port; `R:Q` — один одобренный literal IPv4
remote upstream endpoint, использующий подтверждённый TCP-based V2Ray transport.
Здесь нет реальных значений, аккаунты и listeners не созданы.

```text
Текущий пользователь / обычный ChatGPT Desktop
                ↕ облачный MCP transport (свой отдельный network scope)
         tunnel-client [SID C]
           └── WUA read-only STDIO child [SID C]
                │ TCP only → 127.0.0.1:P
                ▼
         dedicated HTTP CONNECT broker [SID B]
                │ TCP only → R:Q, authenticated V2Ray transport
                ▼
         approved remote proxy → конечные MCP/control-plane destinations
```

Никакого доступа C ко всем 127/8, `localhost:*`, текущим 10808/10813 или LAN.
Защищаемые executable/config directories не writable для C, profile/output —
узкие отдельные ACL. WFP provider/sublayer/filter objects и task/service
definition доступны на изменение только доверенному provisioning principal.
Для setup потребуются отдельно разрешённые административные действия; обычный
MCP-код их не получает. Read-only MCP capabilities не заменяют OS sandbox.

### C2. Windows Defender Firewall: исправить логику исключений

Известная семантика ordinary WFAS rules [K]: explicit **Block** перекрывает
обычный **Allow**, независимо от большей специфичности порта/адреса allow и
порядка создания. Это не ACL с «сначала allow». Поэтому:

```text
Block(C, any destination) + Allow(C, 127.0.0.1:P)  ≠  нужное исключение.
```

Authenticated bypass/OverrideBlockRules — специальная конструкция, связанная
с authentication/IPsec semantics, не универсальный способ заставить обычный
локальный HTTP CONNECT пройти через Block ALL. Здесь её не рекомендуем.
Default outbound block отличается от explicit block: на фоне default block
обычное allow может разрешить traffic, но нельзя менять default всей рабочей
машины ради двух аккаунтов. При existing default allow достаточно корректных
deny-complements; явный allow требуется только если это допускает effective policy.
Existing/GPO explicit block всё равно способен запретить полезный endpoint.

Логически non-loopback complement можно задать непересекающимися адресными
интервалами. Для исключения всего 127/8 в v4 это
`0.0.0.0–126.255.255.255` и `128.0.0.0–255.255.255.255`;
для исключения только `::1` в v6 — `{::}` и `::2–ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff`.
Это математика адресов, **не готовый скрипт Firewall**. Такая P1-политика всё
ещё допускает все локальные порты и не удовлетворяет заданию. Нам нужен exact
`127.0.0.1:P`, а проще всего вообще запретить C весь IPv6 до необходимости
его отдельного разрешения; это account-scoped deny, не глобальное отключение IPv6.

`New-NetFirewallRule -LocalUser` принимает SDDL/authorization expression, не
строку имени пользователя/SID как магический process-tree selector. Наличие
параметра подтверждено CDXML [L]; его effective non-IPsec outbound scope,
Loopback behavior и policy-store merge на нужной Windows требуют [N].
**WFAS-only не выбран как доказанная реализация.** Если targeted lab подтвердит
все эти свойства, допускается более простой WFAS backend той же логической
политики; это не основание заранее обещать «1–2 rules».

### C3. Предпочтительный WFP backend, без собственного kernel driver

User-mode provisioning через Fwpm API может добавлять стандартные terminating
Block/Permit filters — собственный kernel callout driver для самого такого
filter не нужен [K; declarations L]. Это не означает, что каждую дополнительную
гарантию IPC/recipient identity можно реализовать теми же статическими filters.

Основной intended layer — `ALE_AUTH_CONNECT_V4/V6`, с
`FWPM_CONDITION_ALE_USER_ID` и адресом/портом/протоколом. Это security-descriptor
access-check condition, а не числовое сравнение PID или случайное сравнение
SID-string. Требуется правильный descriptor, matching access right и проверка
того token/identity, который используется именно данным layer. Нельзя просто
скопировать значение `FWPM_CONDITION_ALE_REMOTE_USER_ID` для идентификации
локального proxy listener: это не универсальный owner-SID удалённого процесса.

**Проект непересекающейся deny-partition [P]:**

| Principal / family | Предикат нового outbound connect | Решение |
|---|---|---|
| C / v6 | любое назначение, любой protocol | BLOCK |
| C / v4 | protocol != TCP | BLOCK |
| C / v4 TCP | remote address != 127.0.0.1 | BLOCK |
| C / v4 TCP | remote address = 127.0.0.1 AND remote port != P | BLOCK |
| C / v4 TCP | remote address = 127.0.0.1 AND remote port = P | Нет нашего deny; permit только если effective stack разрешает |
| B / v6 | любое назначение | BLOCK |
| B / v4 | protocol != TCP | BLOCK |
| B / v4 TCP | remote address != R | BLOCK |
| B / v4 TCP | remote address = R AND remote port != Q | BLOCK |
| B / v4 TCP | remote address = R AND remote port = Q | Нет нашего deny; нужен effective permit |

Таким образом нужный allow никогда не пересекается с **нашими** explicit blocks.
`!=` — логический предикат, не обещание поддержки такого comparator каждым
layer/type. Backend обязан транслировать его в поддержанные conditions/ranges/
отдельные filters, доказать domain coverage (включая protocol/port boundary
values), IPv4-mapped IPv6 и duplicate-condition semantics. Нельзя произвольно
считать повторяющиеся одноимённые conditions AND/OR без layer-specific проверки.

Другой допустимый вариант — allow-first и catch-all внутри собственной
sublayer с тщательно заданными weights/actions. Он требует больше reasoning
о прекращении classification/rights; в качестве default выбран deny-complement.
Это **не глобальное доказательство арбитража**: WFP sublayers, filter weights,
soft/hard action, `CLEAR_ACTION_RIGHT`, чужие callouts и hard permits/blocks
имеют собственные правила. Нельзя переносить «Block всегда побеждает» из WFAS
на любой произвольный WFP graph. Нужен readback **effective installed graph**
и targeted classification proof, прежде чем принимать loopback enforcement.
Константы SDK наличествуют; ordering текущего host не запрашивался.

Loopback-классификация — не только destination bytes 127/8 или ::1: self-LAN-IP
также может быть local delivery [K/N]. Проверять оба ALE family paths,
loopback flag/fast paths, self-address, mapped addresses и реальные attributed
connect attempts. Если built-in/third-party permits обходят proposed deny,
**STOP**, а не удалить чужие filters или назначить непроверенный «максимальный»
weight. Доказанного user-mode loopback backend в этой TASK не получено.

C не нужны входящие TCP servers: WUA — STDIO. Новые inbound admissions надо
ограничить отдельно на `ALE_AUTH_RECV_ACCEPT`/listen/bind там, где применимо,
а не считать outbound policy сетевым firewall для всех направлений. B принимает
только loopback TCP на P; existing accepted TCP replies не должны ошибочно
рассматриваться как новый B→C outbound connect. Эта stateful/reauthorization
семантика входит в [N]. Health/Harpoon/Unix-socket/IPC surface учитывается отдельно.

### C4. Loopback receiver и port takeover

Endpoint `127.0.0.1:P` сам по себе не идентифицирует B. Если B упал, посторонний
host process может занять порт и выполнить connect от своего неограниченного
SID. Тогда C соблюдает свою policy, а маршрут всё же обходит V2Ray.

Для T1: защищённый B executable/config, exclusive bind до старта C, проверка
SID/process generation/hash, authenticated HTTPS proxy при подтверждённой
поддержке и доверии в native client, остановка на разрыве/owner drift. HTTP Basic
proxy authentication не удостоверяет server клиенту и не решает takeover.
Периодический owner poll и случайный порт не дают строгого zero-window prevention.

Для строгой prevention (включая T2) дополнительно нужен проверенный OS guard
на bind/listen к **зарезервированному P**, запрещающий постороннему principal
занимать его, включая wildcard/IPv6 aliases и handle transfer, либо иной
доказанный recipient-bound IPC/transport. Предполагаемый user-mode WFP вариант
использует resource-assignment/listen conditions, но доступность нужных
identity conditions и арбитраж **не подтверждены**. TCP port exclusion/reservation
без соответствующего owner authorization не приравнивается к SID authentication.
Нельзя выдать дописанный в отчёт «pin listener» за установленную защиту.

Если эту дыру нельзя закрыть, строгий P2 остаётся BLOCKED. Для T2 TLS validation
внутри самого вредоносного C не является принудительной границей: он может её
игнорировать. Нужна внешняя enforcement либо более сильная изоляция.

### C5. Lifetime, boot и отказы защиты

Фильтры/provider/sublayer создаются trusted installer по owner GUID manifest
и закрытым management ACL, до первого C/B process. Policy не размещается в
dynamic session, чьё закрытие снимет deny. SDK имеет PERSISTENT/BOOTTIME flags;
это **не доказательство** их допустимости на выбранных layers, совместимости
или coverage между boot-time и persistent phase. Нельзя слепо выставить оба.

Static persistent filters потенциально устраняют зависимость запрета от жизни
launcher — полезное упрощение Claude. Но BFE stop/crash, reload, reboot, смена
профиля/GPO/third-party provider, disabled rules и existing-flow reauthorization
требуют отдельного доказательства. Poll → заметить → убить процесс оставляет
временное окно и не доказывает fail-closed. Против непреднамеренного отказа
защиты нельзя отвечать только «это администратор/T3».

При startup preflight failure C/B не запускаются. При невозможности доказать
сохранение deny на runtime failure строгая эксплуатация **не разрешается**.
Job kill-on-close помогает cleanup при правильном lifetime/handle ownership,
но не доказывает мгновенное закрытие всех flows и delegated service work.
Обновление/rollback: запрет admissions → остановить и reap только owned workers/
flows → readback их отсутствия → менять только exact owner filters/config →
снова независимый preflight. Удалять deny при живом subject запрещено.

## D. Реализация без второго рабочего стола

Для T1 и самого простого startup — две задачи Task Scheduler с principal C и B,
standard/least-privilege run level, «run whether user is logged on or not» [K].
Сначала готовность B и policy, затем C; отсутствие готовности означает отказ,
не запуск через обычную учётку пользователя. Task definitions защищены от C/B
изменений. Выбор password-backed batch logon либо S4U зависит от credential/
profile needs; «S4U без network credentials» нельзя засчитывать как universal
запрет TCP/DNS egress. LUID/logon rights/profile loading проверяются отдельно.

Для более строгого process/job lifecycle лучше небольшой trusted service
launcher; сам tunnel-client не объявляется Windows service без service-aware
wrapper. Он создаёт процессы с **primary token нужного SID** и не повышает их
до LocalSystem. `LOGON_NETCREDENTIALS_ONLY`/runas `/netonly` непригоден: не меняет
локальную process identity на требуемую. `CREATE_NO_WINDOW` скрывает консоль,
а не создаёт security boundary. API declarations есть в локальных headers [L].

Отдельный logon не требует интерактивного входа пользователя, смены desktop или
новой ОС. Session 0/background window station не предоставляют обычный browser/
prompt текущего desktop. Профиль C, окружение, working directory, executable
paths и certificate trust задаются явно; HKCU/current directory/env текущего
пользователя не должны случайно наследоваться как конфигурация C.

Native tunnel-client создаёт WUA STDIO child под C и собственные stdin/stdout
pipes в том же background tree. Нет необходимости передавать эти handles в
ChatGPT UI. Ограничить inheritable handles; при custom launcher — explicit
handle list и job assignment до resume. Service/Task Scheduler launch не
гарантирует этого автоматически. Cross-user named pipes, если нужны для narrow
control/status, имеют ACL C/B/operator, проверку caller/server identity и узкую
командную схему; они не становятся произвольным execute/fetch relay.

WUA получает лишь read-only synthetic fixture/context paths, а не доступ на
запись во весь `M:\GitHub\ag_llm`, production storage или чужие профили. Credentials
будущего tunnel — только защищённый профиль/secret store C, remote proxy secret
— B; administrator/operator — trust boundary. Нельзя класть пароль учётки,
API key или proxy secret в argv, task XML/public report или общий env. Хранение
Task Scheduler/LSA/DPAPI и обновление secret требуют отдельного provisioning GO;
ключи в текущей TASK не читались и не создавались.

OAuth/browser bootstrap, если действительно нужен, выполняется отдельно
пользователем по поддержанному flow; runtime не пытается открыть UI в Session 0.
Не угадывать native flags, отсутствие browser children или обязательность OAuth:
полный exact source пока недоступен. Auto restart после ошибки не обходит
policy/owner checks. UI остаётся под текущим пользователем.

**Граница ChatGPT Desktop:** рекомендуемый scope C/B — локальная MCP-цепочка;
обычный ChatGPT является отдельным облачным frontend под текущей учёткой.
Его трафик не начинает подчиняться C/B filters. Если «весь трафик» включает
сам Desktop/его webview/browser/helper/system DNS, эта схема **не выполняет
расширенное требование**: требуется другой согласованный app/process scope.
Перевести весь SID текущего пользователя на broker-only нельзя без влияния
на остальные приложения. Принимать это как незаметное изменение scope нельзя.

## E. Proxy и полная маршрутизация

Cached `run_help.txt` [L] описывает global HTTP proxy для control-plane/MCP/
Harpoon и отдельные component overrides; это не новый native вызов. WEB_10
в локальном 19 [C] ранее сообщил exact-tag HTTP/HTTPS-only parser и fixed proxy
на части transports. Установленный EXE при fresh baseline имеет прежний hash;
source→binary build proof всё ещё отсутствует. Проверены два адресных места
для точного runtime source archive — файл не появился; полный новый source
audit **BLOCKED**, но это не мешает настоящему архитектурному вердикту.

Ожидаемый source pack:
`tunnel-client-runtime-source-v0.0.16.tar.gz`, 239841 B,
SHA-256 `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`,
tag `v0.0.16`, commit `5f99daabd4aa4a77049e6d81d54a0d8c18335397`.
Нужен пользовательский offline handoff; скачивание агентом не разрешено.
Из ранее предложенного списка audit достаточно: runtimeconfig/proxy precedence,
transport constructors/dialers, control-plane main/secret/retry paths, MCP
STDIO/HTTP factories, OAuth, Harpoon, proxyhealth, cloudflared supervisor и
соответствующие Go resolver/crypto dependencies. Known path hints — не исходники.

### E1. Минимум компонентов

Native C → dedicated B HTTP CONNECT inbound → approved V2Ray transport.
Если exact sing-box version поддерживает этот inbound, AM07 не нужен. Его
готовый код был synthetic CONNECT-only с `.invalid` allowlist, не production
drop-in для живых хостов; нельзя просто запустить его в этом контуре.
Если реально доступен только SOCKS upstream и понадобится adapter, появляются
ещё process/identity/listener edges; это отдельное изменение архитектуры,
а не «включить пример AM07».

Shared v2rayN с меняемыми DIRECT-профилями не выбран: изменение user GUI не
должно менять security semantics C/B. Второй SID B **обязателен** для системного
pin remote egress без ограничения остальных процессов пользователя; отдельный
process на том же user SID для такого account-scoped pin недостаточен.
Existing working V2Ray не меняется. Никакого второго instance здесь не запускали.

### E2. Что требуется доказать у dedicated broker

1. Exact executable/hash/version/schema, полные argv/config/includes/env,
   прочитанные файлы и **фактически загруженный runtime state**, отсутствие
   GUI-generated overwrite, external control API, selectors/fallback/updater.
2. Только нужный HTTP CONNECT inbound, только P, exact binding/ownership; нет
   transparent/TUN/DNS/listener на произвольном интерфейсе. Доступ к config,
   секретам и reload — лишь trusted provisioning principal/B.
3. Reachable route graph, DNS и transport bootstrap используют единственный
   approved remote outbound; нет local direct/default/implicit bypass.
   `route.final = block` — не универсальный магический switch: в зависимости
   от версии это tag реально существующего outbound либо нужна другая route
   action/schema. Не публиковать непроверенный config как runnable решение.
4. B kernel egress policy допускает лишь R:Q нужного protocol. Если домен/CDN/
   rotating IP нужен для upstream, system DNS и автоматическое расширение allow
   запрещены; нужен отдельно аттестованный bootstrap/endpoint manifest либо
   согласованный стабильный endpoint. Смена R — stop + approved update, не
   «временно разрешить интернет». TLS SNI/domain identity может отличаться от
   pinned connect IP; exact transport должен поддерживать это корректно.
5. Remote server аутентифицирован допустимым протоколом/ключом/cert; один IP:port
   ещё не удостоверяет V2Ray server и его remote routing. Источник доверия remote
   — явная предпосылка. Отправка remote proxy в конечный интернет — ожидаемый
   remote exit, её нельзя путать с запрещённым **локальным** DIRECT fallback.
6. Passive independent flow/process/DNS evidence + broker loaded-config digest/
   outbound logs + при наличии независимый remote observer. Событие 5156 само
   по себе означает allowed flow, не доставленные bytes и не правильный путь
   за удалённым сервером. PID сопоставляется с generation/token, не с поздним
   process name. Нулевой журнал без coverage/loss counters не доказательство.

### E3. DNS, системные посредники и строгий fail-closed

Literal `127.0.0.1` для proxy и literal R для remote устраняют необходимость
локально разрешать **эти** адреса. CONNECT authority можно передать remote proxy
как имя без локального lookup. Это не доказывает отсутствие иных DNS paths
(health, OAuth, Harpoon, updater, trust-chain fetch, component overrides).

Собственные TCP/UDP/DoH/DoT/QUIC обходы C/B должен пресекать OS deny. Но
GetAddrInfoW/Dnscache, PAC/WPAD, certificate AIA/CRL/auto-root fetch и разрешённые
RPC/COM/broker APIs могут задействовать другой security context. **Нельзя
универсально утверждать**, что любой DNS всегда идёт от SID службы и обходит
фильтр: attribution/impersonation зависят от пути и версии. Равно нельзя
утверждать, что SID C покрыл их автоматически. ETW с initiating PID и фактическая
socket identity — разные evidence, требуются оба.

`GODEBUG=netdns=go` не принимается как доказанное решение Windows resolver:
доступность/поведение pure-Go branch именно Go 1.27/windows требуют исходников
и native проверки. WinHTTP библиотека часто работает в caller process; слово
WinHTTP не означает автоматический SYSTEM socket. BITS/COM/system broker
может выполнять действие для стандартного пользователя без передачи ему
админ-прав — доступ определяется ACL/API. Проверять конкретный emissary, а не
объявлять все такие пути T3. Блокировка direct sockets не исчерпывает IPC/data egress.

Поэтому для строгого T1 нужны подтверждённый local-only/default startup mode,
отсутствие таких delegated calls либо принудительное ограничение конкретных
доступных посредников. Для T2 — доказанный IPC/capability boundary или VM-level
изоляция. Глобально выключать DNS/BITS/CryptSvc/firewall ради задачи нельзя.

## F. Security Findings и условия STOP

Все severity ниже — влияние на заявленную гарантию, не описание уже произошедшего
инцидента. Эксплуатационных атак/проверок не проводили.

| ID | Важность / сценарий | Вывод и обязательное условие |
|---|---|---|
| F01 | CRITICAL: Block ALL/Allow exception, LocalUser ambiguity | Исправить predicate partition; подтвердить outbound/SID/layer semantics. Параметр cmdlet не является proof |
| F02 | CRITICAL: P1 или P2 без loopback enforcement | Возможен общий proxy/любой local service с собственным egress. Никакого live P1 до строгого pin |
| F03 | CRITICAL: BFE/profile/provider failure | Poll не гарантирует zero leak window. Проверить kernel enforcement lifetime, reboot/reauthorization/flows; при отсутствии proof эксплуатация BLOCKED |
| F04 | HIGH: DNS/service delegation, T1 и T2 | Прямой socket deny не покрывает весь causal traffic. DNS names могут переносить данные; запрет/attribution требуется, metadata не исключать |
| F05 | HIGH: listener takeover | После падения B клиент может попасть к другому SID на P. OS receiver/bind guard или обоснованный более сильный boundary; owner preflight недостаточен |
| F06 | HIGH: NO_PROXY/direct IPv4/IPv6/UDP/custom child transport | C/B deny должен срабатывать независимо от application flags, env и имени EXE; попытка обхода = client/config FAIL даже при успешном containment |
| F07 | HIGH: delegated child / alternate token / impersonation | Обычный child наследует token, но API к service/task/COM может делегировать. Deny interactive login не запрещает весь IPC. Не требуются обязательно admin права атакующего |
| F08 | HIGH: broker reload/CDN/bootstrap/direct | Pin actual B socket к approved authenticated endpoint; no generic DNS/remote wildcard; config absence DIRECT не достаточно |
| F09 | MEDIUM: health/Harpoon/admin surface | Cached help line 42 прямо говорит: `127.0.0.1:0` просит **ephemeral listener**, не выключает health. Unix socket тоже IPC. Выбрать source-verified disable/private endpoint policy; не угадывать флаги |
| F10 | HIGH: own-LAN-IP oracle / HNS gateway fallback | Self-address может быть loopback-classified; test не доказывает весь external path. Sandbox с доступом к HNS gateway может иметь NAT; нельзя использовать как заранее доказанную zero-egress среду |
| F11 | HIGH: caller trust/ACL/secret scope | C не должен менять policy/task/B config/executable или читать чужой профиль. SID устойчив к PID reuse, но не удостоверяет безопасный code under that SID. File replacement влияет на integrity, не снимает need OS boundary |
| F12 | HIGH: Desktop исключён из обещания без пояснения | C/B policy не управляет UI process и его helpers. Для обещания всей ChatGPT цепочки нужен отдельный явный app scope; обычный Desktop E2E всё ещё 0 доказанных вызовов этим исследованием |
| F13 | HIGH: rollback while workers/flows exist | Удаление rules/accounts «по имени» при живом subject создаёт утечку. Freeze → reap owned tree/flows → удалить только ledger-owned objects; unresolved ownership → BLOCKED |

Остановка launcher не должна удалять deny. Job handles не наследуются subjects
без нужды; не полагаться на kill-on-close, если последний handle может удержать
child. PID reuse учитывается generation/creation time в наблюдении, хотя policy
scope использует SID. Попытки включить новые tokens/helpers/addresses/ports,
event loss, effective-rule mismatch, config drift, unknown delegation, невозможность
подтвердить containment — STOP до реальных данных/credentials.

T3 (злонамеренный администратор/privileged service/ядро) вне гарантии: может менять
policy, токены, код, hypervisor. Отдельный VM на том же скомпрометированном host
не решает T3. Это не оправдание игнорировать обычный отказ security service.

## G. Сравнение альтернатив

| Архитектура | Что даёт | Непокрытый риск / выбор |
|---|---|---|
| SID + WFAS LocalUser | Простой management при подтверждённом outbound matching; обычные потомки | Runtime scope/loopback/arbitration не доказаны. Не основной готовый backend |
| **SID + user-mode WFP + dedicated B** | Точные address/protocol/port predicates; kernel policy не зависит от каждого PID; фоновой запуск | **Основной кандидат для T1.** Требует действительного loopback/bind/lifetime/mediator proof, не installation GO |
| AppContainer/LPAC | Capability/object boundary сильнее обычного account и ограничивает часть broker IPC [K] | Не автоматическая защита от всех brokers; broad loopback exemption недостаточен. Нужны ACL/runtime/cert/profile/child compatibility и exact endpoint policy. Резерв при T2 без VM |
| Windows Sandbox offline | Disposable гостевая среда для native faults; обычно проще full VM provisioning | Не готова на этом host по прежнему bounded inventory; `Networking=Disable` не отменяет shared folders/redirect channels. Writable mapped output в живом guest может стать relay. Не proof host policy |
| Hyper-V / другая VM offline | Полный guest boundary и checkpoints; независимый zero-NIC graph проще проверять | Conditional lab option, не обязательный путь эксплуатации. Live proxy-only guest требует защищённого vSwitch/gateway/host broker и proof всех каналов; «нет default route» недостаточно |
| Process-path WFP / Job / restricted token | Useful integrity/lifecycle supplements | Shared EXE, alternate-token descendants, service delegation; Job не network firewall. Не замена identity/capability boundary |
| Service SID | Может сузить trusted wrapper/service identity | Не считать автоматическим наследуемым network label произвольного service child; нужен реальный token/layer proof. Не упрощает задачу без проверки |
| GitHub Actions | Вспомогательные synthetic source/schema/Windows tests после GO | Не отражает policy пользователя, поддержка SKU/runner различается; hosted runner сам имеет network. Не proof zero-egress/native/V2Ray здесь; не запускался |

**Минимальный приемлемый fallback:** если SID-based user-mode WFP не может
доказанно ограничить loopback/mediated routes на целевой Windows, не переходить
на P1/shared v2rayN. Для native испытаний — отдельно одобренный offline guest
с доказанным отсутствием external/host relay. Для эксплуатации — либо
доказанный AppContainer/IPC+broker boundary, либо выделенный guest с единственным
enforced remote path. Это не обещание, что NAT/Sandbox с сетью безопасны по умолчанию.

## H. Минимальный следующий путь: один implementation/proof пакет

Не требуется ещё серия общих архитектурных исследований. Схема и конкретные
gaps определены; следующий отдельный USER GO может охватить **одну bounded
implementation/lab TASK** с остановками ниже. При отсутствии prerequisites
останавливается зависимый этап, а не имитируется green. Сейчас все этапы NOT RUN.

| Этап | Prerequisites / действия | Независимый PASS/FAIL oracle | Отдельный USER GO и rollback |
|---|---|---|---|
| 1 Offline source/contract | Переданный exact source pack + versioned broker schema/docs; review declarations/condition support, startup/dial/resolve/child graph | Реальные source hashes, complete config/IPC graph, supported comparator/layer mapping; mismatch/unresolved compulsory egress → BLOCKED | GO на offline package handoff/реализацию только в новой TASK folder; никаких credentials/system changes |
| 2 Synthetic policy model | Точная C/B predicate partition, evaluator с независимой enumeration/address-family/port-boundary oracle | Reject overlapping Block/Allow, all forbidden domains classified deny; negative controls действительно меняют verdict | GO на reference tests; результат **не OS proof**, cleanup только owned files/processes |
| 3 OS semantics / zero external egress | Trusted disposable isolated Windows lab; proving observer and no physical/virtual external paths **до** account/rule experiments; same target build/provider assumptions | Actual SID/flow attribution, loopback and self-IP classification, allowed P/denied other local ports, v4/v6/UDP, children, competing filters and missing rules. Negative-control bypass detected. No real public targets | GO на lab-only accounts/filters/ACL; owner GUID ledger. Не на рабочем сетевом host без независимой containment границы. Reap owned processes, restore exact baseline; no global reset |
| 4 Native local faults | Stages 1/3 + separately approved exact EXE/argv/snapshot; only internal synthetic endpoints; no real keys | Observer sees **attempts**, not only packets/FX. Proxy refusal/timeout/reset, env/NO_PROXY, redirects/retries, resolver/crypto/service work and children; bypass attempt FAIL client even if blocked | Отдельный GO на native execution после proof; power-off/stop lab, preserve first FAIL, restore owned snapshot |
| 5 Failures / recovery | Verified initial rule graph, controlled lab failure procedures | Broker/launcher death, port takeover, config drift, rule/profile/provider/BFE failure/boot/reload, existing sockets. Deny must persist; loss of observer = inconclusive/BLOCKED | Separate system-fault GO in isolated lab; no disabling working host BFE/firewall. Freeze/reap before filter rollback |
| 6 Real V2Ray route | Native/system gates passed; approved R:Q/server identity and loaded B config, user keeps keys private; separate deployment scope | Independent local B flows only R:Q + C only P + DNS/delegation evidence and authenticated upstream/remote attestation; wrong path/unknown owner FAIL | Separate live-network/hosted-activation GO explicitly lifts hold where needed; bounded duration; restore only owned config, keep deny until tree gone |
| 7 Ordinary Chat E2E | Stage 6, supported ordinary Chat host mode and tools actually exposed | Four **real** MCP calls: ping, list_capabilities, allowed read_synthetic_context, other_task refusal; independent server receipt/session/nonce/hash match | Separate E2E GO and user permissions; no SDK/reference substitution, no repeated install/@ prompts without new evidence |

Local socket witness на собственный LAN-IP может быть полезным case на этапе 3,
но не заменяет trusted offline lab boundary и оба ALE path oracles. No packet
capture alone proves syscall denial. Policy на другой Windows/CI не доказывает
effective stack пользователя; перенос на host требует scoped readback/acceptance
и нового deployment GO. Ни одна такая операция в этой TASK не выполнялась.

## I. Decision Required

Технические вопросы startup, foreground UX, SID-vs-PID и direct HTTP proxy
решены на уровне архитектуры, пользователю не передаётся список Q1–Q11 для
самостоятельного исследования.

Нужно только **решение о следующем этапе**: разрешать ли bounded implementation/
proof для предложенных C/B identities и WFP backend в отдельно изолированной
лаборатории. До него получить exact source archive и lab resource; это
материальные prerequisites, не повод запускать direct native на рабочем host.
Реальные аккаунты, admin setup, secrets, новый broker и host deployment требуют
явного отдельного GO; текущий GO их не разрешает.

По scope предлагаем защитить локальную C/B MCP-цепочку, оставляя обычный UI
пользователя. Если пользователь требует T2 или охват **самого ChatGPT Desktop**,
это отдельное существенное acceptance decision, а не неявная уступка на DNS/
loopback. По умолчанию не считать эти усиленные свойства доказанными и не
объявлять никакой live V2Ray-only результат.

## J. DOC IMPACT / SHARED DOC DELTA

Фактически: новая папка текущего отчёта + узкая ротация собственной карточки.
Общие 18/19/34/000/05/06, материалы/карточки Claude/LLM12, production, MCP
launcher, V2Ray, firewall/WFP/ACL/system policy не изменялись. Новое правило
own-card rotation уже есть в 18; повторное исправление регламента не требуется.

**Для WEB_10, точное предлагаемое добавление в 19 рядом с Claude architecture review:**

> CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001 — independent analytical review ready.
> Accept dedicated Windows identity and background noninteractive startup as
> design principles; do not accept P1 or unverified P2 as V2Ray-only proof.
> Ordinary WFAS Block ALL cannot be excepted by a normal Allow. Preferred T1
> candidate: two SIDs, disjoint user-mode WFP deny predicates, exact loopback
> endpoint and dedicated broker pinned to approved authenticated remote endpoint.
> User-mode loopback/SID/arbitration/lifetime behavior, bind/receiver protection,
> DNS/system delegation and exact source/broker startup remain open native gates.
> T2 and frontend ChatGPT scope need additional boundaries. No VM obligation
> for operation is asserted; no system/network/native operation authorized.

**Для 34, краткая CURRENT запись после независимого review:**

> Identity-egress analytical review completed; architecture conditional,
> OS/native/V2Ray/ordinary-Chat NOT VERIFIED; hosted hold unchanged. Nine Claude
> manifest entries byte/hash matched locally (not security acceptance). Next
> proposal: one scoped implementation/proof package in independently isolated
> Windows lab, exact source first, with separate native/live/E2E gates. No direct
> host egress probe or shared V2Ray change. Own Codex card safely rotated with
> history preserved; common docs/Claude/LLM12 unchanged by Codex.

Эти тексты — предложения, не внесённые изменения и не independent PASS.
Публикацию и передачу WEB_10 выполняет пользователь; агент не использовал
Git/GitHub и не отправлял сообщений в другие чаты.

## MANUAL ENGINEERING REVIEW

За один аналитический проход прослежены normal/fault пути C→B→R, alternate
token/delegation, port ownership, Windows policy lifetime, stdio/background
startup, DNS/crypto/bootstrap, existing flows, scope UI, rollback и guest channels.
Проверялись альтернативы WFAS-only, user-mode WFP, AppContainer, Sandbox и VM;
не выбирался вариант только ради согласия с прежним предложением Codex.

Adversarial counterexamples: (1) explicit block пересекается с allow; (2) C
остаётся на P, но receiver подменён и его SID выходит direct; (3) lookup/fetch
выполняется посредником вне C; (4) правила исчезают после preflight, poll ещё
не успел остановить client; (5) self-LAN-IP probe попадает в loopback path;
(6) `:0` создаёт новый listener; (7) remote IP pin соблюдён, но wrong server/
loaded route не удостоверен; (8) named pipe/shared output инициирует чужой
fetch; (9) runtime profile/env/component override расходятся с сохранённым
config; (10) rollback убирает deny при живом child или queued delegated work.

Ни один counterexample не проверялся атакой на Windows. Это объяснимые
архитектурные опровержения недостаточного аргумента, не подтверждённые incidents.
Отвергнуты тезисы «VM обязательна для всех случаев», «учётка сама даёт T2»,
«SDK константа = enforcement», «только отсутствие DIRECT гарантирует маршрут»,
«polling даёт мгновенный fail-closed». Сохраняются конкретные [N] gaps,
не маскируемые reference PASS. Ненужный тестовый suite не создавался.

## Проверки, сохранность и ротация

Новых runtime/unit/security tests **0**; Windows accounts/policy queries/native
client/Cloudflared/proxy/VM/Sandbox/network/Git operations **0**. Предыдущие
19/19, 5/5, 36/36, 22/22 suites не повторялись. Работа с SDK/CDXML — чтение файлов,
не вызов Windows security API. Первичная инспекция manifest предполагала list,
получила `KeyError: 0`; schema оказался dict, затем 9/9 hashes успешно проверены.
Ошибка чтения сохранена в `review_evidence.json`, не выдана за runtime FAIL.

Fresh baseline — **207** защищённых файлов, единственное разрешённое изменение —
own card. `card_before.md` — адресный backup; `assignment.md` — полный frozen B1.
В текущей TASK нет дополнительных AMENDMENT; команда запуска соответствует B1.
До ротации сохраняются этот полный отчёт, evidence и предварительный manifest;
после readback новых БЛОКОВ 2–3 БЛОК 1 очищается. Фактический результат —
`card_rotation.json`; итоговая сверка — `integrity.json`. Manifest затем
пересчитывается, включая rotation evidence; self hash не включён в свой список.
Это artifact integrity, не доказательство Windows/network behavior.

Откат own card: только если текущий SHA совпадает с recorded final в rotation
receipt, восстановить точные bytes `card_before.md` и проверить before SHA.
Если появились более поздние изменения — STOP/reconciliation, не overwrite.
Папку отчёта и историю при таком откате не удалять. Для будущего системного
deployment rollback описан отдельно в C5/H/F13; текущий host runtime не менялся.

## Итоговая сверка после ротации

**CARD ROTATION VERIFIED (local).** Первоначально staged БЛОКИ 2–3 были
успешно сохранены и перечитаны, но atomic replace для очистки БЛОКА 1 получил
`PermissionError / WinError 5`. Состояние проверено: B1 остался полным,
B2/B3 и вся прежняя история целы, pending candidate соответствует ровно
финальному состоянию. Выполнен **один** guarded retry только этой оставшейся
замены, без повторного архивирования, правок ACL/атрибутов, повышения прав,
принудительного завершения приложений или изменения системы. Он завершился
успешно; причина исходного отказа доступа не установлена. Первый отказ и
исходный manifest сохранены внутри `card_rotation.json` (attempt01 и
manifest_before_rotation); recovery source — `reconcile_card.py`.

B1 = `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`; полная постановка в B2, factual result в B3.
**435,048 B** предыдущей истории сохранены дословно. Правила/prefix карточки
не изменены. Before SHA-256:
`cdb45bab16b5b346d9675b38915bc3117c792ec623a07bd0b651ed59d862cbc8`;
final SHA-256:
`8f1f0705946099390147802164fc6886db94af90998e1900bfa7707e45dbca2b`.
`integrity.json` сохраняет intermediate staged hash и final readback.

**206/206** защищённых файлов вне own card не изменились (baseline 207 total).
**9/9** Claude manifest entries совпали по size/hash; прочитаны **9** Windows
SDK/CDXML файлов. Это file/static evidence, не native/System PASS. Runtime tests
**0**, прежние reference suites не повторялись; все **7** будущих этапов NOT RUN.
13 security findings — аналитические, не 13 воспроизведённых уязвимостей.
Root `.gitignore` прочитан как файл: новой report folder не касается; вложенные
reports/task `.gitignore` отсутствуют. Global/Git excludes и публикация не
проверялись. Narrow credential-pattern scan и ручной просмотр не нашли реальных
ключей/токенов в комплекте; raw configs других подключений не копировались.
