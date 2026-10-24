# Engine compatibility: BLOCKED

Проверка только разрешённых локальных project evidence; engine не запускался, интернет не использовался, profiles/subscriptions/configs пользователя не читались. Наличие/отсутствие установленного V2Ray на всём компьютере не исследовалось.

Источники и их SHA сохранены в `evidence/engine_cached_metadata.json`:

1. `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/preflight.sanitized.json`: исторический v2rayN.exe PID14456 → sing-box.exe PID6984, loopback ports10808/10813; engine SHA256 `ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3`. Это snapshot 17 октября, не наблюдение текущих процессов.
2. `reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/host_discovery_release/inventory.json`, только broker fields: 44,773,888 bytes, PE_AMD64, тот же hash; version metadata unavailable; version/schema REQUIRES_USER_INPUT, route_graph UNSUPPORTED. STATIC_HASH_ONLY «VERIFIED» относится к хешу исторического файла, не к безопасности движка.

Подтверждённый V2Ray executable path/version/source revision/schema hash: **не получены**. Известный sing-box hash не считается соответствием V2Ray source и не даёт права переключать стек. Историческая SOCKS-проверка не доказывает native HTTP CONNECT. Имя UI v2rayN не устанавливает тип/версию запущенного core.

|Требование к настоящему engine|Результат|Чего не хватает|
|---|---|---|
|Native HTTP inbound с CONNECT|UNKNOWN / BLOCKED|Versioned source/docs и offline schema review|
|Единственный outbound с actual next hop literal R:Q|UNKNOWN / BLOCKED|Конкретный protocol/config и код dial/resolution|
|Запрет freedom/DIRECT/chain/fallback/load balancing|UNKNOWN / BLOCKED|Все default paths, outbound selection и failure paths|
|DNS/UDP/IPv6/health/telemetry/companions|UNKNOWN / BLOCKED|Source audit всех hidden connections; будущая OS-проверка|
|Routing precedence и unmatched behavior|UNKNOWN / BLOCKED|Versioned routing implementation и негативные native tests в изоляции|
|Отдельный config/root без user profile|UNKNOWN / BLOCKED|Config loader, environment/CLI precedence, file/search roots|
|Image/version/source/config/token binding|UNKNOWN / BLOCKED|Проверенная поставка, immutable config, actual process token и socket owner|

Поэтому **ENGINE_VERSION_SOURCE_BLOCKED; ENGINE_CONFIG_COMPATIBILITY_BLOCKED**. Ни `freedom`, ни другие предполагаемые V2Ray protocol fields в native-конфигурацию не генерировались. JSON schema этого комплекта описывает наш versioned contract, а не API движка; `native_config=null` проверяется как обязательное значение. Даже заполненные пользователем version/hash/signature-looking fields не открывают gates.

Для продолжения нужен адресно разрешённый локальный snapshot конкретного V2Ray release: бинарник с проверяемым происхождением и SHA, соответствующие исходники/build provenance, версия схемы и docs, перечень dependencies/companions. Не просить секреты/рабочую subscription. До изучения snapshot нельзя обещать engine compatibility или запускать engine для «проверки».
