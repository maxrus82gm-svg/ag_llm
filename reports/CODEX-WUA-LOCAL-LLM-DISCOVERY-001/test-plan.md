# План последующей проверки и выполненный scope

В этой исследовательской TASK выполнены только GET inventory, host read-only queries, статический source review и проверка собственного отчётного пакета. Реальные inference, latency, streaming, cancel, concurrency, adapters E2E, product suites и model lifecycle **NOT RUN**. Ниже — план инженерной работы, не заявленные результаты.

| Проверка | Изолированный oracle / достаточный результат |
| --- | --- |
| Два host с одинаковым model name | Инъецированные fake transports для conn_A/conn_B; отдельные model_ref/capabilities/results, без смешения IDs |
| Legacy registry / selection | Шесть GigaChat ModelSpec и api:provider:model_id остаются валидны; миграция явная; неизвестная schema/ref отклонена, прежний выбор не перезаписывается |
| GET-only discovery | Fake transport отвергает POST/DELETE/inference URLs, неизвестные destinations и redirects; init/import не посылает запросы и не создаёт каталоги |
| Inventory schemas | Нормальные Ollama tags/ps и OpenAI models; пустой список, дубликаты/слишком длинные IDs, Unicode, colon/slash, malformed JSON, огромный body/list, null fields; bounded отказ без ложного READY |
| Отсутствие credentials | Не читать ключи для anonymous inventory, не показывать environment/header values. 401/403 — AUTH_* для данного method, не пустой успешный catalog |
| SSRF и адреса | Explicit allowlist, userinfo/query/fragment/control chars, DNS rebind, redirect на metadata/loopback другого профиля, IPv6 mapped IPv4, proxy env; peer mismatch fail closed |
| Отказы сети | Connection refused/timeout/read timeout/invalid certificate/HTTP error. Existing selection/history не удаляются; facts становятся stale/unverified |
| Busy/OOM | Mock HTTP 429/503 и backend resource error не дают успех/самовольный alternate-host retry; очереди ограничены |
| Capability provenance | Смена model tag/digest/config/credential revision инвалидирует старую проверку; tools metadata не считается execution evidence |
| Будущий stream | NDJSON/SSE chunks через произвольные границы UTF-8, partial JSON, midstream error при HTTP 200, missing terminal/usage, heartbeat и разрыв. Ошибка не превращается в готовый RAW assistant result |
| Будущий cancel | До отправки = NOT_SENT; после отправки/на границе = UNKNOWN до evidence. Client close не освобождает liability автоматически |
| Будущий Turn recovery | Crash до durable acceptance/после sent/после ответа до RAW/после RAW до terminal; no duplicate provider attempt или messages. Использовать существующие ID/Run Store после отдельного P9 решения |
| Resource group | Два endpoints одного GPU не обходят общий admission limit; CPU offload/context/VRAM pressure проверять позже только с отдельным разрешением |
| Portability | Перепривязка URL у прежнего connection_ref; импорт данных без secrets/прав, revalidation; старые RUN сохраняют source snapshots, никаких hardcoded .9/.77 |
| UI boundary | Browser не вызывает inference host; discovery не зелёный inference indicator. Передача WEB20 через LLM15, server/ui отдельным scope |

Для следующего discovery-only шага исполняются первые девять групп через fake transport/injected config и targeted existing registry/selection tests на disposable paths. Последующие execution/stream/recovery группы сначала только проектируются; Stage3/P9 нельзя обойти успешным mock transport.

Негативные маркеры следующей реализации: same-name collision, hidden POST on list, auto-fallback после timeout, зафиксированный false inference success, redirect destination bypass, secret leakage. Удаление соответствующего guard должно ломать oracle; tests не должны зеркалить только форму dataclass. Реальные server smoke — отдельно согласованные GET на уже известный endpoint, без автоматического model wake-up.
