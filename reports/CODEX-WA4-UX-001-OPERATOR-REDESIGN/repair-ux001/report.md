# UX-001-A/B — factual repair report

TASK: **CODEX-WA4-UX-001-OPERATOR-REDESIGN**  
STATUS: **RESULT READY / AWAITING INDEPENDENT VERIFICATION**  
2026-10-14 · Codex 007 · LOCAL ONLY / NOT SYNCED.

Ответ на независимый SOURCE REVIEW с вердиктом CHANGES REQUESTED. Оба finding подтверждены. Исходный отчёт и evidence сохранены; новая проверка не присваивает DONE / VERIFIED.

## Причины и исправления

**UX-001-A.** Прежний refresh защищал только непустой draft. Для пустого редактора он менял выбранный Workspace A на B, сохраняя draft.workspace_id=A. Изолированный probe дошёл до реальной отправки через тестовый fetch: заголовок B, кнопка enabled, POST /tasks с workspace_id=A. Backend/живые данные в probe не использовались.

Теперь любой открытый draft остаётся связан с исходными ID и root, независимо от наличия текста. Исчезновение Workspace или изменение его root блокирует регистрацию, обновляет навигацию и показывает причину. Для перехода нужен явный выбор проекта и refresh. Текст сохраняется под первоначальным ключом, автоматически в другой Workspace не переносится. Совпадение выбранного Workspace с draft проверяется независимо и в состоянии кнопки, и непосредственно перед POST.

Связанный случай с прежним ID и новым root исследован как та же причина stale binding; исправлен в UI scope. Тест доказывает сохранность исходной записи и чистый editor нового root. Восстановление каталога с первоначальным ID/root вновь разрешает регистрацию без потери текста.

**UX-001-B.** Предыдущее исправление касалось progressText, но отдельная ветвь timeline безусловно объявляла пустой план. Кроме того, старый тест с названием empty plan фактически оставлял непустые stages и не проверял timeline. Теперь fixture действительно содержит stages=[], проверяется весь timeline. При incoherent snapshot выводится «Состав плана не подтверждён. Обновите состояние.»; подтверждённое отсутствие этапов показывается только при coherent=true. Числовой progress и aria-valuenow также не выдаются за подтверждённые при incoherent, включая verified=0.

Это уточняет слишком широкую формулировку прежнего отчёта о решённом incoherent-empty случае: до этого repair timeline оставался дефектным. Исторический отчёт не переписан.

## Файлы и тесты

Production: **web_alarm/ui.py**. Regression: **test_web_alarm_operator_ui.js** — 4 новых сценария A, усилены 2 существующих empty-plan проверки. Backend, Ultra, WA4-R, общие документы, Python tests, runners и CI не изменены. Git/GitHub не использовались. Остальные записи — собственная папка repair-ux001 и отдельное дополнение в персональном БЛОКЕ 3; БЛОКИ 1/2 не менялись.

| Проверка | PASS | FAIL | ERROR | SKIP |
|---|---:|---:|---:|---:|
| Новые/усиленные тесты до production repair | 52 | 5 | 0 | 0 |
| Полный JavaScript regression после repair | 57 | 0 | 0 | 0 |
| Python/HTTP UI + operator + UX + launcher | 36 | 0 | 0 | 0 |
| Negative controls: прежние 4 + новые 2 | 6 | 0 | 0 | 0 |

Красные assertions: incoherent timeline; пустой A при каталоге только B; пустой A при пустом каталоге; изменившийся root; независимый submit guard. Полные первичные logs и before/after probes сохранены в TEMP. Test collection JS: 53 → 57, исходные имена не удалены. Python collection focused: 36, isolation violations=0, exit=0, 41.603 s. JavaScript exit=0; cancel/todo=0. Syntax gate Python/UI script/test script — PASS.

Новые controls намеренно убирают submit binding guard и возвращают безусловное сообщение пустого timeline. Каждый получил ровно один ожидаемый внутренний FAIL/exit1. Прежние controls не изменены. Production-файлы при mutation checks не правились. Подробности и source pins: evidence.json и quality.json; адресный diff: changes.patch.

Команды из M:\GitHub\ag_llm:

```powershell
$env:PYTHONUTF8='1'
$repairTemp='C:\Users\REX\AppData\Local\Temp\codex-wa4ux001-repair-3ew7rtbi'
node --test test_web_alarm_operator_ui.js
.venv\Scripts\python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-UX-001-OPERATOR-REDESIGN --output "$repairTemp\focused-http" test_web_alarm_ui test_web_alarm_operator_ui test_web_alarm_ui_ux test_web_alarm_ui_launcher
node reports\CODEX-WA4-UX-001-OPERATOR-REDESIGN\repair-ux001\quality_controls.js "$repairTemp\quality"
node --check test_web_alarm_operator_ui.js
node --check "$repairTemp\client.js"
```

Для повторения нужны новые TEMP outputs; существующие попытки не перезаписывать.

Полный backend Web Alarm discovery в этом repair **NOT RUN**: изменены только клиентские условия, весь JS слой и его HTTP-взаимодействия проверены. Это адресный выбор по TEST-EXEC-01/36.2, без изменения backend/concurrency mechanisms. Прежний full 770 PASS/1 SKIP относится к прежнему source pin и не выдан за новый прогон. Новый визуальный browser audit также NOT RUN; demo HTTP /ui проверен на совпадение с исправленным INDEX_HTML.

## Отдельный engineering review и ограничения

Проверены empty/nonempty draft, исчезновение всех/одного Workspace, возвращение исходного каталога, смена root, явный переход в B, сохранность ключа A, блокировка прямого submit сверх disabled-кнопки. Late callbacks, locks, quota, unknown POST, cross-workspace draft и stale exports повторно покрыты всем прежним JS набором и controls. Coherent-empty positive case сохранён; incoherent проверен с verified=null и 0. Просмотр/refresh/блокировка не выполняют POST; тестовая регистрация допускается только после осознанного выбора подтверждённого Workspace.

Проверка ID/root относится к последнему полученному каталогу. Атомарную защиту от смены backend root между GET и POST клиент обеспечить не может: для этого нужен серверный revision/CAS contract, вне scope. Прежние ограничения browser-local storage и unknown registration остаются. Новых backend возможностей не заявлено.

Демо **http://127.0.0.1:53833/** перезапущено на исправленном UI с прежним disposable fixture; /ui побайтово совпадает с INDEX_HTML. Данные fixture сохраняются; это не live Workspace. Текущий собственный helper PID31000. Прежние screenshots показывают компоновку, но не доказывают repair invalid-state branches.

## Source pins и handoff

```text
web_alarm/ui.py
BEFORE eb4b54035664560897aba2d1a8cea2420fa78fbe2c250ee24e7d449e305cf420
AFTER  3e61922180e82a904414f096f3d1eb066b510cb6643e5c9872d1af4c16be2441
test_web_alarm_operator_ui.js
BEFORE 5f25b1763ef43a07f12fa71c32d3f439d458013b78a9dd0360d777cdbca1dc0e
AFTER  76e9e3aaf32d0c40445075161298a01c8928a217b2a2992888dbb13f553a71dd
```

**DOC IMPACT / SHARED DOC DELTA:** дополнить будущую запись 25 результатом repair; в 36.2 указать новые binding/empty timeline scenarios; в 23/24 сохранить привязку draft к ID/root и различение отсутствующего/неподтверждённого плана. Общие документы здесь не изменены. Новый canonical document не требуется. Первоначальная карточка и evidence сохранены, repair оформлен отдельным AMENDMENT в БЛОКЕ 3.

**NEXT SAFE ACTION:** независимая проверка ChatGPT / WEB_07 исправлений A/B, test oracles и source pins. Следующие стадии не запускались. Только RESULT READY до нового решения verifier.
