# OFFLINE-проверки

Среда Windows, проектный Python 3.12.10 и Node 22.20.0. Собственный OFFLINE runner перенаправлял TEMP/TMP/TMPDIR и AppData в выделенный scratch, очищал доступные значения провайдерских переменных и блокировал внешнюю сеть и команды Git/GitHub. Провайдерские сценарии использовали MockTransport. Изолированный Chromium использовал отдельный профиль и блокировку нелокальных адресов.

| Проверка | Команда или набор | Итог |
| --- | --- | --- |
| ModelCards, подключение и EVM | `offline_runner.py -q -p no:cacheprovider test_web_alarm_model_cards.py test_web_alarm_persistent_connection.py test_web_alarm_evm_unified.py test_web_alarm_gigachat_live_control.py` | 53 PASS, 103 subtests, exit 0 |
| Соседние модули | `offline_runner.py -q -rs -p no:cacheprovider test_web_alarm_ultra_connections.py test_web_alarm_legacy_session_recovery.py test_web_alarm_launcher.py test_web_alarm_chat_sidebar.py test_web_alarm_colibri_bridge_transport.py test_web_alarm_ultra_chat_s5.py test_web_alarm_ordinary_test_activation.py -k 'not permanent_cmd_chat_flow'` | 68 PASS, 91 subtests, 1 SKIP, 1 deselected, exit 0 |
| JavaScript | `node --test test_web_alarm_evm_ui.js test_web_alarm_ultra_chat_ui.js test_web_alarm_operator_ui.js` | 209 PASS, exit 0 |
| S1 | `runpy.run_path("test_rt002_s1_routes.py", run_name="__main__")` под OFFLINE runner | 69 PASS, 0 нарушений изоляции или проблем evidence, exit 0 |
| S2 | `runpy.run_path("test_rt002_s2_budget_policy.py", run_name="__main__")` под OFFLINE runner | 73 PASS, 0 нарушений изоляции, exit 0 |
| Chromium | `browser_smoke.py` с отдельным профилем | PASS. Сохранение после F5, сброс, красные часы и жёлтая отметка, список чата, избранное, закрепление, счётчик |
| Постоянные CMD и изоляция | `launcher_smoke.py`, оба фактических CMD с изолированным AppData и подставным opener | 2 PASS. TEST возвращает 404 на GET карточек и авторизованный POST порогов. Файл настроек не создан. Штатное завершение. |
| Компиляция | Python compile изменённых Python; чтение JSON отпечатков | PASS, версии в evidence/source.json |

Полные логи и команды находятся в `reports/_local/CODEX-WUA-EVM-GLOBAL-INDICATORS-001` и `_ultra_agent_test/CODEX-WUA-EVM-GLOBAL-INDICATORS-001`. Первая проверка JavaScript дала два FAIL на прежних ожиданиях четырёх счётчиков и поля per-profile. Функции проверки точных значений и сохранения были оставлены, ожидания обновлены под семь статусов и оставшиеся настройки профиля. После этого регрессия прошла. Физический отрицательный S5 требует прежний task guard и пропущен его штатной проверкой. Полный сценарий записи внутри постоянного TEST исключён из этого набора из-за известного ограничения H44 на `.ultra` внутри репозитория. TEST guard не изменён. Сценарий этой задачи для разделения STANDARD/TEST проверен фактическими CMD, ответами 404 и наличием или отсутствием файла настроек на одноразовых корнях.

## Матрица постановки

- Возраст проверен за секунду до границ и точно на 20, 27 и 30 днях. RED_CLOCK отделён от RED_CROSS и UNKNOWN. Два представления одной модели сверены с одним API.
- Нулевые, дробные, булевы, равные, убывающие и неполные пороги отказаны без записи. Проверены F5, новая серверная инстанция, сброс, старые профили, конфликт ревизий и права на HTTP POST.
- Шесть подтверждённых моделей сохранили зелёный статус и идентичные даты после повторного открытия сервиса. Открытие не вызвало OAuth и GET каталога. Повторено после управляемого истечения 86 400 секунд, новый явный запрос восстановил допуск через существующий MockTransport.
- Проверены отзыв согласия, смена ключа, отсутствие повторного inference по прежнему ключу запроса, красные часы при доступной отправке и неизменная дата соседней модели.
- Внешнее окно и режим поверх окон проверены в JavaScript fixture. Ручная физическая приёмка второго монитора и topmost — NOT RUN.
