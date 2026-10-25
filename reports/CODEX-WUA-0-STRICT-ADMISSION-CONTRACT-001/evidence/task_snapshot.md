

# 🟨 Строгая политика допуска MCP-брокера — offline реализация и негативные тесты

**TASK ID:** `CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001`

**ARCH CLASS:** Web Alarm Ultra / External AI Integration / STRICT_V2RAY_BROKER / Security Admission

Уважаемый агент 007 (Codex)!

Приглашаем вас выполнить следующую инженерную задачу проекта `ag_llm / Web Alarm Ultra / ChatGPT MCP`.

## 1. Главная цель

Реализовать и проверить строгую **offline admission-policy** для будущего защищённого MCP-брокера.

Политика должна запрещать переход к использованию сетевого движка, если конфигурация не соответствует требованиям безопасности либо её соответствие нельзя проверить.

Это практическая задача по существующим Python-контрактам и тестам, а не новое общее исследование sing-box.

**Основной принцип: неизвестное или недоказанное состояние = BLOCKED, никогда не DIRECT и не автоматическое разрешение.**

## 2. Исходная база

Перед началом убедиться, что пользователь перенёс документационный closeout из ветки `GPT` в `main` и синхронизировал локальную рабочую копию.

Координаторский source reference для документации: `GPT@37ef710cf0ba34f4988cba46a28595d6ce7801a5`.

Git/GitHub исполнителю запрещены без отдельного USER GO. Сверку опубликованной ревизии при необходимости запросить у пользователя или координатора.

**Адресная матрица чтения:**

|Файл|Раздел|Назначение|
|---|---|---|
|`Документация/000_Задачи Codex.md`|Правила, БЛОК 1, БЛОК 4|Обязательно|
|`Документация/08_Старт.md`|`DOC-TASK-HANDOFF-USER-01@1`, приоритетные права|Обязательно|
|`Документация/34_TACTICAL_CONTEXT.md`|`WEB_12 / CURRENT`|Обязательно|
|`Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md`|`STRICT_V2RAY_BROKER`, §7.6–7.7|Обязательно|
|`Документация/36.1_Обязательный регламент тестирования для LLM.md`|TEST-COLLAB, TEST-ENG, TEST-COV, TEST-EXEC, TEST-QA, TEST-EVID, TEST-SCOPE|Обязательно|
|`Документация/36.2_Профиль тестирования Web Alarm Workspace.md`|Применимые offline/Windows test requirements|Адресно|
|`Документация/18_Регламент сопровождения документации.md`|DOC-GIT, DOC-LOCAL-REPORT-HANDOFF, DOC-TASK-CLOSEOUT-OWNER, DOC-TASK-READ-SCOPE|Адресно|

Технические исходные материалы:

- `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/` — принятый WEB_12 bounded source review, особенно `source_callgraph.md`, `strict_route_gap_matrix.md`, `amendment_01/report.md`.
    
- `integrations/wua_chatgpt_mcp/broker.py`
    
- `integrations/wua_chatgpt_mcp/security_contract.py`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.synthetic.example.json`
    
- `integrations/wua_chatgpt_mcp/tests/broker_suite.py`
    
- `integrations/wua_chatgpt_mcp/singbox_source_review.py` — read-only source reference.
    

Не читать автоматически весь архив `001` или большие документы без адресной необходимости.

## 3. Обязательные проверки строгого допуска

### A. Authentication / credentials

Для будущего strict profile:

1. Отсутствующие или пустые `users` должны приводить к отказу в допуске.
    
2. Конфигурация без доказанного обязательного механизма authentication не может считаться готовой.
    
3. Проверить, что собственные diagnostic/error outputs не раскрывают пароли, `Proxy-Authorization` и credential material.
    
4. Опубликованные сведения об upstream-утечке ошибок должны оставаться отдельным **SECURITY BLOCKER**, пока безопасность соответствующей runtime-границы не доказана.
    

Не изменять исходники стороннего `sing` и не заявлять, что локальная фильтрация Python устранила все ошибки upstream.

### B. Маршрут и отказ от DIRECT

Строгий admission должен отвергать:

- DIRECT и любую неутверждённую fallback-схему;
    
- второй прокси, load balancing или неизвестный outbound;
    
- неутверждённые DNS, UDP, IPv6, UoT и фоновые соединения;
    
- неоднозначный endpoint, host/port или конфигурацию;
    
- неподтверждённый сетевой движок и ownership;
    
- незадекларированные изменения политики после preflight.
    

Синтетический договор с корректной структурой **не равен** разрешению на сетевой запуск.

### C. HTTP CONNECT

Разделить три события:

1. HTTP CONNECT принят обработчиком.
    
2. Маршрут разрешён строгой политикой.
    
3. Реальный исходящий socket принадлежит разрешённому брокеру и идёт к разрешённому upstream.
    

Эти события нельзя считать одним доказательством.

Для целевой CONNECT-only политики неопознанные методы, Upgrade, произвольный HTTP и назначения вне разрешённого контракта должны приводить к отказу либо к явно сохранённому BLOCKED до появления проверяемого oracle.

Не писать собственный HTTP-парсер вместо Go standard library.

### D. JSON / configuration admission

Определить и проверить строгие правила:

- один канонический защищённый источник конфигурации;
    
- запрет duplicate keys и неутверждённых unknown fields;
    
- отказ от неполного, неоднозначного или конфликтующего ввода;
    
- запрет неутверждённых merge/reload/environment overrides;
    
- явный DENY вместо небезопасных значений по умолчанию.
    

Использовать существующий parser/validator pipeline. Не создавать параллельную систему конфигурации.

## 4. Реализация

Предпочтительное решение — небольшое расширение существующих `broker.py` / `security_contract.py` и существующих тестов.

Если разделение **структурно корректен** и **допущен к будущей эксплуатации** требует двух статусов, реализовать их явно.

Не разрушать историческую валидность синтетического fixture: он может оставаться `BROKER_PROFILE_STRUCTURALLY_VALID`, одновременно имея `STRICT_ADMISSION_BLOCKED`.

Любой результат по-прежнему обязан содержать:

`can_apply=false`

`can_start_tunnel=false`

`install_uninstall=BLOCKED`

Реальный запуск запрещён независимо от успешности offline-проверок.

## 5. Разрешённый write scope

Минимально необходимые изменения:

- `integrations/wua_chatgpt_mcp/broker.py`
    
- `integrations/wua_chatgpt_mcp/security_contract.py`
    
- `integrations/wua_chatgpt_mcp/configs/broker.v1.schema.json`, только если действительно требуется совместимое уточнение
    
- `integrations/wua_chatgpt_mcp/tests/broker_suite.py`
    
- адресная новая тестовая часть внутри существующего `integrations/wua_chatgpt_mcp/tests/`, только если переиспользование старого suite неудобно и обосновано
    
- `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/**` для отчёта, manifest и безопасных evidence.
    

Никаких других изменений без отдельного пользовательского разрешения.

**Запрещено:** Git/GitHub, live Windows, WFP, firewall, Windows accounts, proxy/v2rayN, DNS, работающий sing-box/V2Ray, движок, Go install/build, tunnel, реальное сетевое испытание, production Web Alarm и изменение карточек/001/общей документации.

Новых сетевых скачиваний не выполнять.

## 6. Тестирование

Нужны реальные offline проверки Python, а не только source anchors.

Сначала сохранить исходные тесты и результаты, затем показать негативные RED/REJECT сценарии и итоговые PASS. Минимальная матрица:

1. Нет users / пустой users.
    
2. Неверный или отсутствующий credential reference.
    
3. Секрет в ошибке или диагностике.
    
4. CONNECT без подтверждения downstream.
    
5. Plain HTTP / Upgrade при CONNECT-only.
    
6. Неверный destination, порт и незадекларированный IPv6.
    
7. DIRECT, fallback, secondary proxy.
    
8. DNS/UDP/UoT/background egress.
    
9. Duplicate JSON keys, unknown field, null/default ambiguity.
    
10. Merge/reload/environment override.
    
11. Повторная подмена конфигурации после проверки.
    
12. Попытка изменить `can_apply` или `can_start_tunnel` входными данными.
    

Для каждой проверки указывать правильный отказ и его конкретный код. Нельзя считать любое произвольное исключение успешным негативным тестом.

Добавить адресные mutant/negative controls, при которых ослабление обязательной проверки обнаруживается тестами. Сохранить первый FAIL и все исправления оракулов.

Не подменять недостающие native security доказательства Python-симуляцией.

## 7. Критерии результата

**PASS в пределах offline admission**, если:

- реализована одна переиспользуемая строгая admission-policy;
    
- небезопасные и недоказанные входы отвергаются;
    
- тесты фиксируют фактические отказы, а не только наличие исходного кода;
    
- опубликованы source/test hashes, результаты, негативные сценарии и независимые ограничения;
    
- старые применимые проверки не сломаны;
    
- все activation gates остались закрыты.
    

**PARTIAL**, если часть admission требований можно определить, но доказать их нельзя без Go/native/OS среды.

**BLOCKED**, если дальнейшее движение потребует недоступного исходника, запрещённого сетевого действия или нового USER GO.

Техническая сдача:

- `report.md` — полный factual результат и MANUAL ENGINEERING REVIEW;
    
- `manifest.json` — exact paths, bytes, SHA-256;
    
- `admission_matrix.md` — критерии допуска, отказа и остаточные blockers;
    
- `checks.json` и sanitized `runs/` — команды, counts, exit codes, исходный FAIL и финальные результаты;
    
- `DOC_IMPACT.md` — предложения для №19/34/06, без самостоятельного редактирования.
    

**После выполнения:** пользователь публикует отчёт и код на GitHub. WEB_12 независимо проверяет результат. Исполнитель не очищает БЛОК 1, не ротирует БЛОКИ 2–4/001 и не объявляет самостоятельно `VERIFIED`.

**Главная цель:** получить практический, тестируемый механизм, который не позволит по ошибке принять небезопасную сетевую конфигурацию за разрешённую, сохранив все настоящие OS/WFP/MCP-gates для следующих задач.

---

