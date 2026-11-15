# REUSE CHECK

| Механизм | Найденное поведение | Решение/изменение |
|---|---|---|
| gigachat_transport | Единственный старый OAuth owner/cache, fixed 25 min, env credentials | Тот же owner/cache; expires_at/identity/TLS/control session. Второго web cache нет. |
| model_registry | Шесть enabled IDs без account entitlement | Не менять ID/registry; caps/versions — evidence-bound ModelContract, account catalog отдельный факт. |
| ordinary_gigachat_transport | Sealed MockTransport, closed create_real_transport | Mock class сохранён; factory строит network adapter только с session capability. |
| ordinary_chat_service | Immutable prepare, common parser, deadline/cancel, safe errors | Использовать; ProviderResponse расширен optional observed_model; usage сохраняется и при ошибке transport envelope. |
| OrdinaryCoreAdapter | Общий loader/freezer/restorer, reasoning subset | Тот же adapter, for_provider constructor, exact transport types, cached usage propagation. |
| TurnService | Owner, Run Store, S2/S3a, RAW, restart/replay | Тот же автомат и schema v2; additive provider admission/diagnostics/version; no-sender recovery reader. |
| ultra_budget_policy/ledger | HARD_BOUND, durable reserve/SENT/UNKNOWN/cached | Не изменены. Сессионный authorization record считает разрешённые control calls и grant envelope; не подменяет inference ledger и не вычисляет billing. |
| context_storage/audit_storage/run_store | Existing writer/no-follow/history/immutable RAW | Не изменены; используют только synthetic TEMP. Fresh enrollment — существующий initialize; historical adoption HOLD. |
| chat_context.py | Назван в постановке; такого файла в локальном checkout нет | Фактический Ordinary loader — OrdinaryCoreChatService._chat_context в web_alarm/ultra_chat.py. Переиспользован; legacy context не изобретается. |
| provider_accounting | Shared canonical JSON/attempts | Не изменён; H37 compatible billing принят, cached optional интегрирован без смены формулы. |
| server/EVM/UI | Normal create_server(ordinary_factory), per-chat model route, TEST metadata | HTTP сервер не изменён; существующая factory composition, EVM/registry сохранены. UI дополняет статусы/доступность/cache. |
| Tkinter/launcher | Отдельная Tk оболочка, два web CMD и fake TEST | Исходники Tk/launcher/config/CMD не изменены; shared core signatures обратно совместимы. |

Новый gigachat_runtime нужен для отсутствовавшей production server authority, exact live transport и ограниченной OAuth/catalog session. В нём нет нового history, parser, context compiler, Chat/Turn state machine или расчётного ledger. Legacy agent/tool paths не переводились в REAL.
