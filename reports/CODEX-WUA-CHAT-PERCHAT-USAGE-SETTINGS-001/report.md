# CODEX-WUA-CHAT-PERCHAT-USAGE-SETTINGS-001

**RESULT READY / AUTHOR BOUNDED OFFLINE PASS P0+P1 / AWAITING INDEPENDENT VERIFICATION.**

Codex 007, 10.11.2026, Asia/Yekaterinburg. Основная текущая модель; субагенты не использовались. Приоритет CHAT FIRST. Выполнены только usage, предпочтения чата и адресные проверки.

## Основание и база

Основание — актуальный БЛОК 1 и прямое поручение пользователя. Assigned base: main №569 `3f160dde42c697cfe6eb437e99e1eda61e6bc8c4`. Git/GitHub запрещены и не использовались; точный HEAD не подтверждён. Сверены текущие рабочие документы и source hashes H27/H28: принятый bridge/bootstrap совпали с сохранёнными опубликованными манифестами, конфликтующих изменений не обнаружено. 20 контрольных хешей, before-копии и assignment сохранены в пакете. При сдаче изменяемые файлы сверены с фактически протестированными source pins.

Актуальные №08/000/34/40, №37 §3а, №20 §5а, адресный FOLLOWUP №05, профиль №36.3 и результаты H27/H28 прочитаны адресно. Подтверждение пользователем прежнего browser/F5/изоляционного smoke в чате учтено как пользовательское evidence; визуальная проверка **новых** controls этой задачей не выполнялась.

## Что уже существовало и что изменено

Ultra уже предоставляла Turn usage, normalized input/output/total/optional nested reasoning, durable события, RAW, Run Store, модельный каталог, изолированный Ordinary Core TEST и постоянный CMD. Эти компоненты не переписывались.

- `web_alarm/ultra_chat.py`: добавлена только read projection usage выбранного чата из существующих Turn events и GET/POST settings в том же Web Chat service.
- `web_alarm/ui.py`: компактные синтетические счётчики и раскрываемые настройки выбранного чата, проверки чисел и защита от устаревших ответов/потери несохранённых правок.
- `test_web_alarm_perchat_usage_settings.py`: 8 общих Python selectors; `test_web_alarm_ultra_chat_ui.js`: 5 новых случаев поверх прежних 52.
- Собственный reports-пакет с checkpoints, raw evidence и инструкцией проверки.

Ordinary Chat Service, Turn, RAW, Run Store, Model Registry, fake transport, server, bootstrap, оба CMD, launcher/config, Tkinter и нормативная документация не изменены. Нет нового ledger, общего бюджета Workspace или новых модельных вызовов.

## P0 — завершён до P1

В ответ существующего GET messages добавлено optional `usage_summary`. Для текущего Chat читаются существующие RUN/Turn, проверяются durable bindings и события. Каждая started attempt учитывается по стабильному ID один раз; повтор ключа/доставка уже сохранённого результата не создаёт новое слагаемое. Cancel-before-start и подтверждённый NOT_STARTED отказ не считаются расходной попыткой. Сбой после возможного начала остаётся неизвестным; поздний подтверждённый usage учитывается без превращения отменённого результата в успех.

Представление показывает последнюю попытку и известную сумму **одного выбранного чата**, отдельно input/output/reasoning/total. Reasoning уже входит в completion; второй раз к total не прибавляется. Missing не равен нулю. Для частично известной категории показывается известная нижняя сумма; для полностью отсутствующей — UNKNOWN. При неизвестном total хотя бы одной попытки выводится «Общий расход известен не полностью». Неизвестный optional reasoning не аннулирует достоверный provider total.

Все значения помечены «TEST · синтетические токены». Суммы не сохраняются и не являются budget authority. При ошибке/повреждении или превышении bounded projection 512 Turn статистика unavailable/UNKNOWN, а не фиктивный ноль; обычная история не подменяется. Это предел чтения проекции, не квота токенов или число разрешённых сообщений. Новых кэшей и денежных оценок нет.

После P0: **4 Python + 54 JS PASS**, сохранён отдельный неизменяемый `checkpoint_p0.json` с source hashes и текущий checkpoint. Только затем начат P1.

## P1 — завершён

Предпочтения хранятся optional полем `ordinary_chat_settings` в существующем `.ultra/chats/<chat_id>/metadata.json`; второй файл/реестр не создавался. Используются прежние shared writer lock, проверка принадлежности/безопасных путей и verified atomic replacement/readback. Остальные поля карточки сохраняются. Старые карточки без этого поля читаются с defaults; явное сохранение фиксирует даже default значения. Повтор одинакового сохранения идемпотентен. Конкурирующие явные сохранения сериализованы, действует последнее сохранённое значение; отдельный протокол optimistic-edit не добавлялся.

Поля:

- `compression_threshold_tokens`: default 250000, настраиваемый порог будущего предложения сжатия, не размер окна модели.
- `answer_tokens`: default 10000, кнопка расширенного значения 20000, пользователь может менять положительное целое.

Принимаются точные положительные JSON integers в диапазоне безопасного JavaScript integer (до 9007199254740991); это техническая граница представления, не model cap. Bool, null, дробь, строка, ноль, отрицательные, лишние поля и слишком большие числа отклоняются. Повреждённые сохранённые настройки не заменяются defaults молча.

GET `/ultra/chat/workspaces/<ws>/chats/<chat>/settings` использует существующий read capability; POST — отдельный write token и Origin/body validation. Неверные ID/query проходят прежнюю безопасную маршрутизацию. В STANDARD/legacy service этот дополнительный маршрут не включается. Настройки не зависят от выбранной модели, не копируются в соседний Chat и возвращаются после reopen/F5.

Ответ API и UI явно сообщают `applied_to_provider=false`, `automatic_compression=false`. Настройки пока **предпочтения**, не действующие параметры физического вызова: принятый TEST по-прежнему использует прежний max_output_tokens=128, что проверено по durable prepared snapshot после сохранения 20000. Автосжатие не запускается. REAL/S3b не открыты.

В UI устаревший GET/POST старого чата не меняет controls нового чата. Обновление истории текущего чата не перечитывает уже загруженные preferences и не уничтожает несохранённый ввод. Подтверждённое сохранение отделено от ошибки/неподтверждённой записи.

## Проверки и evidence

Windows / Python 3.12.10; Python suite запускается с ранее принятым ранним guard H27, изолированными TEMP fixtures и разрешённым собственным loopback. Node использует прежний VM/DOM/fake-fetch harness. Exact commands, source pins, raw outputs и exit сохранены в evidence. Секреты и реальные пользовательские сообщения не требовались.

| Набор | Результат |
| --- | --- |
| P0 checkpoint | 4 Python + 54 JS PASS |
| P1 первичная проверка | 7 Python + 56 JS PASS |
| Финальный Python, включая уточнённый NOT_STARTED случай | **8 PASS**, 0 FAIL/ERROR/SKIP |
| Финальный UI, включая unsaved-edit regression | **57 PASS**, 0 fail/skip; 52 прежних + 5 новых |
| Physical permanent CMD smoke | **PASS**, exit 0, browser_opened=true; TEMP cleanup PASS |
| Syntax | 3 Python files PASS; embedded JS разобран Node |
| Scope/source readback | PASS; кроме карточки при штатной сдаче изменены только 3 разрешённых существующих файла |

Финальные Python и JS receipts: `final_python.result.json` и `ui_final_js.result.json`. Последний JS-прогон выполнен адресно после защиты несохранённых правок; неизменённые Python tests без причины повторно не запускались. Сохранены все промежуточные результаты; FAIL/ERROR в этих наборах не было. При ручной проверке усилен JS oracle: проверяется реальное число POST, положительный контроль сохранения и неизменность серверного значения при недопустимом вводе.

Через **настоящий неизменённый Start_WebAlarm_Test.cmd** создан TEMP Workspace и два чата; выполнены два fake Turn с разными зарегистрированными моделями, повтор тех же ключей, запись 123456/20000 для A и повторное чтение. У B остались 250000/10000 и 0 попыток; A показывает 2 попытки с UNKNOWN total, поскольку штатный fake не сообщает usage. GET страницы содержит новые controls. REAL-тело отклонено HTTP 400. После Enter процесс завершён, каталог удалён. В этом отдельном smoke известные usage не выдумывались: numeric/reasoning scenarios проверены в injected fake Python/JS fixtures.

## MANUAL ENGINEERING REVIEW / ограничения

Прослежены READ-only проекция и dedup, nested reasoning, missing/malformed usage, NOT_STARTED против may-have-executed, cancel/late result, существующие bindings и selective Chat scope. Проверены metadata read→validate→replace под общим lock, readback, сохранность identity/title, idempotent settings save и отсутствие передачи пользовательских preferences в фактический transport. Ошибки статистики/настроек не создают provider attempt.

Альтернативы нового ledger/хранилища, runtime cap enforcement и общий Workspace aggregate отвергнуты как вне задачи. Полный рефакторинг UI не выполнялся. Обязательные модельные ограничения/принятие S3b не заменены числом в форме.

NOT RUN: ручной визуальный smoke новых controls/настоящее нажатие F5, Chromium/a11y, отдельное чистое развёртывание Windows, Tk, полный несвязанный suite/CI, hardware power-loss, реальные GigaChat/OAuth/paid запросы и provider cap verification. Source-only проверка STANDARD/CMD не называется запуском production storage. Новое поле optional metadata проверено с существующим reader/writer; совместимость со всеми сторонними/древними писателями отдельно не аттестована.

Проверка F5 состоит из JS повторного harness/reload, сохранности metadata и повторных HTTP чтений; визуальная проверка нового интерфейса остаётся пользователю. В TEST после остановки намеренно удаляются все TEMP данные; сохранение настроек относится к работающему профилю и reopen его storage, не к переносу их в новый пустой запуск.

## OPEN, DOC IMPACT и сдача

Действующие S2/S3a не модифицированы и не объявлены production enforcement. S3b, S13a и прочие применимые B2 gates, Stage6/Stage7 live остаются отдельными OPEN. Требуется последующее подтверждение возможностей моделей и безопасное применение числовых preferences; текущее сохранение не делает provider-side cap истинным. Старые legacy RAW policy/portability/GUI OPEN не закрываются автоматически.

SHARED DOC DELTA координатору: P0 per-chat usage и P1 preferences в TEST готовы к независимой проверке, адресный selector добавлен в общую базу. FOLLOWUP-WUA-ORDINARY-CORE-BRIDGE-ACTIVATION-001 пересматривать по фактическому scope, не автоматически закрывать весь вопрос. №05/20/34/37/40, чужие карточки и тестовые нормы исполнителем не редактировались.

Штатный finish текущего TASK выполняется после полного report/manifest. HISTORY ID и факт ротации/readback брать из task_record.json / finish_receipt.json / closeout.json. Отчёт после регистрации неизменяем. Итог — локальная авторская сдача, не независимый PASS и не публикация; Git/commit/push/merge не выполнялись. Пользователь публикует один атомарный пакет, затем независимый verifier принимает точную версию.
