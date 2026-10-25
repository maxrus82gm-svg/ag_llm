# CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001 — factual report

**Исполнитель:** Codex 007. **Дата:** 2026-10-25. **Локальный итог:** PASS / BOUNDED READINESS. **Сдача:** RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12. Это готовность отчётного плана, не готовность включить MCP или утверждение native security.

## Выполненный scope и основания

Пользователь подтвердил синхронизацию локальной копии: USER_DECLARED, Git revision независимо не проверялась. B1, собственные правила и последний независимый B4 прочитаны; адресный read set и source hashes сохранены. Предыдущая strict admission имеет независимую bounded offline приёмку по локальным №19/34/B4; это provenance документации, не новая Git-проверка.

Создан только настоящий TASK-каталог: report/plans, минимальные sanitized host observations, synthetic oracle checker/tests, manifest. Нет новой runtime admission-system, setup scripts или применяемых firewall rules. Содержимое программ, конфигураций, документации и карточки не изменялось. 24 адресных исходных файла совпали по bytes/SHA до/после; это не мониторинг всего workspace/Windows.

## A. Подтверждённые факты

- **OBSERVED_READ_ONLY:** 14/14 ограниченных query groups успешно. Windows10 Pro 10.0.19045 x64, PowerShell7.6.5 Core. Current token administrator_role=false, system=false, authenticated=true; отдельный TOKEN_QUERY: elevated=false. Это не полный inventory privileges и не попытка административного доступа.
- **OBSERVED_READ_ONLY:** Get-LocalUser по exact wua-client и wua-broker вернул отсутствие обеих локальных accounts. Другие пользователи/SID не собирались.
- **OBSERVED_READ_ONLY:** BFE/MpsSvc Running; три Firewall profiles enabled=True. Default inbound/outbound values = NotConfigured в выполненном запросе. Effective defaults/ActiveStore/GPO/filter arbitration UNKNOWN; не интерпретировались как allow/deny.
- **OBSERVED_READ_ONLY:** шесть management commands доступны как metadata; Get-NetFirewallRule/SecurityFilter не исполнялись. 14/14 выбранных System32 WFP/NPFS/ACL/token/launch exports доступны. WFP session не открывалась, pipe не создавался, impersonation/identity launch не выполнялись. Export availability не доказывает права или enforcement.
- **CODE_CONFIRMED:** existing broker strict API повторно проверен на полном synthetic intent и users=[]: VALID + RUNTIME_SECURITY_UNVERIFIED и AUTH_USERS_REQUIRED соответственно; оба оставляют can_apply/can_start_tunnel=false.

Сырые usernames других accounts, SID, privilege/group dumps, реальные connection addresses, passwords/tokens/secret-store bytes отсутствуют. Evidence: [host](evidence/host_observations.json), [API](evidence/api_observations.json), [source locators](evidence/source_findings.json), [матрица](readiness_matrix.md).

## B. Что готово и что ограничивает native переход

**CODE_CONFIRMED:** Python contract проверяет объявленные SID/role/tuple/hashes, не реальный process token. WFP offline backend Apply/Rollback BLOCKED; complement-deny candidate не проверен против actual arbitration. Firewall enabled и API присутствие не заменяют default-deny proof. Все исходные ограничения сохранены.

**CODE_CONFIRMED / существенное уточнение:** existing NPFS — C relay→U server-owned MCP gateway. Gateway содержит CURRENT_USER_FIXTURE_ONLY и child запускается с parent context. Это same-user fixture, не готовая C/B cross-user установка. Accepted C→B proxy path — exact loopback HTTP CONNECT. B-owned engine должен сам владеть внешним R:Q socket, а не wrapper перед U v2rayN.

**BLOCKED:** C→B proxy NPFS adapter не реализован рассмотренными integration/contracts. Требуется решение: оставить narrow loopback HTTP CONNECT + C→U NPFS либо отдельно разработать совместимый no-TCP proxy transport. Нельзя просто заменить endpoint на pipe или разрешить новый helper без review.

**UNKNOWN/BLOCKED:** реальные C/B accounts/launcher/token rights, protected source/secret store, cross-SID peer/DACL/access, engine binary/schema/runtime compatibility, B socket owner, WFP IPv4/IPv6/UDP/raw/DNS/loopback/delegation/existing flows/boot-time guarantees и exact rollback. Ранее обнаруженный sing-box не выбран движком этой TASK; engine.family=V2Ray не менялся. Upstream authentication/error-log secret leak остаётся SECURITY BLOCKER и не устранён Python contract.

## C. Подготовленные планы

[Identities](windows_identity_design.md) описывает minimal C/B tokens, actual socket ownership, server-owned U gateway, noninteractive launcher prerequisites, handle/child/delegation и cross-SID NPFS boundary. [WFP plan](wfp_policy_plan.md) содержит IPv4/IPv6/TCP/UDP/DNS/loopback/NPFS матрицу и complement-deny vs naive Block/Allow caveat; отмечены недоказанные layers/arbitration/boot gaps. Это требования, а не применяемая policy.

[Native plan](native_test_plan.md), machine-readable native_plan.json: **18 семейств**, каждое с independent observation source, ожиданием, negative control, false-PASS risk, preparation/rollback. **Все NOT RUN**, реальных probes=0. Варианты внутри семейства не выданы за выполненные тесты. Timeout/no receipt/CONNECT200/reported zero не считаются достаточными оракулами. Для NPFS/auth/config/boot требуются особые native observers; generic synthetic egress helper их не реализует.

[Rollback](rollback_plan.md): freeze admissions, independent zero processes/flows/handles/delegated work, trusted ownership/readback/CAS, exact owned cleanup, deny removal last. При unknown KEEP DENY. Нет global reset или восстановления рабочего proxy из массового snapshot. Реальное безопасное восстановление ещё BLOCKED; не обещана проверенная гарантия.

Разрешения разделены: READ_ONLY (текущее), LAB_SETUP, RULE_APPLY, NATIVE_EGRESS_TEST, TUNNEL_START. Одно не включает другое; lab setup не создаётся этим отчётом. Native probes требуют независимого outer containment и отдельного GO.

## D. Реальные проверки и counts

| Проверка | Фактический результат |
| --- | --- |
| Targeted Windows observations | 14/14 groups OBSERVED, 0 blocked query groups; exit0 |
| Selected DLL exports | 14/14 present; WFP/NPFS API calls0; current-token query read-only |
| Первый offline RED | 26 methods:25 PASS,0 FAIL,1 ERROR(TypeError),0 SKIP; exit1 |
| Engineering review RED | 28 methods:26 PASS,2 FAIL,0 ERROR/SKIP; exit1 |
| Review intermediate | 28 methods:27 PASS,1 FAIL(fixed rejection code),0 ERROR/SKIP; exit1 |
| Final offline GREEN | 28/28 PASS,0 FAIL/ERROR/SKIP; exit0 |
| Executed mutation controls | 3/3 caught, включены в28; каждый inner1 expected assertion FAIL,0 ERROR |
| Existing broker API reuse | 1 method внутри28: valid intent stays BLOCKED; empty users rejected |
| Syntax | 6 Python files ast.parse +1 PowerShell AST; errors0 |
| Protected inputs | 24/24 bytes/SHA unchanged |
| Native network/NPFS/process probes | 0;18 planned families NOT RUN |

28 =25 ordinary checks +3 controls; первый RED имел26, после engineering review добавлены2. Прогоны перекрываются, counts не складывать как уникальные тесты; прошлые suites не перезапускались. Existing broker pure API повторён без legacy native Harness/import. [Checks](checks.json) содержит команды/exit/counts/limits. [RED](evidence/red_tests.json), [GREEN](evidence/green_tests.json), [repair](evidence/oracle_repair.json) сохранены. [Review repairs](evidence/engineering_review_repairs.json) фиксируют два дополнительных пробела oracle и промежуточный FAIL; они устранены без изменения runtime code.

Первый новый oracle принимал set-membership до type check поля kind, что давало TypeError на list/dict. Исправлен type guard, исходная failed evidence сохранена. Полный pre-fix source отдельно не snapshot-ился: сохранены точные фрагменты исправления, selector/trigger/exception; pre-fix hash не заявляется. Helper выдаёт только OFFLINE_CONSISTENT, native_verified=false, can_apply=false, can_start_tunnel=false; это не аутентификация native receipt.

Audit hook Python tests запрещает socket/registry/subprocess и запись вне TASK; blocked attempts0. Он не OS sandbox и не native fail-closed evidence. Publication scan — ограниченная эвристика приватных paths/keys, не полный secret detector. Manifest включает все файлы пакета кроме себя; bytes/SHA проверяются finalize.py --verify. [Manual engineering review](manual_engineering_review.md) выполнен отдельно от тестов.

## E. Статусы и следующий gate

```text
PASS / BOUNDED READINESS (report preparation only)
LOCAL ONLY / GITHUB NOT YET VERIFIED
AWAITING INDEPENDENT VERIFICATION WEB_12
engine.family=V2Ray
can_apply=false
can_start_tunnel=false
install_uninstall=BLOCKED
STRICT_ADMISSION_BLOCKED
HOSTED_TUNNEL_ON_HOLD_BY_USER
CROSS-SID NPFS NOT VERIFIED
WFP NATIVE ENFORCEMENT NOT VERIFIED
B EGRESS OWNER NOT VERIFIED
REAL CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
ROLLBACK EXECUTION BLOCKED / KEEP DENY
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

Пользователь публикует только эту TASK-папку и передаёт WEB_12 report/manifest для независимой проверки. Никаких Git/GitHub операций или отправки в другой чат исполнителем не выполнялось. [DOC IMPACT](DOC_IMPACT.md) содержит предложения №19/34/06; документы/карточка/001 не изменены и не ротированы по текущим правилам owner-closeout.

NEXT USER DECISION: transport C→B; отдельно approved isolated lab/outer containment; engine/source compatibility и исправление upstream secret boundary. Затем, если пользователь решит продолжать, отдельный ограниченный LAB_SETUP GO с конкретным ownership/rollback планом. Это **не запрос** на немедленную активацию и не разрешение native/tunnel tests. До новой разрешённой реализации и независимой приёмки security gates остаются закрытыми.
