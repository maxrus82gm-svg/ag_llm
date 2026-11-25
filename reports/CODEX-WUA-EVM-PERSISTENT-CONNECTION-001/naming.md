# Продуктовый нейминг

Источник решений владельца — №08 от 24.11.2026. Русская и английская формы приведены в актуальной инструкции WEB_ALARM_START.md.

| Файл | Прежнее отображение | Новое отображение | Причина и проверка |
| --- | --- | --- | --- |
| web_alarm/ui.py | Web Alarm Ultra, WA | Студия Нейрополис, Н | Основное окно, заголовок вкладки и знак. Проверен DOM Chromium. |
| web_alarm/ui.py | Завершить Web Alarm, Web Alarm завершает работу | Завершить Студию Нейрополис, Студия Нейрополис завершает работу | Управление и статус завершения. Проверены DOM и штатный HTTP shutdown. |
| web_alarm/ui.py | Ultra Chat, ULTRA CHAT, Диалоги Ultra | Чат Нейрополис, ЧАТ НЕЙРОПОЛИС, Диалоги | Навигация, шапка, пустые состояния, ARIA и тексты истории. Проверены Node и Chromium. |
| web_alarm/ui.py | Модель Ultra Chat, выбирается в Ultra Chat | Модель Чата Нейрополис, выбирается в Чате Нейрополис | EVM, выбор модели и подсказки при ошибке. Проверены Node и Chromium. |
| web_alarm/ui.py | EVM · Подключения Ultra | EVM · Подключения | EVM сохраняет название модуля. Проверен DOM. |
| web_alarm/ui.py | Блюпринт LLM | Конструктор Нейрополис | Навигация модуля. Проверен DOM Chromium. |
| web_alarm/ui.py | Colibri в статусе клиента и заголовке менеджера | Клиент Нейрополис и Менеджер Нейрополис | Транспортный ID и имена узлов остаются техническими полями. Проверены браузерный JS и существующие OFFLINE тесты Bridge. |
| web_alarm/blueprint_assets/editor.html и editor.js | ULTRA / КОНСТРУКТОР ПРОЦЕССОВ, история Ultra Chat | КОНСТРУКТОР НЕЙРОПОЛИС, история Чата Нейрополис | Редактор и уведомление предпоказа. Проверены активы и DOM Chromium. |
| web_alarm/model_cards.py | Colibri, модель ordinary Ultra Chat | Клиент Нейрополис, модель Чата Нейрополис | Видимое имя провайдера и описание роли. Проверены модельные карточки и существующий контракт provider ID. |
| web_alarm/launcher.py, launch_config.json, launch_test_config.json, ordinary_test_fixture.py | Web Alarm Ultra, Ultra Chat и Ordinary Core Chat в заголовках | Студия Нейрополис и Чат Нейрополис | Названия режимов, баннер и консоль. Проверены оба постоянных CMD. |
| Start_WebAlarm_Standard.cmd и Start_WebAlarm_Test.cmd | Web Alarm Ultra | Neuropolis Studio | Английские строки Windows. Сами файлы запускались с изолированной средой. |
| web_alarm/server.py и ultra_chat.py | Web Alarm is stopping, Ultra Chat, Blueprint | Neuropolis Studio is stopping, Neuropolis Chat, Neuropolis Blueprint | Английская диагностика и справка. Проверены HTTP и совместимость заголовков и маршрутов. |
| WEB_ALARM_START.md | Web Alarm Ultra и прежняя инструкция LIVE 12 | Словарь Нейрополиса и порядок EVM для STANDARD | Руководство приведено к текущим постоянным точкам и поведению. |

Сохранённые термины относятся к техническим ключам и историческим источникам. `web_alarm`, `WebAlarmWorkspace`, `webAlarm.*`, `ultra_chat`, `/ultra/chat`, `X-WebAlarm-*`, `SHUTDOWN WEB ALARM`, `CLEAN EXTRA WEB ALARM`, `colibri`, `WUA-COLIBRI-BRIDGE-001`, имена CMD, маршруты конструктора, TASK/HISTORY ID и пользовательские имена узлов сохраняют исходный формат. Отдельная программа Ultra/Tkinter сохраняет своё имя. Контекстный пакет, схемы API и технические диагностические инструменты продолжают ссылаться на свои исходные названия и пути. Исходники local_LLM не менялись.
