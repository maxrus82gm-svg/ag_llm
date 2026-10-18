# Official tunnel-client source audit — PARTIAL / SOURCE PACK BLOCKED

## Три разных источника

1. **Официальный tag (координаторское evidence).** В текущих документах 34 и 19
   WEB_10 записал независимый exact-tag source review `openai/tunnel-client`
   v0.0.16 → `5f99daabd4aa4a77049e6d81d54a0d8c18335397`. Это прочитанные локально
   выводы координатора, не собственный Git/GitHub read Codex. Точные excerpts и
   hashes canonical источников — `coordinator_findings.json`.
2. **Локальный EXE.** Сохранён AM06 byte audit portable Windows amd64 EXE:
   SHA-256 `4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`,
   CLI commit literal совпадает; build-info main module devel, VCS attestation
   отсутствует. В AM07 EXE только хешировался как защищённый input, не исполнялся.
   Совпадение строки commit не является reproducible build/source attestation.
3. **Локальные исходники официального клиента.** Exact archive
   `tunnel-client-runtime-source-v0.0.16.tar.gz`, expected SHA-256
   `88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`
   не найден в dossier, Downloads/attachments. `source_pack_search.json`.
   Самостоятельный download, Git/API/raw-content обходы не выполнялись.
   **SOURCE PACK BLOCKED**: detailed own source graph audit не сделан.

Собственные исходники `adapter.py` являются отдельным reference prototype,
а не реконструкцией или заменой официального Go клиента.

## Подтверждённые координатором ветви и оставшиеся риски

| Ветвь | Доступный источник факта | Что не доказано локально |
| --- | --- | --- |
| Proxy scheme | Exact tag `pkg/runtimeconfig/proxy.go` по WEB_10 принимает только HTTP/HTTPS, отвергает explicit SOCKS URLs | Native parser error/привязка source→EXE не выполнялись |
| Fixed explicit route | `pkg/transport/proxy.go` задаёт fixed `http.Transport.Proxy`; AM06 embedded docs заявляют ignore NO_PROXY для explicit targets | Все callers/custom dialers/перекрытия не просмотрены по телам source |
| Global/component settings | `pkg/runtimeconfig/config.go` по WEB_10 layers global/component proxies | Полная flags/env/YAML/per-binding precedence, empty refs, file/env overrides |
| Control-plane | Main и secret HTTP transports используют proxy по exact-tag WEB_10 review | Poll/metadata/responses/redirect/retry/reconnect полный граф и fallback |
| MCP | HTTP transport в `pkg/mcpclient/fxmodule.go`, особая Unix-socket ветвь по WEB_10 | Startup/runtime/per-channel/SDK transport и STDIO child network |
| OAuth | Source paths/символы были найдены AM06; local bodies отсутствуют | Discovery/token/metadata/trusted-origin redirects, retries, отдельные HTTP clients |
| Harpoon | Встроенные global/component options и source-path map AM06 | Target-specific routing/discovery/extra native transport, redirects/retries |
| Proxy health | Имена checker/connectThroughProxy/dialTCP из AM06 — только карта | Exact probe destinations, resolver, fallback/health transitions |
| Environment | Embedded docs: без explicit route — HTTP_PROXY/HTTPS_PROXY/NO_PROXY; с explicit route — NO_PROXY игнорируется для affected targets | ALL_PROXY, Windows resolver, все clients/ambient overrides; сами symbols не заменяют source |
| DNS/retries/redirects | Полного matching source pack нет | Нельзя подтвердить все dial paths, запрет direct после error или системный fail-closed |
| Cloudflared/child | Exact-tag supervisor может запускать отдельный EXE при token/managed config; это подтверждено WEB_10 | Child не наследует callback Go http.Transport.Proxy; нужны exclusion proof или отдельное containment/transport evidence |

## Можно ли запретить весь direct одним setting самого клиента

**Не установлено.** Fixed proxy callback для отдельных HTTP transports полезен,
но не OS/process kill switch. Не доказано, что настройки одного экземпляра
охватывают все OAuth/Harpoon/health/native/child paths и каждый default/override.
Нет оснований обещать «global proxy flag делает весь EXE fail-closed».
Нельзя повысить статус на основе symbol names с fallback/direct или результата
отдельного Python adapter.

Для продолжения нужен archive handoff через разрешённый канал, verify SHA/contents/
provenance/dependencies и source-only audit. Native fault execution по-прежнему
запрещён до independently demonstrated OS/process non-loopback deny. В AM07
никакого native, hosted, API key/tunnel ID/OpenAI endpoint использования нет.
