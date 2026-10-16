# WUA 0.2.1: диагностика после полного перезапуска

CODEX-WUA-0-DESKTOP-MCP-E2E-001 · Codex 007 · 16 октября 2026, Asia/Yekaterinburg.

**DESKTOP E2E NOT VERIFIED. Обычный Chat: 0 из 4 настоящих вызовов.**
Результат пользователя: **DESKTOP E2E NEGATIVE / 0 CALLS / AFTER FULL RESTART**.
Повторная установка, перезапуск и повторный ввод `@` не назначаются.

## A. Подтверждённые факты

- Пользователь подтвердил неоднократное полное закрытие и открытие Desktop.
  Обычный Chat распознаёт оформленное упоминание WUA, но сообщает об отсутствии
  `ping`, `list_capabilities`, `read_synthetic_context`. Это ручное наблюдение
  пользователя; исходящий запрос того Chat агентом не перехватывался.
- В установленном кэше находится 0.2.1: все 1 675 файлов совпадают с запечатанным
  candidate_manifest AMENDMENT 04. Плагин включён. Прямая STDIO-запись WUA
  сохранила прежние command/args/cwd. Обе записи оставлены на месте.
- В текущем каталоге инструментов этого локального Codex доступны три функции
  WUA. Через этот каталог они в данном этапе не вызывались. Отдельный loopback-тест транспорта описан ниже; это другой клиент.
- Процессы WUA связаны с прямой регистрацией: venv Python и исходный plugin/server.py.
  Запущенного private Python из установленного кэша 0.2.1 в снимке нет. В ожидаемой
  evidence-папке установленного кэша receipt отсутствуют; в исходном кандидате
  найдено 76 готовых fixture-сессий с нулём событий.
- Отобранные WUA-строки журналов Codex показывают успешную MCP-инициализацию и
  сообщения ready после нескольких запусков приложения. Это подтверждает прямую
  локальную ветку; строки не являются трассой ordinary Chat tools/list.
- Пакет приложения: `OpenAI.Codex_26.1007.9446.0_x64__2p2nqsd0c76g0`,
  бинарник `ChatGPT.exe`; Codex CLI — `0.162.0-alpha.17.2`.
- Строка MCP server-info `version=0.2.0` жёстко задана в server.py даже у кандидата
  0.2.1. Поэтому эта строка журнала сама по себе не доказывает загрузку старого пакета.
- Текущий config.toml отличается от состояния сразу после прошлой установки.
  Прямая запись WUA совпадает; менялись другие MCP-записи. Их содержимое в отчёт
  не экспортировано, изменения не приписаны этой диагностике и не отменялись.
  Начальная контрольная сумма данного этапа:
  `42d764ff21d7e91abe06a02af64368914742903e0e4514eeffe71147c10987b4`.

Сессии `18771be5e4e944bda650db3f81bda963` и
`6a23a2f3f6d04ca4b0d46ff1c1cb8d92` около 18:02 сохранены предыдущим этапом.
`ready` записывается при создании временного fixture до MCP initialize;
`event_total=0`, `events=[]` не подтверждают ни tools/list, ни обращение Chat.
В исходных журналах нет связи этих ID с клиентом; PID/host не записывались.
Историческую принадлежность установить не удалось. См. AMENDMENT 03, раздел
«Два receipt около 18:02»; новых догадок вместо отсутствующего trace не добавлено.

## B. Причина недоступности WUA

**Установлена граница локального исполнения в исследованной сборке.**
Статический код прочитан из установленного app.asar; он не изменялся и внутренние
API не вызывались. Asset `webview/assets/app-initial-102e45562729.js`, SHA-256
`c59b2a0be6c13496b30ebda167925cdccab26799cae350c62d2b37afe3589b57`:

1. `lln`, смещение 1908159, собирает `kind: local_executor` с `mcp_servers` и
   `selected_capability_roots` локальных плагинов.
2. В отправке запроса около смещения 4483600 стоит проверка
   `if(ie!=null&&N!==\`tpp\`)throw Error(\`Local execution targets require a TPP conversation\`);`.
   Другой asset сопоставляет `tpp` с Work. Таким образом, этот маршрут локального
   исполнителя не разрешён для ordinary Chat.
3. `Nai`, смещение 4124199, связывает локальный plugin_id с Chat system hint через
   существующий canonicalAppId/remotePluginId. `Iai`, смещение 4125016, пропускает
   упоминание, если соответствующего hint нет. У локального WUA-пакета отсутствует
   `.app.json`; зарегистрированного для Chat удалённого MCP-подключения этим этапом
   не обнаружено. Снимка server-side bindings конкретного ordinary Chat нет.
4. Найденный `local_function_signatures` описывает передачу задания в Work/Codex,
   а не универсальную регистрацию инструментов WUA для обычного Chat.

**Основное объяснение с высокой уверенностью:** установлен локальный STDIO-плагин,
предназначенный для локального исполнения, но проверка идёт в ordinary Chat,
которому нужен отдельный доступный ChatGPT MCP-маршрут. Это согласуется с ручным
отказом после перезапуска и отсутствием запуска установленного пакета. Это вывод
из кода и наблюдений, а не восстановленная трасса конкретного Chat-запроса.
Он относится к этой сборке и этому способу регистрации, не ко всем версиям ChatGPT.

Дополнительные причины разделены:

| Ветка | Доказанность |
| --- | --- |
| Optional MCP не успевает попасть в каталог первого CLI turn | Доказано контролируемыми A/B/A запусками AMENDMENT 04: default 0, process-only required=true 4, default 0. Это отдельная CLI-проблема; глобальный required не изменён |
| Старый portable parser отказ из-за absolute command | Исторически доказан для 0.2.0; исправленный 0.2.1 принят штатным host-loader в AMENDMENT 04 |
| Совпадение имени direct STDIO и plugin server | Обе записи существуют; текущие процессы используют direct. Ошибки duplicate/collision не найдены. Влияние на выбор источника Codex возможно, причинность для ordinary Chat не доказана |
| Повреждение установленного WUA | Проверка 1 675 файлов не выявила повреждения; предыдущие реальные host/CLI проверки положительны |
| WebSocket os error 10013 | Причинная связь с отсутствием WUA не установлена; сеть не изменялась |

## C. Сравнение режимов

| Режим | Результат и предел |
| --- | --- |
| Обычный ChatGPT Desktop, local marketplace WUA 0.2.1 | Отрицательный ручной gate после полного перезапуска; 0 вызовов; E2E NOT VERIFIED |
| Текущий локальный Codex | Три WUA tools присутствуют в текущем инструментальном каталоге; новый вызов в этом этапе не выполнялся |
| Native Codex и штатный plugin loader | Предыдущие реальные четыре вызова и receipt в AMENDMENT 03/04 прошли; не засчитаны как ordinary Chat |
| Отдельный новый local Work chat | В этом этапе не проверялся; не подменён текущим Codex |
| Codex CLI | Исторический raw trace старого отрицательного запуска отсутствует; новые A/B/A проверки optional omission сохранены |
| Локальный tunnel-client dev proxy → WUA STDIO | PASS: четыре реальных JSON-RPC вызова через официальный Go tunnel bridge; один receipt; не SDK и не обычный Chat |
| Обычный ChatGPT через Secure MCP Tunnel | Официальный альтернативный маршрут подготовлен; hosted-туннель и Chat-проверка ещё не выполнены |

## D. Минимальное исправление

Официальный путь для приватного сервера в ChatGPT — Secure MCP Tunnel. Он поддерживает
существующий STDIO-сервер и исходящее HTTPS-соединение с OpenAI без публичного входящего
порта. Нужны настоящий tunnel_id, restricted runtime API key и связь туннеля с целевым
ChatGPT workspace. Создание подключения ChatGPT выполняется пользователем через
`Add custom MCP server → Connection: Tunnel`. Доступность зависит от учётной записи
и политики workspace. [Официальная документация OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

В `secure_tunnel_preparation/` уже подготовлены:

- официальный portable Windows x64 tunnel-client v0.0.16; SHA-256 ZIP сверена с
  release metadata и SHA256SUMS; никаких глобальных установок;
- профиль точного запечатанного WUA 0.2.1: прежние Python/args/server, отдельный cwd
  и будущая evidence-папка внутри TASK; адаптер не переписан;
- `start_tunnel.py` и `Start-WUA-Tunnel.cmd`: пути уже заполнены, tunnel_id вводится
  локально, ключ запрашивается скрытым вводом и передаётся только окружением нового
  процесса, без записи в профиль или аргументы;
- штатный offline import профиля прошёл, все 1 675 payload hashes и бинарник проверены.
  Это подготовка, не соединение с OpenAI и не MCP E2E.

В текущем окружении tunnel_id и runtime key отсутствуют (проверялось только наличие,
значения не собирались). Hosted-туннель, новые ключи, роли и ChatGPT-подключение не
создавались; постоянный runtime не запускался. В официальном ZIP есть cloudflared.exe, но он не запускался и в профиле
не включён. Остальные действующие подключения сохранены.

### Настоящий локальный тест официального tunnel bridge

Дополнительно выполнен штатный `tunnel-client dev proxy` с Go in-memory backend,
loopback ingress `127.0.0.1:0` и ограничением жизни 45 секунд. Control plane также
на localhost; облачного ключа и обращения к hosted OpenAI tunnel не было. Это новый
изолированный процесс с отдельным cwd `secure_tunnel_preparation/local_bridge_test`,
не перезапуск действующего WUA. Штатный тестовый tunnel_id `tunnel_222...` относится
только к dev proxy и не предлагается для регистрации в ChatGPT.

Реальные HTTP JSON-RPC initialize → initialized → tools/list и четыре tools/call
прошли через официальный tunnel-client в неизменённый sealed WUA STDIO:
три OK, один TASK_ID_DENIED; session `3688d2f72d3d40babe3837a4aed1a5e4`,
nonce `c599185b79f7f1207b5c65afc33bccaa`, context SHA-256
`040e036d0309f69652fd52cafdc3c88e747635d77f79db623f924bdb0aa18598`.
Проверены 13 receipt-инвариантов: одна fixture-сессия, call_id, nonce/hash, только GET,
storage unchanged, ноль production/model calls и guard violations. Peer name явно
`WUA OFFLINE TUNNEL TRANSPORT DIAGNOSTIC`, не положительное подтверждение Chat.
Публичный HTTP MCP session header не выдавался, но все четыре вызова дошли в одну
STDIO fixture-сессию. Это снимает локальное сомнение в совместимости bridge/adapter;
hosted session affinity ещё проверяется будущим gate.

Сырые запросы/ответы, оригинал receipt и validation сохранены в
`secure_tunnel_preparation/local_bridge_test/`. Listener после установленного времени
недоступен. Настоящих ordinary Chat вызовов по-прежнему **0**. Независимая приёмка
не объявляется.

Старый installation rollback сейчас нельзя применять вслепую: config.toml изменён
после установки вне этого этапа. Его guard должен отказать при drift. Данный этап
не менял действующую конфигурацию, поэтому восстанавливать её не требуется.

## E. Следующий проверочный gate

1. Проверить доступ к Platform Tunnels и существующий tunnel_id, связанный именно
   с целевым ChatGPT. Ключ не присылать в чат. Если доступ отсутствует, зафиксировать
   ограничение учётной записи; настройки сети или разрешения не обходить.
2. После получения настоящих реквизитов запустить подготовленный TASK-only runtime,
   проверить health/ready и tools/list. Снять новый receipt baseline перед Chat gate.
   Сам запуск daemon не означает доступность tools у модели.
3. **Ручной GUI gate:** в ChatGPT добавить пользовательский MCP-сервер с Connection:
   Tunnel и выбрать тот же tunnel_id. Автоматизации GUI, повторной marketplace
   установки и перезапуска Desktop в этом плане нет.
4. В новом обычном Chat выбрать новое Tunnel-подключение и выполнить ровно четыре
   настоящих вызова: `ping()`, `list_capabilities()`,
   `read_synthetic_context(fixture_id="synthetic_wua_desktop_001")`,
   `read_synthetic_context(fixture_id="other_task")`.
   Последний должен вернуть `TASK_ID_DENIED`. Получить task_id, session_id, nonce,
   context_sha256, proof_path и реальные ошибки, не конструировать их самостоятельно.
5. Независимый verifier сверяет оригинальный server receipt и сырые результаты
   ordinary Chat: одна session/nonce, верный SHA-256, три OK и один REJECTED, только
   GET, unchanged storage, ноль production/model calls и ноль guard violations.
   Имя клиента в receipt недоверенное; нужен отдельный факт происхождения из
   ordinary Chat. Если tunnel transport создаёт разные MCP-сессии, gate не проходит:
   сначала исследовать session affinity, не объединять receipts вручную.

До успешного gate и независимой проверки итог остаётся **DESKTOP E2E NOT VERIFIED**.
Git/GitHub-публикация не выполнялась. Работа Claude, production, системные права и
сетевые настройки не изменялись. Итоговая контрольная проверка — `integrity.final.json`.
