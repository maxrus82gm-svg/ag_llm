# CODEX-WUA-0-WINDOWS-LAB-GATE-001 — factual report

Исполнитель Codex 007. Дата отчёта: 2026-10-21 (Asia/Yekaterinburg); ограниченный host snapshot собран 2026-10-20. **RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11.** Независимая приёмка не объявляется. Source reference из постановки `main@1db3bb6fef333e8567e8e638690049c1198a6fef` не проверялся через Git; Git/GitHub не использовались.

Подготовлен работающий offline checker I01–I12, signed synthetic fixtures, 52-test suite с negative/mutation controls, bounded host read-only collector, частичный exact-GUID Hyper-V readback candidate и deterministic data-only dry-run plan. **Реальный gate: BLOCKED по всем 12 требованиям. Лаборатория не создана, WFP/native/network tests не проводились.**

## Разделённые статусы

```text
OFFLINE_GATE_LOGIC_TESTED
LAB_PLATFORM_NOT_PROVISIONED
HOST_CONFIG_PROOF_PENDING
GUEST_ISOLATION_PROOF_PENDING
NATIVE_WFP_EXECUTION_BLOCKED
REAL LAB I01-I12: BLOCKED (12/12)
HYPER-V VM ADAPTER: NOT RUN
NATIVE WFP / OS-HYPERVISOR ISOLATION: NOT RUN / NOT VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER
ORDINARY CHAT E2E NOT VERIFIED
```

## A. Реально проверенная среда

`adapters/Collect-Host.ps1` предварительно reviewed (`host_collector_review.json`) и **один раз** выполнен установленным PowerShell 7.6.5 без административной эскалации, policy overrides, VM enumeration или network probes. `host_readonly_inventory.json` содержит очищенные допустимые metadata:

| Факт | Результат |
|---|---|
| Snapshot UTC | 2026-10-20T18:44:45.1792843Z |
| Windows | Version10.0.19045, build19045, SKU48 (Pro), AMD64 |
| CPU | 64bit; firmware virtualization, VM monitor extensions, SLAT=true |
| HypervisorPresent | false |
| Hyper-V | System32 module не найден; module versions/exported selectors пусты; vmms/vmcompute metadata rows отсутствуют |
| Selected optional features | 10 raw InstallState codes=2; не выдаются отдельно за доказательство готовности backend |
| Адресные tool paths | Framework64 csc присутствует; virtmgmt/VMware/VirtualBox/Qemu в пяти проверенных стандартных местах не обнаружены |
| Одобренная VM | GUID/ownership не предоставлены; 0 VM queries; чужие VM не перечислялись |
| Trusted offline media | В верхнем `assets/` TASK 0 кандидатов; trusted source/hash/license не подтверждены |
| Metadata query errors | 0 |

Это bounded snapshot, не whole-host inventory и не live proof. Отсутствие инструмента в стандартном пути не доказывает отсутствие иной установки. Готовый поддерживаемый lab runtime/версия не подтверждены. Кодировка feature state сохранена raw; готовность не выводится из неё. CPU capabilities не разрешают включать Hyper-V. Никакие приватные V2Ray profiles, secrets или конфигурации неизвестных VM не читались.

## B. Что реализовано

`source/lab_gate.py`: strict JSON, deterministic typed validation, full disk-parent DAG/owner/digest cross-bindings, exact loopback endpoint contract, fresh request/host/guest/review, observer versions/hash/coverage/heartbeat/loss, config drift, rollback completeness. По каждому I01–I12 — PASS/BLOCKED/FAIL, reason, source body hashes. Missing proof→BLOCKED; authenticated negative fact→FAIL; all independently reviewed required facts→snapshot PASS. NOT RUN отдельно описывает неисполненный adapter/test, а не положительное isolation условие.

Out-of-band root pin связывает **конкретный approved request SHA-256**, три principal/public keys, helper binary SHA-256 и observers. Host/guest evidence подписаны раздельно; review подписывает их hashes и I-decisions. Managed `source/Signatures.cs`: RSA2048/e65537 PKCS#1/SHA256 verification; private synthetic keys unnamed ephemeral CNG, не экспортировались/не сохранялись. Установка crypto packages не требуется. Test-only trust отвергается real mode. Request validity≤300s, observations≤60s, heartbeat age≤1000ms; real CLI не позволяет подменить decision clock. Raw file SHA и canonical JSON digest различаются, инструкция дана в README.

Три ключа не доказывают независимость людей или истинность sensor facts. Trusted observer implementations и live controller **ещё не предоставлены**. Signatures — provenance, не OS isolation. Real PASS означает только проверенный snapshot; receipt не execution capability. `native_execution_allowed=false`, `vm_changes_allowed=false` и plan `can_apply=false` всегда, включая all-approval=true. Нет функции, применяющей план или запускающей старый WFP/installer.

`Read-HyperVApproved.ps1` — только кандидат: fixed installed module, exact approved GUID/owner/private permission raw pin/TTL и exact VM object selectors, no name fallback; running vmms prerequisite. Он не запускался. NIC/integration/disk/DVD/COM/checkpoint/assignable-device/FC/GPU selectors дают counts/aliases/core before-after digest; неподдерживаемый точный параметр BLOCKED. Полные channel/storage proofs, PSDirect/basic-console semantics, full normalized configuration, guest evidence/watch остаются false/PENDING. Даже успешный такой readback даёт PARTIAL/BLOCKED. Нет Get-VHD remote traversal, provisioning/start/stop/delete/export или гипотезы «одного Get-VMNetworkAdapter достаточно».

Data-only `plan` формирует 13 ordered actions с WHY/TARGET/BEFORE/AFTER/PRIVILEGES/VERIFY/ROLLBACK. Machine plan содержит **явно synthetic proposal parameters**, не выбранный root/VM/media. `lab_build_plan.md` детализирует default-NIC removal **до первого boot**, per-VM channel closure, backing chain, host preboot acceptance, отдельный provisioning GO с controlled baseline boot, guest observers, clean checkpoint, independent review, native GO и owned cleanup. Отсутствующая возможность закрыть канал → BLOCKED; нет глобального workaround.

## C. Реальные тесты и первоначальные сбои

| Проверка | Фактический результат / evidence |
|---|---|
| Final suite | **52/52 PASS, 0 FAIL, 0 ERROR**, `evidence/attempt08/run.json`, `tests/results.json` |
| Positive signed fixture | Все 12 I PASS в SYNTHETIC scope, native/VM apply=false; настоящий CLI вызов также 0/PASS |
| NIC mutation | Копия comparator игнорирует nic_count: **52 total, 50 PASS, 2 ожидаемых FAIL, 0 ERROR**, mutant killed; `evidence/mutant_nic03/` |
| Trust mutation | Копия real mode принимает test trust: **52 total, 51 PASS, 1 ожидаемый FAIL, 0 ERROR**, mutant killed; `evidence/mutant_trust03/` |
| Python/C# | Python AST checks; существующий Framework64 csc `/langversion:5 /warnaserror+` compile exit0, compiler diagnostics0; source/helper pins в каждом run |
| PS5.1 syntax | **2/2 adapter files, 0 parse errors**, runtime5.1.19041.6456; named-command allowlist PASS; ни один adapter этим parser не вызван |
| Actual unprovisioned CLI | exit20, **I01–I12 BLOCKED**, `gate_results.json`; provenance input/inventory SHA и limits в `checks.json` |
| Old barriers / scope | 389 protected input files до rotation без изменений; прежние portable BackendImplemented=false и WFP CanApply=false найдены обычным read; старые модули/NativePreview не импортировались/не выполнялись |

52 — test methods, не сумма assertions и не проверки гипервизора. В suite есть disabled NIC; NAT/bridge/hostonly/forwarding/passthrough; folder/clipboard/enhanced-console/PSDirect/device relay; owner/VM/boot/config/media/chain mismatch; stale/forged/pinned manifests; missing host/guest/review; zero-packets fallacy; observer loss/restart/unknown/clock; descendants; drift; rollback; strict JSON/type/path; deterministic decision; safe CLI/dry-run; all approval flags. Negative fixtures переподписываются, чтобы проверять семантику.

**Initial genuine red сохранён:** `evidence/attempt05` — 51 total, 50 PASS, 1 FAIL, 0 ERROR: signed NIC=1 + missing review ошибочно BLOCKED вместо FAIL. Исправлен приоритет; последующие 51-case и финальный 52-case прогоны PASS. Другой review finding — root не связывал approved request; добавлен request pin и 52-й regression. История ordinary runs: attempt01=42/42;02=47/47;03=48/48;04=50/50;05=50/51 red;06=51/51;07=51/51;08=52/52. Старые mutants01/02 сохранены отдельно, не прибавляются к числу независимых final controls.

PS5.1 `-File` для syntax-helper был заблокирован действующей Execution Policy. Не меняли policy/Unblock/Bypass/elevation; после отказа выполнен direct `Parser.ParseFile` command, который не исполняет adapter text. `tools/Check-AdapterSyntax.ps1` file execution поэтому **NOT RUN / POLICY BLOCKED**, а parser metadata result реально получен. Ошибка handoff assembly (искали portable flag в `.ps1` вместо `.psm1`) исправлена только в собственной TASK; immutable outputs сверены без затирания. Rejected patch/label attempts не считаются пройденными product tests.

## D. Реальные действия и открытые блокеры

VM queries/mutations=0; hypervisor/feature/driver/SDK installations=0; WFP/Fwpm/native-client calls=0; network/DNS/proxy probes=0; V2Ray/network/firewall/service/account/rights/ExecutionPolicy changes=0; Git/GitHub/messages-to-other-chats=0. Были обычные локальные CIM/file/crypto операции и сборка нового managed helper; утверждение «ноль Windows API» не делается. Все записи только новая TASK и затем штатная собственная card rotation. Работа Claude/LLM12/production не менялась.

**BLOCKED / NOT RUN:** ready exact lab host/backend; owned VM/root/ledger/quota; trusted licensed media/asset closure; actual complete channel/device/storage readback; reviewed host/guest attempts sensors; clean checkpoint/recovery; live watch/stop/admission control; реальное OS isolation и WFP execution. Current collector не производит подписанного I-proof; CNG подпись synthetic фактов не закрывает ни один из этих блокеров. Никакие Windows Firewall semantics или remote V2Ray route этим набором не проверены. Native/tunnel/E2E отдельные TASK.

## E. Manual review и следующий gate

`manual_engineering_review.md` отделяет обнаруженные ошибки от остаточных ограничений: TCB/key ceremony, sensor truth, replay/clock/filesystem TOCTOU, per-VM console/PSDirect, private ledger, runtime selector semantics, stop/rollback proof. Настоящая независимая проверка — WEB_11, ещё pending.

NEXT SAFE ACTION: пользователь выбирает отдельный уже готовый Hyper-V lab host + легитимное offline Windows media; WEB_11 проверяет комплект и конкретный plan. Будущий provisioning GO перечисляет exact owner/root/assets/quota/per-VM changes/controlled baseline boot/owned cleanup; **не включает** feature installs/host policy/reboot и native WFP автоматически. Native GO — только после всех шести prerequisites §5F, точных cases и time budget; см. `next_user_go.md`.

## F. DOC IMPACT, evidence и публикация

Нормативная цепочка прочитана локально: 08→000router→18; 01/19/34;36/36.1 и применимые36.2/36.3; прежний VM contract I01–I12 и WFP reference. БЛОК1 заморожен полностью в `assignment.md`. Общие документы и старые TASK не изменялись. DOC IMPACT: новый standalone lab kit/report + штатная ротация **только собственной карточки**, не утверждение новой общей архитектуры. После independent acceptance WEB_11 может предложить в19/34 запись: «offline I01–I12 checker tested; actual lab/containment/native WFP pending; no activation permission». Сейчас shared-doc delta — предложение, не внесённое изменение.

Обязательные артефакты присутствуют: README, source/adapters/tests/fixtures, machine contract, actual gate result, очищенная inventory, JSON/Markdown dry-run, next USER GO, manual review, checks/evidence. `manifest.json` описывает все файлы кроме себя (size/SHA256); его hash передаётся отдельно. Root `.gitignore` прочитан как обычный файл: TASK не исключена показанными правилами; Git index/global excludes не проверялись, Git не вызывался. Сырые private VM/host/proxy/secret конфигурации не публикуются; публичные synthetic RSA keys и signatures не секреты. Полная старая карточка не копируется в TASK.

Ротация выполняется **после сохранения этого полного отчёта и pre-rotation manifest**. Итоговый readback/guard result добавляется ниже и в `card_rotation.json`, `integrity.json`. Если guard обнаружит чужую правку — только rotation BLOCKED, без её перезаписи. Независимая приёмка/публикация остаются за WEB_11/пользователем.


## G. Фактически выполненная ротация и финальная сверка

2026-10-21: полная постановка сохранена в БЛОКЕ 2, factual result — БЛОКЕ 3; промежуточный вариант прочитан до очистки БЛОКА 1. БЛОК 1 теперь `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. Сохранены byte-exact **524629 байт прежней истории** и **6852 байта правил/prefix**. Два отрицательных in-memory guard controls отклоняют чужую правку карточки и подмену постановки. `card_rotation.json` содержит before/stage/final/assignment/history hashes и точный условный откат; исходный before SHA восстанавливается из prefix + assignment + history suffix. Дополнительная сырая копия старой карточки не публиковалась.

После ротации **388/388 защищённых non-card файлов без изменений**. Только собственная карточка изменилась по разрешённой ротации. `integrity.json` фиксирует проверку; финальный `manifest.json` пересобран после сохранения отчёта/receipt. Его внешний SHA передаётся отдельно. Пользователь передаёт пакет WEB_11; самостоятельная independent acceptance не заявлена.
