# OFFLINE-регрессия CODEX-WUA-COLIBRI-REAL-CATALOG-001

26.11.2026, Windows, Python 3.12.10, Node.js 22.20.0. Запуски из корня WUA. Полные сырые логи сохранены локально в `reports/_local/CODEX-WUA-COLIBRI-REAL-CATALOG-001/`. Контрольные суммы и извлечённые результаты входят в [evidence](evidence/checks.json).

## Команды

Для Python использованы `PYTHONDONTWRITEBYTECODE=1` и отдельные значения `WUA_OFFLINE_RUN` для каждого запуска. `offline_runner.py` направляет TEMP, APPDATA и LOCALAPPDATA в одноразовые каталоги, очищает переменные доступа GigaChat, запрещает внешние соединения в Python и отключает сторонние плагины pytest. Для CMD использованы отдельные пути приложения и порты, а открытие браузера заменено локальной заглушкой.

```powershell
$runner = '_ultra_agent_test/CODEX-WUA-COLIBRI-REAL-CATALOG-001/offline_runner.py'

$env:WUA_OFFLINE_RUN = 'cc_sealed_python_serial'
.\.venv\Scripts\python.exe -B -u -X utf8 $runner -q -rs -p no:cacheprovider test_web_alarm_colibri_bridge_transport.py test_web_alarm_model_cards.py test_web_alarm_persistent_connection.py test_web_alarm_launcher.py test_web_alarm_ultra_connections.py test_web_alarm_evm_unified.py

node --test test_web_alarm_evm_ui.js test_web_alarm_ultra_chat_ui.js test_web_alarm_operator_ui.js

$env:WUA_OFFLINE_RUN = 'cc_cmd'
.\.venv\Scripts\python.exe -B -u -X utf8 '_ultra_agent_test/CODEX-WUA-COLIBRI-REAL-CATALOG-001/launcher_smoke.py'

$env:WUA_OFFLINE_RUN = 'cc_sealed_s1'
.\.venv\Scripts\python.exe -B -u -X utf8 -c "import runpy,sys; runpy.run_path(sys.argv[1]); sys.argv=['test_rt002_s1_routes.py']; runpy.run_path(sys.argv[0],run_name='__main__')" $runner

$env:WUA_OFFLINE_RUN = 'cc_sealed_s2'
.\.venv\Scripts\python.exe -B -u -X utf8 -c "import runpy,sys; runpy.run_path(sys.argv[1]); sys.argv=['test_rt002_s2_budget_policy.py']; runpy.run_path(sys.argv[0],run_name='__main__')" $runner
```

## Покрытие требований

| Проверка | Подтверждение |
| --- | --- |
| Нет подключения по умолчанию | NOT_CONNECTED в EVM. Создание READ_ONLY и привязка в launcher не инициируют сетевых запросов. Оба штатных CMD проверены в изоляции. |
| Два разрешённых GET | MockTransport подтвердил точные пути, метод GET и пустые тела. Передача тела, другого пути или неподходящей схемы отклонена до MockTransport. |
| Профиль, ACL и идентичность | Относительный профиль, подмена ожидаемого bridge_id, небезопасные ACL Windows, hardlink, внешний origin и смена launch_identity отклонены до соответствующего HTTP-запроса. Проверены отказ редиректа и отклонение невалидного instance_id. |
| Два Manager и потеря связи | EVM API и DOM показывают две разные цели с одинаковым названием модели и отдельными Manager/слотами. При недоступности Bridge обе цели сохранены с UNKNOWN и без разрешённых операций. |
| Каталог без исполнения | Локальный выбор модели, Turn и диагностика возвращают 400, 403 и 409 соответственно. Счётчик Bridge-запросов при этих вызовах не меняется. В UI диагностика отсутствует и прямое открытие окна заблокировано. |
| Облачная работа и H45 | Чтение доступности облака не инициирует чтения каталога. Пройдены регрессии карточек, индикаторов H45, постоянного подключения, EVM и чата. |
| STANDARD и TEST | Launcher отклоняет неполную пару, неявный режим и комбинации с TEST, `--require-test`, `--self-test` или `--live`. Проверка STD/TEST изолирует профили хранения. TEST с пустым профилем не читает и не пишет EVM-настройки. |
| S1 и S2 | Полные штатные наборы проверяют маршрутные инварианты, действующие отпечатки и бюджетные ограничения на искусственных данных. |

## Ход проверок

Адресный предварительный прогон Python дал 34 теста и 78 подтестов, первый полный набор — 98 тестов и 210 подтестов. Статическая сверка перед обновлением точных отпечатков S1 выявила расхождения в трёх изменённых функциях и связанных декларациях. Отпечатки обновлены по текущим AST. Перед сдачей повторены Python, S1 и S2 после окончательной правки ограждения HTTP-маршрутов.

Во втором параллельном прогоне Python тест `Http.test_indication_write_requires_local_origin_and_write_capability` получил `ConnectionAbortedError (WinError 10053)` при чтении ожидаемого HTTP 403 от loopback WUA. Сохранены 97 прошедших тестов, 1 ошибка теста и 210 прошедших подтестов. Маршрут EVM-настроек, тест и его окружение по этому результату не редактировались. Итоговый повтор полного набора выполнен последовательно после S1 и S2.

Результаты итоговых прогонов и коды завершения зафиксированы в `evidence/checks.json`.

**NOT RUN** Физический запуск WUA с рабочим READ_ONLY-профилем и браузером владельца, обращения к настоящему Client Bridge, реальная генерация, платные вызовы и независимая приёмка. Обязательные проверки этой задачи выполняются OFFLINE.
