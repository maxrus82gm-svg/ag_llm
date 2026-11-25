# Матрица OFFLINE-регрессии

Проектный Python 3.12.10, Node 22.20.0 и изолированный Chromium на Windows. Python запускался с `-B -u -X utf8`. Авторский runner задавал процессу TEMP/TMP/TMPDIR, APPDATA/LOCALAPPDATA в отдельном `_ultra_agent_test/scratch`, очищал доступные GigaChat-переменные и блокировал внешнюю сеть. Реальный GigaChat никогда не вызывался. Синтетические ответы формировались в том же протоколе `httpx.MockTransport`.

## Запуски

| Набор | Команда / selector | Результат |
| --- | --- | --- |
| Транспорт, согласие и EVM | `offline_runner.py -q -p no:cacheprovider`, `test_web_alarm_persistent_connection.py`, `gigachat_live_control`, `gigachat_multimodel`, `gigachat_transport`, `legacy_session_recovery`, `evm_unified`, `model_cards`, `ultra_connections`, `standard_live` | 137 PASS, 177 subtests, exit 0 |
| Согласие и диагностика после финальной привязки к хосту | `offline_runner.py -q -p no:cacheprovider test_web_alarm_persistent_connection.py test_web_alarm_gigachat_live_control.py test_web_alarm_evm_unified.py` | 14 PASS, exit 0, пересекается с первым набором |
| UI, launcher, историю и соседние интеграции | `offline_runner.py -q -p no:cacheprovider`, `graceful_exit`, `instance_control`, `launcher`, `chat_sidebar`, `ui`, `ui_ux`, `blueprints`, `colibri_bridge_transport`, `ultra_chat`, `ultra_chat_s5`, `ultra_chat_s5_recovery`, `ultra_chat_turn_http` | 107 PASS, 1 SKIP, 200 subtests, exit 0 |
| S1 | `runpy.run_path("test_rt002_s1_routes.py", run_name="__main__")` под тем же OFFLINE-ограничением | 69 PASS, 0 violations и evidence problems, exit 0 |
| S2 | `runpy.run_path("test_rt002_s2_budget_policy.py", run_name="__main__")` | 73 PASS, 0 violations, exit 0 |
| JavaScript | `node --test test_web_alarm_evm_ui.js test_web_alarm_ultra_chat_ui.js test_web_alarm_operator_ui.js` | 207 PASS, exit 0 |
| Chromium | `browser_smoke.py` с отдельным пользовательским каталогом | PASS, exit 0, F5, черновик, история, избранное, закрепление, названия |
| Постоянные CMD | `launcher_smoke.py`, два фактических CMD, браузерный opener подменён для детерминированной изоляции | 2 PASS, exit 0, STANDARD capability и shutdown, TEST capability и штатная очистка |
| Защита TEST профиля | `test_web_alarm_ordinary_test_activation.py -k 'not permanent_cmd'` | 2 PASS, 1 deselected, exit 0 |
| Компиляция и совместимость | Компиляция изменённых Python, сравнение строк маршрутов, CMD и структуры профилей с доработочными SHA | PASS, `evidence/source-checks.json` |

Полные stdout и дополнительные скрипты находятся в `reports/_local/CODEX-WUA-EVM-PERSISTENT-CONNECTION-001` и `_ultra_agent_test/CODEX-WUA-EVM-PERSISTENT-CONNECTION-001`. Они содержат одноразовые локальные пути. Для независимой проверки используйте публикуемые сводки из evidence.

## Сценарии задания

| Сценарий | Покрытие |
| --- | --- |
| Первичный запуск, повторный запуск, shutdown, перезапуск после падения | Фактические CMD, повторное создание сервиса над теми же файлами, OS lease и старый ACTIVE в MockTransport/legacy tests. Настоящая перезагрузка Windows — NOT RUN. |
| 24 часа, 30 дней, истечение OAuth | Управляемые времена grant, кэша токена и даты EVM. Отдельно проверены состояние до обновления и расход после нового явного Turn. |
| Отключение, повторное разрешение, ключ, сеть | Явный stop включая отсутствие runtime, изменённый ключ и другой хост без повторного вызова, отказ каталога с recovery и timeout отправки. |
| Одновременное владение, неопределённость, повтор ключа | OS lock, сохранённое recovery evidence и повтор известных Turn, режимы STANDARD/TEST проверены отдельно. |
| EVM, смена модели, все цвета и видимость | Python oracle + JavaScript. Headless DOM и визуальное подтверждение закреплённого окна и избранного. Системный topmost и второй монитор — NOT RUN. |
| Ввод, F5, история, настройки модели | Headless браузер и UI suite. Поле ввода доступно при HOLD, сохранённый черновик возвращается, send остаётся недоступен. |
| Workspace, новый чат, первая запись, восстановление, повреждённый аудит | MockTransport и durable RAW/ledger. Проверено, что частичный usage не подменяется нулём и старый чат остаётся читаемым. |
| Интеграция Colibri, Blueprint и названия | Соседние fixture-тесты, JS и Chromium. Файлы local_LLM и проверка настоящих Client/Manager — вне scope. |

## Промежуточные результаты и блокировки

Первый широкий discovery прогон был прерван после выявления нестабильной локальной среды и пересечения по времени с рабочими правками. Его вывод относится к диагностике, а не к доказанной исходной версии. Первый адресный прогон зафиксировал 10 FAIL, 229 PASS, 1 SKIP. Промежуточные FAIL включали ожидаемо устаревшие названия и AST pins, несовместимый тестовый double и чтение протокольного TEST Turn из STANDARD. Последний дефект исправлен проверкой immutable provider mode до согласования. В финальном Python наборе сохранён один штатный SKIP существующего условия среды проверки. S1 и S2 прогнаны штатными `__main__`, импорт этих файлов через pytest даёт штатные пропуски.

Существующий полный TEST CMD-сценарий дал 503 на записи первого чата при TEMP внутри репозитория. Историческая fixture-защита запрещает этот путь. Результат запуска и штатной очистки проверен отдельно. Последующие прогоны использовали только браузер с отдельным профилем или отключённое открытие браузера. Настоящие сервисы, независимый CI, LIVE и физический пользовательский UX не запускались.
