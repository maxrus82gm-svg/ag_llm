# MANUAL ENGINEERING REVIEW — Codex 007

Проведён смысловой adversarial review артефактов и последовательностей; это
собственная инженерная проверка исполнителя, не независимая приёмка WEB_10
и не новые security/runtime tests. Предыдущие suites 19/19, 5/5, 36/36, 22/22
не запускались повторно. Ни одной сетевой fixture в текущей TASK не создавали.

## Просмотренные ветви и решения

1. **Source admission.** Сверены local inventory → cached metadata/SHA256SUMS →
   ZIP member → установленный EXE. Равенство bytes подтверждено, но цепочка
   одного origin не превращена в независимую build attestation. Список binary
   path hints не представлен как текст Go. При missing source VM-design
   продолжается, exact startup/test invocation остаётся BLOCKED.
2. **Inventory interpretation.** PATH miss недостаточен: дополнительно прочитаны
   CIM CPU/OS/features, uninstall entries, services/drivers, standard binaries,
   Hyper-V module metadata и bounded VM/media directories. Все источники
   согласуются с отсутствием обнаруженной готовой платформы. Нет полного
   machine-wide census, поэтому итог PARTIAL; код InstallState=2 не расшифрован
   без доступного text mapping. Firmware virtualization=true не равна VM ready.
3. **No-NIC boundary.** Отвергнуты host-only/private-switch и guest route-only
   shortcuts. Даже disconnected NIC опасен поздним reconnect; zero objects
   проще аттестовать. Existing host NAT не удаляется: нужно отсутствие VM edge,
   а не “чистая сеть” всей машины. Ни host external canary, ни guest public DNS
   не нужны и не разрешены для доказательства.
4. **Integration bypass.** Отключённый virtual NIC недостаточен при shared
   sockets, named pipes, enhanced/RDP clipboard/drive redirects, PowerShell
   Direct/guest relay или writable shared folder, обслуживаемой host daemon.
   В проект внесён полный channel census; экспорт evidence — только при Off.
   Это контракт, реализованного version-specific verifier пока нет.
5. **Children.** Гость охватывает всё process tree, если trusted hypervisor не
   имеет relay. Это не доказательство, что клиент сам не делает direct dial.
   Cloudflared не должен незаметно войти в startup; нужны source/config proof
   и PC oracle, unexpected child → STOP. Shared host Python/Claude не затрагиваются.
6. **False green.** Нет packets ≠ нет попыток; TCP snapshot пропускает отказ и
   короткий socket. Separate observer coverage required: socket/DNS/process
   attempts, loss accounting, correlation to FX. Невозможность реализовать
   такой observer — BLOCKED, не PASS по молчанию ledger. Контракт текущего gate
   поэтому PARTIAL, несмотря на оформленную матрицу I01–I12.
7. **Race/lifetime.** Один pre-boot screenshot допускает hot-plug/device drift
   после проверки. Введены config digest, validity window, host change watch и
   STOP on observer loss. Никакого automated resume; current design не содержит
   реализованного interlock и не обещает zero race. Hypervisor/admin доверены.
8. **Restore/replay.** Snapshot name недостаточен; после restore повторно
   сверяются chain, config и assets. Case isolation не наследует старый GO.
   Output disk/guest memory snapshot могут нести секреты; свежая offline-база
   и power-off export предпочтительнее working host image.
9. **Rollback ownership.** Неизвестный return ID после partial create не повод
   повторять создание/удаление. Проверять VM GUID, parent chain, exclusive
   resolved paths. Если stop/control недоступен — quarantine, не force reset
   networking/service/reboot. VM removal не откатывает установку hypervisor;
   потому создание на уже подготовленном lab host предпочтительно.
10. **Card transaction.** Последнее USER GO адресно расширяет write_scope только
    для own card. Сначала full backup и frozen assignment, затем report;
    stage B2+B3 с неизменным B1, readback; только после него clear B1. Старый
    B2–B3 tail должен остаться byte-for-byte suffix. Hash drift перед каждой
    заменой останавливает ротацию. Atomic replace не является общей блокировкой
    всех редакторов: поздние внешние изменения требуют reconciliation. Общий
    документ 18 согласован с базовой ротацией; PARTIAL/BLOCKED exception требуется
    явно уточнять для предотвращения прежней неоднозначности scope.

## Новые пробы и качество

Не добавлялся фиктивный unit suite для документального изменения. Новые проверки:
read-only inventory, bounded filename search, ZIP/EXE identity, protected-input
hash comparison, transactional card loss-check и полный final artifact manifest
readback. Источники этих инструментов сохранены. Проверка целостности артефактов
не доказывает работоспособность гипервизора/клиента и не засчитывается native E2E.

Первичных FAIL/ERROR у сохранённых inventory/provenance операций не было;
отрицательные находки (нет source/platform/media) сохранены как BLOCKED.
Широкие предварительные консольные чтения Markdown были усечены размером вывода;
адресные участки B1, rotation rules и coordinator findings прочитаны отдельно.
Такая усечённая выдача не использовалась как доказательство отсутствия данных.

## Открытые риски

Не получены exact source/dependency closure/build attestation, lab platform/image,
полный backend-specific IPC/device verifier и independent guest attempt observer.
Не проверены Windows image support/update/license, software compatibility,
resource capacity и физическая безопасность lab host. Нет доказанной OS границы,
native fail-closed или маршрутизации V2Ray. Эти пробелы нельзя закрыть документом,
SDK model или повторением прежних reference-тестов.

Вывод: разрешённая инженерная подготовка завершена с PARTIAL/BLOCKED gates.
Фактический deployment/native run остаётся отдельным этапом, требующим новых
доказательств, независимого review и отдельного USER GO.
