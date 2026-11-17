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
**SUBMITTED / REVIEW PENDING** · TASK ID `CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001` · перенесено 2026-11-17 · SHA-256 копии `d5221c7d19e74008a9f5771c44ae7faf6b4ceda3ae4e334d13dc5f2eb90cc803` · CHAT-ONLY AMENDMENT: нет · снимок `reports/CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001/handoff_task.md` · отчёт `reports/CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001/report.md` · HISTORY ID `H-CODEX-000043` · запись `reports/CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001/task_record.json`

# CODEX — Web Alarm Ultra: восстановление STANDARD и корректное завершение приложения

**TASK ID:** `CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001`

**Приоритет:** P0  
**Предыдущая задача:** `CODEX-WUA-EVM-OWNER-SMOKE-REPAIR-001`  
**HISTORY ID предыдущей задачи:** `H-CODEX-000042`

**Тип:** устранение подтверждённого пользовательского дефекта, безопасное завершение приложения, восстановление сессий, интеграционные тесты.

## 1. Цель

Довести Web Alarm Ultra до состояния, при котором:

1. STANDARD штатно запускается и способен подключать GigaChat через EVM.
2. Обычный Ultra Chat может отправлять сообщения к разрешённой и реально доступной модели.
3. Кнопка **«Завершить Web Alarm»** корректно останавливает приложение и все принадлежащие ему активные процессы.
4. После остановки не остаются работающие серверы Web Alarm, занятые ими порты и ложные активные runtime-сессии.
5. Следующий запуск не блокируется ошибочно сохранённым состоянием предыдущей сессии.
6. Все пользовательские данные, настройки моделей и провайдеров сохраняются.

**КРИТИЧЕСКИ ВАЖНО:** завершение Web Alarm не означает отключение провайдеров в конфигурации EVM.

## 2. Подтверждённый пользовательский дефект

17.11.2026 владелец запустил штатный `Start_WebAlarm_Standard.cmd`.

Через Desktop Commander установлено:

- Запущен правильный STANDARD, не TEST.
- Сервер слушает `127.0.0.1:8765`.
- История доступна, каталог содержит шесть моделей.
- Capability возвращает `mode=ORDINARY`, `available=false`, `real_available=false`, `execution_mode=HOLD`.
- В личном хранилище GigaChat имеется сохранённая запись состояния `ACTIVE`, несмотря на отсутствие действующей сессии в текущем процессе.
- Нажатие «Подключить» в EVM не приводит к подтверждённому подключению.
- Ultra Chat показывает устаревшую общую надпись про проверку параметров и защит.

Вероятная причина — некорректное согласование долговременной записи провайдера и жизненного цикла процесса.

**Это рабочая гипотеза, которую нужно подтвердить диагностикой, а не заранее объявлять установленным root cause.**

Не изменять реальные пользовательские записи без подтверждённого безопасного механизма восстановления.

## 3. Обязательное исследование существующего кода

Изучить адресно:

- `web_alarm/launcher.py`
- `web_alarm/server.py`
- `web_alarm/ordinary_provider.py`
- `web_alarm/ui.py`
- `web_alarm/model_cards.py`
- `gigachat_runtime.py`
- `gigachat_admission.py`
- Штатные `Start_WebAlarm_Standard.cmd` и `Start_WebAlarm_Test.cmd`.
- Контракты Turn, RAW, S3a ledger, lock, provider session и recovery.
- Отчёты H40–H42.
- Регламенты №18, №34 и применимые разделы №36.

Переиспользовать существующие механизмы. Не создавать второй сервер, второй транспорт GigaChat или отдельный независимый менеджер моделей.

## 4. F-01 — восстановление подключения GigaChat

Воспроизвести в изолированной OFFLINE-среде:

1. Создать действующую сессию провайдера.
2. Сохранить состояние `ACTIVE`.
3. Смоделировать завершение процесса без штатного закрытия сессии.
4. Перезапустить STANDARD.
5. Проверить, что сервер обнаруживает противоречие между сохранённой записью и фактическим отсутствием владельца runtime-сессии.
6. Выполнить безопасное восстановление и повторное явное подключение.

Требования:

- Не удалять историю сессий и их доказательства.
- Не обнулять ledger, затраты или результаты Turn.
- Не считать любое `ACTIVE` автоматически устаревшим: учитывать действующего владельца, блокировки и возможные незавершённые запросы.
- Не допускать двух одновременных владельцев одного account/session.
- При доказанно завершённом процессе обеспечить безопасное закрытие либо восстановление устаревшего runtime-state.
- Если невозможно доказать безопасность автоматического восстановления — возвращать точную диагностическую причину и сохранять состояние для разбора.
- Не выполнять несанкционированный сетевой вызов или повтор inference.
- Различать состояние конфигурации провайдера и состояние текущей сетевой сессии.

После успешного восстановления пользователь должен иметь возможность штатно подключить GigaChat через EVM.

## 5. F-02 — обычная отправка STANDARD

Исправить причинную цепочку, из-за которой обычный чат остаётся в `HOLD` после неудачного подключения.

Проверить путь:

`EVM → подключение провайдера → capability → модель чата → Ordinary Turn → RAW → ledger → история`.

Требования:

- STANDARD — основной рабочий режим, не демонстрационный.
- Не возвращать искусственные ограничения 12 сообщений / 30 минут / 128 токенов.
- Не вводить новые постоянные блокировки по инициативе исполнителя.
- Не обходить реальные требования API, контроль расходов, защиту секретов, лимиты контекста и идемпотентность.
- Выключение модели в EVM запрещает новые отправки именно к этой модели, но не удаляет существующие чаты.
- Даже если все модели выключены, история и настройки остаются доступны.
- Если отправка невозможна, показать действительную техническую причину, а не общее сообщение про «защиты».
- «Проверить чат» использует существующий Ordinary Turn и требует подтверждения реального потенциально платного вызова.

**Задача должна восстановить работоспособность кода, но не разрешает Codex самостоятельно расходовать средства на реальные API-вызовы.**

Отдельно исследовать 24-часовой срок действия session grant. Указать, как он влияет на восстановление; не менять политику срока действия без согласованного решения.

## 6. F-03 — кнопка завершения Web Alarm

Добавить в основной веб-интерфейс понятную команду:

**«Завершить Web Alarm»**

При нажатии:

1. Показать подтверждение, особенно если есть выполняющиеся операции.
2. Прекратить приём новых задач и Turn.
3. Дождаться штатного завершения активных операций в пределах разумного настраиваемого тайм-аута.
4. Сохранить подтверждённые состояния и неопределённые исходы без ложного `SUCCEEDED` или `FAILED`.
5. Корректно остановить HTTP-сервер, фоновые задачи и принадлежащие приложению дочерние процессы.
6. Освободить порты, файлы блокировок и прочие runtime-ресурсы.
7. Отобразить результат завершения.

**Не отключать модели через EVM, не удалять конфигурацию провайдеров, не стирать credentials, Workspace, чаты, RAW или ledger.**

Текущая runtime-сессия, разумеется, не может продолжать работу после завершения её процесса. Её необходимо закрыть корректно, сохранив конфигурацию провайдера для последующего запуска.

## 7. F-04 — какие процессы разрешено завершать

Создать надёжный механизм определения принадлежности процессов экземплярам Web Alarm.

Охватить штатные экземпляры STANDARD и TEST, если они принадлежат управляемому приложению и пользователь выбрал полное завершение.

Останавливать только подтверждённые процессы Web Alarm и его собственные дочерние процессы.

**Запрещено** завершать по одному лишь имени:

- Все `python.exe` или `pythonw.exe`.
- Все `cmd.exe` и `powershell.exe`.
- Chrome, Edge или Firefox целиком.
- Codex, Desktop Commander, GitHub Desktop.
- Colibri Manager, локальные LLM, другие внешние программы.

Не использовать слепую очистку портов, глобальный `taskkill` по имени или уничтожение посторонних сервисов.

Если отдельный фоновый компонент Web Alarm обнаружен, но его принадлежность текущему приложению не доказана, показать его отдельно, не завершать произвольно.

В результате пользователь должен видеть, какие собственные процессы остановлены и какие, если такие есть, остались активными.

## 8. F-05 — закрытие веб-интерфейса

Отдельно проверить особенности запуска браузера из `launcher.py`.

**Явная команда «Завершить Web Alarm» должна надёжно завершать приложение.**

Учесть, что браузер может запрещать программное закрытие вкладок, открытых не через `window.open`. Поэтому:

- Не полагаться исключительно на `beforeunload`, `unload` или закрытие вкладки как на надёжное событие остановки сервера.
- Не завершать общий процесс браузера ради закрытия одной вкладки.
- Если вкладку невозможно закрыть программно, показать понятное состояние «Web Alarm завершён — вкладку можно закрыть».
- Исследовать возможность штатного app-window режима без установки дополнительных нативных компонентов.
- Если автоматическое завершение при нажатии системного крестика браузера технически не гарантируется, честно указать ограничение и предложить безопасный вариант, не выдавая его за PASS.

Не ухудшать существующую работу нескольких вкладок.

## 9. F-06 — безопасное завершение активных Turn

Проверить состояния:

- Нет активных запросов.
- Turn принят, но ещё не отправлен провайдеру.
- Запрос отправлен, ответ ожидается.
- Ответ получен, но сохранение не подтверждено.
- Разрыв соединения или аварийная остановка.
- Одновременный запрос завершения из двух окон.

Нельзя потерять подтверждённый ответ или повторно отправить потенциально платный запрос только из-за повторного запуска программы.

Для неизвестного результата использовать существующую модель `UNKNOWN` / `INTERRUPTED` согласно контрактам системы.

При тайм-ауте штатного завершения не утверждать, что все операции успешно закрыты. Предусмотреть диагностируемый путь принудительной остановки только с отдельным подтверждением.

## 10. F-07 — корректный последующий запуск

После штатного закрытия и повторного запуска:

- История доступна без изменений.
- Workspace и личные чаты сохранены.
- Включённые модели остаются включёнными.
- Настройки подключений не обнулены.
- Не обнаруживается ложная активная сессия старого процесса.
- Приложение не требует ручного удаления файлов или очистки временных записей.
- Создание новой runtime-сессии проходит через действующий контролируемый механизм.
- Никакие OAuth/catalog/inference не запускаются сами по себе лишь из-за открытия страницы.

Проверить также завершение TEST без влияния на постоянное хранилище STANDARD.

## 11. Проверки

**Обязательные OFFLINE сценарии:**

1. STANDARD start → shutdown → port free → restart.
2. STANDARD + TEST одновременно → безопасное полное завершение принадлежащих экземпляров.
3. Повторное нажатие завершения → идемпотентный результат.
4. Существующая GigaChat `ACTIVE` → аварийное завершение → безопасное восстановление.
5. Действующая сессия другого живого процесса → запрет ложного захвата.
6. Сохранение настроек EVM, Workspace, истории, RAW, ledger.
7. Проверка состояний Turn до/после отправки.
8. Отсутствие автоматически повторённых платных запросов.
9. Отсутствие завершения посторонних Python/Chrome/Colibri/Codex.
10. Проверки S1, S2, актуальных Python и JavaScript тестов.
11. Проверка корректной очистки Tcl/Tk и отсутствия прежнего abort.
12. Проверка безопасной обработки отказа, тайм-аута и аварийной остановки.

Физический GUI smoke выполнить только при реально доступной среде и явно указать его результат. Авторские OFFLINE проверки не объявлять независимой технической приёмкой.

## 12. Ограничения исполнителя

- Codex **не использует Git/GitHub**.
- Не изменять БЛОК 1 вручную.
- Не изменять БЛОКИ 2–4.
- Не удалять пользовательские файлы, сессии, секреты или историю.
- Не запускать платные GigaChat API без отдельного разрешения пользователя.
- Не менять права Windows, системные службы или настройки безопасности.
- Не создавать отдельную архитектуру LLM и не переделывать EVM без необходимости.
- Не устанавливать новые системные компоненты.
- Не возвращать старые trial-ограничения STANDARD.

## 13. Отчётный пакет и сдача

Создать:

`reports/CODEX-WUA-STANDARD-GRACEFUL-EXIT-SESSION-RECOVERY-001/`

Обязательные материалы:

- `report.md` — факты, подтверждённая причина, изменения, итог.
- `root-cause.md` — анализ stale ACTIVE/HOLD, shutdown и restart.
- `integration-map.md` — существующие и изменённые маршруты.
- `tests.md` — команды, количества PASS/FAIL/SKIP и границы.
- `process-lifecycle.md` — какие процессы создаются, кто их владелец и как они завершаются.
- `user-smoke.md` — короткая физическая проверка владельцем.
- `manifest.json` — состав и доказательства.

В отчёте по каждому F-01–F-07 указать отдельный статус: `PASS / PARTIAL / FAIL / NOT RUN`, включая неуспешные попытки.

Отдельно перечислить все оставшиеся OPEN/FOLLOWUP и их предлагаемые связи с текущей задачей для постоянного реестра №05.

После завершения выполнить штатный `task_slot_rotate.py finish --apply`, включая readback и сохранение HISTORY ID. Даже при PARTIAL/FAIL задача обязана иметь полную постоянную запись.

**Ожидаемый результат:** STANDARD нормально работает и корректно завершается; повторный запуск не упирается в оставшееся от предыдущего процесса состояние. Провайдеры не удалены и не выключены в EVM.
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
