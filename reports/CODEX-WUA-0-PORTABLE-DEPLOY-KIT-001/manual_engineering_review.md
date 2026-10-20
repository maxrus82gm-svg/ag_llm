# MANUAL ENGINEERING REVIEW — Codex 007

Проведён отдельный source/adversarial walkthrough после synthetic suite.
Это собственное суждение исполнителя, не независимая приёмка WEB_10 и не
тестирование системной защиты Windows.

## Прочитанные потоки

- Collect → exact local path validation → trusted installed CimCmdlets →
  whitelisted local classes/properties → redacted field projection → coverage.
  Нет ComputerName/CimSession, DNS, connect/bind, auto-update, Get-AuthenticodeSignature
  или исполнения version/help EXE. Signature/CRL lookup не используется.
- Contract → typed inventory → config/inventory/requirements digests → 11 staged
  actions → readable plan. Новый SID остаётся null с обязательным local resolution;
  UUID owner и candidate name не являются SID и не переносят identity с другой ОС.
- CLI Install → parse/binding checks → fixed absent backend → BLOCKED. Проверено,
  что Apply/DryRun/ApprovedHash/ledger не ведут к Windows mutator. Метод Gate
  тестировался как pure function; реальные Install/Uninstall entrypoints не
  вызывались. C# stub не подменяет недостающий backend «успешным» return.
- Verify → deterministic content binding плюс **отдельный** static invariant
  verifier (не вызывает generator/model decision); native/actual-object claims
  имеют самостоятельные NOT RUN/NOT VERIFIED поля.
- Rollback → strict ledger/owner/target validation → freeze/disable/quiesce/
  independent zero-work check → account/task cleanup → deny-last. Неизвестный
  ownership, чужой объект или только reported_zero не разрешают удаление.

## Опровержения и изменения по результату review

1. Пустой обязательный field list мог бы дать формальное «готово». Проверяются
   55 unique IDs, все A–K categories, отсутствие missing/extra/duplicate fields;
   representation отличается от verified_metadata и requirement_met.
2. `VERIFIED=false` — знание отрицательного факта, не разрешение установки.
   Добавлен отдельный unmet constraint для отсутствующих BFE/API/free port/
   account collision/admin token. Дополнены explicit admin/script policy,
   working directory, interface count и actual ACL proof. Contract расширен
   50→52→55 в ходе разработки; прежние snapshots сохранены, их PASS не
   приписан финальному source revision.
3. PowerShell truthiness допускает string «true», coercion version «1» и bool
   вместо int. Типы проверяются явно; JSON duplicate keys (включая escaped/case
   aliases), malformed grammar/leading zeros/depth/token limits отвергаются.
   PS7 date parsing отключён feature-detection DateKind, 5.1 fallback допустим.
4. Перестановка JSON properties не должна менять approval digest; Unicode,
   escaping/integers сериализуются собственным deterministic canonical encoder.
   Изменение payload с повторным вычислением hash всё равно отвергается
   относительно independently supplied config/inventory. Hash **не** выдаётся
   за подпись оператора или physical-device binding.
5. Model Block ALL + allow не подходит. Шаблон содержит только непересекающиеся
   символические deny predicates. Independent static verifier выявляет лишний
   Allow и пропущенный port deny; oracle проверяет все 256 protocol numbers
   на 8 port-boundary values и адресные варианты. Это логическая модель,
   не компиляция FWPM conditions и не Windows runtime enforcement.
6. Снимок свободного порта не защищает от будущего listener takeover/port
   exclusion/TOCTOU. receiver_guard всегда UNSUPPORTED, ничего не bind-ится.
   C/B policy не разрешает «временно любой localhost» или DIRECT для ремонта.
7. Private metadata не попадает в public artifacts: whitelisted field shapes,
   counts/booleans/hash/role refs вместо host/user/SID/IP/private-path; proxy
   env values/секретные конфиги не читаются; messages ошибок маскируются.
   Дополнен regression для test-harness error message, чтобы неожиданный I/O
   failure не записал private path в results. `-LocalPreview` — только явный
   локальный opt-in, не публикуемый результат.
8. UNC/provider/ADS/device/dot-dot/reparse/cloud paths отвергаются. Attributes
   проверяются **до** Exists/read, чтобы не следовать последнему link ради
   проверки его существования. Binary hash/version чтение использует shared
   read/write/delete handles и stability checks, не мешает обновлению рабочего
   broker эксклюзивным lock. Kernel race-proof opens ещё не реализованы.
9. 32-bit PowerShell environment мог бы дать ложную OS architecture под WOW64.
   Collector заранее BLOCKED на 32-bit; новый native profile не включается.
   Это честное ограничение, а не fallback с ослаблением защиты.
10. Ledger JSON можно подделать. Поэтому matching UUID/plan или нулевые счётчики
    не авторитет для removal. Resume не создаёт дубликаты, а требует trusted
    actual-object readback. Broad root paths/предсуществующие/чужие ресурсы
    отвергаются; живые процессы/queued delegation предполагают keep_deny.
11. Script execution policy — реальный portability gate. Первый prototype
    запуск 5.1 использовал process-only Bypass; признано ограничением теста,
    не стало функцией продукта. Финальные checks не меняли policy, 5.1 только
    AST под Restricted. Не предлагается «для удобства» auto-unblock/auto-elevate.
12. Ротация карточки не должна экспортировать исторические host identifiers.
    Полный raw backup не копируется в новый publish bundle; сохраняются hashes,
    текущая frozen assignment и byte-exact история в canonical card. Двухфазный
    guarded replace сохраняет B1 до readback B2/B3; staged private file не
    должен остаться среди публикуемых файлов. Откат обратимо восстанавливает
    before bytes из assignment + preserved canonical history при final hash match.

## Остаточные риски

За пределами этого release: реальный C#/Fwpm backend и его build/signature;
привязка к устройству/проверенному ledger; target OS SID/loopback/arbitration/
BFE/boot/old-flow semantics; actual ACL/child/delegation/receiver ownership;
broker actual loaded route and remote identity; credentials provisioning;
совместимость всех Windows. Все эти paths BLOCKED. Для T2 нужен более сильный
boundary, обычная учётка не достаточна. Mock PASS не переносится на них.
