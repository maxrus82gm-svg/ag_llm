# Windows identities — проект, без установки

TASK: CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001. Target requirements ниже — не факты настройки хоста. Native isolation NOT VERIFIED.

## Наблюдение и граница реализации

OBSERVED_READ_ONLY: оба точных имени `wua-client`/`wua-broker` не найдены локальным Get-LocalUser; текущий token не elevated и не состоит в активной administrator role. Сырые SID и остальные пользователи не собирались. Права будущего launcher не проверены и не предоставлены.

CODE_CONFIRMED: security_contract.py проверяет объявленные SID/roles/hashes. Это проверка данных, не OpenProcessToken и не создание logon session. broker.py не устанавливает accounts, WFP, credentials или engine. Existing NPFS gateway явно проверяет `client_sid == CurrentSid()` / `CURRENT_USER_FIXTURE_ONLY`; это **same-user fixture**, а не доказанная cross-SID схема.

## Три владельца, две новые identities

| Роль | Будущее назначение и права | Запрещённое делегирование | Независимое доказательство перед запуском |
| --- | --- | --- | --- |
| C / wua-client | Dedicated local SID; read/execute только pinned relay/client; минимальный scratch; read-only MCP data по scoped IPC | Нет admin, реальных proxy secrets, изменения source/config/ACL/WFP; нет внешних socket | Trusted observer держит process handle и читает primary token SID, image provenance и job ancestry до Resume |
| B / wua-broker | Другой новый local SID; actual approved engine image; read только собственного protected upstream secret/config | Нет передачи egress пользовательскому v2rayN, произвольного child/helper, DNS/UDP/secondary route | Владелец реального внешнего R:Q TCP socket = B engine, а не launcher/wrapper; local listen owner и boot-time launch chain отдельно |
| U / пользовательский gateway | Уже существующая server-owned MCP data boundary; read-only tools, без переноса Python asyncio под C | Не принимать команды запуска/пути/credentials от C; не служить generic network broker | Pinned gateway image/worker и ограниченный tool allowlist; C не получает U token/handle |

Новые SID генерирует Windows при будущей явно разрешённой установке; SID из чужого компьютера не переносить. Отсутствие accounts сегодня означает отсутствие подготовленной C/B boundary, но не ошибку read-only проверки. Реальные engine hashes, upstream IP/port и secret references сейчас не собирались и не выбирались.

## Запуск и token boundary

Нужен отдельно спроектированный доверенный launcher/service в noninteractive session, без второго рабочего стола. UI launcher не должен молча использовать свой token при ошибке C/B logon. Точные logon type, service account rights и API (CreateProcessAsUser/CreateProcessWithToken либо иной поддерживаемый путь) требуют отдельного scope и проверки прав: одного наличия export недостаточно. Не выдавать SeDebug/SeTcb/SeImpersonate C/B ради обхода peer-check. Отсутствие этих привилегий ещё не установлено для несуществующих accounts.

Будущий порядок: trusted source/ACL pins → WFP deny/readback и lab containment → suspended child с правильным primary token → job / explicit handle allowlist → независимая token/image проверка → Resume. Если любой шаг не доказан, не запускать. Минимальная среда без proxy override/NO_PROXY/reload/credential variables; защищённая secret delivery вне argv, environment и общих logs. Секреты не передавать C и не копировать в отчёт.

Обычные дочерние процессы наследуют security context запускающего; это не достаточный sandbox. Все процессы с C/B SID должны подпадать под policy, а не только один image path. Job kill-on-close — lifecycle, не сетевой фильтр и не запрет alternate credentials. Запретить delegation/смену token, task/service/COM helpers под U; провести отрицательные тесты descendants и уже существующих/дублированных handles. C/B не могут изменять доверенные binaries/parents/config/store/startup. Против локального administrator эта схема в текущем T1 контракте гарантии не даёт.

## Два разных IPC пути — обязательное решение

1. **Реализованный fixture C relay → U MCP gateway через NPFS.** Relay STDIO↔pipe, RPC limits/HMAC/session/replay checks, peer PID/SID/image checks с held process handle. Gateway: exclusive pipe instance, remote clients rejected, protected exact-SID DACL; restricted handle inheritance, suspended SDK child и job assignment перед Resume. Результат предыдущей fixture не переносится на разные SID.
2. **Существующий контракт C → B HTTP CONNECT на 127.0.0.1:P.** Только этот exact loopback endpoint оставлен в security_contract / WFP offline candidate. B → exact literal R:Q TCP. Loopback C→B не является внешним egress C, но требует доказать правильного B listener и auth. Никакие живые P/R/Q не утверждены этой TASK.
3. **C → B через NPFS как замена HTTP CONNECT — не реализовано.** Existing MCP pipe не транспортирует proxy protocol tunnel-client→engine. Нельзя объявить совместимость Go HTTP proxy с pipe по наличию NamedPipe API. Новый adapter/helper меняет process/child/IPC contract; нужен отдельный USER DECISION/source scope, без автоматической установки.

Текущий минимальный вариант для рассмотрения: сохранить узкий C→B loopback HTTP CONNECT, NPFS использовать только для C→U MCP. Если требуется абсолютно no-TCP под C, вариант BLOCKED до отдельной разработки совместимого proxy transport. Решение пользователя не подразумевается в этой сдаче.

## NPFS / ACL требования будущей cross-SID версии

- Pipe server создаётся доверенным U (или B для отдельно разработанного B protocol); exact namespace, exclusive first instance, reject remote clients. Не подключаться к UNC pipe. DACL разрешает нужные data/synchronize/read-attributes C, нужные management права server/installer; не generic Everyone/Users write. FILE_CREATE_PIPE_INSTANCE нельзя получить через слишком широкую маску.
- Peer проверять по kernel-reported PID → held process handle → primary token SID + trusted image binding, оба направления. Same-SID unauthorized image отдельно отклоняется; SID-only ACL недостаточно. Проверить доступ QueryLimitedInformation/Synchronize/TokenQuery между C и U/B без SeDebug и без impersonation выше Identification. Текущие native peer checks ещё не испытаны cross-user.
- Не расширять single-SID fixture DACL вслепую: ownership/READ_CONTROL, server access, integrity labels, restricted tokens и реальные AccessCheck outcomes нужно проверить в lab. Наличие Get-Acl/AccessCheck export — лишь capability discovery.
- Protected grant provisioning не равно fixture env `WUA_NPFS_GRANT`; доказать изоляцию выдачи, lifetime/revocation, session binding и отсутствие inherited secret handles. Не записывать grant в manifest.
- C/B без записи binaries/config/store и родительских каталогов; file/reparse/TOCTOU, replacement после hash и already-open handles — отдельные gates. Source pin подтверждает bytes на момент чтения, не доверенную загрузку или ACL.

## Блокировки реализации

BLOCKED: accounts/launcher/credential store/source protection/cross-SID peer access отсутствуют или не доказаны. C_TO_B_NPFS_TRANSPORT_NOT_IMPLEMENTED; TRANSPORT_DECISION_REQUIRED. Фактический владелец upstream socket B, engine compatibility и upstream auth-error secret safety NOT VERIFIED. Никакое из перечисленного не исправлено изменением production в этой TASK.
