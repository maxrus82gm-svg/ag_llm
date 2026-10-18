# Gate D — Isolation Preflight Contract v1 (проект)

**ISOLATION PREFLIGHT CONTRACT PARTIAL. OS/HYPERVISOR ISOLATION NOT VERIFIED.**
Контракт конкретизирует необходимые артефакты и отказ по умолчанию. Exact
backend/version, observer toolchain и их readback semantics ещё не проверены:
контракт нельзя использовать как уже испытанный автоматический security gate.

## Вход и право запуска

Новый gate request должен содержать TASK/owner, точный VM GUID, hypervisor
product/version/build, host trust identity (в приватном lab ledger), guest image
и disk-chain IDs/hashes, нормализованный config digest, staged asset manifest,
observer hashes/version, разрешённые process hashes/argv/environment **без
секретов**, порты fixtures, режимы клиента и UTC validity interval. Политика:
все required facts присутствуют и истинны; UNKNOWN, пустой список без proof,
stale evidence или ошибка observer = BLOCKED. Нет default PASS.

Отдельное письменное USER GO связывает digest этого request, VM GUID, список
native cases, maximum attempts/duration и approved hashes. GO на подготовку VM
не разрешает native запуск. Independent verifier подтверждает **этот** snapshot,
не похожую VM из прошлого. Переходы: DRAFT → STAGED/OFF → HOST+GUEST REVIEWED →
AWAIT USER GO → ONE APPROVED RUN → OFF/QUARANTINE → REVIEW. Нет auto-resume.

| ID | Требуемое evidence до native | Условие PASS | BLOCKED/STOP |
|---|---|---|---|
| I01 identity | Host-side GUID/product/build/config export; guest baseline ID, UTC | Один owner; все ID и digest совпадают с review+GO | Несовпадение/другая VM/недоступный host view |
| I02 virtual hardware | Host runtime device census **всех** adapters/backends, включая legacy NIC/passthrough | Zero NIC objects и zero switch/NAT/bridge/host-only/forwarding attachments | Disconnected NIC тоже не принимается; неполный backend census |
| I03 other channels | Integration service/device inventory, console session/redirection mode, serial/named-pipe/guest-agent/shared-folder/clipboard/USB/GPU/hostbus readback | Отсутствуют guest→host relay/data bridges; basic console без редиректов; нет live host disk mount | Defaults, неизвестный integration channel, enhanced/RDP session, PowerShell Direct |
| I04 storage/media | Owned path inventory, full backing chain + hashes, no remote/reparse paths, attachments census | Только согласованные local VHDX/media, writable guest isolation; input offline read-only; output не подключён как live bridge | Writable shared/base disk, UNC, чужой parent, одновременное host mount |
| I05 guest corroboration | Read-only adapter/PnP/IPv4/IPv6/routes/DNS/proxy/device/service census | Только loopback network; нет nonloopback adapters/gateway/resolver/relay; согласуется с host | Guest-only route claim или конфликт host/guest |
| I06 assets | Size/SHA-256 всех EXE/scripts/runtime/fixtures/observer; official source archive verified; audit closure | Exact hashes, trusted origins, offline deps, audited local-only startup mode, no auto-install | Источник отсутствует, source→binary limitation не принято verifier, команда/режим неизвестны |
| I07 credentials | Sanitized schema/allowlist, empty disposable user/profile, no inherited host credentials, original launcher untouched | Ни API keys, ни real tunnel_id/token/hosted profile; только fake local protocol data | Real credential/profile, secret в argv/log, попытка auth/browse to real endpoint |
| I08 observer | Version/hash/coverage/loss counters, startup before subject, monotonic timestamps + host/guest correlation, trace retention | Видны socket/DNS/process attempts и children, включая refused/guard-denied; fixture logs сопоставимы | Нет журнала syscall attempts, event drop, observer restarted/failed, ledger silence без независимого oracle |
| I09 fixture readiness | Exact literal loopback addresses/owned ports/processes, bounded self-check **внутри guest** без subject | Собственные echo/fault endpoints, не live V2Ray; не используют DNS/remote destinations; cleanup известен | localhost wildcard/unknown listener/port takeover/forwarder с внешним upstream |
| I10 descendants | Source startup graph + approved root/helper hash manifest + independent process create/exit inventory | Каждый процесс в guest; Cloudflared не включён; неизвестный child запрещён контрактом и фиксируется как STOP | Child outside guest, unapproved helper/browser, наследуемые секреты/IPC |
| I11 lifetime/change | Host config-change watch, guest observer continuity, heartbeat/time-budget, power-control ownership | Запрет изменения VM devices/config до power-off; при drift/observer loss host способен остановить owned VM | TOCTOU: readback однажды и свободный reconfigure; потеря контроля/expired GO |
| I12 exit/rollback | Known clean offline checkpoint/disk chain, owned resource ledger, approved shutdown/export/recovery procedure | До старта есть способ остановить VM независимо от subject, сохранить evidence и возвратить только owner state | Нет snapshot integrity/owner/контроля; cleanup требует сброса host network |

## Сбор evidence будущим исполнителем

Для **подтверждённого Hyper-V backend** адресные read-only selectors-кандидаты:
`Get-VM -Id <approved GUID>`; его Id/State/Generation/Version/ConfigurationLocation;
`Get-VMNetworkAdapter -VM <that VM>` (полный вывод, требуется count=0);
`Get-VMIntegrationService -VM <that VM>`; `Get-VMHardDiskDrive`, `Get-VMDvdDrive`,
`Get-VMComPort` на том же VM object; `Get-VMSnapshot -VM <that VM>`.
Версию module, наличие cmdlet/parameter и нормализацию export сначала проверить
offline. Если эти selectors не отражают весь device/IPC graph выбранной версии,
добавить источник или BLOCKED; не выдавать их за исчерпывающий verifier.
`Get-VMNetworkAdapter` не показывает все integration и storage channels.

Внутри guest: `Get-NetAdapter -IncludeHidden`, `Get-NetIPInterface`,
`Get-NetIPAddress`, `Get-NetRoute`, `Get-DnsClientServerAddress`, PnP census;
снимки TCP/UDP endpoints плюс passive process/socket/DNS trace. Только guest
`Get-NetTCPConnection` пропустит короткие/отклонённые попытки: нужен отдельный
observer с проверенной coverage. Его реализация/команды пока не выбраны и
требуют отдельного review, не подменяются Python audit hook на host.

Доказательство physical isolation строится по отсутствию VM device/backend
edges и подтверждённому запрету интеграционных relay, при доверенном hypervisor.
Не проверять запрет внешней связи обращением к public IP, настоящему DNS/OpenAI/
Cloudflare или прокси пользователя. Zero packets в capture не доказывает zero
attempts. Заблокированная OS попытка = attempt observed, не no-attempt.

## Состав итогового receipt будущего gate

`task_id, run_id, owner, vm_guid, host_backend_build, config_digest_before/after,
asset_manifest_sha256, source_archive_sha256, verifier_review_id,
user_go_reference, valid_from/until, process_tree, observer_coverage/loss,
case_id/correlation_id, attempted_destination, fixture_events, result,
stop_reason, shutdown_state, cleanup_receipt`.
Конфиденциальные host IDs остаются в приватном lab ledger; публикационная копия
сохраняет устойчивые псевдонимы и hashes без credentials/raw host configs.

Native fail-closed и VM containment оцениваются отдельно: если клиент пытается
пойти напрямую, но hypervisor boundary предотвращает выход, containment может
сохраниться, **а client fail-closed case FAIL**. Отсутствие такой попытки в
неполном observer не даёт VERIFIED. Текущий gate decision — false;
`preflight_decision.json` перечисляет неполученные доказательства.
