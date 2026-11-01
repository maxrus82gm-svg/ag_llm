# CODEX-WUA-LOCAL-LLM-DISCOVERY-001 — технический результат

**Дата:** 01.11.2026, Asia/Yekaterinburg. **Исполнитель:** Codex 007. **Координатор/verifier:** ChatGPT LLM15.  
**Статус:** RESULT READY / **PARTIAL DIAGNOSTICS** / AWAITING INDEPENDENT VERIFICATION.  
**Разрешение:** пользовательский запуск действующего БЛОКА 1; только исследование, read-only диагностика и собственный отчётный каталог. Реализация/интеграция не выполнены.

## Полученный результат

Диагностическая shell работает на **192.168.0.9**, а не на целевом **192.168.0.77**. На .9 реально работает **Ollama 0.40.13** с listener **127.0.0.1:11434**; API/CLI/install metadata совпадают. Установлена **deepseek-r1:8b**, GGUF/Q4_K_M, 8.2B, 5 225 376 047 байт; /api/ps пуст. Metadata tools/thinking/completion не является проверкой выполнения этих функций.

**192.168.0.77:8000 не ответил** на три адресных HTTP GET с timeout 2 с. Причина неизвестна. Локальный :8000 на .9 принадлежит **Manager.exe PID 5156**, но HTTP закрывается без ответа; идентичность этого процесса и соответствие Colibri не доказаны. Установленный Colibri, его engine/version, модели, auth/queue/cancel, hardware .77 и дополнительная скачиваемая модель **NOT VERIFIED**. Отсутствие удалённого ответа не объявляется отсутствием установки или неисправностью firewall.

Существующее ядро исследовано адресно: **Model Registry уже есть**, но содержит шесть builtin GigaChat моделей. `ultra_connections` строит `api:provider:model_id` и selection; local_llm NOT_CONNECTED, API UNVERIFIED. Manual provider metadata не создаёт adapter. `gigachat_transport` — специфические OAuth/usage helpers, а фактические GigaChat вызовы находятся в нескольких runtime call sites. Готового универсального multi-host execution transport в исследованных точках нет.

Рекомендация: **расширить существующих владельцев Model Registry/settings/selection и выделить узкие protocol adapters с общей HTTP/security основой**. Сначала только health/list_models/discovery facts, без реальных запросов модели, UI и нового storage. Ollama-native inventory подтверждён; ColibriAdapter сейчас был бы предположением. OpenAI-compatible профиль допустим только с проверкой отдельных методов/версий. Run Store P9 и Stage3/Turn/budget permissions сохраняются отдельными prerequisites отправки.

## Файлы результата

| Материал | Назначение |
| --- | --- |
| host-inventory.md | Разделение .9/.77, процессы/версии, installed vs loaded, память/GPU/диски и пределы наблюдения |
| provider-api-matrix.md | Реальные GET outcomes, DOC ONLY и NOT RUN; native/OpenAI границы, Colibri неизвестен |
| ultra-source-map.md | Повторное использование ядра, точные symbols/диапазоны, отсутствующие части и P9 |
| multi-provider-contract.md | Стабильные connection/model refs, states/capabilities, протоколы, безопасность/ошибки/перенос |
| blueprint-integration.md | Кандидат будущего node contract, refs и result mapping без реализации графа |
| test-plan.md | Mock/negative/multi-host/recovery и критерии будущих проверок, не выполненные тесты адаптера |
| next-task-proposal.md | Узкая engineering TASK как DRAFT/NOT ASSIGNED; предполагаемый scope и UI data contract для WEB20 через LLM15 |
| server-side-checklist.md | Минимальные действия на самом .77 для отдельного разрешения без remote admin и reconfiguration |
| evidence/ | HTTP/host hardware snapshots, source hashes/AST selectors, правила с requires, FOLLOWUP excerpt, команды и verification |
| manifest.json | Фактические файлы пакета, байты/SHA-256; собственный manifest исключён |

## Выполненная диагностика и её статус

| Действие | Источник и фактический результат | Статус |
| --- | --- | --- |
| Определить место исполнения | Windows IPv4 192.168.0.9/24; .77 не локальный интерфейс | PASS: граница установлена |
| Процессы/listeners/install metadata | Ollama user app + serve process, loopback 11434; Manager.exe на ::8000; версия registry/API/CLI 0.40.13 | PASS для наблюдений .9; identity Manager/Colibri NOT VERIFIED |
| 4 GET к Ollama | /api/version, /api/tags, /api/ps, /v1/models — HTTP 200, JSON; installed один, loaded ноль | PASS: inventory, не inference |
| 3 GET к локальному :8000 | /health, /v1/models, /openapi.json — RemoteDisconnected, HTTP status не получен | FAIL доступности HTTP; engine/API NOT VERIFIED |
| 3 GET к .77:8000 | Те же пути, 2-секундные timeout; без повторных циклов | NOT ACCESSIBLE FROM DIAGNOSTIC HOST |
| Модели на .9 | API metadata + один локальный manifest, partial blobs/pull process не наблюдались | PASS local inventory; download .77 NOT VERIFIED |
| CPU/RAM/GPU/disks | Windows CIM, nvidia-smi, Get-PhysicalDisk; около 31.83 GiB RAM, RTX3070Ti 8192 MiB | PASS snapshot .9; capacity/concurrency/скорость NOT RUN |
| Launcher preflight | launch_config.active = standard, защищён baseline SHA; приложение не запускалось, target/root/визуальный PASS не проверен | READ-ONLY CONFIG CONFIRMED; launch E2E NOT RUN |
| Ядро/документы | Static text/AST; 248 исходных файлов в контрольном inventory, 9 основных source maps, 11 DOC-определений с requires | SOURCE REVIEW, runtime E2E NOT RUN |
| Публичные контракты | Только официальные docs.ollama.com; сведения отдельно DOC ONLY | Vendor reference, не тест установленной версии |

HTTP script использовал явные три base URLs, GET, no proxy/no redirects/no auth, response cap 512 KiB, timeout 2 с. Обнаруженный native 11434 — локальный listener, не scan remote портов. На .77:11434 запросов не было: этот удалённый listener не подтверждён. Ни IP-диапазоны, ни произвольные порты не сканировались. `ollama --version` вызван отдельно как version check, не load/run модели. Точные команды/ограничения — evidence/commands.json.

## MANUAL ENGINEERING REVIEW

| Проверенная гипотеза | Итог и implication |
| --- | --- |
| «Сейчас shell находится на сервере .77» | Опровергнута локальными интерфейсами. Нельзя переносить hardware/loopback .9 на .77 |
| «На :8000 точно Colibri» | Не подтверждена: PID Manager.exe с недоступным path, HTTP без ответа. Нужна диагностика на самом .77 |
| «Colibri является оболочкой Ollama» | NOT VERIFIED. Ни common backend, ни common model directory не доказаны |
| «Модель в списке уже работает в памяти» | Разделено API: tags имеет deepseek, ps пуст. Запуск не выполнялся |
| «Дополнительная модель скачалась» | Для .77 неизвестно; на .9 в просмотренном стандартном каталоге нет partial. Установку/скачивание не имитировать |
| «Текущий connection_id масштабируется на два одинаковых model name у разных server» | ID производен от provider/model без endpoint identity; требуется явное разделение refs и legacy mapping, не произвольный rename текущих записей |
| «EVM добавленный provider означает готовый backend» | Код manual provider выставляет adapter=None; `_adapter_state` лишь ищет модуль. API/inference/permission — отдельные факты |
| «Можно всё подключить одним OpenAI протоколом» | Подтверждён только Ollama listing. Общая HTTP основа + узкие профили уменьшают дублирование и не теряют native inventory; Colibri профиль требует identity/schema evidence |
| «Local inference бесплатно, значит budget/attempt не нужны» | Неверный архитектурный вывод: compute/resource ограничения и UNKNOWN outcomes остаются, переходы и бюджетные authorities не обходятся |
| «Адаптер исправит P9/Turn» | Нет. Existing recorder/accounting пригодны к reuse, но P9, durable acceptance/recovery и Stage3 права не закрыты discovery |
| «Объёма VRAM достаточно для двух установок» | NOT VERIFIED: free около 4609 MiB в снимке, GGUF disk size не равно runtime footprint. Без loading/benchmarks совместную capacity не обещать |

Рассмотрены альтернативы отдельных engine adapters, единого OpenAI-style transport и рекомендуемого сочетания. Failure cases: wrong host/engine, identical model aliases, URL rebind/redirect/SSRF, auth scope mismatch, corrupt/stale inventory, resource contention, midstream error, timeout после отправки, lost terminal/usage, cancel без подтверждения backend и скрытый alternate-host retry. Конкретные gates и oracles изложены в contract/test-plan; неподтверждённые угрозы не выданы за воспроизведённые инциденты.

## Проверка отчётного пакета

Авторский `tools/finalize_package.py`: **16/16 проверок пакета/evidence**, включая десять allowlisted GET, сохранение ошибок, раздельность installed/loaded/host identity, ограничения публикации и неизменность **248/248** записанных source/config/documentation файлов. Это проверки исследовательского пакета, не тест реализованного адаптера. Manifest хеширует фактически существующие артефакты без самоссылки.

Первый прогон дал 15 PASS/1 FAIL: в draft следующей TASK уже стояло русское «НЕ НАЗНАЧЕНА», но отсутствовал ожидаемый буквальный маркер `NOT ASSIGNED`. Маркер добавлен; исходный результат сохранён в evidence/package_checks_first_failed.json. Runtime/production не затронуты. Ранние обзорные tool outputs местами усекались; выводы опираются на последующие адресные чтения, сохранённые source hashes/selectors и фактические API/hardware JSON, а не на заявление о полном прочтении всех исторических томов.

## Остатки и координация

- **PARTIAL из-за .77/Colibri**, не из-за отсутствия отчёта. Нужны минимальные server-side факты по checklist; удалённый admin не запрашивался и не применялся.
- Локальная №40 ещё WEB19/№483. БЛОК 1 явно сообщает пользовательское распределение WEB20/LLM15 и разрешает использовать его до подтверждённого sync. Расхождение сохранено, файл №40 не исправлялся; server.py/ui.py вне write-scope.
- Следующая реализация только по новому USER GO; draft discovery-only не запускает Stage3 и не создаёт вторую модельную/чатовую/бюджетную систему.
- БЛОК 1/1.1 и карточки **не ротируются**: конкретная TASK разрешает запись только в собственный пакет и прямо запрещает изменения карточек. Старая постановка остаётся у владельца; текущая сохранена как assignment_source.txt для review.
- Передача требований WEB20 — через LLM15, как предписано БЛОКОМ 1. Сообщение/квитанция при наличии адресуемого чата фиксируются отдельно; отправка не является независимой приёмкой или публикацией.

## NOT RUN / запреты соблюдены

Ни одного inference запроса, model load/unload/pull/delete, benchmarks, параллельной генерации, service/firewall/DNS/proxy настройки, нового listener, software update/install, production/UI/общих tests edits, live Workspace/RAW/Turn/Run mutation, paid API, Desktop Commander, Git/GitHub или MCP/tunnel эксперимента. Проектный runtime не импортировался и не запускался. Провайдерные тайм-ауты/ошибки сохранены без повышения до API UNSUPPORTED. Публичная документация получена обычным web-инструментом, GitHub и зеркала не открывались.

## Передача LLM15

По пользовательскому поручению БЛОКА 1 §10 технический кандидат и требования WEB20 направлены в существующий чат **«Сервер LLM15»** (`6adcdf72-946c-83eb-9233-cc91d69def71`). Инструмент принял сообщение; полученный ограниченный readback ещё показывает предыдущий завершённый turn, поэтому прочтение нового сообщения и независимый verdict не подтверждены. Квитанция — handoff_receipt.json. Точный текст — llm15_handoff.txt, 31 416 символов / 44 444 байта, SHA-256 `8be172247a69b2cd7da6c72ec077b8913e40904a02f5f92dcade932abeb51eb2`. Переданы summary фактов, API matrix, source map, proposed contract, Blueprint refs и next-task/UI proposal. Полный файловый readback и независимая приёмка следуют после пользовательской публикации. Напрямую WEB20 сообщений не отправлялось: маршрут через LLM15 соблюдён.

## NEXT

Пользователь публикует этот пакет; ChatGPT LLM15 независимо оценивает evidence/границы, архитектуру и узкий draft. Затем: либо отдельно разрешённая диагностика на .77 для идентификации Colibri/моделей, либо mock-first discovery core без inference/UI. Требования UI/data contract передаются WEB20 через координатора. **RESULT READY / PARTIAL / AWAITING INDEPENDENT VERIFICATION**; реализация, полная совместимость, сетевой security PASS и model E2E не заявлены.
