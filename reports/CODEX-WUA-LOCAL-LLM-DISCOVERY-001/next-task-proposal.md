# Проект следующей узкой TASK — НЕ НАЗНАЧЕНА

Кандидат ID `CODEX-WUA-MULTIHOST-DISCOVERY-ADAPTERS-001`. **DRAFT PROPOSAL / NOT ASSIGNED / USER GO REQUIRED / IMPLEMENTATION NOT STARTED**. Это предложение в рамках исследовательского отчёта, не новая активная TASK и не заполнение БЛОКА 1.

## Цель

Реализовать **только безопасный read-only discovery core**: явно переданные endpoint profiles → проверенный destination → bounded health/list_models → нормализованный catalog/facts общего Model Registry. Поддержать два host с одинаковой моделью без смешения ID. Никаких prompts, chat/generate/stream/cancel/load/unload, автоматического inference, UI или постоянной настройки серверов.

## Предполагаемая область

- Новый небольшой модуль `llm_provider_discovery.py`: typed profile/facts/result, injected HTTP interface, Ollama inventory profile и OpenAI models profile. Engine identity Colibri остаётся UNKNOWN до серверного подтверждения; не создавать специфический ColibriAdapter по названию.
- `model_registry.py`: минимальные обратносовместимые типы/фасад для discovery bindings и явное различение connection_ref/model_ref. Существующие шесть GigaChat ModelSpec, IDs, enabled guard, list/get поведение сохранить. Один логический владелец; не создавать второй независимый catalog у UI.
- Новые адресные `test_llm_provider_discovery.py`, `test_model_registry_discovery.py`; корректировка существующих registry tests только при доказанной необходимости и явном включении координатором.
- Собственный `reports/<new-task-id>/`. Input profiles в первом шаге передаются вызывающим кодом/fake fixtures; **без нового постоянного settings store или изменения selection файла**.
- Исключены `web_alarm/server.py`, `web_alarm/ui.py`, credentials/config services, существующий Run Store, Turn/RAW writers, budget journal, B2/WA4-R и MCP. Названия/точный diff утверждает координатор при назначении, это не текущее write-разрешение.

## Зависимости и стоп-условия

1. Независимая приёмка этого исследования LLM15, согласование candidate contract и versioned ID migration plan.
2. Подтверждённый scope WEB20/LLM15: локальная №40 ещё WEB19. UI requirements передаются WEB20 через LLM15, локальный исполнитель документ не меняет.
3. Для реального smoke отдельно перечислить host/port/method. Проверенная .9:11434 доступна только в её loopback; `127.0.0.1` на другой машине означает другой сервер. Не использовать .77:11434, пока её listener и разрешение не подтверждены.
4. Discovery можно проверить на mocks независимо от P9. **Любое расширение до отправки сообщений — BLOCKED до отдельного P9/Turn/permission/budget решения и USER GO.** Stage3 не открывается успешным inventory.
5. Инжектируемый transport по умолчанию не посылает сеть при import/init. Нельзя тестировать на настоящих Workspace или «проверять» отсутствующую модель её скачиванием.

## Приёмочные критерии

- Два connection profiles с одним provider_model_id дают разные стабильные model_ref; смена machine URL не уничтожает refs, но сбрасывает актуальность подтверждений.
- GET inventory не вызывает POST/inference/model mutation; ограничены timeout/body/models/redirects, host policy, схемы URL и фактический destination. Auth failures/schema failures не превращаются в пустой успешный catalog.
- Старые GigaChat records/selection IDs читаются прежним способом; manual provider metadata с adapter=None не становится выполняемым кодом.
- Понятные facts CONFIGURED/REACHABLE/AUTH*/API_COMPATIBLE/MODEL_AVAILABLE; INFERENCE_CONFIRMED остаётся UNVERIFIED, permissions не повышаются.
- Cache stale/offline не удаляет history/selection; нет скрытого fallback к другой машине. No credentials/raw headers/private prompts в output/logs.
- Targeted tests и отрицательные controls из test-plan.md; scope/команды/source hashes/raw initial FAIL сохранены. Полный продуктовый прогон только по impact/разрешению, без сети/paid/live.
- Документированный Python data contract пригоден для будущей UI-интеграции WEB20 и Blueprint refs, реализация этих клиентов не входит.

## Требования для WEB20 через LLM15

Сценарий настройки: «Добавить сервер» → provider/API profile и machine-local URL → policy/auth ref → **«Проверить доступность» без модели/inference** → catalog с provenance/датой → выбор binding для chat. UI различает доступность, модель на диске/в памяти, устаревшую проверку, разрешённость и отдельно подтверждённый inference. Для непройденной проверки — причина и безопасное повторение; сервер можно disable без удаления истории, URL перепривязать с revalidation.

UI payload: `connection_ref`, `config_revision`, `protocol_profile`, `display_name`, `facts[]`, `observed_at`, `models[{model_ref,connection_ref,provider_model_id,revision,capabilities}]`, `error`, `warnings`, `execution_permission`. В UI нет credential values и кнопки, скрыто запускающей тяжёлый прогрев. «Тест модели» — отдельное будущее действие с явным разрешением. Browser работает с Python-ядром, не напрямую с inference hosts.
