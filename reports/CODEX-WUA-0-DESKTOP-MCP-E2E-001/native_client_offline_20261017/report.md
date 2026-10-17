# AMENDMENT 06 — Native Tunnel-Client Offline Verification

TASK `CODEX-WUA-0-DESKTOP-MCP-E2E-001` · Codex 007 · 17.10.2026,
Asia/Yekaterinburg · координатор WEB_10.

**Итог: PARTIAL / NATIVE EXECUTION BLOCKED / AWAITING INDEPENDENT REVIEW.**
**LOCAL ONLY / GITHUB NOT YET VERIFIED.**

## Обязательные статусы

```text
SOURCE AUDIT PARTIAL
NATIVE OFFLINE TEST NOT VERIFIED
REAL CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

Установлены байтовая идентичность native клиента, его build/dependency metadata
и адресная карта proxy-related кода. Найдены встроенный контракт explicit proxy
и ограничение HTTP(S) proxy URL. **Безопасная изоляция native процесса не доказана**;
по пункту 7 AM06 настоящий клиент не запускался. Это не доказательство неисправности
клиента и не закрытие незавершённого Desktop E2E.

## A. Подтверждённые факты и provenance

1. Прочитаны действующий маршрут 08→000→34→18→01, собственная карточка/БЛОК 1,
   профильные нормы и AM05 report/manual review/checks. `rules_read.json` содержит
   17 Rule-ID/contract definitions с текущими hashes; источники этих правил
   не изменились после AM05. БЛОК 1 не переписан. Старое SELF_PUBLISH/WEB_08 не
   применялось вопреки AM06/DOC-GIT-01.
2. Через read-only app tool прочитан существующий чат **«Cервер WEB_10»**. Его
   readable summary подтверждает: 19/19 AM05 — Python reference, реальный Go
   fail-closed ещё не проверен. **Formal review text получить не удалось**:
   соответствующее сообщение выдаётся как content-reference placeholder.
   Это ограничение сохранено в `web10_review_excerpt.json`; независимая приёмка
   не объявлена. Сообщений в чаты не отправляли. Project main SHA
   `5f91f7ec35b0a008e2d3a9e0730540731c197d01` — только сообщение координатора,
   не самостоятельно сверенный Git HEAD и не commit самого tunnel-client.
3. Установленный portable EXE:

```text
secure_tunnel_preparation/tools/tunnel-client.exe
Windows amd64 (PE machine 0x8664), 22,591,488 bytes
SHA-256: 4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571
Cached CLI version:
0.0.16+5f99daabd4aa4a77049e6d81d54a0d8c18335397
```

Cached CLI output был получен в предыдущем этапе; в AM06 EXE не исполнялся даже
для version/help. Commit literal найден в байтах EXE, offset 11228448.
Это подтверждает наличие строки, не удостоверяет исходники сборки.

4. Заново проверены сохранённые release metadata/SHA256SUMS, ZIP и EXE внутри ZIP.
   ZIP SHA-256 `edef7241b0c647fcb30f1a80ff376b6b25c51927960f257a3f01e21b17c2aba6`;
   cached release digest, опубликованная ранее сохранённая сумма и byte hash ZIP
   совпадают. Единственный `tunnel-client.exe` внутри ZIP совпадает с установленным.
   Источник cached комплекта — официальный release v0.0.16, дата в metadata
   2026-10-06T22:04:53Z. Удалённая повторная сверка **NOT RUN**: Git/GitHub запрещены.
   ZIP не извлекался на диск; чужие файлы не заменялись.
5. Из Go build info напрямую прочитаны **Go 1.27.0**, main path
   `github.com/openai/tunnel-client/cmd/client`, main module `(devel)`,
   `CGO_ENABLED=0`, GOOS=windows, GOARCH=amd64, trimpath. Dependencies:
   `x/net v0.55.0`, `x/oauth2 v0.35.0`, MCP Go SDK v1.7.0; полный список —
   `go_build_info.txt`. SPDX подтверждает эти module entries для **tunnel-client.exe**,
   отдельно от другого набора зависимостей cloudflared.exe.
6. VCS build settings в build info отсутствуют; SPDX main-module version UNKNOWN.
   Embedded PE certificate directory пуст, detached signature/build attestation
   не предоставлены. **Source↔binary correspondence NOT PROVEN.** Нельзя считать
   build commit доказанным по одной CLI строке или SBOM того же origin.
7. Byte parser извлёк 177 project source file paths, 2340 project name entries
   (включая inline names), 43 выбранных network names. Сохранены offsets/excerpts,
   а не вымышленные Go исходники: `binary_symbols.json`, `binary_excerpts.json`.
   В pcHeader 23923 function entries / 1598 file entries всего; эти числа не
   означают число выполненных функций или тестов.

Исторические официальные ориентиры OpenAI — сохранённые ранее материалы
[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
и [подключения ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt).
В AM06 сетевые запросы native клиента/новая внешняя сверка документации не выполнялись.
Встроенная документация конкретного EXE здесь полезнее предположений по CLI flags.

## B. Реальная proxy implementation: что найдено и что осталось открытым

Полная адресная матрица — `proxy_path_audit.md`. Обнаружены отдельные build paths
общего transport/config/route resolver, control-plane poll/metadata/secret HTTP
client, MCP startup/runtime/per-binding clients, OAuth discovery/redirect/retry,
Harpoon targets/additional transports, native DNS, proxy health и Cloudflared.
Функции/имена файлов дают **карту для source audit**, но не их тела или call graph.
Точный порядок DNS, redirects/retries, component overrides и direct fallback
не доказан. Ошибку/уязвимость tunnel-client по этим данным не объявляю.

Новые конкретные находки из самого поставленного EXE:

- Встроенный `Outbound proxy environments` говорит: **explicit proxy flags
  override environment и ignore NO_PROXY для затронутых targets**. Без explicit
  proxy действует HTTP_PROXY/HTTPS_PROXY/NO_PROXY. Фактическое соблюдение native
  процессом ещё не проверено; ALL_PROXY-семантика не установлена.
- Имеются `runtimeconfig.parseHTTPProxyURL` и literal
  `proxy URL scheme must be http or https, got %q`. Поддерживаемый proxy-контракт
  кандидата — HTTP(S), CONNECT для HTTPS targets. Ветка отказа socks5/socks5h
  не исполнялась. Наличие стандартного `net/http.(*socksDialer)` не доказывает,
  что application config пропустит SOCKS URL.
- Поэтому при **только SOCKS5** inbound потребуется HTTP CONNECT endpoint либо
  отдельный проверенный локальный HTTP→SOCKS адаптер. Если существующий inbound
  mixed и принимает CONNECT, адаптер может быть лишним. Протокол HTTP на live
  10808 в AM06 не проверялся; сам proxy/adapter не создавался.
- `resolveProxyWithFallback` не объявлен сетевым fallback: это может быть config
  inheritance. `proxyhealth.recordDirect` не объявлен прямым dial после сбоя.
  Source review нужен именно для устранения такой неоднозначности.

## C. Поиск точных исходников

В dossier и стандартных Go source/module locations соответствующих `.go`/locks
не найдено. В установленном ZIP только EXE/companion/manifest/licenses/SBOM.
В cached metadata обнаружен **точный следующий источник**:

```text
tunnel-client-runtime-source-v0.0.16.tar.gz
239841 bytes
SHA-256: 88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0
```

Его точный release locator и список нужных файлов — `source_request.md`.
Архива нет в проверенных dossier, Downloads и attachments. Его имя не доказывает
полноту содержимого; сам архив не читался и не скачивался. Исходники соседнего
Cloudflared source asset нельзя засчитать как исходники всего Go клиента.
При получении нужны проверка digest/provenance, фактического покрытия путей,
точных dependencies и честная оценка source↔binary bridge.

## D. Изоляция и native offline-тесты

`environment_inventory.json`: Windows 10.0.19045.0; Docker/Podman/WindowsSandbox/
Go в PATH не найдены, штатного WindowsSandbox.exe нет, `wsl --status` exit 50.
Optional feature states сохранены численно. Это bounded inventory, не доказательство
отсутствия всех возможных решений на машине. **Готовая enforceable loopback-only
граница для Windows EXE не найдена/не доказана.**

Python audit родителя, loopback flags, proxy environment и TCP snapshot такую
границу не создают. Не менялись firewall/DNS/V2Ray/sing-box/permissions/features,
не создавались VM, security profiles, exemptions, tunnels или сетевые адаптеры.
Подробный проект будущей границы — `isolation_design.md`: тот же Windows EXE в
заранее предоставленной disposable среде с OS/hypervisor deny всего non-loopback,
включая IPv6/DNS/children; все фиктивные endpoints внутри, без host proxy bridge.
Это требования к следующему gate, не уже доказанная технология.

**Фактический результат native части:**

```text
native collected/executed: 0 / 0
native PASS / FAIL / ERROR / SKIP: 0 / 0 / 0 / 0
18 case contracts: BLOCKED, not collected tests
tunnel-client processes started in AM06: 0
ordinary Chat MCP calls in AM06: 0
```

`native_test_plan.json` задаёт 18 contracts: positive proxy baseline, unavailable
port, refusal/timeout/disconnect, retries, origin/proxy redirects, explicit/ambient
NO_PROXY, DNS/address families, overrides, OAuth, Harpoon, health/companion, SOCKS
validation, TLS refusal. **Native fixtures/driver не реализованы/не запущены**:
API details должны следовать matching source, а исполнение — проверенной границе.
`native_test_gate.py` только фиксирует BLOCKED, exit **3**, и не содержит executor.
Его отказ не является failed product test и не доказывает product fail-closed.

Собственные parser robustness tests: **5 collected / 5 PASS / 0 FAIL/ERROR/SKIP**,
exit 0; проверены independent Go frame и malformed string/varint/PE boundaries.
Это проверка инструмента byte inspection, **не native networking**. Static audit
exit 0; Python AST syntax gate 4/4 PASS. AM05 Python stand не перезапускался.
Точные команды/выходы — `execution.json`, `static_parser_tests.txt`.
Матрица `checks.json`: **26 evidence rows: 17 PASS / 5 BLOCKED / 4 NOT RUN**;
это не 26 native tests и не замена отдельно указанным 5 parser unit tests.
Первый финальный artifact validator остановился из-за неверного имени codec
`utf8-sig`; original traceback сохранён в `validation_attempt01.txt` как
**HARNESS DEFECT**, не отказ клиента. Исправленный `validate_artifacts.py`
использует `utf-8-sig`; финальная проверка комплекта отражена отдельно.

## E. MANUAL ENGINEERING REVIEW

Отдельный полный review — `manual_engineering_review.md`. Проверены sequence
hash→ZIP bytes→build info/pcHeader→bounded source search, уровни доказательств,
config/default/native background paths, различие SOCKS в stdlib и application,
опасность считать OS-blocked direct dial продуктовым fail-closed PASS.

Отвергнуты: повтор Python-модели вместо Go; happy-path bridge вместо fault proof;
только loopback flags; Python hook как native boundary; рабочий V2Ray как fixture;
самовольные firewall/feature/permission changes; GitHub-download обход запрета.
Открытые native semantics помечены BLOCKED, не PASS по имени функции.

## F. Сохранность, публикация и следующий gate

Новая запись — **только** `native_client_offline_20261017/`. Hash baseline и финал:
**70/70 защищённых файлов неизменны** (`inputs_before.json`, `integrity.json`).
Среди них AM05 комплект, canonical docs/карточка, live Codex config, launcher,
profile, прежний local bridge receipt, AM04 candidate manifest. Config SHA до/после:
`062150e5b9e1b8e8b786e0baaad1ccacdeff4a7f3d500044258965eebb8ac1ba`.
`HOSTED_TUNNEL_ON_HOLD_BY_USER` launcher сохранился побайтно. Это файловое
доказательство, не OS-wide network monitoring. Production/Claude/LLM12 не менялись.

Полные конфигурации/DB/ключи не копировались; безопасные hashes, binary metadata
и адресные evidence находятся в новом каталоге. `.gitignore` прочитан как обычный
файл; проектные правила не исключают новый комплект. Реальные Git index/global
excludes/GitHub completeness не проверялись. **Git/GitHub операций — 0**; публикацию
выполняет пользователь после проверки точного состава. Никакой self-acceptance.

Следующий минимальный шаг WEB_10:

1. Передать указанный runtime-source archive с digest/provenance; восполнить
   недоступный formal AM05 review. Разрешённый source-only audit можно продолжить
   без запуска клиента и без изменения инфраструктуры.
2. Для native execution отдельно предоставить/согласовать проверяемую disposable
   Windows boundary. Сначала доказать запрет non-loopback для native/children,
   затем реализовать и независимо проверить native fault driver/oracles.
3. После native успеха требуется самостоятельная проверка **реального** маршрута
   V2Ray; она не входит в этот offline этап. Hosted и ordinary Chat E2E остаются
   отдельными закрытыми gates, до настоящих вызовов и сверки receipt.

**DOC IMPACT / SHARED DOC DELTA:** общие документы и карточки без изменений.
Координатору после публикации/review можно зафиксировать AM06 PARTIAL: byte identity
проверена, explicit-proxy контракт/HTTP(S) validation найдены в EXE, exact source
pack обнаружен по locator, source mapping/containment/native tests ещё BLOCKED.
Данный отчёт передаётся пользователю для WEB_10; независимую приёмку не объявляю.
