# Возможности настоящих движков: UNVERIFIED

Здесь нет выводов по памяти модели или текущим web-страницам. Versioned authentic source/docs/schema в разрешённом material не найдены/не предоставлены. Embedded module names/dependencies и Python-модель не являются доказательством native behavior.

|Требование|sing-box file с claim v1.13.4|V2Ray Core|
|---|---|---|
|Native HTTP CONNECT inbound|UNVERIFIED: нужна matching inbound implementation/docs|UNVERIFIED: конкретного release нет|
|Один inbound → один outbound|UNVERIFIED: routing selection и default paths не исследованы|UNVERIFIED|
|Literal approved next hop R:Q|UNVERIFIED: нужен конкретный encrypted/authenticated remote protocol, dial/resolution audit|UNVERIFIED|
|Unmatched → deny, proxy failure без DIRECT|UNVERIFIED: нельзя выводить из конфигурации нашей модели|UNVERIFIED|
|DNS/UDP/IPv6/health/telemetry/companions|UNVERIFIED: compiled tags не отключают hidden dials|UNVERIFIED|
|Отдельный config/root, env/CLI precedence|UNVERIFIED: config loader/implicit files не проверены|UNVERIFIED|
|Тот же PID владеет CONNECT и remote socket|UNVERIFIED: нужны source paths и позже независимый OS observer|UNVERIFIED|
|Непривилегированный B SID|UNVERIFIED: Windows token/rights не проверялись|UNVERIFIED|
|WFP exact-port/flow enforcement|Не свойство version string; NOT VERIFIED|NOT VERIFIED|

Generic broker contract уже проверяет намерение C→127:P, same B PID→R:Q, запреты resolver/direct/fallback, freshness и spoofed owner. Это отдельный уровень, не native-config compatibility. В этой TASK **ни одна capability не получает SUPPORTED**. UNVERIFIED не означает UNSUPPORTED.

Native schema check: **NOT RUN / ENGINE_NATIVE_CONFIG_SCHEMA_BLOCKED**. Новый mock native config не создавался. `compatibility_gates.json` показывает отказ существующего family contract и сохранение can_apply/can_start_tunnel=false.
