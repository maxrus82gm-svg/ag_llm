# AMENDMENT 05 — V2Ray Proxy Preflight & Isolated Fail-Closed Verification

TASK `CODEX-WUA-0-DESKTOP-MCP-E2E-001` · Codex 007 · 17 октября 2026,
Asia/Yekaterinburg · координатор: ChatGPT «Сервер WEB_10».

**PARTIAL / AWAITING INDEPENDENT VERIFICATION. LOCAL ONLY / GITHUB NOT YET VERIFIED.**

## Итог по обязательным статусам

| Статус | Фактическое основание |
| --- | --- |
| **INBOUND IDENTIFIED** | На `127.0.0.1:10808` подтверждено согласование SOCKS5 без аутентификации; listener принадлежит sing-box, дочернему процессу V2RayN. HTTP CONNECT в этом этапе не проверялся |
| **V2RAY REMOTE ROUTE NOT VERIFIED** | Есть сохранённое GUI-правило PROXY для OpenAI, но загруженный core config/current outbound не подтверждён; внешние запросы запрещены |
| **ISOLATED FAIL-CLOSED VERIFIED — REFERENCE POLICY ONLY** | 19/19 PASS: 17 сценариев отдельной Python TLS/CONNECT-модели и 2 quality controls |
| **REAL CLIENT FAIL-CLOSED NOT VERIFIED** | Настоящий Go tunnel-client в transport-тестах этого этапа не запускался; 8 групп native fault checks BLOCKED |
| **HOSTED TUNNEL NOT STARTED** | Регистрация, ключи и подключения ChatGPT не создавались; hosted run/doctor не выполнялись |
| **ORDINARY CHAT E2E NOT VERIFIED** | Настоящих вызовов ordinary Chat в этом этапе и подтверждённом текущем E2E — 0 |

Это не разрешение активировать туннель. Блокировка
`HOSTED_TUNNEL_ON_HOLD_BY_USER` сохранена побайтно. Существующий launcher,
исторические отчёты, персональный БЛОК 1 и действующая сеть не изменены.

## Источники, scope и provenance

Постановка — `assignment.txt`. Единственная область новой записи — настоящая папка
`reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/`;
disposable TLS fixtures создавались в отдельном проверенном TEMP и удалены.

Маршрут актуальных документов: 08 → 000 → 34 → 18 → 01; профильные 19, 23,
36, 36.1, 36.2, 37 и собственная карточка; dossier и предыдущий localhost bridge.
Прочитаны текущие статусы и применимые архитектурные/нормативные разделы, не
перенесены в работу старые архивные назначения. `inputs.json` фиксирует 22 входных
файла и их byte SHA-256; `rules_read.json` — 17 адресных определений с selectors,
contract, requires и source hashes. Правила frozen БЛОКА 1, локального handoff,
изоляции, честного evidence и самостоятельного engineering review применены.

`main@917dcec28e5732da96c8ec9eedc774d04f317921` — **ревизия, предоставленная
координатором**, не самостоятельно сверенный Git HEAD. Git, `.git`, GitHub и
отправка сообщений в ChatGPT не использовались. Новое AMENDMENT имеет приоритет
над историческими SELF_PUBLISH/WEB_08-инструкциями карточки.

Официальные ориентиры OpenAI — ранее полученные 16.10 материалы
[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
и [подключение MCP](https://developers.openai.com/plugins/deploy/connect-chatgpt).
Новая внешняя проверка документации **NOT RUN** по запрету внешних запросов.
Справка проверенного установленного tunnel-client прочитана заново локально;
`official_*.txt`, `versions.json`. Это не независимое подтверждение актуальности
удалённой документации на 17.10.

## Gate A — read-only preflight

Снимок: V2RayN PID 14456 → sing-box PID 6984. Sing-box слушает только обнаруженные
здесь `127.0.0.1:10808` и `127.0.0.1:10813`. Сохранены имена/PID и hashes
исполняемых файлов; command line с приватными данными не экспортировалась.

Для определения протокола на 10808 отправлено **только** SOCKS5 method greeting
`05 01 00`; ответ `05 00`. SOCKS CONNECT, destination, имя удалённого хоста и
credentials не отправлялись. Никакого fault injection на действующем listener.
Это доказывает приём SOCKS5 greeting, не remote reachability или proxy outbound.
Прежнее сообщение координатора об HTTP CONNECT не засчитано как собственная новая
проверка и не доказывает remote route. Evidence — `inbound_protocol.json`.

Core запущен с относительным `-c config.json`. Его действительный cwd/загруженный
файл в разрешённом поиске не установлен. Произвольная копия не объявлена активной;
данные из памяти процесса не извлекались. Этот источник — **BLOCKED**, а не
основание реконструировать или изменять live config.

Отдельно, read-only, изучены GUI JSON и только routing-поля базы V2RayN:

- GUI inbound: SOCKS, порт 10808, UDP/sniffing включены, `RouteOnly=false`, LAN
  выключен; TUN выключен. Эти сохранённые настройки не заменяют loaded core state.
- В on-disk базе девять routing profiles. Один отмечен `IsActive`; его включённое
  domain-правило PROXY содержит OpenAI. Process rule в этом активном snapshot не
  найден. Восемь остальных профилей содержат DIRECT-правила; это **не** доказательство
  их применения к текущему запросу.
- Настроены direct, remote и bootstrap DNS; есть системные proxy exceptions и
  bypass локальных адресов. Реальный путь DNS и действие bypass для tunnel-client
  не установлены. GUI mode хранит числовое 0; значение enum не угадано.
- HTTP_PROXY, HTTPS_PROXY, ALL_PROXY и NO_PROXY в текущем процессе отсутствуют.
  Из этого не выводится состояние всей ОС или других приложений.

База читалась `mode=ro&immutable=1` с query_only; WAL/SHM при снимке отсутствуют,
JSON/основной DB неизменны во время чтения. Даже стабильный on-disk snapshot не
удостоверяет выбранный runtime outbound. Никакие subscriptions, remote addresses,
пароли или токены не экспортированы. Evidence — `preflight.sanitized.json`,
`gui_policy.sanitized.json`, `routing_summary.json`.

### Выбор proxy у tunnel-client

Установленный v0.0.16 имеет штатные общий `--http-proxy` и отдельные
`--control-plane.http-proxy`, `--mcp.http-proxy`, `--harpoon.http-proxy`.
В per-server MCP URL допускается собственный `http-proxy=...`. Общий заявленный
порядок config — flags → environment → YAML → defaults. Образец enterprise proxy
показывает `http_proxy: env:HTTPS_PROXY`.

Значимые входы: CONTROL_PLANE_BASE_URL/URL_PATH и endpoint overrides;
TUNNEL_CLIENT_CONFIG/PROFILE/PROFILE_FILE/PROFILE_DIR; MCP_SERVER_URL/MCP_COMMAND;
secret references env/file; HTTP(S)_PROXY/ALL_PROXY/NO_PROXY; Harpoon targets,
OAuth trusted origins, Cloudflared managed/token/path и proxy health interval.
Наличие опций не доказывает их точную fallback/NO_PROXY-семантику.

Control-plane обслуживает polling/metadata/responses. STDIO MCP сам не нуждается
во внешнем MCP HTTP; его штатный sample пропускает HTTP OAuth discovery. При HTTP
MCP/OAuth появляются дополнительные origins/discovery, Harpoon может делать
HTTP callouts, Cloudflared — отдельный native transport. Все применимые пути и
per-component/per-server overrides требуют source-level/contained проверки.
Поддержка SOCKS URL данным CLI не выведена из названия `--http-proxy`; нельзя
подставлять `http://127.0.0.1:10808` по одному факту SOCKS5 greeting.

## Gates B–C — изолированный стенд

`isolated_proxy_suite.py` — **эталонная политика на Python, не реализация Go
tunnel-client и не новая production-обёртка**. Два disposable TLS origin и
отдельные CONNECT proxies используют только `127.0.0.1` и OS-selected порты.
Включён Python audit guard: запрещены нелитеральный DNS, не-loopback/чужие порты
и дочерние процессы. Закрытые порты удаляются из allowlist. Рабочий V2Ray в fault
сценариях не используется.

TLS использует собственный временный сертификат с IP SAN 127.0.0.1; системное
доверие не менялось. Private key оставался в disposable TEMP и удалён, не опубликован.
Origin фиксирует физический peer port; он сопоставляется с локальным портом
forward socket прокси. Oracle не полагается на подставленный HTTP header.

Финальный запуск: **19 collected / 19 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, exit 0;
**17 reference-policy scenarios + 2 intentional bypass quality controls**.
Матрица `checks.json` отдельно содержит 38 проверок:
**26 PASS / 0 FAIL / 11 BLOCKED / 1 NOT RUN**; это не 38 сетевых тестов.

| Группа | Что достигнуто реально внутри стенда |
| --- | --- |
| S01 | Успешный TLS/HTTP запрос через CONNECT proxy и корреляция origin socket |
| S02–S06 | Bound/non-listening port, HTTP 503, accept/close, accept/timeout, три retries через тот же proxy; origin не получил запрос |
| S07 | Первый запрос успешен, следующие два CONNECT намеренно оборваны; origin получил только первый запрос |
| S08–S09 | Origin redirect на второй loopback origin снова через proxy; redirect в CONNECT-ответе отвергнут |
| S10 ×3 | Reference policy не принимает ambient NO_PROXY/HTTP(S)_PROXY как замену явному proxy |
| S11–S14 | Конфликт component override, отсутствие proxy, hostname DNS и дополнительный transport отвергнуты до connect |
| S15 | Недоверенный TLS-сертификат отвергнут после CONNECT без перехода на direct |
| Q01–Q02 | Oracle обнаружил намеренный fallback **после реального отказа proxy** и намеренный NO_PROXY-bypass |

В финальном trace — **29 socket connect attempts**, все к 127.0.0.1; это включает
заведомо нарушенные, но полностью локальные quality controls. Ноль внешних запросов
и дочерних процессов. Все serving/handler threads завершены, разрешённых портов
после cleanup 0, TEMP удалён. S15 имеет один ожидаемый fixture ConnectionResetError
после TLS rejection; неожиданных fixture errors 0. Он сохранён в trace и не скрыт
за общим «любое исключение допустимо».

История сохранена: attempt01 18/18; attempt02 19/19; attempt03 19/19; attempt04
19/19 — повторения только после расширения/исправления harness. Ранний SyntaxError
нового preflight helper сохранён отдельно как HARNESS DEFECT, не V2Ray defect.
Тестам не приписаны SDK, MCP или ordinary Chat вызовы.

### Почему native transport checks BLOCKED

Официальный `dev proxy` найден в локальной справке и действительно применялся
в прежнем localhost MCP bridge. Но это не доказательство его fail-closed или
полной сетевой изоляции при новых proxy faults. Для текущего native Go executable
не установлен полный набор возможных outgoing paths; доступны бинарник/справка,
а не проверенные transport sources и принудительная process egress isolation.
Python audit hook не ограничивает отдельный Go process.

Запуск нативного клиента с одними loopback flags при неизвестных background/
override paths не принят за гарантированно изолированный тест. Поэтому восемь
native fault groups **BLOCKED / NOT EXECUTED**, а не PASS. Это не утверждение,
что безопасный dev-тест невозможен; нужна дополнительная доказательная подготовка.
Hosted run, сетевой doctor, реальный tunnel_id и API-key не применялись.

## MANUAL ENGINEERING REVIEW

Полный отдельный review — `manual_engineering_review.md`. Основные выводы:

1. Разделены сокет/protocol proof, сохранённая GUI policy, loaded core routing,
   remote proxy outcome и ordinary Chat. Одно не повышает статус другого.
2. Прослежены реальные аварийные пути Python-модели: connect/timeout, отказ CONNECT,
   TLS trust failure, read/disconnect, retries, redirect и policy validation.
3. Review исправил слабый quality control «просто direct» на реальный отказ→direct,
   stale allowed ports и недожидавшиеся daemon handlers. Исходные результаты сохранены.
4. Model NO_PROXY/DNS/extra-transport checks проверяют **наш explicit reference
   contract**; они не исполняют Go resolver, QUIC, OAuth или config precedence.
5. Python audit — не OS packet capture/kill switch и не защита произвольного native
   binary. Прямой remote egress настоящего tunnel-client не исключён доказательствами.

## Риски, SHARED DOC DELTA и следующий безопасный этап

Открыто: actual core config/cwd, current outbound/Clash mode, DNS/bypass/fallback;
HTTP CONNECT и совместимость HTTP/SOCKS proxy URL; все native Go transport failures,
reconnect/redirect/NO_PROXY semantics и process-wide egress proof. Platform Tunnels
пользователем пока не подтверждён. Полный Desktop E2E остаётся NOT VERIFIED.

**Предложение следующего offline этапа:** координатор предоставляет адресный
проверенный source pack официального tunnel-client именно v0.0.16/build commit
из `official_version.txt`: config/secret resolution, proxy HTTP transport,
control-plane/metadata/poll/response, discovery/OAuth, Harpoon, proxy-health,
Cloudflared wiring и module locks. Без Git/внешних запросов Codex проверяет все
пути и возможность действительно contained dev proxy. Если source audit не
обеспечивает изоляцию, отдельно согласуется подходящее process/container egress
ограничение; действующий firewall/сеть самовольно не менять. Loaded V2Ray config
и выбор outbound устанавливаются отдельным read-only материалом, не угадываются.
Только после этого имеет смысл новый native offline fault gate. Hosted-связь —
другой, отдельно разрешаемый этап, не следствие данного результата.

**SHARED DOC DELTA — только предложение координатору после публикации/review:**
в 34 и профильном 19 отметить AM05 PARTIAL; SOCKS5 inbound identified; сохранённая
OpenAI PROXY policy ≠ verified remote route; 19/19 reference-only tests с двумя
quality controls; actual Go fail-closed BLOCKED; hosted hold intact, ordinary
Chat 0 calls. При необходимости в test profile дать locator на этот узкий
stand/limitations. Общие документы, root TASK status/gate и карточка **не изменялись**.
Production architecture/lifecycle и context library не менялись.

## Публикация, сохранность и воспроизведение

`manifest.json` перечисляет безопасный комплект с SHA-256. Raw GUI config/DB не
копировались: `not_published.json` содержит fingerprints и `EVIDENCE NOT PUBLISHED`.
Публикуются только очищенные snapshots, исходники стенда, summaries и synthetic traces.
Project `.gitignore` и возможные вложенные правила прочитаны без Git: новая папка и
расширения .py/.json/.md/.txt проектными правилами не исключены. Global excludes и
реальный Git status/check-ignore не проверялись; перед commit это проверяет пользователь.
Никакие ignore rules не изменены. GitHub-доступность до пользовательского push
не заявляется. Сообщений WEB_10/WEB_08 не отправлялось.

`integrity.json`: 22 защищённых input hashes неизменны; текущий config.toml
SHA-256 до/после `062150e5b9e1b8e8b786e0baaad1ccacdeff4a7f3d500044258965eebb8ac1ba`.
Это граница данного этапа, не утверждение о состоянии предыдущего дня.
Проверки безопасности/consistency комплекта — `artifact_validation.json`.

Фактическая команда финального стенда:

```powershell
& 'M:/GitHub/ag_llm/.venv/Scripts/python.exe' -I -X utf8 -B 'M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/v2ray_preflight_20261017/isolated_proxy_suite.py'
```

Для независимого повтора сначала скопировать harness в новый disposable каталог
TEMP и запускать копию: исходный сданный `isolated_results.json` не перезаписывать.
Python 3.12.10, OpenSSL 3.0.16, cryptography 50.0.1; никаких установок зависимостей.
Source SHA-256 финального harness — `934c832cc14635a1948ca8ecba560de3d6b1c10487dc03b75f53912a03583579`.
Exact invocation, exit, stdout/stderr и hash — `final_execution.json`.

Пользователь публикует безопасную папку после проверки состава. WEB_10 независимо
проверяет фактически опубликованный SHA и evidence; этот self-review не является
его независимой приёмкой.
