# CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001 — Portable Secure Deployment Kit

Codex 007 · 2026-10-20, Asia/Yekaterinburg · для независимой проверки WEB_10.

**RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
**Готовы рабочие Discovery, Plan, Contracts, static Verify, rollback planner
и synthetic tests. Реальные Install/Uninstall — явно заблокированный scaffold.**
Это разрешённый результат по §6.3/§12 постановки при недоказанном security backend,
не установленный защищённый MCP и не гарантия работы на всех Windows.

```text
DISCOVERY IMPLEMENTED / BOUNDED LOCAL READ-ONLY CHECKED
PLAN IMPLEMENTED / STATIC CHECKED
INSTALL SCAFFOLD / APPLY BLOCKED
VERIFY STATIC IMPLEMENTED / LIVE SECURITY NOT VERIFIED
ROLLBACK PLANNER IMPLEMENTED / APPLY BLOCKED / KEEP DENY
PORTABILITY CONDITIONAL / MULTI-HOST NATIVE NOT VERIFIED
OS-ENFORCED EGRESS ISOLATION NOT VERIFIED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

## Что создано

Переносимая папка **`toolkit/`** самостоятельна: относительные imports/contracts,
PowerShell и встроенный .NET, без Python/Pester/NuGet/runtime downloads.
Python в `tools/` используется только для разработки/handoff этой TASK.
Текущие Windows/PowerShell execution policy соблюдаются entrypoints; auto-elevation,
auto-unblock и flags «force insecure» отсутствуют.

| Entry point / компонент | Реальная функция выпуска |
|---|---|
| `Collect-Host.ps1`, `Discovery.ps1` | Адресное локальное CIM/file/token/policy metadata чтение; автообнаружение известных бинарников через safe local PATH/process executable paths; public inventory/coverage/plan |
| `New-DeploymentPlan.ps1` | Детерминированные JSON+MD планы, 11 staged действий с WHAT/WHY/TARGET/BEFORE/AFTER/PRIVILEGES/VERIFICATION/ROLLBACK; private local preview по явному opt-in |
| `Install-WuaMcp.ps1` | Parse/binding/approval/resume gate и понятный BLOCKED. Ни одной системной provisioning операции нет |
| `Test-WuaMcpInstallation.ps1` | Проверка content binding, отдельный static predicate invariant verifier, сравнение redacted metadata; live claims отдельно NOT RUN/NOT VERIFIED |
| `Uninstall-WuaMcp.ps1` | Strict ledger-based rollback plan, keep_deny=true; реальные stop/delete/account/WFP calls отсутствуют |
| `WuaMcp.psm1` | Strict JSON grammar/duplicate-key guard, canonical digest, type/domain validation, coverage, policies/model, plan, gate, drift/resume/rollback |
| `contracts/`, `policy/` | Полный versioned requirements/discovery contract, nonsecret operator/ledger examples и backend safety contract |
| `backends/UnavailableWfpBackend.cs` | Source-only инженерный интерфейс будущего identity/rights/ACL/WFP/startup/readback backend; CanApply=false, методы явно NotSupportedException |
| `tests/Test-Toolkit.ps1` | Работающий standalone synthetic runner без Pester, source pins, negative controls, redacted errors |

C# stub **не собирался и не является реальным WFP провижнером**. Нет P/Invoke,
Add-Type, native security DLL loading или скрытого dynamic helper. Для полноценного
user-mode Fwpm provisioning потребуется отдельно reviewed/built helper, private
host-bound ledger и target-Windows proof. Это обозначенная dependency будущего
этапа, а не требование установить новую программу сейчас. Само наличие Windows
SDK/API не засчитывается enforcement.

## Контракт полноты и фактический сбор

`toolkit/contracts/requirements_manifest.json`: **55 обязательных полей, 11 категорий**.
У каждого ID есть purpose/source/safe_read/type/validation/required/sensitivity/
statuses/stop_rule/dependent_actions. `discovery_contract.json` объясняет метрики.

| Категория | Полей | Что представлено |
|---|---:|---|
| A система | 6 | Version/build/SKU/architecture/PowerShell/library presence |
| B защита | 7 | BFE/firewall/profile aggregates/GPO-MDM presence/product count/admin token/effective policy proof |
| C identities | 3 | Technical-name collision, будущие local SID bindings, logon rights |
| D endpoint | 3 | Selected loopback endpoint, free snapshot, receiver/bind guard |
| E сеть | 5 | Adapter/family/route counts, proxy context, DNS/delegation proof |
| F broker | 6 | Binary/hash/version/schema/route graph/private endpoint/authentication |
| G MCP | 8 | Client/version/source/STDIO interpreter+script/cwd/resources/launcher hold |
| H startup | 5 | Schedule, execution policy, mode, dependencies, child identity |
| I файлы | 3 | New deployment root, desired ACL contract, actual effective ACL proof |
| J lifecycle | 3 | Ownership baseline, real ledger backend, quiescence |
| K security | 6 | SID/loopback/arbitration/lifecycle/observer/host binding |

**100% coverage здесь — 55/55 entries со статусами, не 100% обнаружения и не
100% доказанной безопасности.** MISSING/UNSUPPORTED/CONFLICT/REQUIRES_USER_INPUT
не заменяются безопасными значениями. Metadata VERIFIED означает корректное
получение/тип факта, не выполнение всех security требований. Например,
admin_token=false — подтверждённый отрицательный факт, который блокирует Apply.

Перед каждым из **трёх ограниченных реальных read-only прогонов** сохранён
source-level locality review. Перечень фактически прочитанных classes/properties
и исключённых операций — `collector_source_review*.json`. Последний release
результат — `host_discovery_release/`:

- **55/55 (100%)** полей представлены; **14** metadata VERIFIED;
- **42** requirement rows блокируют установку (включая known-negative admin token);
- Windows 10 Pro SKU 48 / build 19045 / AMD64; runtime PowerShell 7.6.5;
- BFE/MpsSvc/Schedule доступны как Running, DLL presence=true — **не WFP proof**;
- текущий token не admin; auto-elevation не выполнялось;
- найден PE_AMD64 broker, посчитаны size/hash, metadata version отсутствует;
  никакого `--version` или broker test instance;
- выбрана локальная port candidate по снимку TCP/UDP, **не** reservation/owner proof;
- interface/family/route/product/profile metadata редактированы в counts/codes,
  не экспортированы реальные addresses, SID, user/host names или private paths.

Остальные сведения честно требуют operator input/реального backend proof.
Proxy environment secret values не читаются; runtime config остальных подключений
не копируется. Рабочий v2rayN не опрашивается через control API и не меняется.
Три прогона были вызваны изменениями contract/validation/release guard в ходе
разработки; первоначальные snapshots сохранены, им не приписан более новый source.

## Автоматизация и ввод оператора

Автоматически: поддержанные метаданные ОС/процесса, service state, cache policy
presence/aggregates, token boolean, script policy, только technical-name collision,
socket-table snapshot без connect/bind, network counts, безопасные local binary
candidates/metadata hashes, coverage и draft installation/verification plans.

Оператор задаёт **nonsecret** paths при невозможности safe discovery, STDIO/cwd/
readonly roots, новый deployment root, offline native source archive, versioned
broker schema, private literal remote endpoint и authentication reference,
startup/profile choices. Нет fields для Windows password, API/proxy credential,
cookies, imported SID или произвольного права. Верификационные proof поля нельзя
заполнить «true» вместо отсутствующего executable security backend.

Public plan использует symbolic role/path references. Exact local parameters и
technical names доступны только через явный **private** `-LocalPreview`; этот
вывод не включается в публикуемый пакет. Default paths/root/user/ports текущего
компьютера не зашиты в рабочий toolkit. Synthetic C-drive paths в тестах —
не реальные чтения и не зависимость от исходной машины.

SID всегда должен происходить от **нового локального account** будущего Apply;
existing name означает CONFLICT, не adoption. Candidate names зависят от
deployment UUID/prefix; порт от explicit input либо bounded snapshot choice.
Менять их после approval без нового plan digest нельзя. Private host binding
не реализован — обязательный security BLOCKER, публичный inventory hash им не является.

## Plan, Verify и rollback

Plan связывает canonical payload + inventory + versioned config + requirements
SHA-256. Digest — защита от незаметной подмены содержимого, **не подпись**,
не доказательство operator authority и не identity компьютера. Модифицированный
план с пересчитанным digest всё равно отвергается относительно исходных inputs.

На release inventory реальный `New-DeploymentPlan.ps1` повторно построил тот же
план с 11 действиями; `Test-WuaMcpInstallation.ps1` подтвердил binding и static
predicate invariants. `verification_release.json` отдельно оставляет real SID,
effective WFP, receiver, denied endpoints, DNS, children, route и E2E недоказанными.
Рабочие entrypoints Install и Uninstall **не вызывались**; их safety functions
тестировались только синтетически, без Windows mutators.

Логика P2 — disjoint deny complement C→exact loopback TCP, B→exact remote TCP,
v6/non-TCP/other endpoints deny; прямого разрешения «любой localhost» нет.
Пересекающиеся Block ALL/Allow, пропущенный port deny и arbitrary privileges
выявляются негативными cases. Символические predicates не подменяют actual
Fwpm conditions, arbitration/loopback semantics или native fail-closed.

Ledger UUID/created_by_kit/reported_zero считаются недоверенными до independently
read-back actual objects/flows/queued work. Matching owner/plan не создаёт
дубликаты и не разрешает cleanup. Rollback планирует freeze → disable own
startup/accounts → quiesce+independent zero work → exact owned cleanup → deny-last.
Неизвестное состояние оставляет deny и ROLLBACK BLOCKED. Реального удаления нет.

## Тесты и границы подтверждения

**Финальный source-pinned PowerShell 7 synthetic suite: 62/62 PASS, 0 FAIL.**
`synthetic_evidence/attempt06_ps7/results.json` содержит cases и hashes загруженных
source files. Внутри одного case — **2048 protocol/port combinations** плюс
адресные negative cases; это не 2048 Windows tests. Один deliberately broken
loopback-any-port mutant выявлен oracle; другие malformed/tampered cases
отвергнуты. Ни сокетов, ни real install/uninstall wrappers, ни policy calls.

Покрыты: contract completeness, strict types/missing/duplicate/extra fields,
false-fact constraints, unsafe privileges/ACL, paths, portable metadata profiles,
missing/unknown components, GPO/MDM/conflict cases, SID copying, plan tamper с
перехешированием, Apply denial, independent static policy checks, repeated plan/
resume/rollback, redaction/errors, parser grammar/canonicalization, owned file
hash/invalid PE fixture и source drift check. Windows 11 — **fixtures only**.

Промежуточные suite результаты (47→55→57→60→61→62) сохранены с source hashes;
это последовательность разработки, не сумма независимых native проверок.
Предыдущие исследования 19/19, 5/5, 36/36, 22/22 не перезапускались.

**Windows PowerShell 5.1:** финальные **8/8** PS files синтаксически разобраны,
parse errors **0**, policy **Restricted**, override=false. Финальный runtime
suite/collector на 5.1 **NOT RUN**. Ранний 47-case prototype запускался с
process-only `-ExecutionPolicy Bypass` — это недостаток проверочного запуска,
явно сохранённый в checks, не рекомендуемый workflow и не PASS финального
release. Постоянные policy stores не редактировались; отдельный процесс завершён.
Дальнейшие проверки не обходили Restricted; entrypoints не имеют auto bypass.

Нельзя объявлять Windows 5.1/все Windows готовыми по parser-only результату.
Код не требует дополнительного runtime package, но требует уже разрешённой
среды исполнения. C# backend source не собирался. Полный manual/adversarial
walkthrough — `manual_engineering_review.md`; остаточные ограничения —
`known_limitations.md`.

## Safety, privacy и сохранность

По выполненным source/командам: создания accounts/ACL/rights/WFP/firewall/services/
tasks, изменения V2Ray/DNS/routes, native tunnel/broker/Cloudflared launches,
network probes/downloads, VM/Sandbox, Git/GitHub — **0**. Это не утверждение об
отсутствии фонового трафика всей машины. Допускавшиеся read-only metadata/API
чтения не засчитываются security execution proof.

Новые файлы — только эта TASK directory; дополнительно own-card rotation.
Protected baseline: **209 project files**, из них own card — единственное
разрешённое изменение; конечная сверка noncard — `integrity.json`.
External credentials/configs не читались; полные исторические card backups
не копировались в новый publish bundle. Public data — aggregates, hashes,
new deployment nonce и role refs, не hardware/host identity. Raw terminal/private
preview не публикуются. Все intermediary examples/fixtures — синтетические.

До ротации сохраняются report/evidence/manifest. Full frozen assignment и
принятые AMENDMENT (нет) — в B2, factual result — B3, prefix/history сохраняются
byte-for-byte; только после readback B1 становится ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.
Фактический receipt — `card_rotation.json`. Откат card возможен без публичного
raw backup: при совпадении текущего final SHA взять прежнюю историю suffix
длины/hash из receipt, unchanged prefix и `assignment.md`, собрать before
и проверить его SHA. При поздних изменениях STOP/reconciliation, не overwrite.

## DOC IMPACT / SHARED DOC DELTA

Фактически: новая TASK folder и узкая ротация собственной карточки. Общие 18/19/
34/000, Claude/LLM12, root code/tests/CI, production, существующий MCP launcher
и подключения не изменялись. Git source pin `a9615a135b87e933b672c25d1323a2c892e93290`
— ориентир из задания, не самостоятельно проверенный HEAD.

Предложение WEB_10 для **19**:

> Portable kit v0.1.0-offline: implemented local discovery (55 explicit required
> fields), deterministic redacted planning, static binding/policy verification,
> owned-ledger rollback planner and synthetic tests. Apply/Uninstall mutation
> backend absent and unconditionally BLOCKED. No input proof/approval flag can
> enable it. SID bindings must be newly resolved locally; no portable SID/secret
> transfer. T1 candidate only, UI excluded; OS/native/DNS/receiver/BFE/V2Ray/E2E
> remain NOT VERIFIED. Final PS7 tests 62/62; PS5.1 final AST 8/8, runtime not
> accepted under Restricted. Do not deploy from this evidence.

Для **34**:

> CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001 RESULT READY pending independent review.
> Read-only release inventory 55/55 represented, 14 metadata verified, 42 blocking
> requirements; 11-action plan rebuilt/static verified. No accounts/policy/native/
> network activation. Next: review toolkit, then one separately authorized
> isolated-lab implementation/proof package for trusted executable backend.

Это предложения, не внесённые правки и не независимая приёмка. Пользователь
публикует комплект и передаёт WEB_10; агент не отправлял сообщений в другие чаты.
Конкретные следующий gate и необходимые inputs — `next_stage_plan.md`.

## Фактическое закрытие локального исполнения

`card_rotation.json` и независимый readback `handoff_verification.json`
подтверждают: B2/B3 сохранены до очистки B1; B1 = **ОЖИДАНИЕ НОВОЙ ЗАДАЧИ**.
Rule prefix не изменён, все **463 833 bytes** прежней истории byte-exact;
из prefix + assignment.md + history suffix реконструируется исходный card SHA.
Публичная raw-копия исторической карточки не создавалась.

При втором atomic replace был WinError 5; один ограниченный retry после
повторной проверки expected card SHA завершился успешно. Права/атрибуты не
перенастраивались, процессы/Obsidian не останавливались. Финальная сверка
`integrity.json`: **208/208 noncard файлов неизменны**, own card — единственное
изменение защищённого baseline. Два первых вызова handoff integrity reader
показали ошибку locale-decoding кириллических JSON paths; исправлен только
authoring helper на явный UTF-8. Никакие исходные файлы не восстанавливались
и не переписывались для прохождения этой проверки.

Очищенный package дополнительно проверен на типичные private user paths,
machine/SID/token shapes и реальные IPv4 literals; итог —
`privacy_review_final.json`. Это bounded review, не универсальный detector
секретов; новые private inputs потребуют нового review. Root .gitignore
прочитан как обычный файл: видимые правила не исключают новые source/evidence
имена TASK. Global excludes и фактическая Git-публикация не проверялись.

Полный текущий список размеров/SHA-256 — финальный `manifest.json` (сам manifest
исключён из собственного списка). Предротационный manifest имел другой hash;
receipt сохраняет именно предротационный контрольный hash, не выдаёт его за
конечный. После добавления closing evidence final manifest сформирован заново.

Итог для копирования WEB_10 — `factual_result.txt`. Независимая приёмка,
реальная установка, OS/native fail-closed, V2Ray remote route и ordinary Chat
E2E этим локальным закрытием не подтверждены.
