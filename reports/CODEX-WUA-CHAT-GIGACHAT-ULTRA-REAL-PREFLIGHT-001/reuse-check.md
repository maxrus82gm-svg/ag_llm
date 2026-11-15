# REUSE CHECK — до изменения runtime, 2026-11-15

| Область | Найденный владелец | Решение |
| --- | --- | --- |
| Модель | model_registry.get_model_spec; Ordinary prepare_request/_model; TEST per-chat metadata в ultra_chat; STANDARD OrdinaryProviderFactory.MODEL_ID | Сохранить registry и STANDARD единственную Pro; Ultra уже есть в TEST. |
| Финальные bytes | ordinary_chat_service.prepare_request; PreparedRequest; provider_accounting.canonical_json_text; policy.serialize_request_body | Использовать существующий immutable serializer. |
| OAuth | gigachat_transport.get_access_token, require_real_authority перед cache/env/HTTP | Сохранить единственный gate; не активировать старый cache/refresh. Cache не account-bound, TTL 25 минут вместо проверки expires_at; trust_env/default transport нуждаются в отдельном review до LIVE. |
| Физический HTTP | ordinary_gigachat_transport.GigaChatTransport.send_bytes, exact OfflineHTTPFixture, MockTransport | Сохранить один byte transport; добавить только закрытый конструктор real и read-only диагностику неполного контракта. Реальный клиент не строить. |
| Admission | TurnService/_TurnAdmission для ordinary; gigachat_admission._ServerAttempt для legacy | reserve/readback → SENT/readback → token → final physical check. Все capabilities остаются процессными и synthetic TEMP-only. Не менять shared Turn/Run/ledger. |
| Ошибки/учёт | execute_request/parse_response/_usage; provider_accounting; BudgetLedger terminal/recover | Переиспользовать UNKNOWN/liability/replay; reasoning не прибавлять к total. Не считать synthetic schema доказательством real accounting. |
| Сохранение | OrdinaryCoreAdapter, TurnService, Run Store, RAW/history, metadata per chat | Не создавать storage/schema/Chat Core; проверить существующие сценарии с Ultra. |
| STANDARD | web_alarm.ordinary_provider.require_real/submit_turn | Без изменений; Ultra не включать в STANDARD. |

H33 проверяет exact HTTP bytes и durable terminal, H34 — 7 legacy send-sites; H35 — нормальный application entrypoint и Pro HOLD; H36 — TEST per-chat persistence. Это ограниченные OFFLINE доказательства, не полный S3b/S3c/S9/S13a.

Пробел REAL: подтверждённые output/reasoning caps, account entitlement, bounded authority/enrollment, TLS/proxy/cache/redaction, production recovery/fencing. Полные AST safety gates admission/Turn/bridge/application pinned в S2; менять shared contracts здесь запрещено. Предлагаемая минимальная адаптация затрагивает только два разрешённых transport-модуля и адресные тесты. Она не выдаёт authority, не читает секреты, не вызывает OAuth и не предоставляет обхода HOLD. При недостаточном контракте итог PARTIAL/BLOCKED.
