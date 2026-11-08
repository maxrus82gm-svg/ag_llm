# S1 reconciliation — точные constructions, callers и endpoint origins

TASK `CODEX-RT002-B2-S1-INVENTORY-RECON-001`; STRICT OFFLINE.
Authority этой записи — локальные source hashes, исходный RED и финальный guarded run;
не утверждение нового production route или полного S3b coverage.

| Site identity (module / owner / kind) | Ранее | Теперь / multiplicity | Источник и доказательство |
| --- | --- | --- | --- |
| server.py / ask_gigachat / client.post | LLM | LLM / 1 | CHAT_URL; два MCP callers gigachat_ask / gigachat_file_task; прежние transport/AST tests сохранены |
| server.py / _request_audit_diagnostic / client.post | LLM | LLM / 1 | CHAT_URL; диагностическая LLM-ветвь; прежний wire fake |
| server.py / _run_agent_task_impl / client.post | LLM | LLM / 1 | CHAT_URL; Executor, direct/planner branches; прежний wire fake |
| planner_runtime.py / PlannerSession.call / client.post | LLM | LLM / 1 | CHAT_URL; PlannerSession; прежний wire fake |
| planner_runtime.py / run_planner / client.post | LLM | LLM / 1 | CHAT_URL; прямой режим без production caller; прежний reachability test |
| verifier_runtime.py / _request_gigachat / client.post | LLM | LLM / 1 | CHAT_URL; verifier/final/permission/planner review; прежние fake tests |
| compressor_runtime.py / _request_gigachat / client.post | LLM | LLM / 1 | CHAT_URL; Compressor; прежний wire fake |
| gigachat_transport.py / get_access_token / client.post | OAUTH | OAUTH / 1 | OAUTH_URL; только dummy credential и fake OAuth response |
| web_alarm/launcher.py / import urllib.request | UNKNOWN / RED | LOCAL_HTTP_ORIGIN / 1 | Импорт стека для следующего _get; не физический send сам по себе |
| web_alarm/launcher.py / _get / urlopen | UNKNOWN / RED | LOCAL_HTTP_ORIGIN / 1 | Request(url, Cache-Control:no-store), стандартный GET; fake urlopen фиксирует full_url/method/timeout |
| ordinary_chat_service.py / execute_request / getattr.send | UNKNOWN / RED | CAPABILITY_CHECK / 1 | callable(getattr(transport, 'send', None)); это проверка интерфейса, не отправка |
| ordinary_chat_service.py / execute_request / dynamic.send | Не замечался receiver-анализатором | POTENTIAL_LLM / 1 | Настоящий await transport.send в nested send(); сохранён как будущая физическая граница S3b |
| web_alarm/model_cards.py / BUILTIN_PROVIDERS / Provider.oauth_url literal | Unexplained / RED | Точный metadata AST node / 1 | https://ngw.devices.sberbank.ru:9443/api/v2/oauth; не сетевой вызов |
| web_alarm/model_cards.py / BUILTIN_PROVIDERS / Provider.api_url literal | Unexplained / RED | Точный metadata AST node / 1 | https://api.giga.chat/v1/chat/completions; не сетевой вызов |

В `EXPECTED_SEND_SITES` оставлен прежний публичный контракт восьми утверждённых
physical routes: S2 импортирует его напрямую. Полный S1 oracle сравнивает
**EXPECTED_PRODUCTION_SITES = восемь прежних + четыре явно классифицированных
constructions**. Ни UNKNOWN, ни дополнительная потенциальная отправка не
отфильтрованы. LLM POST=7, OAuth POST=1, дополнительные constructions=4.
Metadata nodes не включаются в число sends.

## Launcher — замкнутая цепочка текущих callers

Production references `_get`: `_already_running` два вызова (root, status),
`_self_test` три вызова (status, root, ui/ultra-chat/capability).
Обе функции вызываются из `run_web_alarm`; его production caller — `main`.
URL строится как `http://{HOST}:{port}/`, HOST — `127.0.0.1`.
В занятой ветви используется bind_port из Launch, в успешной — server.server_port.

`main` выбирает standard_launch/load_launch; standard_port принимает только
цифры 1024–65535 из WEB_ALARM_PORT либо постоянный STANDARD_PORT=8765.
`_profile` требует целый int, запрещает bool и значения вне диапазона; script
profile с port=0 уходит в run_script, не в этот HTTP-path. В fake-тестах нельзя
передать URL/userinfo в штатный port source. Прямой Python API run_web_alarm
аннотирован int, но не является security boundary против произвольного caller.

Семантические AST pins охватывают HOST, STANDARD_PORT, Launch, port/profile/load/main
и HTTP-call цепочку. Полный reference census сохраняет aliases/imports/reflection
и обнаруживает новые callers в любом сканируемом production module. Pins не
рассчитываются из текущих sources во время tests; их нельзя автоматически обновлять
для получения PASS. Reviewed AST/source/line/hash находятся в
`evidence/reconciliation_pins.json` (Python AST 3.12; строки/отступы не authority).

**Граница LOCAL_HTTP_ORIGIN:** подтверждён начальный URL, а не запрет redirects
или environment proxies у urllib. Production использует обычный urlopen;
абсолютная loopback confinement не реализована и не заявлена. Live поведение
не проверялось; возможные proxy/redirect protections требуют отдельного scope.
Ни один настоящий local HTTP listener или browser в этой TASK не запускался.

## Ordinary Chat — потенциальная отправка остаётся видимой

ChatTransport — injected protocol, дефолтного sender нет. execute_request делает
preflight, один await send, deadline/cancel/result processing без retry.
Известный caller — OfflineTestAdapter.execute: chat.execute_request(...,
transport=self._transport); _FixtureTransport.send возвращает deepcopy response.
Это доказывает только текущий fake adapter. Будущий реальный adapter обязан
получить S1/S2 policy approval и S3b guard; POTENTIAL_LLM не означает безопасный,
уже защищённый или новый утверждённый route. Тест вызывает реальный execute_request
с явным memory-only transport и подтверждает ровно одну invocation.

AST pins ChatTransport/execute_request и fixture adapter связаны с reference
census. Новые unknown transport.send, alias.send, getattr.send и execute_request
caller вызывают RED. Даже повтор внутри прежнего execute_request не скрывается:
изменяется pin, а кратность physical-send construction становится 2.

## Metadata endpoints — адресное исключение двух AST nodes

Исключены только два exact keyword values в неизменённой frozen Provider
construction BUILTIN_PROVIDERS['gigachat']. Provider schema и construction
закреплены; endpoint-field consumers в _settings_version, catalog и run_check
сверяются полным reference census. Дополнительный literal даже того же URL в
другом месте остаётся unexplained. Новое чтение .api_url/.oauth_url в любом
сканируемом module также требует reconciliation.

Данные выходят в settings version/provider display. run_check может передать
provider.api_url в CheckRequest для **injected authorized checker**. Default
LiveCheckNotAuthorized.authorized=False возвращает LIVE_CHECK_NOT_AUTHORIZED,
network_calls=0 до checker.check. Fake test доказывает, что default checker не
вызван. Инъектируемый checker — потенциальная extension boundary, а не разрешение
платного вызова или доказательство его защиты. Pins init/run_check/default checker
не позволяют незаметно изменить этот факт. Общего исключения provider URL нет.

## Негативное доказательство и пределы

18 in-memory source mutations прогоняют **два настоящих S1 oracle test methods**;
assertions дополнительно требуют testsRun=2 и SKIP=0. Каждая mutation даёт
реальный inner FAIL с traceback, сохранённым в checks.result.json/stdout.
Внешние 23 checks зелёные потому, что ожидаемый RED подтверждён; три ослабления
oracle отдельно превращают эти checks в exit1. Baseline manifest 69 не изменён.

Область сканера прежняя: корневые .py и web_alarm/*.py с отдельным контролем
не-production fixtures. Не доказывается полная межмодульная динамическая
интерпретация Python, произвольных config/env destinations, exec/plugins,
runtime monkeypatching или враждебной одновременной замены sources. Новые routes
должны пройти отдельный review; S3b охват не считается доказанным этим S1 repair.
