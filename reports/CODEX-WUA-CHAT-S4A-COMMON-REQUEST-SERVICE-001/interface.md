# S4A: интерфейс общего сервиса

`ordinary_chat_service.py` — автономное Python-ядро. Никакая оболочка его пока не импортирует. Допустим только внедрённый fake/mock. `gigachat_transport.extract_usage` используется как чистый parser; импорт содержащего его модуля также загружает httpx, но сервис не создаёт клиент и не вызывает OAuth. Единого chat sender в этом модуле сейчас нет: существующие физические вызовы находятся в агентском `server.py`. Его сервис не импортирует.

```python
prepared = prepare_request(
    model_id="gigachat_2_pro",
    context=({"role": "system", "content": "Synthetic instruction"},),
    user_text="Synthetic question", context_ref="fixture-revision-1",
    limits=RequestLimits(
        max_messages=9, max_message_bytes=1024, max_request_bytes=8192,
        max_response_bytes=4096, max_output_tokens=64, timeout_seconds=0.1,
    ),
)
result = await execute_request(prepared, transport=fake)
```

Числа здесь исключительно значения синтетического примера; production-значений по умолчанию нет. Все шесть ограничений обязательны. Это не тарифная или бюджетная политика, оценка токенов не выполняется.

## Подготовка

`prepare_request` принимает только точный зарегистрированный ID, без приведения типов, обрезки и fallback. Проверяет enabled, provider=gigachat, is_local=False и непустой provider_model_id. `ModelSpec` копируется в неизменяемый снимок из канонического реестра. При выполнении запись реестра проверяется снова: отзыв или любое изменение spec даёт REJECTED без вызова транспорта, замены модели нет.

Разрешённый здесь текстовый профиль контекста: необязательный единственный system в начале, затем законченные пары user/assistant. Текущий user добавляется последним. Пустой контекст допустим. Каждый элемент — ровно dict с role/content, оба текстовые; пустые/пробельные строки, повреждённый Unicode, незаконченный предыдущий user, tools/functions и лишние поля отвергаются. Это ограниченный контракт S4A, не заявление о всех возможностях API GigaChat. Текст сохраняется без trim/нормализации.

Caller заранее авторизует контекст; сервис не устанавливает доступ к Workspace и не читает его. `context_ref` — непустая непрозрачная строка, также ограниченная max_message_bytes; как путь не используется. Будущий интегратор сам выбирает конкретную разрешённую проекцию RAW и её revision, включая правила для cancelled/failed/unknown Turns. Сервис не подтягивает скрытую историю.

max_messages включает system и текущий user. max_message_bytes — UTF-8 содержимого каждого сообщения и context_ref. max_request_bytes — полный wire payload в canonical JSON (`provider_accounting.canonical_json_text`), включая model/max_tokens/stream. В payload передаётся provider_model_id, stream=False и явный max_tokens. Локальные context_ref и limits в wire не добавляются.

PreparedRequest содержит tuple неизменяемых Message, замороженные ModelSpec/RequestLimits и SHA-256 ссылку, связанную с payload, spec, context_ref и limits. payload property возвращает свежий dict. Изменение исходного контекста, выбора оболочки или dict транспорта не изменяет подготовленный снимок. request_ref детерминирован; **это не Turn ID, право доступа, ключ идемпотентности или защита от повторной отправки**. Повторный execute снова вызовет fake. Frozen Python objects не являются защитой от враждебного кода в том же процессе; сервис предназначен для доверенного Python caller, не для прямого разбора HTTP.

Ошибка подготовки — `PreparationError.code` со статическим кодом. Содержание ввода и исключение реестра наружу не добавляются.

## Выполнение и ответ

Обязательный `ChatTransport.send(payload, *, timeout_seconds)` — async, возвращает уже декодированный JSON. Встроенного транспорта, OAuth, retry и fallback нет. Сервис вызывает его один раз, передавая копию payload. Доверенный fake может быть любым объектом с этим контрактом. Интерфейс сам по себе не sandbox для произвольного Python adapter; реальные sender сейчас запрещены. Task-local guard установлен только у тестового runner, не в production.

`parse_response(prepared, decoded_response)` доступен отдельно и предполагает запрос из prepare_request. Лимит ответа считается по UTF-8 JSON с обычными разделителями Python JSONEncoder, ensure_ascii=False, allow_nan=False, включая отброшенные поля. Это предел представления уже декодированного объекта, не исходного HTTP body. Будущий адаптер обязан отдельно ограничивать физический body до decode, соблюдать deadlines и не передавать произвольные объекты вместо JSON.

Принимается ровно один choice с текстовым assistant message. Пустой content, tool_calls/function_call (даже null), неизвестный finish_reason, несовпавший model echo, повреждённые created/JSON отвергаются. finish_reason допускает stop/eos либо отсутствие/null, как у нынешнего parser server.py. Это проверка формата, не доказательство полноты генерации при отсутствии finish_reason. model/created также могут отсутствовать. Лишние поля ответа не возвращаются. Метаданные whitelist: совпавший model, stop/eos/None, неотрицательный integer created. Ответный текст — недоверенный контент; будущая оболочка сама безопасно его отображает.

ChatResult содержит outcome, execution, зафиксированный ModelSpec, request_ref, text, Usage, ResponseMetadata, error_code. Исключения транспорта и raw provider error/headers/credentials в нём не возвращаются. Ограничение относится к служебным ошибкам/metadata, а не к автоматической редакции произвольного текста модели.

Usage переиспользует extract_usage, затем дополнительно отвергает bool/нецелые/отрицательные счётчики и несовпавшую сумму полного triple. status: missing, partial, complete, invalid. Известные partial числа сохраняются; неизвестные остаются None. Только явно предоставленные нули являются нулями. raw usage и произвольные дополнительные поля не публикуются. Валидный usage сохраняется и при отклонённом ответе после успешной ограниченной проверки JSON: некорректный ответ может быть платным. При повреждённом/слишком большом JSON usage остаётся неизвестным.

| Случай | outcome / execution | Действие будущего владельца Turn |
|---|---|---|
| Preflight refusal, включая отзыв модели | rejected / not_started | Без отправки; сохранить отказ по существующему контракту |
| cancelled predicate True до вызова | cancelled_before_start / not_started | Транспорт не вызван; usage всё равно None |
| Валидный ответ | completed / response_received | Сначала durable recheck/revision/cancel, затем existing RAW/Run Store commit |
| Ошибка формата ответа | invalid_response / response_received | Не показывать как успех; учитывать предоставленный usage |
| Исключение после вызова send | transport_error / may_have_executed | Консервативный UNKNOWN, не автоматический FAILED/retry |
| Timeout или Task.cancel после вызова | unknown_after_start / may_have_executed | Не обещать нулевой расход/отсутствие исполнения, не replay |
| Ответ после deadline/отмены | unknown_after_start / response_received | Не публиковать answer; доступный usage сохранить |

cancelled callback — синхронный bool predicate, проверяется перед и после send; это не фоновый watcher. Для прерывания ожидания caller может отменить asyncio Task. Вызванный до старта cancel самого Task, при котором coroutine вообще не запускалась, обрабатывает caller. После входа отмена возвращается как типизированный UNKNOWN. wait_for требует кооперативный adapter и не может физически остановить игнорирующий отмену код; поздний вернувшийся ответ отдельно проверяется по monotonic deadline и успехом не считается.

## Условия будущего подключения

Отдельная разрешённая задача должна назначить владельца контекста и durable attempt, сопоставить results с существующим Stage 3 без второй машины состояний, обеспечить B2/бюджетные/маршрутные gates и согласовать cooperative cancellation. Нужно использовать существующий transport/OAuth-механизм, а не дублировать его. Требуются отдельные integration/restart/late-callback tests, независимая приёмка зависимостей, явное разрешение реального sender. Нынешний Stage 3 TEST не имеет подключения к этому модулю. Tk/HTTP/UI, Blueprint и real LLM остаются за пределами S4A. `chat_context.py`, упомянутый в программе как будущее ядро контекста, в текущем checkout отсутствует; новый модуль его не имитирует и не создаёт.
