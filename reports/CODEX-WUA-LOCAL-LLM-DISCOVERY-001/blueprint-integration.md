# Стыковка с Blueprint LLM — кандидат

Blueprint LLM.md §3/§5/§6 и его тактический контекст описывают концепцию. Исполняемого графа, окончательной схемы node или нового USER GO на конструктор эта TASK не создаёт.

| Кандидат поля | Смысл / владелец |
| --- | --- |
| node_id | Стабильный ID узла будущего blueprint definition; не API URL |
| kind | Версионированный тип, например llm.call; ещё не действующий enum |
| connection_ref | Ссылка на общий EndpointProfile, machine-local URL разрешает core |
| model_ref | Binding из существующего расширенного Model Registry; обязан принадлежать connection_ref |
| role_ref | Ссылка на общий role/model assignment, не вторая копия инструкции |
| context_refs | Ссылки на разрешённые версии контекста с provenance; не файловые права из самого графа |
| input | Typed вход или ссылка на принятую пользовательскую запись; read-only snapshot на запуск |
| response | Ссылка на результат/RAW/артефакт существующего ядра после выполнения; не второй storage текста |
| status | Состояние node invocation; не подмена Turn/RUN/attempt state |
| error | Безопасная ссылка/структура ошибки ядра; UNKNOWN не превращать в SUCCESS |
| usage | Ссылка на фактические provider usage и существующий accounting; неизвестное остаётся неизвестным |
| run_ref | Ссылка на существующий RUN/attempt; для отдельного graph execution потребуется поздний mapping |

Configuration definition (node_id/kind/refs/input-binding) отделить от invocation result (resolved versions/response/status/error/usage/run_ref). При запуске заморозить config/model/context revisions, затем повторно проверить действующие права перед физической отправкой. Изменение URL во время очереди не должно переключить уже принятую попытку на другой endpoint незаметно.

Путь будущего вызова: **Blueprint node → общий execution facade → разрешения/Turn/attempt/budget/recorder → protocol adapter**. Tk и Web используют тот же путь; provider adapter не исполняет граф и не создаёт сессии/agent tools. Разрешённость tools/function calling — отдельный authority, даже если модель объявляет такую capability.

Узлы не хранят IP, ключи, OAuth tokens или machine-specific paths. При выключенном/неперепривязанном connection_ref вернуть явную ошибку; историю сохранить. Alias модели не смешивает одинаковые имена разных серверов. Никакой автоматической paid/live или другой host fallback после неизвестного исхода.

Число выходов не ограничивать придуманными двумя/тремя состояниями: первоисточник допускает именованные typed outputs/ветви; политика отказов/циклов/повторов потребует отдельной архитектуры. Текущая рекомендация только сохраняет совместимость refs, не утверждает полную схему графа.
