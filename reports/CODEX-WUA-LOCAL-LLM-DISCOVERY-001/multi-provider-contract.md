# Минимальный многохостовый контракт — ПРОЕКТ

Статус **PROPOSAL / IMPLEMENTATION NOT AUTHORIZED**. Это контракт дальнейшей работы, не описание реализованного адаптера. Наблюдения установки — host-inventory.md и provider-api-matrix.md. Сохраняются №37 §2.1–2.4, общий Model Registry, Workspace/Chat/RAW, будущий Turn и существующие RUN/attempt/budget authorities.

## Выбор варианта

| Вариант | Преимущества | Ограничения по полученным фактам |
| --- | --- | --- |
| Полностью отдельные Ollama/Colibri adapters | Native inventory, load state, engine-specific diagnostics | Colibri не идентифицирован; написание ColibriAdapter сейчас зафиксирует догадки. Полное дублирование HTTP/errors/streaming нежелательно |
| Один OpenAI-compatible transport для всех | Общие list_models/chat и часть stream/parser, проще новый совместимый сервер | Ollama GET models работает, но chat не испытан. Native tags/ps/digest/load policy теряются; Colibri compatibility неизвестна. OpenAI-compatible не равно полное равенство протоколов |
| **Рекомендация: тонкие protocol adapters + общая HTTP/security основа** | Общая сеть, deadlines, лимиты, диагностика; узкие Ollama-native и OpenAI-chat profiles; engine identity отдельно | Нужны schema/version/capability tests каждого реально включённого профиля. На первом шаге только discovery, без inference/UI |

Существующий GigaChat helper сохраняется до отдельного безопасного выделения execution facade. Название Colibri не регистрируется как поддерживаемый engine без его identity/version. При подтверждении OpenAI-compatible Colibri можно подключить через такой профиль с узким override; новый IP не создаёт новую ветку кода.

## Единственные логические владельцы

1. **Model Registry** остаётся model_registry.py / общий core. Builtin ModelSpec и прежние IDs продолжают читаться. Discovery добавляет проверенные bindings через расширение этого владельца, а не второй каталог моделей у UI/Blueprint.
2. **Endpoint profile** — расширение существующего settings/profile механизма, не замена файла selection. Текущий ultra/connections.json хранит выбор роли; нельзя объявить его уже готовым connection server registry или молча переписать его схему.
3. **Selection** остаётся shared/core ref; EVM отображает общий catalog. Tk/web clients не заводят отдельные модели/ключи и не посылают HTTP к inference host напрямую.
4. **Execution** — будущий общий сервис Turn/attempt/budget/recorder по №37. Адаптер переводит протокол, но не создаёт параллельные Chat/RAW/Task/Run/budget stores. P9 и Stage3 разрешения — отдельные gates.

В первой узкой реализации endpoint profiles передаются сервису как явно разрешённые read-only параметры. Постоянное редактирование/перенос настроек и UI идут отдельной принятой дельтой. Это позволяет проверить discovery, не создавая преждевременно второе хранилище.

## Идентичности и версии

Кандидат EndpointProfile:

```json
{
  "connection_ref": "conn_example_a",
  "provider_kind": "ollama_native",
  "protocol_profile": "ollama_http_v1",
  "config_revision": 1,
  "endpoint_binding_ref": "machine_local_endpoint_a",
  "credential_ref": null,
  "credential_revision": 0,
  "security_policy_ref": "explicit_host_policy_a",
  "enabled": true
}
```

Значения — синтетические примеры. Физический URL хранится в проверяемой machine-local binding-конфигурации, секрет — только по credential_ref в выбранном credential store; store/политика требуют отдельного решения. URL не входит в Blueprint/переносимый Chat и не является стабильным ID. Один физический сервер может иметь несколько API endpoints; endpoint identity не равна утверждению об одном физическом компьютере.

ModelBinding общего Model Registry: `model_ref`, `connection_ref`, `provider_model_id` (неизменяемая строка, например deepseek-r1:8b), `display_name`, `observed_model_revision/digest` (nullable), `capabilities`, `source`, `observed_at`, `valid_until`, `enabled`. `model_ref` — стабильный внутренний ID привязки; уникальность минимум `(connection_ref, provider_model_id)`, а используемый digest фиксируется снимком при исполнении. Одинаковые названия на conn_A/conn_B — разные bindings. На смене тега/digest наблюдение устаревает; старый RUN не переписывается. Если backend не позволяет закрепить digest, строгая воспроизводимость отмечается UNVERIFIED, а не обещается по tag.

Существующий `api:provider:model_id` остаётся **legacy binding ID**, не server ID. Нужны явная versioned mapping и сохранение старого выбора; нельзя просто добавить двоеточия и пройти parser ровно трёх сегментов. Ни rename IP, ни импорт Workspace не создают новую identity модели/чата автоматически. Удаление/disable endpoint сохраняет references в истории и возвращает понятную ошибку, не выбирает другой host молча.

## Discovery и состояния

Факты независимы, а не один зелёный последовательный статус:

| Факт | Достаточное свидетельство | Что он не доказывает |
| --- | --- | --- |
| CONFIGURED | Валидный разрешённый profile с revision | Что реальный сервер доступен |
| REACHABLE | HTTP ответ от разрешённого destination, timestamp | Что ответил нужный engine либо нужный API |
| AUTHENTICATED | Принята применимая auth для указанного scope; для анонимного discovery — NOT_REQUIRED_FOR_THIS_METHOD | Что inference/управление моделью разрешены |
| API_COMPATIBLE | Валидный ответ конкретного method/profile/schema | Полную совместимость /v1/chat/completions по одному /v1/models |
| MODEL_AVAILABLE | Нужная identity в свежем catalog этого connection | Что она в памяти, помещается в VRAM и отвечает |
| INFERENCE_CONFIRMED | Отдельно разрешённая реальная успешная попытка, точные version/model/config, scope и время | Product PASS, tools/vision support или разрешение следующей попытки |

Каждый факт: `value`, `verification=VERIFIED/UNVERIFIED/UNSUPPORTED`, `scope`, `observed_at`, `expires_at`, `config_fingerprint`, `evidence_ref`. UNSUPPORTED только по явному контракту/доказанному отказу, не по timeout. Отдельно `execution_permission=DENIED/NOT_GRANTED/GRANTED` с authority ref; discovery никогда её не повышает. На смене URL/credentials/protocol/model revision прежние подтверждения инвалидируются, история остаётся.

Discovery явно запускается пользователем или принятой политикой; health/list_models без auto-inference, pull, warm-up, unload, model switching. TTL cache с ограничением числа записей/байт; stale catalog виден как stale, не подтверждает доступность. Недоступный host не удаляет его модели/выбор/историю. API не даёт достоверного active-download статуса — вернуть UNKNOWN.

## Интерфейс адаптера

Кандидат `health(connection_snapshot, deadline)`, `list_models(...)`, `get_capabilities(model_ref, ...)`; позже `chat(request, attempt_ref, permission_snapshot)`, `generate(...)`, `stream(...)`, `cancel(attempt_ref)`. Каждый метод имеет явный supported/verification scope. API methods не запускают shell, не подхватывают user-named Python modules и не выбирают адрес из произвольного prompt.

Результат discovery: `connection_ref`, `config_revision`, `protocol_profile`, `server_version`, `engine_identity={value,verification}`, `observed_at`, `models[]`, `facts[]`, `warnings[]`, `error={code,retryability,scope}`. Неподдерживаемое необязательное поле — null/UNVERIFIED; не придумывать windows/context/capacity из display name.

Поздний stream нормализует `text_delta`, отдельные optional reasoning/tool deltas, `usage`, `terminal`, `error`, сохраняя профиль исходного протокола. NDJSON/SSE парсеры раздельные; incomplete terminal/потерянный final usage не становятся SUCCESS/нулевым расходом. Tool declaration не даёт прав выполнять tools; выполнение по authority Ultra/Web Alarm.

## Ошибки, ресурсы и восстановление

Обязательная классификация: CONFIG_INVALID, DESTINATION_DENIED, CONNECT_FAILED, CONNECT_TIMEOUT, AUTH_REQUIRED/REJECTED, API_SCHEMA_MISMATCH, MODEL_NOT_FOUND, SERVER_BUSY, RESOURCE_EXHAUSTED, READ_TIMEOUT, STREAM_ERROR, CANCEL_REQUESTED, CANCEL_CONFIRMED (только доказанно), OUTCOME_UNKNOWN, USAGE_UNKNOWN. Отдельно HTTP status, provider error code и безопасная диагностика; без raw headers/secrets/prompts по умолчанию.

Discovery GET можно ограниченно повторять по отдельной политике. Inference после возможной отправки при timeout/disconnect/cancel — UNKNOWN с существующей attempt identity/обязательствами. Не повторять автоматически на другом сервере, не уменьшать бюджет до нуля и не объявлять отмену backend подтверждённой только по закрытию клиента. Host outage/rename/disabling сохраняет историю; восстановление не повторяет физическую отправку по одному наличию RAW.

Очередь/лимиты: admission на connection и общую resource group, поскольку два endpoints могут делить GPU. Max in-flight сначала консервативно 1 для отдельно принятой execution-политики; реальные capacity/серверные queue limits UNKNOWN до измерений. Это проектное значение, не диагностика сегодняшнего Ollama. При невозможности durable записи attempt/result — fail closed по будущему execution contract. Не превращать diagnostic callback в авторитетный журнал.

## Сетевой доступ и перенос

Все вызовы идут из общего Python-ядра. До запроса: allowlisted scheme/host/port/path profile, запрет URL userinfo/fragment, control chars и произвольных query, canonical IP/IPv6, ограниченные redirects (на первом шаге запрещены), time/response/body/model-count limits. Environment proxy не должен расширять destination; TLS verification не отключать.

LAN-сети требуют **явного адресного разрешения**, а не общего разрешения на любой private IP. DNS rebind, IPv4-mapped IPv6 и redirects не должны обходить проверку фактического peer. Link-local metadata/service endpoints, Unix sockets, file/FTP и иные schemes запрещены по умолчанию. Credential не переносится на другой origin; логирование редактирует чувствительные поля.

Для нынешней .77 доступ не доказан. Будущий безопасный вариант: отдельно согласованный bind на нужный интерфейс плюс адресный firewall и auth/TLS proxy/VPN по выбранной политике. Это варианты для USER GO, без текущей настройки. MCP/V2Ray/WFP freeze не обходится созданием туннеля. Loopback допустим только на своей машине; после переноса URL перепривязывается, все факты revalidated, credentials/OS rights авторизуются заново. Второй/третий host — новые data records в том же профиле, без if-ветвей по IP.
