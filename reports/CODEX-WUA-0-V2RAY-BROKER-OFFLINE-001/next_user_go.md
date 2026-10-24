# NEXT SAFE ACTION и будущие gates

Сейчас требуется независимый review WEB_11 и пользовательская публикация очищенных report/source/evidence. Не требуется ещё один restart/переустановка плагина или ручной ввод proxy settings: эта TASK их не меняла.

1. **Source gate, без network/run:** адресно предоставить разрешённый локальный snapshot конкретного V2Ray release (не subscription/secret): provenance, binary hash/version/build metadata, matching sources/schema/docs. Проверить семь capability questions из `engine_compatibility.md`, все config/default/env/CLI paths. Сформировать native config только после этого. Другая proxy stack требует отдельного решения.
2. **Isolation gate, отдельный USER GO:** независимое принятие лабораторной OS isolation с доказанным отсутствием прямого внешнего выхода до запуска native engine. Источник одного encrypted authenticated upstream и peer trust/credential delivery должен быть выбран явно. Рабочий V2Ray не использовать как substitute B-owned engine.
3. **Identity/WFP gate, отдельный USER GO в принятой лаборатории:** новые target-local C/B SIDs; защищённые roots; effective tokens + held image/config handles. C только TCP4 127:P, B только literal R:Q, no companion/delegation. Нужен independent observer с request/session/generation/source/image/config/WFP binding; его потеря не может сохранять разрешённый маршрут.

Будущие **не реализованные и не запущенные** native verification selectors (спецификация следующего gate, не зелёные tests):

|Selector|Обязательный эффект/проверка|
|---|---|
|`native_engine_same_B_pid_listener_and_remote_socket`|Реальные B token+image+config и оба socket у одного процесса, receiver correlation|
|`native_no_rule_no_direct_fallback`|Unmatched destination/proxy failure → zero forbidden edges, independent OS observer|
|`native_dns_udp_ipv6_companion_denied`|Неожиданные DNS/UDP/IPv6/health/telemetry/child dials реально отклонены WFP|
|`native_wrong_listener_and_old_receipt_denied`|Takeover/stale/replay не дают C продолжить цепочку|
|`native_config_source_token_drift_stop`|Drift между preflight/startup/runtime прекращает owned chain|
|`native_observer_policy_loss_and_preexisting_flow_stop`|Observer loss, policy restart и существующие flows не переживают fail-closed transition|
|`native_boot_restart_inheritance_no_auto_resume`|Boot/restart/child token/handle inheritance не обходят deny-before-start|
|`native_wfp_arbitration_loopback_exact_port`|Реальное взаимодействие WFP providers/filters, loopback и exact P/R:Q, foreign allow не даёт обход|

Не вызывать их на рабочей Windows. При отсутствии подтверждённой изоляции/USER GO — BLOCKED; не заменять OS proof Python audit hook или SDK smoke test.

4. **Hosted/ordinary Chat gate позднее, отдельный USER GO:** только после native gates и решения пользователя о снятии HOLD. Настоящие ordinary Chat MCP calls `ping`, `list_capabilities`, `read_synthetic_context(allowed)` и отказ для `other_task` с независимой server receipt сверкой. До этого ORDINARY_CHATGPT_E2E_NOT_VERIFIED, HOSTED_TUNNEL_ON_HOLD_BY_USER.
