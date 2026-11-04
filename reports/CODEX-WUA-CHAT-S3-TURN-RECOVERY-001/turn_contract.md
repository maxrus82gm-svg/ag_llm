# Turn / Stage3 — проект контракта после исследования

STATUS: DESIGN ONLY / NOT IMPLEMENTED. Два подтверждённых Run Store blocker останавливают зависимую реализацию по TASK §4.4. Этот документ не вводит рабочий формат, HTTP API или отдельный Run Store.

## Владение и записи

Существующие Workspace/Chat IDs принадлежат `context_storage`; RAW остаётся в `.ultra/chats/<chat_id>/messages/<message_id>.json`. Для Turn допустима только компактная связующая запись под тем же Chat и общим Workspace writer lock. Полные RAW не дублируются в журнале Turn. `run_store.py` остаётся единственным хранилищем RUN и событий попытки; Web Alarm TASK не создаётся автоматически. `task_block_id` — только техническая группировка существующего recorder.

Кандидат схемы `turn.v1`: schema/version, turn_id, workspace_id, chat_id, idempotency_key, request_sha256, user_message_id, frozen references (connection_id/model_id/provider_model_id/role, context reference+revision/hash, policy reference+revision), attempt_id/run_id при устойчивой фиксации попытки, assistant_message_id при опубликованном ответе, cancel_requested, revision/error classification. `state` — проверяемая проекция устойчивых фактов Turn/RAW/единственного RUN, а не вторая независимо изменяемая машина исполнения. Точные типы и public API требуют продолжения реализации после снятия blocker.

Ключ scoped к Workspace ID + Chat ID. Клиент создаёт его один раз до POST. Можно вывести постоянные turn/user-message IDs из этого scope и ключа; fingerprint считается по каноническому телу запроса, а не по меняющемуся глобальному выбору модели. Другой ключ при том же тексте — новый намеренный Turn. Отказ при совпадении ключа и различном fingerprint не меняет первую запись.

## Порядок и recovery (требования к реализации)

1. Существующая authority: Origin/method/body bounds/write-token; регистрация и ownership, no implicit storage initialization. До новой записи валидируются разрешённые references. Модель разрешается через общий `UltraConnectionService.selection('chat')`; `SAVED` означает актуальную ссылку, не разрешение внешней отправки. CORRUPT/INVALID_REFERENCE/REGISTRY_UNAVAILABLE отклоняются.
2. Под общей OS-блокировкой Workspace найти прежний Turn до выбора новых model/context snapshots. При replay вернуть его прежние snapshots; при конфликте тела — 409. Изменение EVM preference не переписывает принятый Turn. Контекст должен ссылаться на разрешённые Project/Message Context версии из ядра; отсутствие нужного read/permission-контракта — отказ, не произвольный путь из HTTP.
3. Устойчиво опубликовать intent/fingerprint/определённые IDs, затем `commit_raw_message(..., message_id=<same>, expected_workspace_id=...)`. Текст после сбоя до RAW не считается принятым: чтение показывает незавершённое принятие; продолжение требует тела исходного запроса с тем же ключом и fingerprint. Нельзя генерировать новый UUID через `append_raw_message` при replay.
4. HTTP success только после проверки связки intent + user RAW. Сбой после RAW до подтверждения intent восстанавливается по тому же message_id без дубля. GET не выполняет запрос провайдеру и не начинает попытку.
5. Перед имитатором устойчиво зарезервировать попытку/единственного владельца, сохранить RUN link и факт разрешённого начала в **существующем Run Store**. Именно этот шаг сейчас небезопасен и остановлен. Нельзя заменить его файлами `attempts.jsonl` в другом месте.
6. Событие результата имеет стабильную identity. Повтор события проверяется по содержимому и receipt; assistant RAW коммитится одним определённым ID. Успех — только после проверки result receipt и RAW, не по тексту диагностического callback. При позднем событии после terminal/cancel оно не переводит исход незаметно в SUCCESS.

## Минимальные состояния

| Проекция | Устойчивое основание | Recovery |
| --- | --- | --- |
| ACCEPTING | Есть intent, но необходимая RAW-связка не подтверждена | Та же identity; приём не объявлять успешным |
| READY | Intent + user RAW согласованы, попытка не начата | Чтение/явное разрешение попытки, без автоотправки |
| ATTEMPTING | Устойчивый RUN/attempt start и владелец | После утраты владельца исход UNKNOWN, без автоматического повторного вызова |
| SUCCEEDED | Подтверждён результат + assistant RAW, нет terminal-конфликта | Только чтение/replay того же события |
| FAILED | Есть доказанный terminal failure | Не превращать диагностический текст в успешный ответ |
| CANCELLED | Отмена зафиксирована до возможного начала попытки | Позднее событие не восстанавливает выполнение |
| UNKNOWN | Попытка могла начаться, но конечный факт не доказан; в том числе cancel после начала | Явное решение для новой attempt identity; не SUCCESS и не обещание нулевой стоимости |

Отказ невалидного HTTP до устойчивого принятия не требует отдельного Turn. Отмена после ATTEMPTING — cancel_requested + честная неопределённость, а не доказательство отсутствия вызова.

## HTTP/UI после prerequisite repair

Минимальный будущий API: POST принятия по Chat + клиентский ключ; GET по тому же scope/key или Turn ID; отдельная явная отмена. Чтение только read-authority, изменение только write-authority, без root/context paths из body. STANDARD сохраняет disabled send. TEST разрешается только для синтетической конфигурации и детерминированного имитатора, с видимой маркировкой.

UI до повтора после lost response сначала читает прежний ключ. Pending key сохраняется до подтверждённого исхода; refresh не создаёт новый ключ. Граница хранения текста pending-запроса в браузере требует отдельного решения о приватности; запись tokens/секретов в localStorage запрещена. Текущий composer в этой TASK оставлен без изменений: кнопка disabled и новых Turn-маршрутов нет.
