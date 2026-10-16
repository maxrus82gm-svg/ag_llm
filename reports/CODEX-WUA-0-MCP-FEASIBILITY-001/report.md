# CODEX-WUA-0-MCP-FEASIBILITY-001 — итоговый отчёт Codex 007

Дата: 16 октября 2026, Asia/Yekaterinburg.
**Итог: PARTIAL / RESULT READY / AWAITING INDEPENDENT VERIFICATION.**
Локальная цепочка MCP → Web Alarm доказана на синтетической TASK. Подключение из обычного ChatGPT Desktop Chat и подтверждённый двусторонний канал уведомлений пока не доказаны. Независимая приёмка не объявляется.

## 1. Что исследовано

Адресно изучены актуальные локальные документы 08, 000, 18, 01, 19, 34, 37, архитектурные ссылки 23–25 и тестовый маршрут 36 / 36.1 / 36.2. Постановка пользователя сохранена в assignment.md; SHA-256 локальных документов — document_sources.json. Удалённая актуальность документов не подтверждалась.

В существующем коде:
- server.py:20,65,7219–7290 — MCP старой Ultra: gigachat_ask, gigachat_file_task, gigachat_agent_task. Это модельные/файловые операции; они не вызывались.
- web_alarm/server.py:165,299 — WebAlarmApi; GET /status и GET /tasks/{id}/context доступны через собственный HTTP API. Это REST API, само по себе не MCP.
- web_alarm/context_pack.py:34 — Entry Context Pack получает факты из server-owned projection; сохранённый checkpoint не считается authority.
- Новую Ultra Tab, модельный runtime и production интеграцию эта TASK не реализует.

## 2. Реальная среда и доступность подключения

Обнаружен запущенный ChatGPT.exe из пакета OpenAI.Codex_26.1007.9446.0. Это сведения о пути процесса, а не проверка обновлений или тарифа аккаунта. Python 3.12.10, mcp 2.2.0, httpx 0.28.1, pydantic 2.13.5.

В прочитанной конфигурации Codex есть stdio MCP node_repl, astro_modeler и gigachat_ultra; Web Alarm MCP там не зарегистрирован. Текущая Codex-сессия действительно предоставляет инструменты gigachat_ultra. Из этого нельзя заключить, что тот же MCP доступен обычному ChatGPT Chat.

Поиск Plugin Management по Web Alarm не дал точного совпадения; каталог не является полным реестром установленных или частных плагинов. Тариф, workspace entitlement и права на создание локального плагина не проверены. Get-AppxPackage оказался недоступен в текущем PowerShell; версия установлена по пути процесса. Подробности — environment.json.

## 3. Способы подключения по OpenAI Docs

1. **Локальный плагин со stdio MCP.** Документация описывает локальные marketplaces и установку в desktop-приложении. Это наиболее прямой кандидат для частной разработки. Подготовлены candidate-plugin/plugin.json и mcp.json; они не установлены, используют абсолютные пути этой машины и не являются переносимым пакетом. Применимость именно к обычному Chat требует отдельной проверки. [Package your plugin](https://developers.openai.com/plugins/build/plugins)

2. **Частный сервер через Secure MCP Tunnel.** Поддерживаются stdio/HTTP на стороне локального tunnel-client; нужен tunnel_id, runtime API key и соответствующие права организации/workspace. Это технически документированный запасной путь; туннель, ключи и сетевые настройки не создавались. Потребность в runtime key не равна вызову модели через OpenAI API. [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

3. **Удалённый custom MCP через HTTPS, SSE/streaming HTTP.** Нужен достижимый MCP endpoint и разрешения аккаунта/workspace. Обычный localhost пользователя не следует считать автоматически доступным облачному клиенту. Публичный endpoint в этой TASK не поднимался. [Add custom MCP server](https://developers.openai.com/api/docs/guides/custom-mcp-server), [Connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt)

Публичная публикация desktop-only MCP-плагина — отдельная процедура с ограничением для approved partners; это не доказательство запрета на частную локальную разработку. [Desktop-only plugins](https://developers.openai.com/plugins/deploy/desktop-only)

## 4. Фактически выполненный proof-of-concept

Цепочка:
**локальный SDK MCP client → stdio MCP adapter.py → собственный HTTP loopback Web Alarm → одноразовый synthetic Workspace/TASK.**

Адаптер создаёт TemporaryDirectory с префиксом wua-mcp-, использует явный storage_root, привязывает HTTP к 127.0.0.1:0 и удаляет только собственную временную fixture при завершении. Production URL или произвольный workspace/file path ему передать нельзя.

Три MCP-инструмента:
- ping — читает GET /status собственного fixture-сервера;
- list_capabilities — возвращает точный allowlist и диагностику неизменности fixture;
- read_synthetic_context — читает только synthetic_wua_0 через настоящий GET /tasks/synthetic_wua_0/context.

Все инструменты отмечены read-only/non-destructive. Исходящий HTTP не использует proxy из окружения; redirects запрещены, ответ ограничен 65 536 байтами, timeout — 3 секунды. После создания Windows event loop аудит ограничивает соединения точным fixture loopback-портом, запрещает запуск дочерних процессов адаптером и запись файлов вне его временного root. Это дополнительный исследовательский guard, не полноценная security sandbox.

**Последний прогон: 34 PASS, 0 FAIL, 0 ERROR, 0 SKIP; exit 0, 3.563 секунды.** Это 34 именованные проверки одного интеграционного smoke, не 34 независимых больших теста. Два свежих MCP-процесса, согласованный protocolVersion 2025-11-25.

Подтверждены initialize и точный набор tools, health настоящего WebAlarmApi, идентичность синтетической TASK, lifecycle authority, PLANNED/NO_MICROTASK/MISSING checkpoint, SHA-256 результата, одинаковое повторное чтение; отказ для чужого TASK ID, path traversal, абсолютного пути, неправильного типа и отсутствующего mutation tool. Оба процесса сделали только три разрешённых GET. Байтовые хеши fixture до/после совпали; guard violations = 0. После перезапуска получен новый synthetic nonce. Хеши 45 runtime/PoC файлов до/после прогона совпали.

Команда из M:/GitHub/ag_llm:
`./.venv/Scripts/python.exe -B reports/CODEX-WUA-0-MCP-FEASIBILITY-001/verify_smoke.py --output <НОВЫЙ_ПУТЬ_JSON>`
Использовать новый output, сохраняя исходные evidence.

Основное доказательство — smoke_attempt_05.json с именами checks, SDK результатами, raw fixture fingerprints, версиями и source hashes. Первые попытки сохранены:
- 01: ERROR до assertions — guard блокировал внутренний Windows asyncio socketpair;
- 02: ERROR до assertions — verifier использовал v1 Python field names вместо snake_case в SDK 2.2.0;
- 03: 5 PASS / 1 FAIL — неверный oracle authority_source=projection, исправлен на точный lifecycle contract существующего кода/теста;
- 04: 8 PASS / 1 FAIL — правильный отказ скрывал стабильный код через ValueError; заменён на штатный ToolError;
- 05: 34 PASS.
Это дефекты исследовательского прототипа/проверки, не установленные дефекты Web Alarm. Подробности — initial_failure.md; прежние ошибки не стирались.

## 5. Уведомления в существующий чат

Точный целевой чат найден по ID **6acfcf40-e98c-83ed-b435-cc0eb062b996**, название сверено: «Сервер WEB_08». Название используется для отображения, ID — для адресации.

Один синтетический probe с event_id CODEX-WUA-0-MCP-FEASIBILITY-001:delivery-probe:20261016:01 отправлен штатным инструментом Codex. Вызов вернул целевой threadId без ошибки: **TRANSPORT ACCEPTED**. Два последующих bounded readback не показали сам event_id/ACK; часть ответов чата возвращается как content-reference. Поэтому **MESSAGE VISIBLE / RECEIVER ACK / двусторонняя доставка — UNVERIFIED**. Повторного probe не было.

В доступной операции отправки нет caller idempotency key, messageId или delivery receipt. Это возможность активного Codex-чата; standalone Web Alarm не получает её автоматически. Автозапуск relay, пробуждение спящего чата, ответ обратно в Web Alarm, concurrent delivery, offline recovery и exactly-once не проверены.

Для следующего этапа предлагаю server-owned outbox: event_id + TASK ID + target_chat_id + report hash; отдельные состояния prepared, sending, transport_accepted, message_visible, receiver_ack, delivery_unknown. Дедупликация на отправителе и получателе. Только определённый отказ до отправки допускает ограниченный повтор; timeout/потеря ответа требуют readback/reconciliation, без слепого resend. ACK не равен independent acceptance. STOP, человеческая авторизация и Web Alarm gates сохраняются. Это предложение, не реализованная функция.

Полный настоящий отчёт передаётся тем же разрешённым механизмом с отдельным event_id CODEX-WUA-0-MCP-FEASIBILITY-001:final-report:20261016:01. Результат вызова и предел подтверждения фиксируются в notification_delivery.json. Полный текст report.md остаётся доступным для ручной передачи.

## 6. MANUAL ENGINEERING REVIEW и ограничения

Проверены порядок bootstrap → явный fixture root → loopback listener → allowlisted GET → redaction путей → MCP result и shutdown; отказ до HTTP для чужих IDs; отсутствие tools для mutations/model API/Git. Источник результата — настоящий server-owned context endpoint, а nonce и независимое вычисление SHA исключают подмену ответа одной статичной строкой. Проверка байтов охватывает только disposable fixture; она не является аудитом всех дисков компьютера.

До production нужны authentication/authorization, workspace/TASK scopes, версионированные contracts для status/context/report/evidence, ограничения размера/частоты, freshness/source revision и управление lifecycle. Локальный HTTP fixture без auth безопасен только в данном disposable scope; исследовательские guards и annotations не заменяют permissions. Конкурентное изменение реальных данных, STOP/cancel, потеря соединения, oversized/auth/error HTTP ответы и backpressure отдельно не тестировались. Полный Web Alarm/Ultra regression и CI не запускались: production runtime не менялся.

UI-проверка обычного ChatGPT Desktop осталась NOT RUN. Применён [Computer Use SKILL.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/skills/computer-use/SKILL.md); его [guidance.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/docs/guidance.md) прямо требует: «Do not automate the ChatGPT desktop app UI or Codex CLI or Codex extensions within Windows apps.» Запрет не обходился другим UI-механизмом. Регистрация плагина, выбор обычного Chat и три вызова из него остаются отдельным ручным end-to-end gate.

**Процессное отклонение:** до чтения карточки выполнены read-only git status и git log -1, запрещённые DOC-GIT-01@1. Это нарушение регламента; Git-записей не было, после обнаружения запрета Git/GitHub не использовались. Локальный PASS не отменяет отклонение. simple_local оказался недоступен; работа продолжена на основной модели.

## 7. Материалы, DOC IMPACT и NEXT

Папка: [reports/CODEX-WUA-0-MCP-FEASIBILITY-001](M:/GitHub/ag_llm/reports/CODEX-WUA-0-MCP-FEASIBILITY-001).

Созданы scope.md, assignment.md, adapter.py, verify_smoke.py, environment.json, document_sources.json, smoke_attempt_01.json … smoke_attempt_05.json, initial_failure.md, notification_delivery.json, candidate-plugin/plugin.json, candidate-plugin/mcp.json, candidate-plugin/README.md, report.md и manifest.json. Ротируется только собственная [карточка Codex](<M:/GitHub/ag_llm/Документация/000_Задачи Codex.md>); полная постановка/closeout сохраняются, прежние блоки не уничтожаются.

DOC IMPACT: рабочие исходники Web Alarm/старой Ultra, production storage, config и общая документация не изменялись. Канонические 19/34/37 и тестовый каталог verifier сможет дополнить после независимого review. Evidence и candidate plugin **LOCAL ONLY / NOT SYNCED**, не опубликованы на GitHub. Наличие пути в сообщении не означает, что получатель уже имеет к нему доступ.

Следующий инженерный этап — отдельный bounded Desktop E2E gate: установить кандидат в разрешённый локальный host, проверить из обычного Chat три read tools и сравнить nonce/hash; отдельно подтвердить ACK конкретного сообщения по ID. При успехе — проектировать read-only sidecar к утверждённому Web Alarm API и server-owned notification outbox. Перенос Tkinter, model API и production write tools для этого первого gate не нужны.

Прошу независимую проверку ChatGPT фактических исходников, oracle и evidence; доступ к локальным материалам либо их публикацию организовать штатным разрешённым способом. Пользователь при необходимости публикует папку TASK и изменённую карточку после просмотра. **Независимая приёмка остаётся PENDING.**

Задача выполнена. Отчёт передан. Ожидаю независимой проверки ChatGPT в чате „Сервер WEB_08“.
