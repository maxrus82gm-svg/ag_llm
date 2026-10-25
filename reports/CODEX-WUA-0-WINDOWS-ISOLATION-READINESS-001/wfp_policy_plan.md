# WFP policy plan — требования, не устанавливаемые правила

TASK: CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001. Никакие фильтры не созданы и native enforcement не проверен.

## Исходная модель и достоверность

CODE_CONFIRMED: `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/contracts/backend-contract.json` и `source/Core.cs`: candidate использует ALE_AUTH_CONNECT_V4/V6, block-only complement, восемь declarative объектов, PERSISTENT; Apply/Rollback всегда BLOCKED. ALE_USER_ID запланирован как FWP_SECURITY_DESCRIPTOR_TYPE с exact-SID self-relative DACL / FWP_ACTRL_MATCH_FILTER, а не строка SID. NativePreview/ABI не считаются применённым backend.

OBSERVED_READ_ONLY: BFE/MpsSvc Running, три Firewall profiles enabled, default actions в запросе Get-NetFirewallProfile = NotConfigured. Эффективные defaults/ActiveStore, GPO, filter arbitration и runtime block events не исследовались; NotConfigured не переводится в ALLOW или DENY. Наличие пяти fwpuclnt exports подтверждено без открытия WFP session. Права управления/фильтров неизвестны; elevation не запрашивалось.

## Не путать Firewall rules с WFP enforcement

План «broad Block для SID, затем узкий Allow» нельзя принимать как carve-out: для обычных Windows Firewall rules explicit block имеет приоритет над conflicting allow. И в raw WFP порядок — не просто последний rule или наибольший произвольно выбранный weight: layer/sublayer, action rights, hard permit и callouts требуют собственного review и native evidence. Offline candidate поэтому описывает **запрет дополнения к выбранному endpoint**, без собственного permit. Это не доказывает, что чужой фильтр не вмешается и что разрешённый edge работает.

Семантика здесь — инженерное ограничение существующего локального контракта, а не новая проверка live OS. При отсутствии разрешённого точечного native readback/effective arbitration теста общий default-deny остаётся NOT VERIFIED. Массовый dump текущих правил не разрешён и не нужен этой TASK.

## Матрица будущих ограничений

| Поток / ресурс | Target policy | Обязательный источник доказательства / gap |
| --- | --- | --- |
| C IPv4 TCP | Запрет всего кроме выбранного 127.0.0.1:P **только для существующего HTTP CONNECT варианта** | SID-bound ALE, wrong-address/wrong-port tests, loopback-specific hit/readback; export/policy JSON не доказательство |
| C IPv6 | Запрет всех адресов, включая ::1, mapped/transition paths | ALE V6 + effective dual-stack tests; IPv4-mapped IPv6 классификацию не угадывать |
| B IPv4 TCP egress | Только exact approved physical R:Q, socket владельца B engine | Primary token + independent socket/flow/process image correlation + upstream receipt. HTTP200 не доказательство |
| B wrong IP/port / alternate proxy | Запрет независимо от engine config | Endpoint complement denies + independent initiated negative probes |
| C/B UDP, raw/ICMP, secondary protocols | Никаких egress | Existing candidate protocol!=TCP intent; достаточность layers для всех типов сокетов, raw/ICMP/forwarding требует lab gap analysis, не обещание восьми фильтров |
| DNS | Нет local DNS/DoH/DoT/system resolver delegation; literal endpoints в approved plan | Проверка C/B и делегированного DNS Client service traffic. SID connect filter сам по себе не доказывает отсутствие U/SYSTEM DNS по IPC |
| C→B loopback listener | Exact address/port, exclusive B-owned bind, authenticated CONNECT; port rebind/owner theft fail-closed | Inbound bind/listen/accept scopes, ALE_AUTH_RECV_ACCEPT / RESOURCE_ASSIGNMENT/LISTEN review отдельно; текущий CONNECT-only candidate их не реализует |
| C→U NPFS | Exact authenticated pipe, не сетевой carve-out | NPFS token/DACL/peer/image/session tests; WFP не заменяет pipe ACL |
| C→B NPFS alternative | Не готов; если выбран, C TCP exception исключается после отдельного contract review | New transport design/compatibility USER GO, сегодня BLOCKED |
| Unknown processes / children с C/B SID | Те же SID restrictions, deny undeclared images/children в launcher | SID-coverage + suspended admission, child same-SID/alternate-token/job-escape tests; WFP endpoint constraint не image allowlist |
| Delegated helpers под U/SYSTEM | Не разрешать generic egress/secret/token delegation | IPC/COM/task/service/handle threat review; WFP C/B SID не покрывает сокеты U автоматически |
| Existing connected sockets/handles | Не допускать запуска до deny; отдельно выявить stale flows and inherited sockets | ALE connect-time enforcement нельзя считать retroactive revoke. Zero-work gate перед снятием deny |
| Retries/redirect/env/NO_PROXY | Только approved route, любое отклонение BLOCKED | Engine source pin, canonical config and process environment enforcement + retries/failure native evidence |
| Reboot/service crash/controller loss | Не запускать C/B без подтверждённой effective policy; keep-deny / suspended admission | PERSISTENT ≠ boot-time coverage. Startup/service ordering, BFE failure, reboot gap — отдельные gates |

Утверждённый логический CONNECT destination D:port отличается от physical upstream R:Q. Allow R:Q не ограничивает само содержимое зашифрованного proxy; CONNECT auth/target policy и upstream identity verification остаются обязательными независимыми слоями. Никаких реальных endpoint/secret значений в этом плане.

## Будущий lifecycle с запретом небезопасных переходов

1. Изолированная лаборатория без доступа к рабочему proxy/production/секретам; containment вне проверяемой guest policy. Проверить out-of-band recovery. До NATIVE EGRESS TEST network probes запрещены даже для подготовки positive control.
2. Новые local C/B SID, отдельно утверждённый trusted launcher, source/store ACL и exact approved endpoint tuple; snapshot signed inventory/ownership и scope. Нет auto-import SID/config/credentials с рабочего хоста.
3. Отдельный RULE APPLY GO; atomic transaction для exact task-owned provider/sublayer/filter set, minimal management ACL. Никаких глобальных profile changes/disable/reset. Readback типов/layers/predicates/flags/security descriptors/ownership; error/crash → не запускать C/B.
4. Admission проверяет свежесть readback и native permissions перед Resume. Concurrent policy change/reboot/engine/source drift → freeze admissions, quiesce, keep-deny. Race между readback и стартом пока не решён реализацией.
5. Только отдельный NATIVE EGRESS TEST GO: native matrix и независимый verifier. Необходимы контролируемые разрешённые и запрещённые lab endpoints; не реальные OpenAI sockets/keys. Отдельный TUNNEL START GO не выводится из успешных проб.

## Gates, которые здесь не закрыты

Native backend/ABI, effective WFP arbitration, loopback filtering, DNS delegation, IPv6/UDP/raw coverage, SID child/token escape, pre-existing flows, boot/BFE crash, precise ownership/transaction rollback, engine compatibility и physical B-owned route — NOT VERIFIED. Upstream auth-error secret leakage SECURITY BLOCKER. Разрешено только описать будущие политики; применяемых .ps1/.reg/WFP installation scripts в пакете нет.
