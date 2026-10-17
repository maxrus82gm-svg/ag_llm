# Адресный запрос источников координатору WEB_10

## Первый доступный след — уже известный официальный release asset

В сохранённом `secure_tunnel_preparation/official_release_metadata.json` есть:

```text
tunnel-client-runtime-source-v0.0.16.tar.gz
size: 239841 bytes
sha256: 88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0
```

Его точный locator из cached metadata:
https://github.com/openai/tunnel-client/releases/download/v0.0.16/tunnel-client-runtime-source-v0.0.16.tar.gz

Это **не выполненный запрос** и не независимо перепроверенный сегодня release.
Локально архив не найден: dossier, Go module/SDK defaults, пользовательские
Downloads и `.codex/attachments` проверены ограниченным поиском имён. В Go cache/
SDK defaults соответствующих каталогов нет. Содержимое архива пока неизвестно;
имя runtime-source не доказывает полноту исходников CLI и всех transports.

Следующий минимальный шаг координатора: получить этот asset своим разрешённым
каналом и передать локальный архив с provenance/digest. Codex не скачивает его,
не обращается к Git/GitHub и не расширяет себе права. Также нужны полный текст
формального review AM05 и точный опубликованный SHA для последующей независимой
проверки, если они должны стать нормативным входом: app read_thread для formal
review вернул только content-reference placeholder; readable summary сохранён.

## Какой binary/source bridge требуется проверить

Установлен **Windows amd64**, EXE SHA-256
`4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`
(также в `static_audit.json`).
Cached CLI version: `0.0.16+5f99daabd4aa4a77049e6d81d54a0d8c18335397`.
Этот commit literal действительно найден в EXE, но Go build info не содержит
VCS revision, main module имеет `(devel)`, SPDX version этого module — UNKNOWN.
Полноценной build attestation/reproducible source↔binary proof пока нет.
При получении архива надо сверить manifest/build provenance, не назначить
соответствие по одному имени тега. Даже подходящий source pack сам по себе не
снимает требование принудительной native network containment.

## Приоритетные исходники, обнаруженные в pcHeader/filetab EXE

Пути внутри модуля `github.com/openai/tunnel-client/`:

- `pkg/transport/default.go`, `proxy.go`;
- `pkg/proxy/route.go`, `logging.go`;
- `pkg/runtimeconfig/config.go`, `file_config.go`, `profile.go`, `proxy.go`,
  `oauth_origins.go`, `http_headers.go`, `header_rules_config.go`;
- `pkg/controlplane/internal/tunnel_service_client.go`, `poller.go`, `retry_after.go`,
  `roundtripper.go`, `routing.go`; `pkg/controlplane/metadata.go`, `health.go`,
  `admin/tunnel_client.go`; `pkg/controlplane/fx/fxmodule.go`;
- `pkg/mcpclient/channel_transport_factory.go`, `transport_provider.go`,
  `transport_provider_fx.go`, `stdio_command.go`, `stdio_command_factory.go`,
  `forwarding_transport*.go`, `shared_connection_transport.go`, `fxmodule.go`,
  `internal/roundtripper.go`, `internal/static_headers.go`;
- `pkg/oauth/module.go`, `resource_meta.go`, `auth_meta.go`, `discovery_origin.go`,
  `discovery.go`, `discovery_retry_policy.go`, `hostbundle.go`, `state.go`;
- `pkg/runtimeharpoon/shared_wiring.go`, `fxmodule.go`, `server.go`, `registry.go`,
  `host_registration.go`, `metadata.go`, `discovery_budget.go`, `policy_binding.go`;
- `pkg/proxyhealth/checker.go`, `health.go`, `metrics.go`;
- `pkg/tlsconfig/*.go`, `pkg/httpguard/guard.go`, `pkg/process/process.go`,
  `pkg/app/app.go`, `pkg/runtimecli/runtimecli.go`, `pkg/localproxy/localproxy.go`;
- `pkg/cloudflared/runtime/{supervisor,manifest,state,startup_timeout}.go`,
  `pkg/cloudflared/runtime_adapter.go`;
- `cmd/client/{root_command,run_command,dev_command,stdio_preflight,profile_samples}.go`;
- `go.mod`, `go.sum`, build/release metadata, generated inputs и relevant tests.

Полный список **177 file paths** и 2340 project name entries (включая inline names,
не счётчик исполнявшихся функций) — `binary_symbols.json`.

Зависимости, прочитанные из самого EXE: Go **1.27.0**, `golang.org/x/net v0.55.0`,
`golang.org/x/oauth2 v0.35.0`, `github.com/modelcontextprotocol/go-sdk v1.7.0`.
Нужны соответствующие vendor/module/stdlib transport/resolver тела и locks, если
архив их не содержит. Нельзя подставить исходники последней версии или смешать
с компонентами отдельного cloudflared.exe из того же SBOM.
