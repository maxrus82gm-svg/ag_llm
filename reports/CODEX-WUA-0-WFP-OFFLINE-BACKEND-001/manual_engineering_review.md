# Manual engineering / adversarial source review

Codex 007, 2026-10-20. Это самостоятельный source walkthrough после автоматических
проверок; **не независимая приёмка WEB_11** и не Windows behavioral experiment.
Рассмотрен финальный source, соответствующий `evidence/attempt05/build.json`.

## Потоки данных и исполнения

`Request` → immutable binary canonical content/digest → `Builder` → восемь
раздельных denies → `StaticVerifier` (schema отдельно от regeneration) → pure
`FilterLease`/managed memory → pure `Readback` comparator. Любой public Apply
останавливается на `OfflineBackend` после input validation, capability false.
Executable принимает только `selftest` с новым output внутри своей directory.

Другой граф: internal `LabSourceSession` → реальные `Fwpm*` declarations.
Это отдельная compile-only DLL без exported types/entrypoint; managed runtime
assemblies её не reference. Tests читают её reflection-only metadata. Нативный
граф в этой TASK **не выполнялся**. Assembly visibility не sandbox и не защита
от намеренного reflection/admin host; это явное ограничение доставки.

## Попытки опровергнуть решение

| Finding / вопрос | Инженерное решение и предел |
|---|---|
| Неправильный SID representation | По SDK нужен SECURITY_DESCRIPTOR_TYPE, не FWP_SID. Реализованы exact self-relative SD bytes и независимые raw-byte assertions. Windows AccessCheck semantics ещё не доказаны |
| Разрешён любой loopback port | Условия exact address+port; independent endpoint oracle и seven behavior mutants, включая wrong-port, неверный SID, byte swap, protocol и duplicate predicate |
| Ложный readback при том же owner/hash | Проверка полей, SD/blob, keys/provider/layer/sublayer, flags/action/context/id, weight pointer, types/match/value. Реальный compiled mutant пропускает U16 port и падает ровно в нужном regression |
| Readback comparator непокрыт, потому что в native source | После первого прогона вынесен в pure `Abi.Readback`, native source использует этот же модуль. Добавлены positive controls и malformed/drift cases, без реальных OS pointers |
| Arbitrary struct содержит managed resources | `Arena.Struct` ограничен reviewed blittable Guid/Blob перед allocation, освобождение arenas idempotent. Нет обещания memory safety для произвольных pointers |
| DLL search hijack будущего interop | В NativePreview задан `DefaultDllImportSearchPaths(System32)`. SDK DLL на текущем runtime не загружалась; реальный target binary trust всё ещё gate |
| Commit выполнился, ack потерян | Признак commitAttempted устанавливается перед вызовом; ни abort, ни delete, ни direct fallback после ambiguous commit. Mock подтверждает сохранённые объекты; runtime семантика не испытана |
| Postcommit readback потерян/данные изменились | Добавлены отдельные injected failure/drift cases; result UNKNOWN_KEEP_DENY. При повторном входе partial/foreign readback блокирует новые Begin/Add |
| Abort сам не завершился | Сохранён prior transaction unknown; нет слепого повторного Begin или cleanup. Это bounded fake transaction behavior, не проверка BFE recovery |
| Foreign filters и weights | Conservative survey не объявляет precedence PASS даже при максимальном собственном/чужом weight. HARD/SOFT permit/callout/unknown остаются BLOCKED; чужой BLOCK может ломать availability |
| Scope current UI / other identities | C/B/UI различны, C/B machine prefix согласован; unrelated SID unaffected в модели. Это не реальное token/provenance proof; смена SID/делегирование SYSTEM не охвачены |
| Host hash / signed approval подменены | Hash binds content, не authority. Regeneration rejects rehashed forged key, но attacker с новой всей input authority не останавливается hash. Поэтому no real Apply до trusted local host/controller proof |
| Unsigned providerData выдаёт чужой object за свой | Matching bytes — только comparison. Native existing-match требует отдельно trusted lineage, не authorizes adoption/deletion. ACL/lineage backend отсутствует |
| Новый plan создаёт другой набор keys | В provider/key derivation входит request digest. Нужен single-generation ownership catalog в будущем; без него нельзя предлагать повторный live deploy как idempotent installation |
| Rollback bool reported_zero / чужой ledger | Pure mock rejects owner/hash/readback mismatch, но даже perfect mock и reported_zero оставляют KEEP_DENY. Native RemoveCandidate всегда throws; delete declarations не используются |
| Старый toolkit невольно разблокирован | Старые files hashes сверяются; 3 адресные pure-function проверки подтверждают matching-hash Apply BLOCKED, wrong-hash FAIL, rollback KEEP_DENY. Install/Uninstall wrappers не вызывались |
| Что значат 73 728 случаев | Одна bounded finite matrix (3 identities × 2 families × 256 protocols × 6 addresses × 8 ports), не Windows network tests. Oracle использует прямое равенство endpoint, не Builder/conditions |
| Можно ли получить false green runner | Exact nonzero counts, source pins before/after; compiler exit checked; warnings-as-errors; default command must exit 20. Mutant compile failure не считается killed: нужен ровно ожидаемый failed test |
| Oracle сам зависит от fixture адреса | Финальный oracle переводит packet address обратно в dotted text и сравнивает с input, не использует Builder address conversion. Добавлен другой remote со всеми ненулевыми октетами и port 1/65535; код не зависит от исходного R/P |
| Compiler options/credentials наследуются через environment | Финальный harness передаёт allowlist системных environment keys и свой PATH/TEMP/TMP, не наследует CL/_CL_/CSC, proxy/API credentials. Orchestrator SHA и имена переданных keys сохранены, значения не публикуются |

## Что ручной review оставляет открытым

Главные gaps — layer comparator support, ALE_SD semantics и token scope;
loopback listener authentication/ownership; effective foreign WFP graph/arbitration;
boot/BFE/pre-existing flows; DNS/IPC/delegated operations/child identity; broker
remote identity/no DIRECT; authenticated host ledger + controller/object ACL;
реальный rollback/quiescence и различия Windows. Они перечислены как blocking
gates, не «покрыты» mocks. `security_boundary.md` и `lab_gate.md` дают источники
истины и STOP для будущего отдельно разрешённого этапа.

## История проверок и исходные отклонения

- Первый source: 44/44; после readback/authority hardening: 55/55; после DLL-search
  и postcommit coverage: 58/58; arbitration/delegation: 61/61; финальный
  parameterized-endpoint oracle и isolated compiler env: **62/62**.
  Сохраняются все source hashes, это не сумма независимых security tests.
- Четыре compiled mutant attempts соответствуют successive source revisions:
  каждый имеет ровно 1 намеренный FAIL (port readback omission), остальные PASS.
  Финальный mutant: **61 PASS / 1 EXPECTED FAIL**, exit 1; orchestration проверяет
  trigger/name/count и фиксирует killed. Эти красные evidence не удалены.
- Не было product compile errors или неожиданных managed test FAIL. Попытка
  выбрать PS5.1 через shell selector фактически дала runtime 7.6.5; файл сохранён
  как исходное наблюдение, не зачтён PS5.1. Явный запуск установленного Windows
  PowerShell дал 5.1.19041.6456: AST 1/1, errors 0, **не runtime suite**.
- Проверочный ledger fixture перед запуском приведён к точному прежнему schema
  process_state/flow_state. Нет неподтверждённого claims о first-red regression.
- Execution Policy/Bypass/Unblock/elevation в этой TASK не применялись.

Verdict: **bounded offline source/build/test result ready**. Native enforcement,
live rollback и host security остаются NOT VERIFIED; самостоятельная приёмка
агентом не объявляется.
