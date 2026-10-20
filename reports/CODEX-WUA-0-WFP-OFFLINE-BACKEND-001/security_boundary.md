# Security boundary — current code and unproved assumptions

**Нынешняя граница — граница доставки/исполнения исходного OFFLINE-пакета,
не OS-enforced egress isolation.** Ни текущий пользователь, ни ChatGPT Desktop
не получают никаких новых Windows rules, accounts или прав.

## Три независимые части

1. Core/Abi — pure managed policy/data/memory operations; P/Invoke declarations 0.
2. OfflineTests — единственный executable entrypoint, только фиксированный
   synthetic selftest. Любая иная команда, включая `apply`, exit 20 / BLOCKED.
3. NativePreview — compile-only отдельная DLL: internal classes, exported types 0,
   executable entrypoint отсутствует, нет assembly reference из Core/Abi/Tests.
   В тестах metadata прочитана через `ReflectionOnlyLoadFrom`, не execution load;
   native fwpuclnt imports не вызываются. System32-only DLL search задан для
   будущего источникового кандидата, не испытан вызовом Windows API.

Рефлексия/привилегированный пользователь могут намеренно выполнить internal
код DLL; C# visibility не является sandbox. Данный пакет не защищается от
такого T2/администраторского запуска и не предоставляет его как workflow.
Отсутствие native call path в нынешних entrypoints подтверждено source + assembly
metadata; это не whole-host network/API trace, не OS-level изоляция compiler.

## Математическое намерение policy

Для каждой охваченной identity четыре BLOCK predicates:

| Family | Conditions после exact ALE user descriptor |
|---|---|
| IPv6 | любые исходящие connect attempts |
| IPv4 | protocol != TCP |
| IPv4 | TCP и address != согласованный address |
| IPv4 | TCP, address == согласованный, port != согласованный |

Предикаты внутри одной role не пересекаются. Client candidate edge — только
TCP `127.0.0.1:P`; broker edge — TCP `R:Q`. На selected edge **нет собственного
permit**: он остаётся unmatched, а фактическая доступность определяется Windows
и другими filters. Нельзя переносить этот результат модели на WFP arbitration.
Вес 256 — фиксированная сериализуемая metadata, **не доказательство приоритета**.

## Данные SID / provenance

Parser принимает canonical SID shape локального account, reject well-known /
built-in RID / overflow / leading zeros. C и B различны, machine prefix совпадает,
UI SID исключён. Это проверки синтаксиса и согласованности synthetic inputs;
нет LookupAccountSid, account creation, token query или доказательства нового
локального происхождения SID. UI/domain/AAD/другие identities потребуют отдельного
расширения и proof; нельзя угадывать SID или silently reuse старый account.

ALE condition использует `FWP_SECURITY_DESCRIPTOR_TYPE`, self-relative SD с
одним ACE `FWP_ACTRL_MATCH_FILTER` для SID. Нативная семантика AccessCheck,
restricted tokens, group membership, service impersonation и loopback на
target Windows **NOT RUN**. No-liveSD parser validation не заменяет эти проверки.

Host/inventory digest, owner UUID, providerData и ledger — content references.
Они не являются подписью, authenticated local authority или доказательством
lineage. Их нельзя использовать для принятия/удаления чужого Windows object.

## Остаточные blocking gates

| Gate | Почему не решён исходниками |
|---|---|
| ALE comparators/layer support | SDK содержит enum NOT_EQUAL, но не доказывает допустимость каждой condition/type/match комбинации на layer |
| IPv4 value byte order | ABI использует numeric host-value candidate; смысл Windows classifier должен сверить независимый lab observer |
| Listener ownership / port takeover | Exact `127.0.0.1:P` не аутентифицирует процесс-получатель и не резервирует порт |
| Foreign filters / arbitration | Нет live effective graph, callout knowledge и доказанной soft/hard permit/block precedence |
| Existing flows / reauthorization | Наличие будущего filter не доказывает прекращение уже установленных flows |
| Persistent / boot / BFE | Persistent flag не доказывает boot-time coverage или безопасность BFE stop/restart |
| Children / identity change | Тот же SID покрывается намерением rules; изменённый SID и delegated SYSTEM operation могут их обходить |
| DNS / BITS / COM / services | UDP under C/B модель запрещает, но системный resolver/IPC proxy действует под другой identity |
| Broker correctness | Один R:Q не доказывает V2Ray remote identity, отсутствие DIRECT внутри profile или отсутствие маршрута через посредника |
| Trusted controller / ACL | Object ACL source input в preview не является проверенным минимальным ACL; создание и независимый readback controller authority отсутствуют |
| Rollback quiescence | reported_zero не доказывает отсутствие процессов, flows, queued/delegated work; delete BLOCKED |
| Multi-host/runtime | Проверены x64 .NET managed tests/ABI compilation, не native Windows 10/11 security; x86/ARM64 не поддержаны |

Все перечисленные гарантии остаются BLOCKED/NOT VERIFIED. Класс `Admission`
показывает причины, но никакой набор ClaimedTrue не снимает release BLOCKED.

Native stage/readback source не является готовым installer: он не читает effective
graph, не создаёт identities, не обеспечивает flow draining и не запускает child.
`RemoveCandidate` всегда отказывает. На working Windows ничего из этого не применять.
