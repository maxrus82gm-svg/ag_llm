# UX-002-B — предложение расширения scope

2026-10-14 · INITIAL PROPOSAL. Исходное предложение сохранено ниже.

**AMENDMENT / USER GO:** пользователь в ответе на scope question явно разрешил «указанные четыре файла и контракт». Разрешены server.py (только защищённые picker routes), новый folder_picker.py, новый test_web_alarm_folder_picker.py и wa4o_ui_demo.py, в дополнение к исходному UI/test scope. БЛОК 1 не переписывается. GO не означает independent acceptance, Git/CI/Ultra permissions или изменение Registry authority.

В текущем сервере нет native picker. Browser showDirectoryPicker возвращает FileSystemDirectoryHandle, а существующий Workspace Registry принимает проверяемый абсолютный путь. У установленного Python доступен Tkinter/Tcl-Tk 8.6. Предлагается native directory dialog через tkinter.filedialog.askdirectory(mustexist=True) в отдельном локальном Python-процессе. Это штатный системный диалог, не HTML-имитация и не передача handle за Windows path.

## Точный дополнительный write-scope

1. **web_alarm/server.py** — только HTTP adapter/capability для picker и параметр явного включения; существующие lifecycle/authority/Registry routes не менять.
2. **Новый web_alarm/folder_picker.py** — bounded subprocess adapter и изолированный Tk native helper, Windows-only; без shell/PowerShell, сетевых вызовов, записи в выбранный каталог, регистрации Workspace или TASK.
3. **Новый test_web_alarm_folder_picker.py** — security/HTTP, cancellation, helper failures/timeouts, single flight, validation и raw-state tests на TEMP fixtures с mocked native dialog.
4. **wa4o_ui_demo.py** — явно включить возможность в существующем локальном интерактивном demo, чтобы кнопка работала при запуске Start_WebAlarm_Demo.cmd. Launcher/BAT и CI не менять.

Уже разрешённые ui.py, test_web_alarm_operator_ui.js и test_web_alarm_ui_ux.py используются для кнопки, notices, capability checks, stale response guards и UI/HTTP tests. Другие файлы не входят в запрос.

## Контракт

- Native bridge выключен по умолчанию у общего сервера; включается отдельным параметром/CLI flag, а demo задаёт его явно. На non-Windows, неинтерактивной/неподдерживаемой среде — честный unavailable и ручной ввод пути.
- GET **/ui/capabilities** сообщает доступность и выдаёт случайный process-local capability token только разрешённому loopback origin. Не запускает dialog, не возвращает файловый каталог и ничего не регистрирует.
- POST **/ui/pick-workspace-folder** с пустым JSON object, строгим Origin и token в отдельном header. Client не передаёт произвольный путь/команду. Только явное нажатие «Обзор…» вызывает route.
- Response: **SELECTED + workspace_root**, **CANCELLED без пути**, либо точная ошибка unavailable/busy/timeout. Результат — только подстановка пути; существующая явная регистрация Workspace с подтверждением остаётся отдельным POST.
- Root из native helper проверяется как существующий абсолютный filesystem directory. Обычная регистрация повторяет действующую Registry-валидацию без ослабления. Отмена не меняет input/Registry/TASK/Workspace bytes.
- Один picker на server process, ограниченный временем (предлагается 120 s); собственный helper завершается и reaped при timeout. Browser request timeout для этого route согласуется с server timeout, не меняя mutation requests. Late response не переписывает изменённую/закрытую форму или другой выбранный путь.

## Границы доверия

Loopback bind сам по себе недостаточен. Для новых routes обязательны точный Host с реальным портом, loopback peer, same-origin Origin, отсутствие CORS grants, random token и отказ при foreign/null Origin. При явном non-loopback bind native capability отключена. От чужого iframe UI защищается frame denial. Token не хранится на диске/localStorage и не попадает в logs. Проверки выполняются до открытия helper.

Обычный GET/refresh, внешний сайт, неподтверждённый POST или повторный клик не открывают диалог. Backend picker не читает файлы внутри выбранного проекта, не меняет ownership/authority и не выполняет операции. Windows Shell может иметь свои UI/cache эффекты; отсутствие собственных записей в выбранный проект проверяется по bytes TEMP fixture. Не выдавать это за запрет пользователю вручную пользоваться командами Проводника.

## Проверки до сдачи

1. Foreign/missing/null Origin, неверные Host/port/token, cross-site Fetch Metadata, form POST и disabled/non-loopback mode не доходят до helper.
2. SELECTED/Unicode/space path; CANCELLED; nonexistent/file/relative path; unavailable; bounded timeout/worker reap; concurrent clicks/requests.
3. Picker не вызывает Registry.register/create_task/execution; raw bytes до/после равны. Явная регистрация после выбора сохраняет прежнее подтверждение.
4. Форма не теряет ручной путь при отмене/error/late response; сохраняются draft-binding, unknown POST, freshness и negative controls.
5. Windows native selection/cancel и browser evidence — если доступно управляемое desktop interaction; иначе честный NOT RUN для человеческого диалога, без подмены mocked tests визуальным PASS.

## Основания выбора

- [Python 3.12: native tkinter dialogs / askdirectory](https://docs.python.org/3.12/library/dialog.html).
- [Tk: tk_chooseDirectory](https://www.tcl-lang.org/man/tcl8.6/TkCmd/chooseDirectory.htm).
- [MDN: showDirectoryPicker возвращает directory handle](https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker).
- Альтернатива — прямой [Windows IFileDialog/FOS_PICKFOLDERS](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/ne-shobjidl_core-_fileopendialogoptions) через COM; не выбрана для первой итерации из-за дополнительного кода ABI/COM lifecycle при доступном штатном Tk.

Основание запроса разрешения: §3 и §4 исходного БЛОКА 1 этой TASK прямо запрещают backend/new native bridge без отдельного scope GO; DOC-PARALLEL-01@1 требует согласовать новые файлы до записи. До ответа разрешённая работа UX-002-A продолжается.
