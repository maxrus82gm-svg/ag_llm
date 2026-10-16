# AMENDMENT 03 — актуальный результат диагностики

**DESKTOP E2E NOT VERIFIED.** Режим: READ-ONLY DIAGNOSTICS, 2026-10-16.

Полный отчёт с требуемыми разделами A–E:
[amendment_03_diagnostics/report.md](M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/amendment_03_diagnostics/report.md).

Установленная причина отказов локального плагина: host loader отклонил абсолютный
command в portable mcp.json. Прямая user STDIO-запись валидна: в текущем локальном
Codex получены настоящие native MCP tools и выполнены 3 успешных запроса плюс
TASK_ID_DENIED для other_task. Session b8f830274dd449909e3a7d0e3e0fddb2, protocol
2025-06-18, nonce/hash/storage сверены с receipt. Это не SDK и не обычный Chat.

Для отрицательного независимого CLI-теста точная причина не установлена: сильная
гипотеза — получение cached catalog до завершения optional MCP startup. В логах
наблюдается cached catalog without waiting и ready через 1.97–4.60 секунды.
Конфликт двух WUA-записей и причинная связь WebSocket 10013 не подтверждены.
Сессии около 18:02 сохранены; ready/event_total=0 означает готовую синтетическую
HTTP fixture до MCP initialize, без сведений о клиенте. Их происхождение неизвестно.

Никакие исправления, перезапуски, записи config, сетевые/системные изменения или
Git-публикация в AMENDMENT 03 не выполнялись. Предлагаемый новый CLI gate с временным
required=true оставлен на отдельное разрешение. Общая TASK активна до настоящего
ordinary Chat gate и независимой сверки. Прежние отчёты и receipt сохранены в
amendment_03_diagnostics/pre_* и receipts_before/.

Далее сохранён предыдущий отчёт; его инструкция Restart заменена текущим
NEXT_MANUAL_GATE.md. Сейчас перезапуск не разрешён.

# CODEX-WUA-0-DESKTOP-MCP-E2E-001 — прямая STDIO-регистрация после AMENDMENT

Дата: 2026-10-16, Asia/Yekaterinburg. Исполнитель: Codex 007.
**TASK ACTIVE / DIRECT STDIO REGISTERED / AWAITING MANUAL DESKTOP ACTIVATION AND ORDINARY CHAT TEST.**
**LOCAL MCP: PASS. DESKTOP E2E: NOT VERIFIED. PUBLICATION: ON HOLD / LOCAL ONLY.**
Это промежуточный воспроизводимый пакет, не сообщение о завершении TASK и не независимая приёмка.

## Прямая регистрация по AMENDMENT 02

С разрешения пользователя добавлено прямое STDIO-подключение
mcp_servers.wua_desktop_readonly в документированный C:/Users/REX/.codex/config.toml.
Источник — plugin/mcp.json с раскрытым абсолютным PLUGIN_ROOT. Официальный механизм
описан в [OpenAI Docs](https://learn.chatgpt.com/docs/extend/mcp) для Desktop/CLI/IDE
одного локального Codex host. Это не гарантия доступности в обычном Chat.

Полная before-копия сохранена вне репозитория. Исходные байты конфигурации остаются
неизменным префиксом; все прочие настройки и существующие MCP-серверы сохранены.
CLI get подтвердил новую enabled STDIO-запись с точными command/args/cwd.
Подробности, hashes и точный защищённый от последующего drift откат —
STDIO_REGISTRATION.md и stdio_registration_01.json. rollback_stdio.py проверен
без --apply; откат не выполнялся.

По зарегистрированным значениям успешно вызваны три инструмента в отдельном
SDK-сеансе: ping, list_capabilities, read_synthetic_context. Session/nonce/hash
согласованы, synthetic storage неизменён. registered_stdio_check_01.json — PASS;
receipt SDK 328a038a85944102b345d25cddbfc102. Это **не Desktop E2E**.

Обычный Chat после регистрации ещё не проверен; прежний отрицательный gate
с MCP TOOLS UNAVAILABLE сохранён. Реальных вызовов из обычного Chat — 0.
Осталось вручную активировать конфигурацию через Settings → MCP servers → Restart
и провести настоящий Chat gate из NEXT_MANUAL_GATE.md. Marketplace-регистрация
для добавленного прямого подключения не нужна и не выполнялась.
Приложение и другие MCP-процессы агент не перезапускал; permissions, production,
GitHub и сетевые настройки не менялись.

## Сохранённый результат первого ручного gate и диагностики

Этот раздел описывает состояние до прямой регистрации; актуальный статус выше.

Пользователь подтвердил видимость WUA Desktop Read-only v0.2.0, затем сообщил
результат реальной проверки: в обычной ChatGPT-сессии недоступны все три инструмента,
настоящих вызовов WUA — **0**. Идентификаторы/nonce/hash/код отказа не получены;
этот отрицательный результат сохранён в manual_gate_01.json.

Установленная копия побайтно совпадает с кандидатом (47 файлов), enabled=true.
При этом CLI не рассматривает marketplace wua-desktop-e2e-local, а его scoped
listing пуст. Это конкретный пробел discovery, возможная причина проблемы
активации; причинная связь с обычным Chat ещё не доказана.

Именно установленная копия успешно выполнила initialize и tools/list через
отдельный SDK-клиент и объявила ping, list_capabilities, read_synthetic_context.
Вызовов инструментов в диагностике — 0. Протокол 2025-11-25; создан отдельный
явно обозначенный SDK receipt. Этот запуск **не засчитывается как Desktop E2E**.
Пакет, установленный кэш и config.toml не изменились.

По официальной документации локальный stdio требует локального исполнения
конкретного чата. Новый Work Local/Codex ещё не проверен, поэтому ограничение
обычного Chat пока является гипотезой данной конфигурации. Общее отсутствие
поддержки MCP в обычном Chat не заявляется.

Полная матрица установки/активации/host-mode, источники и пределы выводов —
diagnosis.md; машиночитаемые evidence — installation_diagnostic_01.json и
activation_layers.json. Минимальный следующий шаг — ручная регистрация уже
существующего локального каталога, затем проверка discovery и один ping для
сравнения новых сеансов. Инструкция — NEXT_MANUAL_GATE.md.
Первоначальные report/status/manifest сохранены в checkpoints/pre_host_diagnosis/.

## Подготовленное подключение

Отдельный кандидат **WUA Desktop Read-only 0.2.0**:
ChatGPT Desktop host → stdio MCP → plugin/server.py → read-only bridge →
собственный HTTP loopback fixture → зафиксированный WebAlarmApi.

41 исходный Python-файл Web Alarm (813 415 байт) скопирован без изменений в
plugin/vendor/web_alarm/. До записи проверена согласованность прочитанных байтов;
хеши — plugin/vendor_manifest.json и preflight.json. Это собственная копия внутри
TASK, не правка production и не второй production control plane. При запуске
проверяются все vendor hashes; drift блокирует запуск.

Entry point и cwd используют ${PLUGIN_ROOT}; в симуляции установки весь пакет
скопирован в посторонний cache-каталог и запущен оттуда с Python -I.
Пакет не импортирует рабочий checkout и предыдущий feasibility adapter.
Host-specific зависимости: существующий M:/GitHub/ag_llm/.venv/Scripts/python.exe
и установленный mcp 2.2.0. Ничего не скачивалось и не устанавливалось.

Только ping, list_capabilities и read_synthetic_context.
Fixture TASK ID: synthetic_wua_desktop_001. Роуты GET /status и
GET /tasks/synthetic_wua_desktop_001/context обращаются к настоящему WebAlarmApi
на собственной disposable TEMP fixture. Даже HTTP fixture отклоняет POST/PUT/
PATCH/DELETE до dispatch. Никаких production URL, произвольных путей или write tools.

Размер HTTP ответа ≤65 536 байт, timeout 2 секунды, redirects запрещены;
client не использует proxy из окружения. Глобальные proxy/VPN/firewall/kill switch
не менялись. После создания внутреннего Windows event loop аудит допускает
соединение только с собственным loopback-портом, запрещает дочерние процессы и
запись вне своей fixture/evidence root. Это Python guard, не полноценная OS sandbox.

Session ID, случайный nonce, canonical context hash, byte fingerprint хранилища,
согласованный MCP protocol и ограниченный журнал событий сохраняются в
evidence/<session_id>/session.json под этой TASK. Копия результата остаётся после
остановки и удаления fixture; история ограничена 64 последними событиями,
event_total показывает полное число. Произвольные отклонённые IDs не сохраняются
в журнале. MCP client name/version помечены как недоверенные peer claims.

## Проверки

Команда:
`./.venv/Scripts/python.exe -X utf8 -B reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/verify_local.py --output <НОВЫЙ_JSON>`

**local_attempt_02.json: 15 collected, 15 PASS, 0 FAIL/ERROR/SKIP; exit 0;
16.125 секунды.** Это новые package/contract/adversarial tests этой TASK,
а не повтор предыдущих 34 assertions.

Подтверждены реальные read tools и server-owned ожидаемый контекст, nonce/hash,
сохранение receipts, исходные bytes fixture; отказ другой TASK, traversal,
абсолютного пути и неверного типа; запрет HTTP мутаций и неизвестного MCP tool;
fail-closed при недоступном HTTP, synthetic storage drift, oversized/invalid JSON,
HTTP 503, redirect и timeout; настоящий audit-hook deny для external connect,
внешней записи и subprocess; ограничение журнала; отказ при vendor drift;
настоящий stdio сеанс из копии пакета в cache-каталоге. Протокол локального SDK
сеанса: 2025-11-25; client специально назван WUA Local SDK Regression.

**local_attempt_01.json сохранён: 13 PASS, 2 FAIL.**
Первый FAIL — слишком узкий oracle: закрытый loopback-порт на этой Windows-среде
дал HTTP_TIMEOUT вместо немедленного HTTP_UNAVAILABLE. Теперь принимаются только
эти два точных fail-closed кода с пределом времени и неизменностью fixture.
Второй FAIL — собственный cleanup guard-probe вне ошибочно суженного test root;
проверка исправлена на полный owned root и внешнюю запись, отклоняемую до создания.
Production не исправлялся; см. initial_failures.md.

doctor.py подтвердил 9 условий локальной готовности конфигурации.
desktop_validator_checks.json — 8 синтетических контролей валидатора приёмки:
SDK receipts не могут быть выданы за Desktop E2E, отсутствующая human attestation,
другие nonce/hash/TASK, изменённый storage и отсутствующие receipts отклоняются.
Положительный control искусственный и не считается вызовом из Desktop.

## Требования к успешному Desktop gate — ещё не выполнены

Подготовлен собственный marketplace в .agents/plugins/marketplace.json **внутри
этой TASK**; общие repo/user marketplaces и config не изменялись.
[Инструкция установки и точный запрос](M:/GitHub/ag_llm/reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/INSTALL.md).

Официальные источники описывают:
- локальные marketplace и package layout — [Package your plugin](https://developers.openai.com/plugins/build/plugins);
- открытие локального кандидата по абсолютному marketplace.json —
  [Commands / Local plugin](https://learn.chatgpt.com/docs/reference/commands);
- ручную установку и выбор через @ — [Plugins](https://learn.chatgpt.com/docs/plugins).

Раздел локальных marketplaces явно называет Work/Codex. Поддержка именно обычного
Chat в установленной конфигурации не предполагается по тарифу, имени процесса
или успешному SDK тесту. Пользователю было предложено открыть страницу кандидата,
самостоятельно установить/подтвердить permissions и выбрать его в обычном Desktop
Chat. Если он доступен только в Work/Codex, фиксируется ограничение целевого режима;
туннель и другой режим не считаются выполнением этого gate.

После реальных вызовов нужны human confirmation обычного Desktop Chat и server
proof: одинаковые session_id/nonce, совпадающий context_sha256, все три успешных
tools, отказ другой TASK и отсутствие изменений fixture. verify_desktop.py
проверяет наблюдения против независимого сохранённого proof; metadata клиента
используются лишь для исключения нашего SDK regression, не для positive host trust.

TASK §4.C требует ручного gate. [Computer Use SKILL.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/skills/computer-use/SKILL.md)
обязывает соблюдать [guidance.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/docs/guidance.md):
«Do not automate the ChatGPT desktop app UI or Codex CLI or Codex extensions within Windows apps.»
Другой UI-метод для обхода не использовался. Автоматической регистрации,
установки, выдачи permissions или отправки теста из Desktop не было.

## MANUAL ENGINEERING REVIEW

Прослежены bootstrap с явным TEMP root → ожидаемый server context → baseline →
GET-only HTTP listener → MCP allowlist → проверка storage/hash → ограниченный
sanitized receipt → cleanup. Кэш больше не зависит от положения папки в рабочем
checkout; vendor hash verification отвергает неполную/изменённую копию.
Неправильные IDs отклоняются до HTTP; network redirects блокируются до второго
connect; вызов list_capabilities проверяет живой backend и не возвращает ложный
ready после отключения. Неизвестный tool/schema errors отвергаются SDK.

Сохранённый после shutdown proof нужен для сверки реального пользовательского
вызова. Он содержит server facts и недоверенную client metadata; самостоятельно
не доказывает UI mode. Поэтому Desktop PASS зависит от отдельного human gate.
Нет production authentication, многопользовательского доступа, lifecycle/STOP
интеграции, autosend/outbox и массового callback recovery — не заявляются.
Наличие snapshot API с mutation-кодом внутри vendor не выдаёт эти возможности
MCP клиенту; внешний HTTP handler также не предоставляет write маршруты.

## Scope, публикация и продолжение

Рабочий Web Alarm/Ultra, материалы Claude, предыдущий feasibility пакет,
общая документация, CI и сетевые настройки не изменялись нами.
Проверки воспроизводятся в собственных TEMP fixture roots.
Полный baseline — preflight.json; файловый состав и SHA-256 — manifest.json.

Параллельная TASK Claude: CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001.
Исходный SELF_PUBLISH ограничен DOC-CODEX-SELF-PUBLISH-01@1 и безопасным окном.
Последующее прямое указание пользователя приостановило изменения GitHub до
согласования. Публикация ON HOLD; scoped Git preflight, commit/push и синхронизация
не выполнялись. Никаких утверждений PUBLISHED/GitHub SHA. Активный БЛОК 1 не менялся
и не ротировался: требуется следующий manual gate диагностики.
Финальный отчёт в «Сервер WEB_08» пока не отправляется, потому что TASK не закрыта.

NEXT: ручная активация прямой STDIO-конфигурации → настоящий gate в обычном Chat →
сравнение с новым Work Local/Codex при необходимости → сверка proof →
окончательный PASS/PARTIAL/BLOCKED отдельно для Local и Desktop → closeout карточки →
разрешённый scoped publication gate → полный итоговый handoff в «Сервер WEB_08».

