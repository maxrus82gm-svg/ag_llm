# Рабочая карточка исполнителя — Codex 007

**USER GO 04.11.2026 / история по ID:** порядок общего №000 и нового №18 имеет приоритет над старыми указаниями о полном №001. После итогового пакета исполнитель или пользователь запускает штатный `finish`: сохранение источников и HISTORY ID → проверка → перенос БЛОК 1 в 1.1. Номер и адрес записи видны в 1.1/протоколе; повтор не создаёт новый номер. Веб-координатор проверяет запись по этому ID и ведёт короткие индексы №001/05. Полные постановки в №001 больше не вставлять; последние десять строк не заменяют очередь всех OPEN. Для старой 1.1 без H-номера использовать точный TASK ID и протокол, не переписывать постановку.

**Назначение:** персональная TASK и factual результаты Codex 007. Текущее состояние определяется только фактическими БЛОКАМИ1/1.1 ниже и штатной проверкой скрипта; пролог не дублирует статус. БЛОКИ2–4 содержат историю и независимые verdict. Правила скриптовой сдачи уточнены USER GO 2026-11-04; новых implementation GO этот пролог не даёт.

## Рабочий порядок

1. Действовать по конкретной утверждённой TASK/прямому поручению пользователя в разрешённом scope. Обычное новое назначение пользователь помещает в БЛОК 1; адресное поручение текущего чата не требует искусственного повторного GO. Старый NEXT не является запуском новой задачи. Уточнения привязывать к TASK/версии как AMENDMENT, не подменять исходную постановку.
2. Читать собственные Правила, относящиеся БЛОКИ 1/4; применимые разделы №08/34/профиля и тестовых контрактов по read matrix. Нормы №18 получать адресно со всеми requires при пробеле/конфликте. Общий №000 и весь №18/05 не загружать механически; архивы №001 не читать/искать рекурсивно. INDEPENDENT_PLAN сохраняет BLIND-START.
3. Git/GitHub запрещены без отдельного явного разрешения на операции и scope, включая чтение через CLI/UI/API/скрипты. Работать с локальными исходниками. Не менять чужие scope, live-storage, права, секреты, runtime/CI вне назначения. Публикация обычно за пользователем. Подробно: №18 → DOC-GIT-01/DOC-PARALLEL-01.
4. Исследовать причины и существующие механизмы; самостоятельно проверить релевантные edge cases и соседние инварианты. Исправлять подтверждённое внутри scope; находки вне scope сохранять с evidence и предложением. Не повторять одинаковые неудачные действия без новой диагностики. Проверки по риску и профилю №36.1/36.2/36.3; для чистой документации — смысл/сохранность/адреса/граф.
5. По каждой TASK, включая исследование/PARTIAL/FAIL/BLOCKED, сохранить внутри разрешённой публикуемой части проекта полный report, manifest и безопасные evidence. Указать версии, изменения, команды/exit/counts, исходные FAIL, NOT RUN, риски и DOC IMPACT. Не оставлять результат только в TEMP/переписке. Перед RESULT READY закончить обязательные проверки; незаконченный отчёт явно DRAFT.
6. Исполнитель не ротирует БЛОКИ 2–4 и не пишет №001 или общую документацию. Только исключение DOC-BLOCK1-SLOT-01@2 позволяет после финальной сдачи локально и дословно перенести свою завершённую TASK из БЛОКА 1 в один БЛОК 1.1 без Git, при подтверждённой сохранности старого слота. После пользовательской публикации ChatGPT независимо проверяет, сохраняет историю/readback и закрывает TASK. БЛОК 4 READ-ONLY для автора результата; self-PASS не является VERIFIED. Обнаруженный риск передать по форме №07; не объявлять его закрытым собственным предположением.
7. Для каждой технической TASK проверить launcher: один Start_WebAlarm.bat, штатный STANDARD; разрешённый TEST с TASK ID/целью; автор переключения возвращает STANDARD. При недоказанном восстановлении RESTORE_BLOCKED, без ложного зелёного. Не ослаблять backup/rollback или безопасность данных. №18 → DOC-WUA-LAUNCH-01.
8. Финал в чате — один самодостаточный копируемый text-блок: TASK, статус, изменения, проверки/NOT RUN, риски, DOC IMPACT, NEXT и отчётный путь. Полный фактический пакет остаётся в проекте. Прямая отправка другому чату/агенту требует разрешения на эту передачу; старый транспортный smoke не даёт постоянного права.

Локальный исполнитель не создаёт Remote-continuity сессии Alarm/ALARM_TASK_SESSION и пооперационные INTENT/DONE-журналы по привычке. Специальный аудит/защита — только если отдельно предусмотрены задачей; штатные runtime backup/rollback и существующая история при этом сохраняются.

**Обязательная сдача слота / №18 → DOC-BLOCK1-SLOT-01@2:** после финального пакета запустить одну команду:

```powershell
python -B tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id TASK-ID --no-chat-amendment --apply
```

При отдельных поправках вместо --no-chat-amendment передать --chat-amendment FILE для каждой. Скрипт сам делает check/dry-run/apply/readback, находит точный предыдущий снимок по ссылке в 1.1, переиспользует его или сначала сохраняет отсутствующую копию. Прежние snapshots не перезаписываются. Утраченные поправки, разные тексты одного ID, конфликт/ошибка записи — NO ROTATE. Никаких ручных переносов/очистки. JSON и handoff_task.md сохранить в пакете, затем актуализировать manifest. ALREADY_ROTATED — успешный повтор без записи; ожидание никогда не переносится в 1.1. Локальное сохранение не доказывает публикацию/независимую приёмку.

Окно: tools/task_slot_debug.json, enabled true/false; --monitor на один запуск, --headless без окна. Ярлык «Карточка Codex — статус» открывает наблюдение, обновление30 минут/по кнопке. Пользователь может завершить TASK через finish либо назначить новую через «Новая задача…» справа вверху, только когда БЛОК1 WAITING; форма запускает проверенный assign и не запускает агента автоматически. Только пользователь назначает следующую TASK между постоянными маркерами БЛОКА1. БЛОК1.1 заполняет только скрипт; БЛОКИ2–4/001 не затрагивать.

**Канон сопровождения:** №18 → DOC-CONTEXT-OPS-01, DOC-TASK-CLOSEOUT-OWNER-01, DOC-LOCAL-REPORT-HANDOFF-01, DOC-HISTORY-ACCESS-01, DOC-VERIFIER-BLOCK4-01@2 и DOC-TEST-LIFECYCLE-01. Формы — №07. Новый координационный порядок не меняет технические статусы, B2/WA4-R/EVM/live/paid/MCP freeze и права предыдущих TASK.

# Задачи Codex

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

## Правила

Действующие общие правила — раздел «Рабочий порядок» выше и №18 → DOC-CONTEXT-OPS-01.

[[000_Задачи для агента]]

[[001_История выполненных задач Codex]]

**USER GO 2026-11-04 / обязательный автоматизм:** после финального пакета запускать `tools/task_slot_rotate.py finish` (check→dry-run→apply→readback). Ручной перенос и очистка БЛОКОВ1/1.1 запрещены. Канон @2 разрешает скрипту сначала создать/проверить отсутствующий локальный снимок прежнего 1.1, не объявляя публикацию. Старые требования опубликованного snapshot/ручного previous-archive ниже уступают @2. Повторный запуск не переносит ожидание и не дублирует сданную TASK. Watch/ярлык открывает локальное наблюдение, обновление каждые30 минут; отдельные кнопки запускают finish/назначение пользователем через assign. Новая TASK допускается только в WAITING, без замены занятого слота.

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

###### ▼ НАЧАЛО ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:BEGIN
**ОЖИДАНИЕ НОВОЙ ЗАДАЧИ.**
###### ▲ КОНЕЦ ЗАДАЧИ — строку-маркер не удалять · TASK-SLOT:BLOCK-1:END

---

# БЛОК 1.1 — ПОСЛЕДНЯЯ СДАННАЯ ЗАДАЧА

###### ▼ НАЧАЛО КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:BEGIN
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001` · перенесено 2026-11-17 · SHA-256 копии `2211fe7c081f5f1bead7550cc7edd7e9bbd17a368c190b1ae198e16eb5f333c4` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/handoff_task.md` · отчёт `reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/report.md` · HISTORY ID `H-CODEX-000042` · запись `reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/task_record.json`

# Web Alarm Ultra — исправление EVM после пользовательской проверки STANDARD

**TASK ID:** `CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001`

**Исполнитель:** Codex 007  
**Проект:** `maxrus82gm-svg/ag_llm`  
**Приоритет:** P0 — исправление выявленных пользовательских дефектов  
**Предыдущая задача:** `CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001`  
**Предыдущий HISTORY ID:** `H-CODEX-000041`  
**Исходная опубликованная версия для сравнения:** `70870380fc2828087f785357eeb70c0ac343da9f` (№641)  
**Режим:** LOCAL ONLY / REUSE FIRST / OFFLINE FIRST

## 1. Основание и цель

17.11.2026 владелец запустил штатный `Start_WebAlarm_Standard.cmd` и выполнил первичную физическую проверку EVM.

Подтверждено:

- Карточки раскрываются.
- Кнопка «↗ Внешнее окно» создаёт отдельное окно.
- Оригинальная карточка остаётся в EVM.
- Индивидуальный переключатель модели отображается.

Выявлены проблемы:

**F-01. Внешнее окно не переносится на другой монитор.**

Владелец подтверждает, что окно открывается и работает, но при попытке переноса на второй монитор перемещение не удаётся.

**F-02. «Проверить чат» не выполняет ожидаемую проверку.**

Пользователь получает сообщение о том, что запрос не отправлялся, и предложение явно подключить GigaChat. При этом инструкция ссылается на Ultra Chat, хотя управление подключением перенесено в EVM.

**F-03. Неочевидное состояние подключения.**

На карточке модели доступна кнопка «Отключить», а индикатор работоспособности остаётся в состоянии «не проверено». Пользователю необходимо ясно различать разрешение модели, состояние общей сессии провайдера и результат настоящей проверки API.

**F-04. Открытая регрессия S2 предыдущей задачи.**

`72/73 PASS`, отказ `test_no_production_module_imports_the_policy_yet`.

**F-05. Общий Python-прогон предыдущей задачи завершился аварийно при очистке Tcl/Tk.**

Нужно диагностировать причину или корректно подтвердить границу проблемы.

Задача — адресно исправить выявленные дефекты, не переписывая уже работающую архитектуру.

## 2. Обязательный REUSE CHECK

Перед началом:

1. Прочитать действующие правила Codex, БЛОК 1, применимые нормы №08/18/36.1/36.3.
2. Проверить состояние слота штатным скриптом.
3. Изучить исходники, отчёт и доказательства H41.
4. Сопоставить локальную рабочую копию с опубликованной версией №641 без использования Git самим Codex.
5. Воспроизвести дефекты безопасно на изолированной конфигурации.

Основные источники:

- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/report.md`
- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/tests.md`
- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/window-review.md`
- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/user-smoke.md`
- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/integration-map.md`
- `reports/CODEX-WUA-EVM-CONTROLS-MULTIWINDOW-001/evidence/s2.txt`
- `reports/CODEX-WUA-EVM-UNIFIED-CONNECTION-001/report.md`

Основные модули для проверки:

- `web_alarm/ui.py`
- `web_alarm/model_cards.py`
- `web_alarm/ordinary_provider.py`
- `web_alarm/ultra_connections.py`
- `web_alarm/server.py`
- существующие GigaChat runtime, Ordinary Turn, RAW и ledger
- применимые Python/JS и S1/S2 тесты.

## 3. F-01 — перенос внешних окон между мониторами

Требуется установить фактическую причину отказа.

Различать три механизма:

1. Внутренние закреплённые карточки EVM.
2. Отдельные браузерные окна, созданные через `window.open`.
3. Окна Document Picture-in-Picture, работающие поверх других приложений.

**Критерий:** копия карточки должна перемещаться на второй физический монитор, оставаясь самостоятельным окном. Оригинальная карточка в EVM не удаляется.

Проверить:

- Перенос обычного внешнего окна мышью за системный заголовок.
- Перемещение через штатную комбинацию Windows `Win + Shift + ←/→`.
- Поведение при разных масштабах дисплеев.
- Перенос PiP-окна на второй монитор.
- Независимость окна от основного браузера при переключении разделов.
- Синхронизацию модели между главным и внешним окном.
- Закрытие, повторное открытие, F5.
- Несколько окон разных моделей одновременно.
- Отображение поверх Blender или другого отдельного приложения при включённом режиме.

Не считать перемещение DOM-панели внутри страницы успешным переносом между мониторами.

Не считать успешный вызов `window.open` или `requestWindow` подтверждением физической работы.

Если проблема связана с платформенным ограничением браузера, предоставить воспроизводимые доказательства и предложить технический вариант решения. Не внедрять новый нативный менеджер окон или системную службу без отдельного согласования.

Если физическая проверка недоступна инструментам исполнителя, подготовить точный пользовательский smoke и явно оставить соответствующий критерий NOT VERIFIED.

## 4. F-02 — восстановление «Проверить чат»

Сейчас в `web_alarm/ordinary_provider.py` присутствует текст:

`Сначала явно подключите GigaChat в Ultra Chat`

Это устаревшая инструкция.

**Единая точка управления подключением — EVM.**

Требуется:

1. Исправить ошибочную навигацию и текст.
2. Проверить полный путь кнопки EVM «Проверить чат».
3. При отсутствии активной сессии GigaChat показывать понятное состояние: «Провайдер не подключён».
4. Предоставлять пользователю возможность перейти к подключению непосредственно в EVM.
5. Подключение выполнять только после явного подтверждения пользователя.
6. Если сессия уже активна, кнопка проверки должна отправлять один разрешённый тестовый Turn выбранной модели.
7. Использовать существующий Ordinary Turn, provider admission, ledger и EVM check-result.
8. Успешный реальный ответ должен переводить индикатор соответствующей модели в зелёный.
9. Подтверждённая ошибка должна отображаться красным.
10. UNKNOWN, отсутствие разрешения и отсутствие отправки не должны выдавать ложный красный или зелёный результат.

**Нельзя создавать второй путь отправки API-запросов только для диагностики.**

Не создавать скрытых повторных запросов. Проверить, что повторное нажатие и повторный Turn не приводят к дублированию оплачиваемого обращения.

Учесть, что диагностическая проверка может тарифицироваться провайдером: перед реальной отправкой пользователь должен получить понятное уведомление и явно подтвердить действие.

## 5. F-03 — однозначное управление состояниями

Отделить в интерфейсе три разных понятия.

### А. Состояние модели

- «Включена»
- «Отключена»

Это разрешение модели в EVM. Кнопка «Отключить» означает, что модель сейчас включена и её можно отключить.

### Б. Состояние подключения провайдера

- «GigaChat подключён»
- «GigaChat отключён»
- «Подключение выполняется»
- «Ошибка подключения»

Одна активная сессия GigaChat может обслуживать несколько включённых моделей.

### В. Работоспособность модели

- Зелёная галочка — подтверждённый успешный ответ.
- Красный крестик — подтверждённая ошибка.
- Серый индикатор — не проверено или результат неизвестен.
- Оранжевый индикатор — прежнее подтверждение устарело.

Не смешивать эти состояния между собой.

Убедиться, что пользователь понимает, почему модель включена, но не проверена.

После F5 значения должны восстанавливаться из серверного состояния, без ложного успеха.

## 6. Полноценный STANDARD с реальными LLM

STANDARD — основной рабочий режим Web Alarm Ultra.

**Не возвращать искусственные испытательные ограничения:** 12 сообщений, 30 минут, 128 токенов и аналогичные старые trial-ограничители.

Сохранять:

- реальные ограничения провайдера и технические безопасные границы;
- параметры ответа, включая предпочтения до 20 000 токенов, если поддерживается;
- контроль контекста;
- реальные бюджеты, токены и учёт затрат;
- явное подтверждение потенциально платных действий;
- отсутствие автоматических оплачиваемых повторов;
- защиту реальных отправок и историю Turn/RAW.

Существующая конечная сессия подключения не должна превращаться в пробную квоту по сообщениям. Изменение её политики времени жизни допускается только после отдельного анализа безопасности.

TEST остаётся отдельным изолированным режимом и не обращается к реальным LLM.

## 7. Сохранность чатов

Обязательные инварианты:

- Чаты существуют независимо от моделей.
- Отключение любой LLM не удаляет переписку.
- Отключение всех моделей оставляет чаты доступными для чтения.
- При повторном включении модели можно продолжить существующий чат.
- Отключённая модель не принимает новый Turn.
- Уже существующие Turn, RAW, ledger и контекст не стираются.
- Удаление/закрытие внешнего окна не влияет на подключение модели или историю чатов.

Проверить эти сценарии в регрессиях.

## 8. F-04 — диагностика S2

Предыдущая задача завершила S2 с результатом **72/73, FAIL**.

Проблемный тест:

`test_no_production_module_imports_the_policy_yet`

Обнаруженная цепочка:

`ultra_ui → web_alarm.server → web_alarm.ordinary_provider → ultra_budget_ledger → ultra_budget_policy`

Порядок:

1. Проверить, существовала ли цепочка до H41.
2. Определить, является ли она архитектурным нарушением или несогласованностью прежнего тестового контракта с уже принятой интеграцией.
3. Сохранить исходный красный результат.
4. Исправить только доказанную проблему, в рамках разрешённого scope.
5. Не удалять и не ослаблять защитный тест ради зелёного результата.
6. Повторно выполнить адресный S2 и применимые соседние проверки.

Если для исправления потребуется большая перестройка бюджетной архитектуры, остановить это направление и представить отдельную минимальную задачу с доказательствами. Не выполнять такую перестройку самостоятельно.

## 9. F-05 — Tcl/Tk и полный Python-прогон

Адресно разобрать аварийное завершение общей проверки H41.

Определить:

- воспроизводится ли ошибка;
- связана ли она с порядком завершения тестов;
- относится ли к этой задаче;
- затрагивает ли штатный STANDARD/TEST.

Не считать раздельные PASS доказательством успешного общего прогона.

Не менять Tkinter Ultra или глобальные механизмы запуска без подтверждённой необходимости и отдельного разрешения.

## 10. Обязательная программа проверки

**OFFLINE обязательно:**

- Python и JS для EVM.
- EVM ↔ Ultra Chat.
- Включение/отключение одной, нескольких и всех моделей.
- Сохранение истории при нуле LLM.
- EVM check: нет сессии, подключён, успешный Turn, отказ, UNKNOWN, повторный Turn.
- Сохранение состояния после F5.
- Два и более внешних окна.
- Негативные случаи popup/PiP.
- S1 и S2.
- Применимые соседние STANDARD/TEST-тесты.

**Физическая Windows-проверка:**

- Два монитора.
- Перемещение внешнего окна.
- Перенос PiP.
- Режим поверх другого приложения.
- Несколько окон одновременно.

Если исполнитель не может провести физический сценарий, зафиксировать NOT RUN и передать короткий воспроизводимый протокол владельцу.

Никаких реальных OAuth, каталога и inference-запросов самим Codex без нового отдельного пользовательского разрешения. OFFLINE-успех не считать LIVE PASS.

## 11. Ограничения полномочий

Codex не выполняет Git/GitHub-операции.

Не менять рабочие пользовательские Workspace, историю, RAW, секреты, VPN, настройки Windows и существующие CMD.

Не создавать новое ядро, транспорт, менеджер моделей, второй каталог или новый способ тарификации.

Не переписывать уже принятую H41. Новая задача является отдельной исправительной итерацией.

## 12. Отчётность и завершение

Сохранить результат в:

`reports/CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001/`

Минимальный пакет:

- `report.md`
- `root-cause.md`
- `tests.md`
- `windows-review.md`
- `user-smoke.md`
- `manifest.json`
- безопасные evidence, исходные FAIL и окончательные результаты.

Отдельно перечислить каждую проблему F-01…F-05 со статусом:

`FIXED / NOT REPRODUCED / PARTIAL / BLOCKED / NOT VERIFIED`

Перед сдачей сохранить все OPEN/NEXT.

Затем выполнить штатный `tools/task_slot_rotate.py finish` по действующему регламенту с check → dry-run → apply → readback. Сохранить HISTORY ID, snapshot и протокол.

Не объявлять общий PASS при остающемся красном обязательном gate или неподтверждённом многооконном поведении.

**Итоговая цель:** пользователь открывает STANDARD, управляет GigaChat из EVM, выполняет настоящую проверку модели после явного разрешения, видит достоверный статус и может перенести отдельную карточку на второй монитор без потери связи с основной карточкой.
###### ▲ КОНЕЦ КОПИИ СДАННОЙ ЗАДАЧИ — заполняет только скрипт · TASK-SLOT:BLOCK-1.1:END

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Старые БЛОКИ 2–4 сохранены в `reports/CHATGPT-WEB29-H35-REVIEW-20261114/prior_closeout_snapshot.md`; B1/1.1 неизменны. Авторский `finish` H35 не означает полной REAL/UX-приёмки.

- **14.11 / H-CODEX-000035:** STANDARD → Ordinary Core per-chat model/settings/history, actual HTTP fixture; independent Windows 3 jobs PASS, author PARTIAL, REAL/USER UX HOLD.
- **14.11 / H-CODEX-000034:** seven legacy GigaChat send-site bounded independent Windows OFFLINE PASS; REAL HOLD.
- **13.11 / H-CODEX-000033:** GigaChat MockTransport exact bytes/Turn/usage bounded OFFLINE PASS.
- **13.11 / H-CODEX-000032:** Ordinary fake send S2/S3a/Turn/RAW bounded OFFLINE PASS.
- **12.11 / H-CODEX-000031:** launcher F-01 guard PASS, physical CMD NOT RUN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H36:** TEST each chat persists its own model across switch/F5; owner GUI PASS 15.11; independent CI 43635085454 2/2; REAL HOLD.
- **H35:** standard `create_server` now builds `OrdinaryApplicationChatService`; one `GigaChat 2 Pro` model, per-chat persisted preference/settings, history/usage UNKNOWN when not known, real HOLD fail-closed. Source18/18; CI 43598906253 3/3 PASS. **USER GUI BOUNDED ACCEPTED 15.11 (history/settings/F5); TECHNICAL REAL NOT READY**.
- **H34:** all seven legacy send-sites synthetic owner-gated through S2/S3a/H33; REAL blocked.
- **H33:** byte-accurate GigaChat HTTP mock→durable terminal/Turn/RAW accepted.
- **H32:** Ordinary fake one-send guard accepted.
- **H31:** launcher F-01 guard accepted; physical GUI still separate.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB30 / 15.11.2026 — H-CODEX-000036 — TEST per-chat model persistence owner+CI accepted

**TASK:** `CODEX-WUA-CHAT-TEST-PER-CHAT-MODEL-PERSIST-001`; original source `main@9dd93ba09408217781c9b8f423a9cecf5bd264aa`; [Windows run 43635085454](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43635085454) **SUCCESS 2/2**; old failing oracle expected RED, fixed code model/HTTP/UI + regression safety GREEN. **OWNER TEST GUI 15.11 BOUNDED ACCEPTED:** Lightning/Ultra remain assigned to separate chats after switches and F5; synthetic message handled. **H36 DOC CLOSED / BOUNDED INDEPENDENT OFFLINE + USER TEST GUI PASS.** All real/paid/S3b+ and independent historical S1 RAW remain HOLD/NOT RUN. `reports/CHATGPT-WEB30-H36-REVIEW-20261115/review.md`; H36 B1/1.1 already script-rotated, unchanged. H35 STANDARD owner GUI separately accepted for history/independent settings/F5 (`reports/CHATGPT-WEB30-H35-OWNER-GUI-20261115/review.md`); H35 author REAL BLOCKED remains.

## WEB29 / 14.11.2026 — H-CODEX-000035 — STANDARD Ordinary Core bounded independent review

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-ONE-MODEL-REAL-PREFLIGHT-001`, published source `main@cd0e4d943bb8d341baf07eef2a1d5c2a1619035a` №604; independent CI-only #605–607 `GPT@1c2930e0aedcebbcae01dd6455e8a6a532cf1d6e`. [Windows run 43598906253](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43598906253) **SUCCESS / 3 jobs + 3 artifacts**: source18/18, actual STANDARD9+10, Core263+266, legacy244+110, S2 73, quality52+7, JS61, 4 expected RED, no unexpected guard; compile/Tk PASS. First CI RED from missing sparse history source, second from stale app count, both independently fixed in CI only; product code unchanged. **Verdict: PASS BOUNDED INDEPENDENT WINDOWS OFFLINE for STANDARD integration; author PARTIAL, TECHNICAL REAL NOT READY/FACTORY BLOCKED/RELEASE HOLD. USER UX PENDING; physical CMD/Chrome/F5, real OAuth/API/paid/provider caps, S1 historical RAW, full S3b/S3c/S9/S13a NOT RUN.** Separate global full smoke checkout long path FOLLOWUP. Review `reports/CHATGPT-WEB29-H35-REVIEW-20261114/review.md` and `reports/CHATGPT-WEB29-H35-REVIEW-20261114/independent_runs.json`. B1 WAITING, B1.1 H35 immutable; no automatic OWNER GO.

## WEB29 / 14.11.2026 — H-CODEX-000034 — seven legacy sends bounded independent PASS

TASK CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001, author source main #595 db34931753ad1a6af88434a4ffe6b1097032070f; CI-only #602 5eafbbe2a036738723dc7d2b9c1409f8f518c554. [Windows run 43576129606](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43576129606) **SUCCESS / 3 jobs** with artifacts 14106478799 / 14106388326 / 14106099308: source SHA16/16, legacy244+110, regression254+256, S2 73, quality52+6, 7-site denial1+7, UI57, 3 expected RED, guard0, compile/Tk smoke PASS. Initial CI #601 SHA LF/CRLF false RED preserved, corrected only CI. **VERDICT DOC CLOSED / PASS BOUNDED INDEPENDENT WINDOWS OFFLINE**; S1 historical RAW, physical CMD/browser/F5, real OAuth/API/paid, model caps, full S3b/S3c/S9/S13a NOT RUN/OPEN; REAL HOLD. Review reports/CHATGPT-WEB29-H34-REVIEW-20261114/review.md, receipts reports/CHATGPT-WEB29-H34-REVIEW-20261114/independent_runs.json. B1 WAITING / B1.1 H34 unchanged; no REAL authorization.

## WEB29 / 13.11.2026 — H-CODEX-000033 — GigaChat MockTransport bounded independent PASS

**TASK:** `CODEX-WUA-CHAT-GIGACHAT-TRANSPORT-OFFLINE-GATE-001`, source `main@56e7f33c351624de94db77e080767930b8cf3d38` №592; CI-only `GPT@397040862b63fb23f7f3b51e1e1e1d793fee5179` №593. Independent [Windows run 43478748679](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43478748679) **SUCCESS**, job 132069412034, artifact 14062849789 (29 files): H33 **18 PASS + 36 subtests**, H32/core regression **236 PASS + 220 subtests**, S2 **73 PASS**, isolation **52 PASS + 5 subtests**, Node UI **57 PASS**, **2 expected RED**, unexpected guards 0. Exact-wire/ledger/terminal/reopen verified in synthetic `httpx.MockTransport`, real_available=false. **VERDICT: PASS / H33 DOC CLOSED STRICTLY BOUNDED INDEPENDENT WINDOWS OFFLINE.** Historical S1 pinned RAW NOT RUN (author 69 is not independent), physical CMD/browser/F5 NOT RUN, real provider caps/OAuth/paid, all-route S3b/S3c/S9/S13a, old-audit migration/capacity and host fencing OPEN. **REAL/Stage6 full/Stage7 HOLD**, no user live GO. Review `reports/CHATGPT-WEB29-H33-REVIEW-20261113/review.md`, №06 `EVT-WEB29-H33-MOCK-HTTP-CLOSEOUT-20261113`. БЛОК 1 WAITING, БЛОК 1.1 immutable H33.

## WEB28 / 13.11.2026 — H-CODEX-000032 — прежний bounded independent OFFLINE PASS

Ordinary fake one-send; independent Windows runs 43417573566 and 43416113378 SUCCESS, 236/74/52/57 and two expected RED. Full `reports/CHATGPT-WEB28-H32-REVIEW-20261113/review.md`, №06; no REAL/full S3b.

## WEB29 / 12.11.2026 — H-CODEX-000031 — прежний bounded independent OFFLINE PASS

TEST launcher F-01 Windows independent 21 PASS, physical CMD/browser/F5 NOT RUN. Full `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`, №06.

**Снимок вытесненной старой записи H30 и БЛОКОВ 2–4:** `reports/CHATGPT-WEB29-H33-REVIEW-20261113/prior_closeout_snapshot.md`; исходные evidence/№06 сохранены.
