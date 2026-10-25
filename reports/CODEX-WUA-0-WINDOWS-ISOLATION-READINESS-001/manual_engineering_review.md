# MANUAL ENGINEERING REVIEW

Выполнен основным Codex 007, отдельно от автоматических проверок. Это self-review, не независимая приёмка WEB_12.

## Изученные ветви

broker strict_preflight → existing parser/canonical/schema → security.validate → validate_admission → permanently blocked native gates. Результат VALID/policy_route_allowed=true не разрешает запуск. Positive и users=[] rejection повторены через этот API; новый runtime broker/Go parser не создан.

Gateway fixture Main → same current SID guard → protected single-SID DACL → exclusive remote-reject pipe → client PID/held process/token/image → wire grant → Identification-only RunAsClient → suspended SDK CreateProcess, explicit handles, job-before-Resume. Relay проверяет server PID/SID/image и использует ограниченную маску pipe access. Это полезные механизмы, но CurrentSid guard и parent-token CreateProcess показывают, что готовой cross-SID installation здесь нет. Никаких native NPFS calls или builds в текущей TASK.

WFP backend contract → block-only complement / two connect layers → no direct Apply/Rollback. Декларативное исключение tuple не аутентифицирует listener, не предоставляет разрешение и не покрывает доказанно delegated U/SYSTEM DNS, existing flows, boot gap либо foreign hard permit. Core.cs simulation не native enforcement.

## Проверенные альтернативы и контрпримеры

- «Раз есть pipe, значит C→B no-TCP готов» отвергнуто: pipe — другой protocol/peer, C→U MCP. Сохранять existing loopback или отдельно разрабатывать B adapter — решение пользователя, не скрытая смена архитектуры.
- «Firewall включён, значит default-deny действует» отвергнуто: наблюдались только profile values, NotConfigured не resolved policy. Management command/export не тест применимости.
- «C/B SID в JSON и engine.family=V2Ray доказывают owner» отвергнуто: нужны реальные token/socket/image и exact engine compatibility, wrapper под B с U-owned engine недостаточен.
- «Timeout = deny», «CONNECT200 = B route», «reported zero = safe removal» отвергнуты. Offline oracles требуют самостоятельные initiation/control/decision/receiver/lifecycle сведения; даже корректные строки source и boolean flags — лишь синтетическая consistency, не аутентифицированная native evidence.
- «PERSISTENT = fail-closed при загрузке» отвергнуто: startup/BFE/boot-time gaps и existing sockets требуют отдельного контроля. Deny removal при unknown запрещён, безопасный rollback включает остановку admissions и quiescence.
- «Широкий Block плюс Allow исправляет Windows Firewall» отвергнуто как базовый carve-out. Reviewed complement candidate не объявлен достаточным для raw WFP arbitration.

## Собственный новый код и edge cases

collect_readonly.ps1 ограничен двумя exact account names, двумя services, тремя profiles и шестью command metadata checks. Ошибки запроса не превращаются в отсутствие account, кроме ObjectNotFound. Нет registry/network/secret dumps, elevation, management sessions, listeners или rules. observe_apis.py загружает только системные DLL через System32 search; WFP/NPFS symbols не вызываются. Current token открыт с TOKEN_QUERY, handle закрывается finally; реальные identity/SID/privileges не печатаются. PowerShell script parser и Python syntax проверяются до сдачи.

В oracle parser найдена ошибка типа kind=list/dict: set-membership вызывал TypeError. Первый RED сохранён (26 methods:25 PASS,1 ERROR); добавлена type(kind) is str проверка. При отдельном review найдены ещё два пробела: quiescence без effective readback и DENY для чужой U/wrapper роли. Добавлены2 теста: review RED28=26 PASS/2 FAIL; после исправления intermediate28=27 PASS/1 FAIL показал изменение фиксированного ALLOW rejection code. Сужение новой role-проверки до DENY сохранило прежний B_ROUTE_UNPROVED. Итог GREEN28/28. Все неуспешные результаты сохранены. Cases stale/mixed run, incomplete window, same-source claims, wrong owner, existing receiver payload, bool-as-count, surviving handles/work, malformed inputs и caller promotion проверены. Три executed mutants демонстрируют, что rejection oracle ловит удаление provenance gate, подмену U owner на B и ложный zero-work. Это tests нового review helper, не Windows attack simulation.

Audit hook процесса tests блокирует Python socket/registry/subprocess и записи вне TASK; заблокированных попыток 0. Это контроль данного Python процесса, **не OS sandbox** и не обещание изоляции ctypes/native-кода. Новые тесты не вызывают observe_apis/PowerShell/WinDLL; существующий broker import и pure function переиспользованы без legacy native Harness.

## Открытые риски / review outcome

1. Нет C/B accounts, trusted launcher, protected config/secret store и independent native observers. Cross-SID access может потребовать разрешённых narrowly scoped process rights; повышать C/B privilege ради теста нельзя.
2. Engine actual binary/schema/runtime owner, upstream secret logging, WFP loopback/delegation/IPv6/raw/boot-time coverage и exact rollback неизвестны. Эти blockers вынесены в matrix/plans и не скрыты за offline PASS.
3. Native evidence signature, origin/freshness attestation и special NPFS/auth/config/boot observers ещё не реализованы. offline_oracles.py не verifier и не исполняет cleanup. Не использовать OFFLINE_CONSISTENT как USER GO.
4. Protected hashes охватывают 24 адресных input files, не весь workspace и не состояние Windows. Не заявлять по ним отсутствие чужих concurrent edits или побочных служебных cache writes Windows при чтении.
5. Наличие хостовых возможностей достаточно для scoped readiness report, но не для native readiness. Итог self-review: PASS / BOUNDED READINESS; security activation BLOCKED, independent acceptance pending.
