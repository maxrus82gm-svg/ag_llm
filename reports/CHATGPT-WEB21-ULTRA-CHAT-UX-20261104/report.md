# WEB21 / Ultra Chat UX — CHATGPT-WEB21-ULTRA-CHAT-UX-20261104

STATUS: RESULT READY / LOCAL ONLY / AWAITING INDEPENDENT REVIEW.
BASE: main@9142f0967612fb7ef37ec632eb6ab87626c94be5. NOT COMMITTED / NOT PUBLISHED. Свой код не объявлен независимо принятым.
Исполнитель: ChatGPT по прямому поручению пользователя; Codex не привлекался.

## Что проверено пользователем
Workspace «123» подключён к ранее существующей папке Ultra. Старый «Чат 1» и история показаны. Новый «Чат 2» создан и переименован в «Тест интерфейса». Отправка недоступна. Полный протокол и ограничения: evidence/manual_observations.md.

## Новые локальные изменения
- web_alarm/ui.py: дерево Workspace → вложенные чаты; раскрытие/сворачивание; видимые плюс и карандаши; старые отдельно стоящие кнопки спрятаны; активный объект подсвечен.
- web_alarm/ui.py: кнопка «+ Создать Workspace» сразу использует имеющиеся /ui/capabilities и /ui/pick-workspace-folder, берёт имя папки, применяет существующий /workspaces. Нет перехода к операторской панели; отмена не регистрирует папку.
- web_alarm/ultra_chat.py и web_alarm/workspace_registry.py: переименование только отображаемого имени Workspace через уже существующий защищённый Ultra Chat write-token. POST /ultra/chat/workspaces/<id>/title с проверкой прежнего имени. Путь/ID/история Ultra не изменяются.
- test_web_alarm_ultra_chat_ui.js и test_web_alarm_ultra_chat_storage.py: сценарии дерева, пути, отмены, создания, rename, отказов и неизменности данных.

## Авторские тесты (синтетические)
- node --test test_web_alarm_ultra_chat_ui.js test_web_alarm_operator_ui.js test_web_alarm_evm_ui.js: 145 PASS / 0 FAIL.
- python -B -X utf8 -m unittest test_web_alarm_ultra_chat_storage test_web_alarm_ultra_chat test_web_alarm_ui test_web_alarm_ui_ux -q: 44 PASS / 0 FAIL.
- 3 адресных HTTP-теста rename Workspace входят в число 44. Подробный лог сохранён.
- git diff --check: PASS по выводу команды. Авторский тест ≠ независимая приёмка.
- Реальный Windows GUI и новый нативный folder-picker после перезапуска: NOT RUN. Активный сервер не перезапускался.

## Ограничения
- Для новой пустой папки старое ядро сообщает missing_history; создание чатов там пока недоступно. Автоматическая инициализация истории не внедрялась.
- Удаление/архивирование Workspace и чатов не реализовано; это отдельная будущая задача с подтверждением.
- Stage 3, отправка/Turn, провайдеры, Blueprint, сетевые настройки и реальные сообщения не менялись.
- Пользовательские untracked .ultra данные папки Чат_pro и локальные .obsidian изменения не добавлять в коммит.
- Проверить concurrency/simultaneous rename как будущий verification gap; нельзя выдавать самопроверку за независимый PASS.

NEXT: пользователь согласует перезапуск STANDARD; затем ручная проверка и скриншоты нового UX, independent review другого проверяющего и отдельно пользовательская публикация.
