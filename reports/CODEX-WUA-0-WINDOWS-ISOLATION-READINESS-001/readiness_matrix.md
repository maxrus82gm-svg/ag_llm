# Readiness matrix

TASK: CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001. Classifications describe evidence origin, not permission. Timestamped host facts apply only to this observation window.

| ID / область | Класс | Факт / предел вывода | Готовность следующего этапа |
| --- | --- | --- | --- |
| R01 Sync gate | USER_DECLARED | Пользователь: «Да, локальная копия синхронизирована»; evidence/sync_gate.json. Git revision независимо не проверялась | Gate подготовки удовлетворён; не attestation коммита |
| R02 OS/shell | OBSERVED_READ_ONLY | Windows 10 Pro 10.0.19045 x64, PowerShell 7.6.5 Core x64; host_observations shell/os | Только capability snapshot, не security certification |
| R03 Current token | OBSERVED_READ_ONLY | Administrator role=false, system=false, authenticated=true; current token elevated=false отдельно GetTokenInformation | Elevation/administrative operations не запрашивались |
| R04 C account | OBSERVED_READ_ONLY | Exact wua-client: exists=false | BLOCKED: identity не provisioned; создание требует LAB_SETUP |
| R05 B account | OBSERVED_READ_ONLY | Exact wua-broker: exists=false | BLOCKED: B-owned engine пока не может быть подтверждён |
| R06 BFE/MpsSvc | OBSERVED_READ_ONLY | Обе службы Running | Наличие служб ≠ applied WFP rules |
| R07 Firewall profiles | OBSERVED_READ_ONLY | Domain/Private/Public enabled=True; inbound/outbound NotConfigured в данном запросе | UNKNOWN: effective policy/defaults/ActiveStore/GPO; full rules не читались |
| R08 Management commands | OBSERVED_READ_ONLY | Get-LocalUser, Get-Acl, Get-NetFirewallProfile/Rule/SecurityFilter, Get-Service доступны | Command metadata, не proof management rights; Rule/SecurityFilter НЕ исполнялись |
| R09 WFP APIs | OBSERVED_READ_ONLY | 5/5 selected fwpuclnt exports доступны; engine session не открывалась | UNKNOWN: effective access, policy, ABI/transaction/application |
| R10 NPFS/ACL/token APIs | OBSERVED_READ_ONLY | 3 kernel32 +6 advapi32 selected exports доступны; только current-token query вызван | UNKNOWN: cross-SID access, actual DACL/token semantics |
| R11 Admission | CODE_CONFIRMED | Existing strict_preflight reused: synthetic valid intent → RUNTIME_SECURITY_UNVERIFIED; users=[] → AUTH_USERS_REQUIRED | STRICT_ADMISSION_BLOCKED; can_apply/can_start_tunnel=false |
| R12 SID validation | CODE_CONFIRMED | security_contract.py validates SID strings/process role declarations; identities_proven=false | BLOCKED: real logon/launcher/token/credential store отсутствуют в этом контракте |
| R13 C→B transport | CODE_CONFIRMED | Approved offline shape: HTTP CONNECT exact 127.0.0.1:P; B physical R:Q | Требуется USER DECISION о loopback vs new NPFS proxy transport; live P/R/Q не собраны |
| R14 C→U NPFS | CODE_CONFIRMED | Existing Gateway CURRENT_USER_FIXTURE_ONLY; relay peer PID/SID/hash, protected DACL и Identification checks | BLOCKED: same-user fixture не cross-user C→U proof |
| R15 C→B NPFS proxy | BLOCKED | Existing pipe implements MCP STDIO transport, не tunnel-client HTTP CONNECT adapter | C_TO_B_NPFS_TRANSPORT_NOT_IMPLEMENTED; отдельный design scope при выборе |
| R16 WFP backend | CODE_CONFIRMED | Existing offline contract block-only endpoint complement; Apply/Rollback BLOCKED | Native backend / ABI / readback / foreign arbitration NOT VERIFIED |
| R17 DNS/UDP/IPv6/loopback | UNKNOWN | Декларативные запреты и выбранные ALE layers не доказывают delegate DNS, mapped IPv6, raw/ICMP, inbound/bind и loopback behavior | BLOCKED: отдельная isolated native matrix и observers |
| R18 B egress owner / engine | UNKNOWN | Работающий engine и его sockets не инспектировались; ранее документирован sing-box under v2rayN, family остаётся V2Ray | Не выбирать/запускать engine; actual B socket owner NOT VERIFIED |
| R19 Source/store/auth boundary | BLOCKED | №19 §§7.7–7.8: upstream auth-error leak SECURITY BLOCKER; Python refs не store ACL/secret delivery | Native real-credential/auth и tunnel не разрешены |
| R20 Lab/recovery | UNKNOWN | Lab availability/outer containment/reboot/zero-work rollback не исследовались и не созданы | LAB NOT READY FOR ADMISSION; unknown не означает «lab отсутствует» |
| R21 Prepared plan | CODE_CONFIRMED | 18 future families с observers/negative controls/false-PASS/preparation/rollback; separate GO gates | Offline report readiness only; 18 NOT RUN, actual probe count=0 |
| R22 Verification status | BLOCKED | Independent current TASK review ещё не проводился | AWAITING WEB_12; ORDINARY CHAT E2E NOT VERIFIED |

Подтверждённые source locations и их hashes: evidence/source_findings.json. Scoped input hashes до/после: evidence/protected_inputs_*.json. В R15 BLOCKED обозначает отсутствующий транспорт по рассмотренным существующим integration/contracts, а не исчерпывающий поиск всего диска.
