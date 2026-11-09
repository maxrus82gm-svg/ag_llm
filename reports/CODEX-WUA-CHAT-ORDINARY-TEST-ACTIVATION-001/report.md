# CODEX-WUA-CHAT-ORDINARY-TEST-ACTIVATION-001

**RESULT READY / AUTHOR BOUNDED PASS P0+P1 / P2 DEFERRED / AWAITING INDEPENDENT VERIFICATION.**

Codex 007; 09.11.2026; текущая основная модель, без субагентов. Выполнено экономно: новый launcher bootstrap и семь адресных тестов; старые 109 core/52 JS теста не повторялись, поскольку принятый core/UI не изменялся.

## Основание, база и scope

Основание — актуальный БЛОК 1 и прямой запуск пользователя. Assignment base: main №567 `e9f6fd2e1dfb1a00cf029f98aa1473201f27e8f6`. Изучены текущие №08/000/34/40, маршрут №37 §3а, ограничения №20 §5а, FOLLOWUP-WUA-ORDINARY-CORE-BRIDGE-ACTIVATION-001 и независимый review H-CODEX-000027. Git/GitHub не использовались; точный HEAD не подтверждался. Все пять production/test pins принятого bridge совпали с его опубликованным манифестом; локальная рабочая карта соответствует следующему шагу активации. Пересечений/дрейфа этих источников не найдено. Контрольные хеши 19 существующих файлов и before-копии карточки/config сохранены в evidence/baseline.json и before/.

## P0 — реализовано и проверено

- Добавлен `web_alarm/ordinary_test_fixture.py`: web-only запуск существующих WebAlarmApi, OrdinaryCoreChatService и create_server в собственном TemporaryDirectory. Нет нового ядра, модели, Turn или storage.
- В `web_alarm/launch_test_config.json` добавлен и выбран active `ordinary-core-offline`; прежний `stage5-offline` с его script/args сохранён для отката.
- Имена и содержимое Start_WebAlarm_Test.cmd / Start_WebAlarm_Standard.cmd, web_alarm/launcher.py, принятый bridge, UI и Tkinter не изменены. Постоянный TEST CMD сам читает новый active профиль; STANDARD его не читает.
- До импорта core всегда устанавливается прежний проверенный guard из пакета H27. Внешние Python socket/DNS, credentials/.env и repository live-storage закрыты. Переменная окружения с похожим именем не считается признаком установленной защиты. При отсутствии guard bootstrap останавливается до core.
- Запуск браузера сохранён, красное предупреждение/задержка существующего launcher сохранены. В Windows физический CMD вернул exit 0, browser_requested=true и browser_opened=true; HTTP capability подтвердила core_bridge=true / real_available=false.
- Enter/EOF либо обработанный Ctrl+C останавливает сервер; его текущий TEMP root удаляется стандартным TemporaryDirectory. В проверке Enter действительно завершил процесс, вывел ORDINARY_TEST_CLEANED и удалил root. Принудительный OS kill/аварийное выключение не проверялись и не обещаются как гарантированная cleanup.

Bootstrap использует существующий проверенный guard из `reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/guard/sitecustomize.py`; этот файл должен сохраняться в поставке репозитория. Guard не копировался и не менялся. Fake transport и REAL admission gate — прежние принятые механизмы, S3b не объявляется реализованным.

## P1 — адресные испытания

Новый общий selector: `test_web_alarm_ordinary_test_activation.ActivationTests` — 3 теста. Дополнительно прежний `test_web_alarm_launcher.StableEntryTests` — 4 теста. Итог **7 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, Windows, Python 3.12.10. Exact command, исходные хеши, elapsed и raw stdout/stderr — evidence/activation.result.json и соседние файлы.

Физическая проверка использовала именно `cmd.exe /d /c M:/GitHub/ag_llm/Start_WebAlarm_Test.cmd`, без изменения постоянного config для теста. CMD запускался скрытым subprocess; его штатный браузер действительно получил команду открытия. Через собственный loopback HTTP выполнены:

1. Проверка выбранного профиля и признака core_bridge, доступных моделей и запрета REAL.
2. Создание Workspace и двух разных Chat, выбор зарегистрированной модели.
3. Три последовательных сообщения в A и отдельное сообщение в B.
4. Проверка durable prepared context третьего запроса A: обе предыдущие user-реплики A присутствуют, private-B отсутствует.
5. Повтор каждого Turn по тому же ключу вернул тот же результат; история A содержит ровно шесть RAW-сообщений.
6. Повторные GET history/latest и GET web page сохраняют историю/Turn и TEST-маркировку — серверная часть reopen/F5.
7. REAL/config_ref запрос отклонён HTTP 400 без изменения истории. Настоящий provider/OAuth не подключался.
8. После Enter exit 0, TEMP root исчез; хеши обоих CMD и launcher совпали.

Отдельно проверены отсутствие fallback при пропавшем/standard/повреждённом TEST config, игнорирование TEST выбора штатным --standard и сохранение старого Stage5 dispatch. Эти проверки используют mocks/disposable config и не открывают настоящее STANDARD storage.

Первый физический smoke обнаружил ошибку нового тестового клиента: локальная функция http затенила импорт http.client. Bootstrap уже запустился и корректно очистился; harness исправлен. Исходный **2 PASS / 1 ERROR** сохранён в evidence/first_*. Второй прогон **3 PASS** имел ResourceWarning незакрытого stdout pipe теста; pipe закрыт, результат сохранён в passed_before_pipe_cleanup_*. Финальные 7 PASS — без этого предупреждения. Ошибки не скрыты повторным перезаписыванием evidence.

Syntax проверен для нового bootstrap и тестового файла. Checkpoints сохранялись после чтения, реализации P0 и runtime P0/P1; финальное состояние — checkpoint.json. Имена семи реально запущенных тестов доступны в verbose stderr.

## P2 и ограничения

**Usage UI намеренно DEFERRED** по приоритету пользователя и ограниченному недельному бюджету. Существующее отображение total не менялось; добавление отдельных input/output/known reasoning/UNKNOWN и панели настроек здесь не принималось. Новых фиктивных токеновых чисел не добавлено; прежние fake usage/None проходят через принятый bridge.

Визуальное браузерное F5/клавиатура/a11y, ручной Windows GUI, настоящий STANDARD launch, Tk, полный suite/CI, clean-Windows перенос, аппаратный crash и реальные GigaChat/OAuth/paid запросы **NOT RUN**. Автоматическое открытие браузера подтверждено возвратом системного browser API и готовностью страницы по HTTP, а не визуальным просмотром вкладки. Физически отправленных LLM-запросов — 0: профиль предоставляет только принятый точный fake sender и закрытый REAL gate.

Пределы временного fixture остаются прежними; 250k/10k/20k и модельные cap — следующий отдельный scope. S3b и применимые B2-гейты, Stage6/Stage7 и live остаются HOLD. Не создавались глобальные бюджеты Workspace, финансовая аналитика, Blueprint, MCP или Colibri.

## MANUAL ENGINEERING REVIEW / DOC IMPACT

Прослежен полный запуск: неизменный TEST CMD → launcher --require-test → активный python_script → обязательная установка guard → существующий core bridge → отдельный TEMP registry/server → Enter → shutdown/close/join → TEMP cleanup. Проверены отсутствие импорта Tk, отсутствие endpoint/secret/real-mode переключателей в bootstrap и невозможность включить реальный sender HTTP-телом. Force-kill cleanup оставлен честным ограничением. SYSTEM/browser настройки не менялись.

Из существующих файлов изменён только launch_test_config.json; добавлены bootstrap, общий адресный test module и собственный отчётный пакет. Карточка меняется только штатным finish. №05/20/34/37/40, чужие карточки, core, UI, CMD и launcher READ-ONLY. SHARED DOC DELTA координатору: P0 activation и bounded P1 готовы; общий FOLLOWUP не считать закрытым целиком, поскольку usage/per-chat settings и визуальный smoke остаются открытыми. Актуализация общего test catalog — за координатором в его scope.

Штатная сдача выполняется только после report/manifest и сохранения результата. Факт HISTORY ID, ротации и readback фиксируется в finish_receipt.json / task_record.json / closeout.json. Отчёт после регистрации не редактировать. Git/commit/push/merge NOT PERFORMED; публикация и независимая приёмка — пользователю/координатору.
