# Manual engineering / adversarial self-review

Codex 007; 2026-10-21 local. Проведён отдельно от автоматического test verdict: прочитаны доверительные границы, решения, parser/crypto launch, adapters, provisioning transitions и сохранение истории. Это **self-review**, не независимая приёмка WEB_11 и не review работающего гипервизора.

## Найденные и исправленные ошибки

1. **Приоритет signed negative fact.** В промежуточной реализации отсутствие review блокировало обработку уже проверенного host negative fact. В результате NIC=1 и отсутствующий review давали BLOCKED вместо требуемого FAIL. До исправления добавлен адресный regression: `evidence/attempt05` — 51 total, 50 PASS, 1 FAIL, 0 ERROR. Исправление: authenticated host/guest facts анализируются независимо от доступности review, FAIL имеет приоритет над missing-proof BLOCKED; positive PASS всё ещё требует отдельного review. Исходный red/runner/source pins сохранены. Это не security acceptance на VM.
2. **Привязка полномочия к request.** Три доверенных ключа и подпись произвольного request недостаточны: те же ключи могли подписать другую VM/boot/config. Добавлен `approved_request_sha256` в **внешне pinned** root; валидно подписанный другой VM request отклоняется. Дополнительный test вошёл в final 52. Trust root нельзя произвольно брать из bundle или принимать по заново вычисленному непроверенному pin.
3. **Cross-bindings и ownership.** При разработке усилены связи Windows-media asset ↔ media digest, observer asset ↔ pinned observer, full parent DAG ↔ chain digest, guest baseline/boot ↔ host/current run, host OFF ↔ невозможный guest-live PASS. Зафиксированы тестами; неизвестный parent/remote/shared/reparse/storage owner → отказ.

## Атаки и пределы контроля

| Вектор | Проверка кода / результат / оставшийся предел |
|---|---|
| Самоподписанный self-report, одна роль за обе стороны | Root вне bundle, три distinct principal IDs/key fingerprints, separate signatures и review hashes. Guest-only/self-report BLOCKED. Но independence лиц/датчиков нельзя доказать JSON или тремя ключами: нужна внешняя trust ceremony |
| Сфабрикованный sensor JSON | Валидная подпись подтверждает источник, не истинность фактов. Доверенные observer versions/hashes и review — prerequisites, реальных sensor implementations/proof в этой TASK нет. Против malicious trusted signer гарантии не заявлены |
| Key/helper substitution | Canonical root pin, approved request pin и exact helper/observer hashes. Helper хранится локально; real rejects test-only root. Compromised OS/admin, подмена executable между hash и launch, clock/filesystem TOCTOU за пределами TCB: это не sandbox и не защита от локального администратора |
| Replay/expired/foreign snapshot | Request UTC≤300s, observations≤60s, run/boot/nonce/config/baseline/owner/request binding и review host/guest body hashes. Real CLI не принимает `--now`; synthetic не real proof. Root approval и повторная admission могут потребовать внешний replay ledger; checker не ведёт live nonce-consumption ledger |
| Empty lists / zero packets / observer silence | Census-complete/coverage facts required, unknown observer/missing observations/heartbeat-age/loss/restart/zero-packets-only отклоняются. Значения пока synthetic; реальный Attempts/ETW observer не создан и не проверен |
| Disconnected NIC / forwarding / host relay | Даже nic_count=1 FAIL; NAT/bridge/hostonly/forwarders/passthrough, enhanced console/PSDirect/clipboard/USB/GPU/serial/hostmount flags проверяются. Полнота backend census должна быть доказана внешне, она не выводится из одного Get-VMNetworkAdapter |
| Частичный Hyper-V readback | Exact GUID query после pinned ownership permission, no name fallback; fixed System32 module, проверяется наличие `-VM`; vmms должен уже работать. Кандидат НЕ запускался, runtime семантика не доказана. Counts/core digest не полный device graph. Adapter сам ставит census/chain=false и proof BLOCKED, не выдаёт signed real attestations |
| Remote path via VHD parent / permission/output | Adapter не вызывает Get-VHD/mount и не открывает attachment paths; только hashes aliases. Permission input проверяет local volume/ancestors before read. CLI staged input/output отвергает UNC/URL/reparse/offline/cloud. Task directory/OS считаются доверенными; output path checks адаптеров не race-safe, враждебный writable ancestor требует отдельного hardened design |
| Unsafe JSON / bool-as-int / shell injection | Size/depth/items/string limits, duplicate/escaped duplicate keys, strict fields/types, no floats/nonfinite; helper вызывается argv list, не shell; sanitized child environment. Endpoint — только literal127.0.0.1/TCP, distinct ports. Dry-run root не интерполируется в команды, metachar/reserved/dotdot/ADS/remote синтаксис отвергается |
| Host/guest channel bypass, DNS, children | Полный I03/I05/I08/I10/I11 нужен даже при отсутствии NIC. Current adapters/fixtures не проверяли реальное разрешение PSDirect/guest-agent/service delegation/DNS/children. Любой unknown channel блокирует будущий baseline boot/native gate |
| Dynamic config / watch loss | Before/after digest + watch/loss/heartbeat/independent-stop facts required. Offline checker не запускает watcher, не замораживает конфигурацию, не выключает VM и не обеспечивает TOCTOU lease. Future controller и signed live evidence обязательны; сейчас native false всегда |
| All approval booleans true | Автотест подтверждает `native_execution_allowed=false`, `vm_changes_allowed=false`; у plan `can_apply=false`. Нет hidden apply/start/stop/delete executor и import прежнего WFP/installer |
| Destructive rollback | План требует exact owner/GUID/full path/ledger, отдельные stop/delete permissions, никакого host reset. Исполнителя rollback в комплекте нет. Реальная восстановимость до native запуска ещё NOT VERIFIED |

## Независимость tests и mutation controls

Positive fixture expectations вручную сформулированы в тесте, не получены вызовом production `facts_check`. Негативные facts переподписываются ephemeral test-role keys, поэтому тестируют смысл, а не только повреждённую подпись. Final positive проходит все 12 I. Для mutation copies отключены NIC comparison и real/test trust segregation; текущая suite обнаруживает соответственно **2** и **1** ожидаемый сбой, без ошибок. Это две мутации, не 104 независимых проверок гипервизора и не доказательство отсутствия всех дефектов. Набор проверяет алгоритм на конечных адресных примерах.

## Toolchain / policy / scope

Нет downloads/SDK/package install. Существующий Framework64 csc компилирует только новый managed crypto helper, не старый WFP NativePreview. CNG ephemeral keys остаются в памяти; нет private export/cert-store/persisted-key creation. Поэтому «ноль Windows API» не утверждается: были trusted local CIM, file metadata, GetDriveTypeW и managed CNG; **ноль VM/security/network config mutations и WFP/native client calls**.

PowerShell 5.1 file execution syntax-helper был отклонён штатной policy. Не применялись Bypass/Unblock/elevation/изменение policy; затем direct Parser.ParseFile прочитал source только как текст. Сохранены runtime/error-free AST metadata. Host collector штатно выполнен в PS7.6.5; две PS5.1 AST проверки не считаются двумя runtime tests.

Вспомогательная сборка отчёта сначала остановилась на неверном поиске portable flag в `.ps1` вместо фактического `.psm1` (и пробелах). Исправлено только в собственной TASK; ранее созданные immutable outputs сверены и переиспользованы без перезаписи. Это ошибка сборки handoff, не дополнительный gate test или OS failure. Две rejected patch application попытки и неверная harness label не меняли production source; продуктовые initial failures отражены в attempt05.

## Вывод review

Готов **offline evidence validator с негативными контролями и data-only plan**. Реальная лаборатория, исчерпывающие host/guest collectors/observers, live lease/stop, isolation и WFP execution не реализованы/не подтверждены этой TASK. Их отсутствие честно BLOCKED. Следующий минимальный этап — отдельный ready lab host/media + review конкретного plan, а не запуск native на текущей Windows. Independent WEB_11 acceptance pending.
