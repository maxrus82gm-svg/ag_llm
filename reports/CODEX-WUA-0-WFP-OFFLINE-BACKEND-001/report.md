# CODEX-WUA-0-WFP-OFFLINE-BACKEND-001 — защитное ядро MCP, OFFLINE

Codex 007 · 2026-10-20 · independent verifier: **WEB_11**.

**RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Подготовлен и собран самостоятельный C# WFP backend-кандидат: typed contract,
policy builder, managed native-ABI/marshalling/readback и отдельный неактивный
Fwpm source preview. Финальная offline suite **62/62 PASS**, C++ SDK layout
gate **22/22 compile-time assertions**. **Это не готовый системный installer.**

```text
OFFLINE LOGIC / SOURCE / BUILD VERIFIED — BOUNDED LOCAL CHECKS ONLY
NATIVE WFP ENFORCEMENT — NOT RUN / NOT VERIFIED
REAL HOST SECURITY — NOT VERIFIED
V2RAY REMOTE ROUTE — NOT VERIFIED
ORDINARY CHAT MCP E2E — NOT VERIFIED
HOSTED TUNNEL — NOT STARTED / USER HOLD PRESERVED
INSTALL / LIVE ROLLBACK — BLOCKED
INDEPENDENT ACCEPTANCE — PENDING WEB_11
```

## Постановка, scope и источники

Пользователь исправил размещение задания: при первом чтении собственный БЛОК 1
был WAITING, найденный текст был в карточке Claude; код/карточки до уточнения не
менялись. После сообщения пользователя перечитан обновлённый **собственный**
БЛОК 1; полный frozen текст — `assignment.md`. Карточка Claude не менялась.
Coordinator текущей TASK — WEB_11, не WEB_10 предыдущего этапа.

Прочитаны применимые локальные части 08 → 000 → 18 → 01 → профиль 19, особенно
7.1/7.2, 34 и 36/36.1/36.2; predecessor reports portable kit / identity review /
native egress / VM preflight. Старые исследования и regression suites заново
не запускались. Исходный ориентир `8cc376c2de1bf41a0e504bb12a8624ed5a9cd79a`
взят из задания; Git HEAD/публикация не проверялись.

Все новые source/test/build/report/evidence — только эта TASK directory.
Единственное дополнительное разрешение — own-card rotation после сохранения
report/manifest/evidence. Никаких production/shared/Claude/LLM12/старого toolkit
правок. Protected baseline: **298 project files**, включая own card;
конечная проверка **297 noncard** — `integrity.json`.

## Что реализовано

| Компонент | Фактическая готовность |
|---|---|
| `source/Core.cs` | Immutable typed Request/Policy, SID/address/port/profile/freshness validation, deterministic owner/request keys, content/approval binding, 8 deny predicates, independent schema verifier |
| `PredicateInterpreter` + test oracle | Interpreter generated predicates и отдельный прямой endpoint-equality oracle; проверяется coverage/disjointness и unaffected UI |
| `Admission` / `ArbitrationSurvey` | Conservative reasons BLOCKED для failure/unknown/claimed proof/foreign precedence; никакой имитации WFP arbitration |
| `MemoryStore` / `TransactionSimulation` | Sealed memory-only transaction exercise: idempotent same-content resume, foreign/partial/unknown stop, before/after commit faults, keep-deny rollback plan |
| `source/Abi.cs` | x64 structures, exact managed-owned pointers/arenas, self-relative ALE user SD, filter lease и отдельный field-by-field readback comparator |
| `source/SdkConstants.cs` | GUID definitions извлечены из установленных SDK, не угаданы |
| `native/NativePreview.cs` | Отдельная internal compile-only DLL: 15 реальных Fwpm declarations; engine/session/transaction, persistent provider/sublayer/filter stage и exact readback source. **Не вызывалась** |
| `contracts/backend-contract.json` | Input/object/provenance/boundary/rollback contract с безусловным CanApply=false |
| `tests/` / `tools/` | Воспроизводимые local compilers/synthetic tests, negative mutants, source hashes, очищенные результаты |

Native source содержит настоящий API interop, не только simulator. Но **readback/
transaction API source compilation не означает working Windows implementation**:
SDK support на layer, arbitration, controller ACL/lineage, lifecycle и runtime
не доказаны. Account provisioning, startup и real rollback delete намеренно не
реализованы. Нативный `RemoveCandidate` всегда BLOCKED; delete API declarations
подготовлены, но не вызываются. Это адресные оставшиеся blockers, не скрытая
псевдореализация готового installer.

## Граница исполнения

Core, Abi и OfflineTests не имеют P/Invoke. OfflineTests не reference NativePreview,
принимает только фиксированный `selftest`; команда `apply` возвращает exit 20.
NativePreview не имеет exported public types/entrypoint, читается **только
reflection-only metadata**. Нет factory/adapter, соединяющего её с executable
или прежним installer. `OfflineBackend.CanApply=false` и любой valid Apply
возвращает BLOCKED. Никакой input/claim/hash/flag не может включить backend.

Visibility не является sandbox против намеренного reflection/привилегированного
host. DLL нельзя запускать таким способом. Будущий lab adapter требует новых
source changes, review и отдельного USER GO. Сам пакет не претендует на OS-level
изоляцию собственного compiler/runtime.

## Policy и важные ограничения

Для каждого SID: IPv6 deny; IPv4 non-TCP deny; TCP wrong-address deny; TCP
right-address/wrong-port deny. Это disjoint complement, **без собственного ALLOW**.
Client edge — exact `127.0.0.1:P`, broker — exact literal R:Q. Selected edge
unmatched нашими deny rules; не гарантирована доступность через Windows/чужие rules.
Вес 256 не используется как предположение «мы выше всех».

`ALE_USER_ID` получает `FWP_SECURITY_DESCRIPTOR_TYPE`, не FWP_SID. В descriptor
один exact-SID ACE с FWP_ACTRL_MATCH_FILTER; raw bytes/type/alignment проверены.
Canonical SID shape, одинаковый machine-prefix C/B и UI exclusion не доказывают
реального нового local account/token. Imported SID/host hash/operator claim не
являются authority. В этой TASK все полные SID — только synthetic fixtures.

Native stage использует persistent session/object intent, точные keys, transaction
и exact readback; ambiguity после commit не приводит к delete/reconnect/direct
fallback. Full existing readback match не доказывает trusted lineage. Новый plan
может создать новые keys — будущему installer нужен single-generation catalog.
providerData/ledger не дают права удалять объект. Rollback остаётся KEEP_DENY,
пока нет независимого live zero processes/flows/queued/delegated work.

Гарантии loopback receiver/port takeover, ALE comparators, effective foreign
graph/arbitration, active flows, BFE/boot, DNS/службы-посредники/смена identity,
broker authentication/no DIRECT, trusted ACL/ledger и native rollback **BLOCKED**.
Полная матрица — `security_boundary.md`; будущие observers/STOP — `lab_gate.md`.

## Проверки и числа

| Gate | Фактический результат |
|---|---|
| Финальный C#5/x64 build | 4 outputs собраны: Core, Abi, NativePreview DLL + managed OfflineTests EXE; errors/warnings 0 |
| SDK provenance | 3 установленных SDK версии, 9 ключевых header hashes; 6 GUID values совпали, 15 prototypes найдены |
| Независимый C++ `/Zs` gate | **22 static_assert PASS**, no link, no C++ executable/native API invocation |
| Final synthetic suite | **62/62 PASS / 0 FAIL**, source pinned before/after: `evidence/attempt05/` |
| Finite behavioral matrix | **73 728** комбинаций внутри одного test case: identities × families × all protocol bytes × address/port boundaries |
| Behavior mutants | **7/7 killed**, в составе 62 cases; positive controls сохранены |
| Compiled readback mutant | **61 PASS / 1 EXPECTED FAIL**, exit 1, exactly port-check regression; `evidence/mutant_port04/` |
| Предыдущий toolkit | **3/3 pure gates PASS**: matching-hash Apply BLOCKED, wrong-hash FAIL, reported-zero rollback KEEP_DENY; wrappers/collector не запускались |
| Windows PowerShell 5.1 | Только AST новой guard script: **1/1**, errors 0; PS5.1 runtime suite NOT RUN |

Компиляторы/SDK уже установлены. Нет скачиваний/restore/NuGet/install; C# source
использует штатный .NET Framework 4.5+ x64 и C# 5. Orchestration helpers требуют
существующий Python 3 и известный установленный MSVC/SDK layout, это dependency
build harness, не policy/runtime machine identity. x86/ARM64 не поддержаны;
реальная WFP-совместимость разных Windows НЕ подтверждена.

Сохранена история разработки: **44/44 → 55/55 → 58/58 → 61/61 → 62/62**. Это не сумма
independent/native tests. Каждый повтор имел новые source/coverage findings.
Красные compiled-mutant результаты всех четырёх ревизий сохранены; unexpected
product FAIL/compile ERROR не было. Первое AST наблюдение через shell selector
оказалось PS7 (несмотря на имя `ps51_syntax.json`) и не зачтено за PS5; явный
Windows PowerShell дал 5.1.19041.6456 — `ps51_syntax_actual.json`. Ни Execution
Policy changes, ни Bypass/Unblock/elevation в текущей TASK не применялись.

Результаты source/build/logical tests не считаются native enforcement/host
security/E2E. Самостоятельный adversarial walkthrough —
`manual_engineering_review.md`. Финальные числа и pin checks — `checks_final.json`;
`checks.json` сохраняет предшествующий 61-case snapshot. Последний test добавлен
для другого remote endpoint и крайних портов; финальный compiler harness также
использует environment allowlist без CL/_CL_/CSC и proxy/API credentials,
с собственными PATH/TEMP/TMP. Его source hash записан в build evidence.

## Safety / privacy / handoff

По source/call graph и выполненным командам: реальные Fwpm calls — **0**;
Windows account/rights/ACL/firewall/BFE/service/task mutations — **0**;
V2Ray/DNS/proxy/route changes — **0**; network probe/connect/listener/tunnel
запуски — **0**; Git/GitHub — **0**. Стандартная работа compiler/.NET/crypto/
filesystem не выдаётся за отсутствие любых Windows API или фонового трафика
машины. OS-level tracing/изоляция working host этой TASK не выполнялась.

Не читались credential stores, private proxy/MCP configs, чужие профили или
секреты. В publish bundle нет raw historic card backup, реальных host/user/SID/
private endpoint данных. Public paths — project-relative; source system SDK/
compiler build locations не являются личными параметрами policy. Privacy review
bounded, не универсальный secret detector. Compiled mutant DLL/EXE — только
evidence, не поставка для установки; production artifacts не заменялись.

Ротация own card выполняется после report/evidence/предварительного manifest:
полная постановка в B2, factual result в B3, прежняя история byte-exact;
после readback B1 — WAITING. Receipt `card_rotation.json`, final protected hashes
`integrity.json`; итоговые детали closing добавляются после фактического readback.
Полный старый card не копируется в отчёт ради privacy; проверяемый откат —
unchanged prefix + frozen assignment + old-history suffix при exact hash guard.

## DOC IMPACT / SHARED DOC DELTA proposal

Фактический write scope: новая TASK folder и own-card rotation. Общие docs,
Claude/LLM12, production и предыдущие отчёты не изменены. Root .gitignore читается
как обычный файл; global excludes/Git index/publication не проверяются.

Для WEB_11, предложение к 19/34 после независимой проверки:

> WFP offline backend candidate built under C#5/.NET x64: typed disjoint deny
> policy, SDK-derived ABI and readback comparison; native Fwpm source isolated
> in internal compile-only preview. Local logic suite 62/62, 22 SDK static
> assertions, 7 behavior mutants plus compiled port-check mutant detected;
> prior toolkit 3 pure gates still BLOCKED. No real WFP/native/network/Windows
> deployment. Effective enforcement, listener/SID/arbitration/boot/DNS/controller/
> quiescence/remote-route/E2E gates remain open; live install/rollback BLOCKED.

Предложение не внесено в общие документы и не является независимой приёмкой.
Публикацию и передачу WEB_11 делает пользователь; агент сообщений в другие чаты
не отправлял.

## NEXT SAFE ACTION

WEB_11 независимо проверяет source/manifest/границу native delivery и red mutant
evidence. Затем отдельный USER GO на доказанно изолированную Windows lab и
reviewed lab adapter с trusted lineage/identity/ACL/effective-policy observers.
Рабочую Windows, сеть, V2Ray, прежний launcher и MCP сейчас не активировать.

## Фактический итог ротации и локальной сохранности

`card_rotation.json` / independent readback `handoff_verification.json`:
БЛОК 2 содержит полную постановку, БЛОК 3 factual result; только после их
readback БЛОК 1 стал **ОЖИДАНИЕ НОВОЙ ЗАДАЧИ**. Все **502,226 bytes**
прежней истории и rules prefix byte-exact. Реконструкция prefix + assignment +
history suffix совпала с первоначальным SHA. Raw historic card copy не создана.
Recorded file-replace retry events: **0**; сохраняются
коды/фазы без raw paths. Никаких permission overrides или остановки приложений.

`integrity.json`: **297/297 protected noncard файлов неизменны**; own card —
единственное разрешённое изменение baseline. Финальные source pins/runtime
numbers — `checks_final.json`; список всего пакета/размеры/SHA — `manifest.json`.
Receipt связывает **предротационные** report/manifest hashes; final manifest
пересоздан после добавления closing evidence, это разные контрольные снимки.
Privacy pattern/manual review — `privacy_review.json`; исходные старые files не
перезаписывались. Git/global excludes/index/publication/independent acceptance
не проверялись. Root ignore patterns не исключают текущие отчёты/source/evidence.
