# Следующий gate для WEB_11 и пользователя

Текущий итог: **OFFLINE_GATE_LOGIC_TESTED; LAB_PLATFORM_NOT_PROVISIONED; HOST_CONFIG_PROOF_PENDING; GUEST_ISOLATION_PROOF_PENDING; NATIVE_WFP_EXECUTION_BLOCKED**. Read-only snapshot — 2026-10-20 18:44:45 UTC, не continuous verification. Native WFP/tunnel/network/E2E не запускались.

## Минимальный следующий шаг

Пользователь выбирает **отдельный уже подготовленный Windows/Hyper-V lab host** и легитимное offline Windows media. Передать verifier только допустимые metadata/hash references; private host identity/root/ledger остаются у оператора. Выбор не разрешает никаких установок, reboot или VM действий на рабочем компьютере.

Следующая отдельная TASK должна сначала адресно подтвердить platform version/selector semantics, ownership нового root, квоты, media source/license/hash, инструменты host/guest observation и возможность закрыть **все** relay channels для этого backend. Нужны доказанный basic console и отсутствие PowerShell Direct; если это нельзя обеспечить per-VM в выбранной конфигурации — BLOCKED, иной lab design, не глобальные изменения текущего Windows.

Только после review конкретного неплейсхолдерного dry-run пользователь отдельно может дать GO на:

1. Создание ровно одного нового owner/root/ledger и OFF VM с actual returned GUID, local exclusive disk/media.
2. Удаление NIC и настройку integration/data/device channels **только этой VM**, без switches/NAT/bridge/host network changes.
3. После host-side preboot acceptance — controlled baseline boot, guest-only collection и локальные fixture controls без MCP/WFP/native subject.
4. Clean owned checkpoint, проверку восстановления, signed host/guest evidence + независимый review, stop/quarantine/cleanup **только принадлежащих lab ресурсов** по exact GUID/root/ledger.

В GO должны быть: task/owner/GUID-or-create-and-return constraint, lab host/build/root, exact assets/raw hashes, CPU/RAM/disk/time/attempt quotas, permitted per-VM operations, privileges, срок, observer/stop authority, incident handling, retained evidence и границы удаления. Сейчас ни один из этих lab actions не выполнен. Даже выключение VM требует будущего адресного полномочия; текущая TASK этого не даёт.

Риски будущего provisioning: default NIC при создании, enhanced/PSDirect/host-device relay, foreign/remote backing chain, shared writable base, subject outside guest, неполный observer, TOCTOU, cleanup чужого ресурса. Контроли и порядок в `lab_build_plan.md`. Если требуется установка/включение Hyper-V, SDK/драйвера/feature либо reboot на host, нужен **отдельный явно перечисленный host-change USER GO**; нет автоматического fallback/дозагрузки.

## Ещё один отдельный gate: native WFP

Все шесть prerequisites из БЛОКА 1 §5F обязательны: идентифицированная disposable VM; независимо доказанная внешняя изоляция с negative controls; trusted baseline/quota/clean checkpoint/private ledger/recovery; exact WFP source/binary и privilege/ACL review; WEB_11 acceptance конкретного lab evidence; отдельный USER GO на exact native cases/max attempts/duration. Только новая TASK после этого может создавать guest Windows identities и пробовать WFP filters. Offline PASS нынешнего checker не заменяет ни один пункт.

MCP activation, hosted tunnel, native tunnel-client, V2Ray route и ordinary ChatGPT E2E сюда не входят. `HOSTED_TUNNEL_ON_HOLD_BY_USER`, прежние `CanApply=false`, Install/Uninstall BLOCKED сохраняются. Ни ключи в чат, ни прямой Windows egress, ни изменения V2Ray не нужны для следующего **offline lab-preparation review**.

## Что передать WEB_11 сейчас

Весь каталог TASK с `report.md`, `manifest.json`, исходниками, actual BLOCKED receipt, host inventory, final 52-case suite и двумя killed mutants, сохранённым initial red, manual engineering review и receipt ротации. WEB_11 независимо сверяет hashes, собственным offline прогоном проверяет positive/negative controls и оценивает ограниченную готовность инструмента. Пользователь публикует/передаёт; Codex Git/GitHub и сообщения в другие чаты в этой TASK не использовал. Независимая приёмка не объявлена.
