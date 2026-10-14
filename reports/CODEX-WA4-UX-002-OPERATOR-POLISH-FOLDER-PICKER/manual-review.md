# MANUAL ENGINEERING REVIEW — UX-002

2026-10-14 · Codex 007 · самостоятельная проверка после реализации. Это не независимая приёмка.

## Инварианты и побочные эффекты

| Проверенный механизм | Вывод / доказательство / предел |
|---|---|
| Регистрация и отображение | Один слот результата в потоке main. Успех соответствует проверенному POST acknowledgement; последующий неудачный GET не отменяет факт регистрации. Health независимо описывает GET /status. textContent исключает исполнение имени как HTML. |
| Потеря ответа | Никакого автоматического повторного mutation POST. TASK pending сохраняется до POST, затем unknown защищает текст и повтор. Warning сохраняется при последующем GET. Этот UX не вводит серверную идемпотентность регистрации Workspace: её прежний контракт не менялся. |
| Смена Workspace / root / формы | Прежние ID/root draft guards и reread под Web Lock сохранены. Picker сравнивает generation/revision/value; поздний результат не переносит путь в новую форму. Поздний Workspace acknowledgement не закрывает повторно открытую форму. |
| Server authority | Picker не вызывает WebAlarmApi.dispatch, Registry.register, TaskStore, executor или state machine. Only protected HTTP transport → native path → input. Регистрация остаётся отдельным подтверждаемым POST с прежней Registry validation. |
| Доступ с внешнего сайта | До helper: фактические loopback bind/peer, точный Host с портом, same-origin Origin для POST, process token, Fetch Metadata, strict JSON/body. Foreign/null/missing Origin POST, duplicate headers, wrong Host/token и cross-site metadata отвергаются. Нет CORS grants; UI имеет X-Frame-Options DENY. Это защита новых picker routes, не аудит/перепроектирование прежних API. |
| Capability / restart | GET не открывает диалог; token только в памяти процесса/UI, не localStorage. После отказа 403 UI обновляет capability, но не повторяет диалог автоматически. Новый экземпляр сервера получает новый token. Native bridge выключен по умолчанию, demo включает явно. |
| Native процесс | Собственный subprocess, список аргументов, без shell и аргументов от клиента. Singleflight lock в finally; subprocess.run ограничен 120 s, убивает/reaps собственного ребёнка. Настоящий sleep subprocess timeout проверен, не только mock. Native watchdog 125 s после исчезновения родителя проверен по исходнику; hard-crash сценарий отдельно НЕ запускался. |
| Результат native helper | Строгая схема CANCELLED/SELECTED, JSON, bounded accepted stdout; Path абсолютный, существующий directory с resolve(strict=True). CANCEL/error не перезаписывает ручной путь. Нет обхода Registry validation. Windows Shell/Tk может иметь собственные UI/cache effects, и пользователь может вручную пользоваться Shell; обещание относится к нашим программным записям в проект. |
| Новые негативные находки | guard отказал DEVNULL/\\.\NUL, исправлено stdin=PIPE без ослабления guard. HTTP token с не-ASCII вызывал TypeError compare_digest и 500; явный isascii guard даёт 403 до helper. Оба исходных FAIL сохранены. |
| Восстановление редактора | В настоящем браузере после offline → online обнаружена прежняя freshness-плашка при уже свежем каталоге. Адресная коррекция очищает её через setFresh(false), а не объявлять TASK fresh; копирование NEXT/context остаётся заблокированным. Проверка и source pin фиксируются в основном отчёте. |

## Остаточные ограничения

- Реальный диалог появился по сообщению пользователя, но коррелированный автоматический HTTP-исход был timeout. Сообщение пользователя «нажал Отмена» не подменяет недоказанный CANCELLED response. Настоящий native SELECTED → заполненный input требует отдельной человеческой приёмки.
- Встроенный браузер не показал/не дал обработать штатный window.confirm регистрации Workspace; исходная защита не обходилась. Новый Workspace в этой browser-пробе не зарегистрирован. Автоматические SELECTED/CANCELLED и confirmation gate подтверждены тестами с явными mocks.
- Tkinter availability не гарантирует доступность интерактивного desktop; startup/GUI errors дают unavailable, ручной путь остаётся. Linux/macOS native route недоступен.
- Общий сервер требует --enable-folder-picker; demo включает его. В разрешённом scope launcher/BAT/общий CI не менялись.
- Известный SKIP symlink test из-за прав Windows не считается PASS. Контроль isolation доказывает зарегистрированные операции тестов, не все возможные OS/kernel side effects.
- Злонамеренный локальный процесс или уже исполняющийся same-origin XSS не входят в защиту HTTP capability; same-origin code обладает её правами. Token не является новой учётной записью или правом изменения файлов.

## Решение

Реализация пригодна для независимой технической проверки после сохранения финальных тестов и raw-state. Визуальную приёмку и реальную native selection/cancel нельзя объявить завершёнными автоматически. Только RESULT READY / AWAITING INDEPENDENT VERIFICATION.
