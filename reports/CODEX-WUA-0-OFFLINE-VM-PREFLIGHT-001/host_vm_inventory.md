# Gate B — bounded read-only inventory

**VM PLATFORM INVENTORY PARTIAL.** Evidence: `host_inventory.json`,
`local_file_inventory.json`; воспроизведение — `collect_host.ps1` и
`collect_local_files.py` (повторный запуск отказывается затирать первый результат).
Ни одна команда гипервизора/VM не запускалась; чтение CIM/registry/file metadata
не устанавливает и не активирует компоненты.

| Источник | Факт 2026-10-18 |
|---|---|
| Win32_OperatingSystem | Windows 10 Pro, 10.0.19045 / build 19045, x64 |
| Win32_ComputerSystem | ASRock Z790 Pro RS; HypervisorPresent=false; RAM 34,175,574,016 B |
| Win32_Processor | Intel i5-12400F; AddressWidth=64; VirtualizationFirmwareEnabled=true; VMMonitorModeExtensions=true; SLAT=true |
| Win32_OptionalFeature | 12 отобранных компонентов, все InstallState=2: Hyper-V (включая hypervisor/tools/management), HypervisorPlatform, VMP, WSL, Sandbox, Containers |
| Локальная CIM-схема | ValueMap 1/2/3/4 доступен, текст Values не предоставлен; человекочитаемое состояние по одному коду здесь не утверждается |
| Installed-products registry | В 3 стандартных HKLM/HKCU uninstall roots нет DisplayName VirtualBox/VMware/QEMU/Hyper-V/Parallels/Docker Desktop |
| Services / drivers | Отфильтрованные vmms/vmcompute/VBox/VMware services и VBox/vmx86/vmnet drivers не найдены |
| Hyper-V module | `Get-Module -ListAvailable -Name Hyper-V`: пусто; модуль не импортировался |
| Стандартные бинарники | 7 проверенных путей Hyper-V, Sandbox, VirtualBox, VMware, QEMU отсутствуют |
| PATH | 8 имён CLI не найдены, что само по себе **не доказывает отсутствие продукта** |
| VM-конфигурации / Windows media | В 8 перечисленных roots поиска нет VMX/VBOX/VMCX/WSB/VirtualBox.xml и ISO/WIM/ESD |
| Ошибки queries/search | 0 сохранённых ошибок; глубина/skip/отсутствующие roots перечислены в evidence |

Из совокупности источников не подтверждена готовая локальная платформа или
доступная существующая VM. Не утверждается, что portable/нестандартная установка,
VM на другом диске или ISO вне read_scope невозможны. HypervisorPresent=false
и CPU flags не заменяют проверку конкретного гипервизора; firmware не менялась.

Не подтверждены offline Windows install image, его release/hash/license,
Hyper-V provisioning payload, точная версия hypervisor/backend, свободный
TASK-owned storage, доверенный guest baseline, guest Python/runtime dependencies,
guest observer/trace tools. Показатель RAM не является разрешением резервировать
ресурсы. Запросов повышения прав не было. Нет заблокированной попытки WMI,
которую мы выдали бы за отсутствие продукта.

Готовый VM runtime проверить не удалось: он не обнаружен, а запуск/создание
запрещены. Инвентаризация остаётся PARTIAL, несмотря на успешные bounded queries.
Никаких выводов о текущем протоколе V2Ray inbound или его remote route из этой
инвентаризации не следует; сеть и конфигурации V2Ray не опрашивались и не менялись.
