# Stage 3 TEST contract — implemented v1

Это реализация только локального детерминированного имитатора. Постоянные model/context/config references: `local-test:v1`, `empty:v1`, `test-only:v1`. Они являются конфигурацией test double, не вторым реестром моделей. EVM preference не выбирает transport и не изменяет принятый Turn. Любая другая ссылка отклоняется до записи. Сборка контекста реального провайдера и общие transport/budget routes относятся к следующим этапам.

## Владение

- Workspace и Chat принадлежат существующему `context_storage`; перед каждой операцией проверяются регистрация, identity и chat ownership.
- `turn_id = run_id = turn_ + SHA256([workspace_id, chat_id, idempotency_key])`; stable user/assistant message IDs и attempt ID производны от того же scope. Одинаковые тексты с разными ключами дают разные Turn.
- Компактная связка Turn хранится в поле `turn` существующего RUN `summary.json` через API Run Store. Отдельных chat/turn/attempt журналов нет. RAW body не дублируется в summary; сохраняются fingerprint, IDs, references, state и cancel flag.
- Исполнение и результат — SERVER events того же RUN. `task_block_id` — техническая группировка, Web Alarm TASK не создаётся.
- RAW записывается исключительно `context_storage.commit_raw_message()` с постоянным ID, workspace binding, producer `test_imitation` и техническим task_block_id. Текст producer/состояния не подменяет RAW.

## Порядок и recovery

Общий Workspace OS lock ядра охватывает проверку/приём/публикацию, но не удерживается во время имитатора. Создание RUN summary выполняется только при отсутствии прежнего summary. Пустая резервация после сбоя ещё не означает принятого текста.

1. Проверить TEST root allowlist и ownership, строгую схему (text ≤2048 UTF-8 bytes, key 16–128 ASCII), frozen references.
2. Под shared lock создать компактный intent в RUN summary (ACCEPTING) до user RAW. Повтор сравнивает fingerprint и при конфликте возвращает 409 без изменения первой записи.
3. Commit user RAW тем же ID; READY только после успешной устойчивой публикации. Сбой до/после RAW оставляет ACCEPTING; явный повтор оригинального тела завершает приём без дублей.
4. Перед исполнением повторно проверить RAW и RUN facts. ATTEMPTING сохраняется до `turn_started`; затем выполняется один вызов константного `_imitate()` вне lock.
5. Под lock: сверить, что отмены нет; записать `turn_result` с attempt ID и фиксированным ответом через Run Store; commit assistant RAW; только затем SUCCEEDED.
6. Явный POST replay вызывает существующий `recover_run_records()`. Подтверждённый result может завершить assistant RAW/summary без повторного имитатора. Начатая попытка без подтверждённого result не запускается заново. Pending/orphan/corrupt данные без безопасного восстановления дают 503.
7. READY cancellation → CANCELLED; после начала → UNKNOWN + cancel_requested. Поздний результат получает discard event и не публикует assistant RAW. Terminal replay не добавляет events.

GET проверяет связку summary/events/RAW и использует shared lock для согласованного снимка, ничего не ремонтирует и не исполняет. ATTEMPTING без локально известного активного владельца проецируется UNKNOWN; другой server process тоже может честно видеть UNKNOWN, пока первый работает. Это консервативная видимость, не разрешение повторного исполнения. HTTP read/write capabilities различны, но coherent GET может вернуть 503 при занятом/недоступном writer lock. Отдельная lock-free read оптимизация не реализована.

Проекция проверяется против durable events: READY/ACCEPTING не могут сосуществовать с execution facts; result/failure требуют start; terminal facts не дублируются/не противоречат друг другу. SUCCEEDED дополнительно требует согласованного user fingerprint, verified result и assistant RAW. Неопределённость или повреждение не превращается в success.

## HTTP

Prefix: `/ultra/chat/workspaces/{wa_workspace_id}/chats/{chat_id}/turns`.

| Метод / суффикс | Доступ / действие |
| --- | --- |
| POST prefix | Ultra Chat write token, single same Origin; принять/явно продолжить тот же request; 200 только с проверенной проекцией |
| GET `/{turn_id}` | Read token; только чтение |
| GET `/by-key/{idempotency_key}` | Read token; scoped lookup для потерянного ответа |
| POST `/{turn_id}/cancel` | Write token, body `{}`, single same Origin |

Общие host/fetch-metadata, query/method/content-type/body limits существующего handler сохраняются. Полный HTTP body ограничен прежними 4096 bytes. Незарегистрированные/чужие/повреждённые данные и произвольные пути не принимаются. TEST roots передаются только через локальный `create_server(test_turn_roots=...)`; по умолчанию список пуст, non-loopback/read-disabled/write-disabled bind не включает TEST. HTTP запрос не может расширить allowlist.

## UI / запуск

STANDARD composer disabled. TEST имеет явные подписи и фиксированную модель имитатора, использует прежнюю панель диалогов. Enter отправляет, Shift+Enter/IME оставляет ввод. Busy guard предотвращает двойной click.

В localStorage хранится только scoped retry key. Текст и capability tokens не сохраняются. Ключ записывается до POST, при потере ответа остаётся. Перед ручным повтором читается прежний Turn; после reload выполняется GET lookup, без POST. Неподтверждённый исход не очищает ключ. Продолжение ACCEPTING после reload требует ввода исходного текста; другой текст получает conflict. UNKNOWN допускает отдельный новый запрос только отдельной явной кнопкой, с новым key и сохранением неизвестного старого исхода.

Воспроизводимый TEST entry: `demo_turn_chat.py` внутри этого пакета. Он создаёт только disposable TEMP Workspace/API storage, печатает URL, имеет ограниченную длительность и очищает TEMP. `--smoke` выполняет create → send → restart → history/RAW hashes. `Start_WebAlarm.bat` и launch_config.json не переключаются; это адресный TASK test harness, не второй пользовательский launcher.
