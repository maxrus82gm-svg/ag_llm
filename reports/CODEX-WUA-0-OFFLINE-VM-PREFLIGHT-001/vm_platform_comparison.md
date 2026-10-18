# Gate C — выбор платформы (проект, не установка)

Сравнение — инженерный анализ по доступным локальным данным и общим свойствам
технологий. Свежая внешняя документация не запрашивалась по запрету сети;
version-specific команды/semantics будущего backend должны быть отдельно сверены
с его доверенной offline-документацией. Ни один из вариантов не аттестован здесь.

| Вариант | Сетевой разрыв / descendants | Доказательства, snapshots, rollback | Стоимость и риск для рабочей машины | Решение |
|---|---|---|---|---|
| Полная Windows Gen2 VM / Hyper-V | Проектируется без **всех** virtual NIC, forwarding, host IPC/redirectors; дети остаются внутри гостя при доверенном hypervisor | VM GUID + host config/readback + независимый device census; известный чистый offline checkpoint/disk chain; owned removal | На этой машине платформа не подтверждена; включение Windows feature/reboot изменит host и требует отдельного GO, не выполняется | Предпочтительный условный backend, лучше на уже подготовленном отдельном lab host |
| Windows VM / VirtualBox | Можно спроектировать отсутствие NIC, shared folders/clipboard/USB/serial relay; конкретные defaults неизвестны до проверки версии | Machine UUID/config + media registry + snapshot chain; независимо проверить все адаптеры/интеграции | Локальная установка не найдена; установка drivers и host networking недопустима в этой TASK | Резервный кандидат; не запускать даже portable manager без нового scope |
| Windows VM / VMware | Аналогичная полная VM; NAT/bridged/host-only должны отсутствовать, integrations отключены | VMX + hypervisor runtime view + VMDK/snapshot chain; version-specific audit | Установка не найдена; services/virtual networks могут влиять на host | Резерв; лицензия/дистрибутив/настройки не установлены |
| Windows guest / QEMU | Явно нулевые network devices/backends; user-mode networking, monitor, chardev, virtio-fs и guest agent каналы исключены | Полный argv/device tree и owner process tree + QCOW2 backing chain; отсутствие NIC по обоим наблюдателям | Не найден; accelerator/dependencies/performance не подтверждены | Резерв только после exact-version audit; не полагаться на defaults |
| Windows Sandbox | Эфемерность полезна; нужен доказанный запрет networking и всех sharing/redirection channels | Хуже подходит для закреплённого disk/checkpoint identity и многоэтапного независимого readback | EXE/платформа не найдены; включение feature не разрешено | Не выбран для первого доказательного gate |
| WSL/контейнер/Python guard | Не тот Windows EXE runtime или общий host boundary; inherited/shared network и daemon могут иметь egress | Снимок контейнера/кодовый guard не подтверждает защиту всего native tree | Риск ложного VERIFIED; reference suites уже существуют | Не замена полной Windows VM и не OS gate |

**Выбор:** conditional Hyper-V Gen2 disposable Windows VM с нулём сетевых
устройств, на доверенном уже подготовленном Windows lab host. На текущем host
это пока проект. Отсутствие платформы не разрешает установить её автоматически.
Если пользователь хочет именно текущую машину, сначала нужен отдельный план
системных изменений, проверки совместимости V2Ray и адресный USER GO; такие
изменения не включены в предложенный минимальный gate.

Host-only/internal/private switch не принимается как сокращённый вариант:
даже закрытый switch создаёт дополнительную edge для будущего relay. Для первой
лаборатории проще проверять **zero NIC objects**, а не правильность маршрутов
при наличии NIC. Существующие host NAT/firewall/V2Ray остаются как есть: критерий
относится к отсутствию **VM attachment** к ним, не к уничтожению сетей хоста.
