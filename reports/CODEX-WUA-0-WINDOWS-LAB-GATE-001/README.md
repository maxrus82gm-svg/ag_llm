# Windows Lab Gate — offline kit

TASK `CODEX-WUA-0-WINDOWS-LAB-GATE-001`. RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11.

Комплект проверяет **согласованность, полноту, происхождение и свежесть evidence** I01–I12. Он не создаёт VM, не реализует live containment, не включает WFP и не выдаёт разрешения на исполнение. Текущий реальный результат — `BLOCKED`, 12/12. Синтетический положительный набор проходит; он явно тестовый.

## Состав

| Файл | Назначение |
|---|---|
| `source/lab_gate.py` | `check` signed snapshots, `plan` non-executing dry-run |
| `source/Signatures.cs` | Ограниченный C#5/.NET Framework RSA verifier; ephemeral signer только synthetic tests |
| `adapters/Collect-Host.ps1` | Ограниченная локальная read-only инвентаризация, без VM enumeration |
| `adapters/Read-HyperVApproved.ps1` | Кандидат частичного read-only metadata adapter по точному разрешённому GUID; NOT RUN |
| `tests/test_gate.py` | 52 самостоятельных test methods, handwritten positive/negative fixtures |
| `tools/run_checks.py` | Локальная сборка helper, syntax checks, тесты, два mutation controls |
| `contracts/isolation_contract.json` | Машиночитаемая карта I01–I12 и источников |
| `gate_results.json`, `checks.json` | Реальное BLOCKED-решение и разделённые факты тестирования |
| `evidence/attempt08/tests/positive_bundle.json`, `synthetic_trust.json` | Подписанный **тестовый** пример полного входа и публичные test keys |
| `evidence/attempt08/Signatures.exe` | Проверенный helper для опубликованного примера; SHA-256 в `run.json` |

Зависимости: установленный Python 3.9+ для core; проверено на Python 3.13; для helper — Windows x64, .NET Framework 4.6+ с RSACng и существующий Framework64 C# compiler. Harness рассчитан на Windows с указанным установленным toolchain. Отсутствующие зависимости означают BLOCKED. Автозагрузки/установки нет. Python crypto packages не требуются. Сборки helper имеют разные PE hashes; trust pin всегда должен соответствовать **конкретному** EXE.

## Воспроизведение без VM

В PowerShell из корня `M:\GitHub\ag_llm`:

```powershell
python -B reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/tools/run_checks.py attempt09
python -B reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/tools/run_checks.py mutant_nic04
python -B reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/tools/run_checks.py mutant_trust04
```

Это **инструкция для verifier**, данные каталоги в сдаче не создавались. Выбирайте ещё не существующий номер, максимум две цифры. Выход 0 harness означает: обычный набор прошёл либо конкретная мутация обнаружена строго ожидаемыми тестами. У mutant suite внутренний test exit=1 ожидаем; 50/52 или 51/52 здесь не скрывают обычный regression. Выходы: `evidence/<label>/run.json`, `tests/results.json`, очищенный `runner.txt`, публичные fixtures, helper. Никаких VM или сетевых тестов harness не вызывает. Новые прогоны добавят файлы и потребуют отдельного нового manifest; текущий сдаваемый manifest не переписывать как будто это исходное evidence.

Настоящий текущий результат можно воспроизвести новым выходным именем:

```powershell
python -B reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/source/lab_gate.py check --bundle reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/fixtures/unprovisioned.json --helper reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/evidence/attempt08/Signatures.exe --output reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/evidence/verifier_unprovisioned.json
```

Ожидается exit **20**, `decision=BLOCKED`, I01–I12 BLOCKED. Exit20 здесь правильный отказ, не доказательство изоляции. `check`: 0=PASS evidence, 10=FAIL, 20=BLOCKED. `plan`: 0 означает запись плана, **не применение**. Все выходы CreateNew, существующие файлы не затираются. CLI разрешает только staged files внутри собственной TASK, локальные Fixed/Removable volumes, без UNC/URL/reparse/offline/cloud-recall paths. Нужен доверенный неизменяемый файловый контекст; эти проверки не устраняют файловый TOCTOU против администратора.

## Signed positive fixture

Полный образец схемы — `evidence/attempt08/tests/positive_bundle.json`; корень доверия — соседний `synthetic_trust.json`. Положительный CLI уже вызван тестом: `evidence/attempt08/cli/positive.json`. Параметры: `--synthetic --now 2030-01-01T00:00:30Z`; точное fixture time смотрите в `request.valid_from/valid_until` (не используйте этот пример для real). `--trust-sha256` — **SHA-256 canonical JSON**, не raw файла: ASCII, sort_keys, separators=(',',':'). В доверенном review shell можно вычислить так:

```powershell
python -B -c "import json,hashlib,pathlib; p=pathlib.Path('reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/evidence/attempt08/tests/synthetic_trust.json'); print(hashlib.sha256(json.dumps(json.loads(p.read_bytes()),ensure_ascii=True,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest())"
```

Это вычисление демонстрационного pin **не заменяет** независимое получение production trust root. Для real `--synthetic` и `--now` запрещены/не используются; `test_only=true` root отвергается. Настоящего real trust root, ключей или подписанных лабораторных наблюдений эта TASK не создала.

### Вход и доверие

`bundle`: request + host + guest + review. Request связывает owner/VM GUID/boot/run/nonce, backend/version/config/baseline/rollback hashes, full owned disk DAG, шесть asset roles с size/hash/origin review, 1–8 exact IPv4 loopback TCP endpoints, срок UTC ≤300 s и typed approval booleans. Запрет execution сохраняется при любом значении approval. Host/guest body отдельно подписаны и содержат только применимые I-факты; review подписывает hashes обоих body и `CONFIRMED/BLOCKED/FAIL` каждого I.

Out-of-band pinned root содержит **approved_request_sha256**, три различных principal IDs/public RSA keys, helper hash и версии/hashes host/guest observers. RSA2048/e65537, PKCS#1 SHA-256; private synthetic keys ephemeral CNG, никогда не экспортируются. Root и его pin проверяются внешним оператором/verifier, а не принимаются из bundle. Три ключа сами по себе не доказывают три независимых человека. Подпись доказывает источник; истинность sensor facts требует внешней инженерной проверки. Request TTL≤300s, наблюдения ≤60s; silence, incomplete census, unknown observer, missing review — BLOCKED. Подписанное отрицательное наблюдение даёт FAIL даже без review. Любой итоговый receipt — snapshot validation, не lease на исполнение.

## Read-only adapters и политика

`Collect-Host.ps1` реально выполнен один раз штатным PowerShell 7.6.5 без изменения policy. Snapshot UTC указан в inventory; это не live proof. `Read-HyperVApproved.ps1` сейчас **не запускать**: нет платформы/одобренной VM. Для будущего чтения нужны exact GUID/owner, приватный permission JSON с шестью полями `operation=READ_ONLY_EXISTING_OWNED_VM`, `vm_guid`, `owner`, `ownership_ledger_sha256`, `independent_review_sha256`, `valid_until` (UTC, не дальше 5 min) и независимо сверенный raw SHA-256. Не создавать такую авторизацию из имени VM/Notes. Даже разрешённый readback этого адаптера остаётся PARTIAL: полного channel/storage/guest/watch proof он не производит.

При отсутствии Hyper-V — NOT RUN без VM queries. Неподдерживаемый точный `-VM` selector → BLOCKED; обхода через VMName/общий поиск нет. Нужны уже работающий vmms и фиксированный System32 module. Native/platform runtime semantics на текущем host не проверены.

Оба PS-адаптера разобраны Parser.ParseFile Windows PowerShell 5.1 без ошибок, без исполнения. Попытка запуска вспомогательного `tools/Check-AdapterSyntax.ps1` через PS5.1 `-File` заблокирована штатной Execution Policy; её не изменяли. Затем выполнен только прямой parser command, без `Invoke-Expression`, dot-source, evaluation adapter text или policy bypass. Эта TASK не разрешает ослаблять policy ради запуска.

См. `report.md`, `manual_engineering_review.md`, `lab_build_plan.md`, `next_user_go.md`. До отдельного USER GO все VM/native/security/proxy actions BLOCKED.
