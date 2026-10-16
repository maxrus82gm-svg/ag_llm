# AMENDMENT 04 — ремонт portable WUA и проверка host

TASK CODEX-WUA-0-DESKTOP-MCP-E2E-001. Codex 007. 2026-10-16,
Asia/Yekaterinburg. **AMENDMENT 04 LOCAL COMPLETE. DESKTOP E2E NOT VERIFIED.**

## Результат

Кандидат WUA Desktop Read-only **0.2.1** исправлен и проверен настоящим
Codex plugin loader. Установленный плагин 0.2.0 и прямая user STDIO-регистрация
не изменены. Адаптер и семантика трёх инструментов сохранены.

| Gate | Статус | Фактическая проверка |
| --- | --- | --- |
| A — упаковка | PASS | Старый пакет воспроизвёл ошибку absolute command; новый принят plugin/read и запущен host loader из собственного тестового кэша |
| B — запуск | PASS | Host MCP connected, initialize и tools/list, ровно ping/list_capabilities/read_synthetic_context; protocol 2025-06-18 |
| C — безопасность | PASS | Четыре настоящих вызова через MCP RPC host: 3 OK, TASK_ID_DENIED для other_task; session/nonce/hash/call_id/receipt согласованы, состояние неизменно |
| D — независимый CLI | PASS | Три новых CLI-процесса: default — 0 calls, required=true — 4 calls, снова default — 0 calls. Сохранены JSONL, stderr и сверенный receipt |

## Исправленная упаковка

В mcp.json теперь:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
  "mcpServers": {
    "wua_desktop_readonly": {
      "type": "stdio",
      "command": "./runtime/python.exe",
      "args": ["-I", "-X", "utf8", "-B", "./server.py"],
      "cwd": "./"
    }
  }
}
```

Это contained executable внутри пакета, без shell-обёртки, установки в систему
или поиска Python в PATH. Включён частный **Windows x64 CPython 3.12.10** из
официального embeddable ZIP и 29 установленных дистрибутивов замыкания зависимостей
MCP SDK **2.2.0**. Общий runtime — 1 628 файлов, 63 107 418 байт.
Это переносимость в пределах Windows x64, не универсальный пакет для других ОС.

Официальная документация [локальных MCP](https://developers.openai.com/plugins/deploy/desktop-only)
предусматривает включение сервера и зависимостей в пакет. CPython документирует
[embeddable distribution и vendoring](https://docs.python.org/3.12/using/windows.html#the-embeddable-package).
Python archive MD5 совпал с опубликованным
[релизом 3.12.10](https://www.python.org/downloads/release/python-31210/);
SHA-256 сохранён в runtime_provenance.json. Authenticode python.exe: Valid,
подписант Python Software Foundation (runtime_signature.json).

python312._pth ограничивает sys.path локальным runtime и его site-packages;
-I отключает user site/PYTHONPATH, -B исключает pyc-запись. Реальный host-test
выполнен с PATH, содержащим только Windows System32. Зависимости взяты из
существующего проверенного venv, их версии и hashes зафиксированы; pip/global
install или изменение системного Python не выполнялись. Лицензии сохранены
в runtime и dist-info. Новых hooks, tools или возможностей Write нет.

Контролируемые отказы проверены на отдельной копии: отсутствие contained
python.exe даёт FileNotFoundError без fallback в PATH; неверная версия SDK
даёт UNVERIFIED_MCP_SDK_VERSION до fixture/initialize. Результаты —
negative_runtime_results.json.

## Минимальная правка bootstrap

Для переносимости local_config.json содержит относительную собственную папку
CODEX-WUA-0-DESKTOP-MCP-E2E-001/evidence внутри plugin cwd. Права audit policy
по-прежнему ограничены этой evidence root и disposable TEMP fixture.

Первый реальный запуск исправленного manifest был сохранён как FAIL:
fixed.result.json / fixed.failure.json / fixed.stderr.log. Он выявил, что
отсутствующий родитель evidence root создаётся после включения аудита и
отклоняется как WUA_ISOLATION_FILE_WRITE. Отдельный stderr diagnostic зафиксировал
точную причину. Поэтому в server.py после прежней проверки TASK-scoped пути
добавлена только подготовка evidence_root.mkdir до регистрации audit hook.
Сами ping/list_capabilities/read_synthetic_context, runtime.py и 41 vendor-файл
не менялись. Повторный реальный host-test fixed02 прошёл.

## Доказательства Gate A–C

Использован настоящий codex.exe 0.162.0-alpha.17.2 и его документированный
[app-server протокол](https://learn.chatgpt.com/docs/app-server). Для каждого
контроля создан отдельный CODEX_HOME внутри amendment_04/test_environment/.
Marketplace add/install касались только собственного тестового home и его кэша.
Рабочее приложение и действующие MCP-процессы не перезапускались.

before.stderr.log воспроизводит прежнюю ошибку parser, before.result.json
показывает пустой MCP inventory. fixed02.result.json связывает connected server
с pluginId wua-desktop-readonly@wua-a04-fixed02 и точными тремя tools.
fixed02.rpc.json содержит реальные initialize/plugin/read/thread/start,
mcpServerStatus/list и четыре mcpServer/tool/call. Это host-test,
не прямой SDK запуск и не ordinary Chat.

Gate C session: **121f89663edb418195a52fc3d0abc950**.
Nonce: a8e6b0c69dbffd79c68315baa7cb2121.
Context SHA-256: 3ff38dc2dc6263c5379bc64d152622d72b8b59458eb44897fdb0c1796cd8999d.
Receipt: gate_c_receipt.json; 11 событий, 3 OK + 1 REJECTED,
storage_unchanged=true, guard_denials=0. Проверка — gate_abc.json.

Пустой тестовый home не содержит OAuth credentials; в его логах есть отдельные
неуспешные featured-catalog/prewarm запросы. Они не помешали plugin/MCP gate.
Модельный turn для A–C не запускался.

## Gate D: подтверждённый эффект required=true

Новый CLI запущен с --ephemeral --sandbox read-only. Для изоляции только в этих
новых процессах применены --ignore-user-config и --disable plugins, а единственный
WUA server задан CLI overrides. Использованы прежний явный Python и отдельная
копия кандидата. Обычная Codex account authentication использована на месте;
credentials не копировались и не выводились. Другие MCP-серверы не запускались
этими тестами. Постоянный config.toml и действующие подключения не менялись.

Три запуска имеют одинаковую основу; средний отличается required=true:

| CLI-run | Native calls | Результат |
| --- | --- | --- |
| default | 0 | tools unavailable |
| required=true | 4 | 3 OK и TASK_ID_DENIED, receipt сверён |
| default после required | 0 | tools unavailable повторно, несмотря на прогретую копию |

В обоих default stderr прямо содержит:

```text
omitting pending optional MCP server server_name=wua_desktop_readonly
```

Таким образом, для **нового контролируемого эксперимента** подтверждено исключение
ожидающего optional WUA из каталога. required=true устранил недоступность в этом
эксперименте. Это согласуется с документированным
[optional startup grace](https://learn.chatgpt.com/docs/extend/mcp).
Глобально required=true не записывался. Это не восстановление отсутствующего
trace старого теста и не доказательство первопричины всех ordinary Chat отказов.

Gate D session: **ae45acce1255467caae4e18c263ce38b**.
Nonce: b2fd04bb42c9c5a048482b68c7cba4c9.
Context SHA-256: be40e98fed04845879cd8918cfb3a0174cb0a40883b99d527703cce5108dba09.
Доказательства: cli_pair/*.jsonl, cli_pair/*.stderr.log, gate_d_pair.json,
gate_d_summary.json и gate_d_required_receipt.json. Начальные/завершённые события
не считаются двумя вызовами: native completed calls именно 4, а не 8.

## Сохранность, откат и следующий шаг

Изменены четыре прежних файла кандидата: mcp.json, plugin.json, local_config.json,
server.py (только bootstrap). Добавлен runtime/. Полный состав и hashes —
candidate_manifest.json; конкретный diff — changed_files.json.
Исходный кандидат из 47 файлов сохранён побайтно в rollback/plugin/.

rollback_candidate.py без --apply проверяет точный возврат; с --apply, только по
отдельному запросу, восстанавливает четыре before-файла и удаляет лишь собственный
добавленный runtime после проверки полного after-manifest. При любом последующем
drift отказывается от записи. Глобальные config/cache не входят в откат.
Откат не выполнялся.

Существующий native direct MCP ping прошёл после ремонта без Restart:
existing_direct_ping.json. Config hash и установленный cache сравниваются с
baseline.json; server.py API, runtime.py и vendor сохранены по контрольным суммам
и сравнению исходников. Прямая регистрация не повреждена.

Уточнение независимого verifier принято: старый отрицательный CLI-тест был около
18:11–18:12, сырой JSONL/stderr не сохранялся. Сессии 18:02 не отнесены к нему.
AMENDMENT 03 и его оригинальные evidence сохранены.

Нужное следующее решение пользователя — отдельное разрешение установить/активировать
кандидат 0.2.1. Здесь этого не делалось. После разрешённой активации нужны четыре
настоящих вызова ordinary ChatGPT и независимая сверка receipt. До этого
**DESKTOP E2E NOT VERIFIED**. Git-публикация, сеть, системные права, production и
работа Claude не затрагивались. По AMENDMENT 04 дальнейшее расширение остановлено.
