# AMENDMENT 03 — диагностика WUA в host/mode

TASK: CODEX-WUA-0-DESKTOP-MCP-E2E-001. Codex 007. 16 октября 2026,
Asia/Yekaterinburg (UTC+05:00). Режим: READ-ONLY DIAGNOSTICS.

**DESKTOP E2E NOT VERIFIED.** Локальный Codex Desktop: настоящие native MCP-вызовы
подтверждены. Причина отказа прежнего плагина найдена в host parser; точная причина
отдельного отрицательного CLI-теста пока не установлена.

## A. Подтверждённые факты

### Конфигурация, сервер и инструменты

Текущий CLI 0.162.0-alpha.17.2 читает wua_desktop_readonly как enabled STDIO.
Command, args и cwd совпадают с plugin/mcp.json после раскрытия PLUGIN_ROOT.
В прямой записи нет enabled_tools/disabled_tools, required или отдельного
startup_timeout_sec. mcp_optional_startup_grace_ms явно не задан.
Конфигурация WUA, package/cache и их SHA сохранены выборочно; другие подключения
и секреты не выводились. Полный config.toml не копировался в TASK.

В текущем локальном Codex Desktop-сеансе модель получила реальные функции:
mcp__wua_desktop_readonly__ping, __list_capabilities, __read_synthetic_context.
Через них, без SDK/терминала, последовательно выполнены четыре настоящих запроса:

| Вызов | Фактический результат |
| --- | --- |
| ping | status=ok, service=web_alarm_server |
| list_capabilities | точные три tools, read_only=true, mutations=false |
| read_synthetic_context(synthetic_wua_desktop_001) | синтетический контекст, совпадающий canonical hash |
| read_synthetic_context(other_task) | TASK_ID_DENIED; в receipt REJECTED, без HTTP-запроса |

Общий session_id: **b8f830274dd449909e3a7d0e3e0fddb2**.
Nonce: b3212ddb73d6150043b643e5104d669d.
Context SHA-256: 27618bee587b4837832c6609c275952f12d4b52aea87ed7a101983946ba1f3d1.
Сверены call_id и события server receipt; 3 OK, 1 REJECTED, 11 событий вместе с
HTTP, storage_unchanged=true, guard_denials=0. MCP protocol: **2025-06-18**.
Ранее SDK согласовывал 2025-11-25; оба действительно наблюдались, ошибки версии
в текущем native-сеансе нет.

Receipt peer_claim: codex-mcp-client 0.162.0-alpha.17.2, identity_trusted=false.
Происхождение теста подтверждается контекстом нашего текущего Codex-сеанса и
настоящими tool calls, а не одним client name. Это **не ordinary Chat** и не
независимая приёмка. Все результаты и копия receipt:
native_codex_calls.json, native_codex_receipt_after.json,
native_codex_receipt_validation.json.

### Логи host и плагин

Из существующего журнала C:/Users/REX/.codex/logs_2.sqlite сделаны только
read-only SELECT; записаны лишь отобранные WUA-строки с маскированием секретов.
Полный журнал не экспортировался. Также прочитаны WUA-строки текущих Desktop logs
из C:/Users/REX/AppData/Local/Codex/Logs/2026/10/16/.

Установка локального плагина завершилась успешно в 12:44:06 по времени пользователя.
Затем host loader зафиксировал пять ошибок разбора его MCP-записи, в том числе
в 12:51:39 и 13:15:33–38:

```text
failed to parse plugin MCP server ... server="wua_desktop_readonly"
error="Agent Plugins stdio command must be a bare executable name or a contained `./` path"
```

В portable plugin/mcp.json command равен абсолютному
M:/GitHub/ag_llm/.venv/Scripts/python.exe. В прямом user TOML тот же абсолютный
command принят. Ошибка относится к plugin parser до запуска STDIO и tools/list,
а не к реализации трёх инструментов. Источник: wua_runtime_log_excerpts.json,
строки SQLite id 12143432, 12146300, 12146309, 12146456, 12146486.

Ранее найденное отсутствие WUA marketplace в CLI listing остаётся наблюдением,
но не доказанной первопричиной. Новый журнал даёт более конкретный диагноз.
Прежние SDK/doctor проверки обходили этот host parser и не выявили несовместимость
portable command. Это предел предыдущей проверки, который теперь явно исправлен
в выводах; пакет и адаптер не переписаны.

### Готовность и каталог

Desktop logs показывают успешные starting → ready для прямого WUA без failureReason.
Наблюдавшееся ожидание: примерно 1.97–4.60 секунды. Для текущего Codex thread
01a1407b-08b1-7360-9979-23c93793c3c7: starting 18:09:25.718,
ready 18:09:30.315. Внутренний журнал для нескольких других локальных thread/start
содержит `using cached MCP catalog without waiting for startup server_name=wua_desktop_readonly`.
Эти строки не содержат самого списка tools; dynamic_tool_count=0 в соседнем
контексте не использован как доказательство пустого MCP-каталога.

Журнал WebSocket 10013 относится к codex_api Responses, включая текущий Codex
thread; позже этот же локальный агент успешно вызвал WUA. Это исключает вывод,
что одна такая ошибка неизбежно делает локальный MCP недоступным. Первопричина
самой сетевой ошибки не исследовалась изменением сети; её причинная связь с
отдельным отрицательным CLI-сеансом остаётся недоказанной.

### Два receipt около 18:02

Оба сохранены побайтно до любых новых вызовов:

| session_id | Время создания, Asia/Yekaterinburg | Состояние |
| --- | --- | --- |
| 18771be5e4e944bda650db3f81bda963 | 18:02:03.661 | ready, events=[], event_total=0 |
| 6a23a2f3f6d04ca4b0d46ff1c1cb8d92 | 18:02:03.733 | ready, events=[], event_total=0 |

В runtime.py:128 `ready` записывается после bootstrap временного HTTP fixture,
**до создания MCPServer и до MCP initialize** в server.py:46. Поэтому эти файлы
доказывают создание двух fixture instances, но не успешный handshake, tools/list
или вызов Chat. Клиент, PID и идентификатор host в ready-receipt не сохранены;
peer_claim появляется только при tool_started.

Поиск этих ID в сегодняшних runtime/Desktop logs не дал совпадений. В SQLite
во временном окне 18:01:30–18:03:00 вообще нет строк. Связь с сообщённым CLI-тестом
возможна по времени, но не доказана. Принадлежность двух instances прямой записи,
плагину, retry или разным клиентам установить из имеющихся данных нельзя.
Отсутствие closed не доказывает, что процесс сейчас жив. См. session_provenance.json.

## B. Причина недоступности WUA

| Ветка / гипотеза | Степень подтверждения | Доказательства и предел |
| --- | --- | --- |
| Установленный portable plugin отвергнут из-за абсолютного command | Установленная причина для зафиксированных plugin load failures | Пять прямых ошибок host parser, совпадающий mcp.json |
| Прямой сервер не успевает попасть в каталог первого запроса | Наиболее сильная гипотеза для отрицательного direct CLI | ready через 1.97–4.60 s; cached catalog without waiting; отсутствие явного startup grace. Но raw catalog отрицательного CLI отсутствует |
| Целевой обычный Chat не использует локальный Codex executor | Вероятная отдельная граница host/mode; не доказана универсально | ordinary Chat отрицателен по отчёту пользователя; native local Codex положителен; локальный stdio требует подходящего исполнения |
| Модель проверила буквальное dotted имя вместо доступного native имени / не выполнила tool call | Дополнительная гипотеза | Ответ CLI — текст модели, а не сам raw tool catalog; настоящее имя здесь mcp__wua_desktop_readonly__ping. Исходный JSON trace не найден |
| Конфликт прямой записи и плагина | Не подтверждён | Plugin отклонялся до запуска; direct работает при сохранённой plugin enabled-записи. Нет ошибки collision/duplicate в найденных WUA-строках |
| WebSocket 10013 блокирует WUA | Не подтверждён | Сетевой сбой Responses и native MCP успех наблюдались в одном локальном Codex thread |

[OpenAI Docs MCP](https://learn.chatgpt.com/docs/extend/mcp) документирует отдельное
ожидание optional MCP перед формированием каталога: default grace 1000 ms;
0 ждёт индивидуальный startup timeout. Это согласуется с timing-гипотезой,
но не превращает её в установленную причину конкретного CLI-теста.
Его stdout/stderr и raw catalog запрошены у пользователя; новый модельный CLI-run
в этой диагностике не запускался.

Локализация по шести уровням:

1. Загрузка direct config — PASS по CLI get и текущим native tools.
2. Обнаружение direct server — PASS; plugin metadata/install успешны, его MCP parse
   FAILED в зафиксированных логах. Отдельный CLI marketplace list пуст.
3. STDIO initialize — PASS в текущем local Codex (host logs и protocol receipt).
4. tools/list — три native descriptors доступны агенту; сохранённые SDK данные также
   показывают три. Raw tools/list отрицательного CLI не получен.
5. Передача агенту — PASS здесь, отрицательное сообщение модели в независимом CLI
   требует trace для точного разграничения каталога/решения модели.
6. Обычный Chat — NOT VERIFIED; локальный Codex PASS не переносится на него.

## C. Сравнение режимов и двух механизмов

| Режим | Фактическое состояние | Источник |
| --- | --- | --- |
| Обычный ChatGPT Desktop после Restart | Пользователь сообщает tools unavailable, 0 вызовов; E2E не подтверждён | AMENDMENT 03; новый ordinary Chat здесь не запускался |
| Текущий локальный Codex Desktop | PASS: три native tools и отказ other_task, 4 реальных calls | native_codex_calls + сверенный receipt |
| Отдельный локальный Work | NOT RUN | Не заменяется тестом Codex |
| Независимый Codex CLI --ephemeral --sandbox read-only | По сообщению пользователя: unavailable, 0 calls; точный слой не определён | Нет сохранённого raw trace в найденных материалах |
| SDK по зарегистрированным значениям | Ранее PASS, три calls | registered_stdio_check_01.json; не Desktop E2E |

Прямой STDIO берётся из mcp_servers.<name>; portable plugin сначала проходит
проверку package/manifest, затем получает собственный MCP launch. Одинаковые строки
command не означают одинаковую валидацию этих механизмов. Документация описывает
[plugin-provided servers](https://learn.chatgpt.com/docs/extend/mcp) отдельно от
user config и [локальные каталоги](https://developers.openai.com/plugins/build/plugins)
для поддерживаемых локальных клиентов. Desktop-only требует потока с локальным
исполнением: [официальная граница](https://developers.openai.com/plugins/deploy/desktop-only).

В текущем config сохранены одна прямая WUA-запись и enabled plugin. В старом Desktop
логе есть отключение wua_desktop_readonly-2 в 15:33:40; сейчас такой direct записи
в прочитанном config нет. Нельзя приписывать это действие данному агенту или считать
исторический суффикс действующим конфликтом. Ни одна запись не изменена.

## D. Минимальное исправление — только предложение

Работающую прямую запись и адаптер сохранить. Не нужно менять сеть, permissions
или переустанавливать пакет для проверки direct MCP.

Первый предлагаемый шаг после отдельного разрешения — новый независимый CLI gate
с **одним временным override**, чтобы WUA был обязательным при старте:

```powershell
codex exec --ephemeral --sandbox read-only -c 'mcp_servers.wua_desktop_readonly.required=true' --json "Вызови настоящие инструменты WUA ping, list_capabilities, read_synthetic_context для synthetic_wua_desktop_001 и проверь отказ other_task. Используй фактические доступные MCP-имена, без SDK или shell-замены. Покажи session_id, nonce, context_sha256 и proof_path; при отсутствии tools сообщи об этом."
```

Это предложенный тест, **не выполнен**. Override только для нового CLI-run,
не запись в config.toml и не расширение sandbox/прав. Он проверит гипотезу
раннего каталога. До запуска следует предусмотреть вывод JSON/stderr только в TASK
и исключить секреты других серверов из публикуемой выдержки.

Если понадобится именно плагин, отдельно исправить лишь его launch manifest:
допустимый bare executable либо contained ./ launcher с подтверждённым runtime
и mcp 2.2.0. Простая замена на python без проверки PATH не предлагается как готовое
исправление. Этот ремонт не нужен для работающей direct-ветки; здесь не применялся.
Не предлагать duplicate-cleanup как доказанное лечение: конфликт не установлен.

## E. Следующий проверочный gate

1. Независимый verifier может сразу сверить native_codex_calls и копию receipt:
   3 OK, TASK_ID_DENIED для other_task, nonce/hash/storage и происхождение local Codex.
   Это приёмка лишь локальной ветки, не ordinary Chat.
2. После отдельного разрешения выполнить предложенный CLI gate с machine-readable
   trace и WUA-логами initialize/tools/list/tool calls. Если ready есть, но tools
   нет у агента, проблема остаётся в catalog/exposure; если initialize не проходит,
   анализировать конкретную ошибку запуска. Само сообщение модели недостаточно.
3. В обычном ChatGPT выполнить четыре настоящих MCP-запроса теми же tools,
   без SDK/shell. Записать точный режим, время, session_id, nonce, hash и proof_path.
   Никакой перезапуск в рамках этой диагностики не предлагается к исполнению.
4. Только после независимой сверки ordinary Chat receipt возможна смена общего
   статуса. Отсутствие tools сохраняется как отрицательный результат; local Work,
   Codex или SDK не подставляются вместо него.

**DESKTOP E2E NOT VERIFIED.** Конфигурация, installed cache, адаптер, production,
сеть и системные права не менялись; существующие процессы не перезапускались.
Записаны только диагностические артефакты в этой TASK и штатные audit receipts её
синтетических read tools. Публикация ON HOLD; независимая приёмка не объявляется.
