# CODEX-WUA-0-DESKTOP-MCP-E2E-001 — manual gate checkpoint

Дата: 2026-10-16, Asia/Yekaterinburg. Исполнитель: Codex 007.
**TASK ACTIVE / AWAITING USER MANUAL GATE.**
**LOCAL MCP: PASS. DESKTOP E2E: NOT RUN. PUBLICATION: DEFERRED / LOCAL ONLY.**
Это промежуточный воспроизводимый пакет, не сообщение о завершении TASK и не независимая приёмка.

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

## Реальный Desktop gate — пока NOT RUN

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
или успешному SDK тесту. Пользователю предложено открыть страницу кандидата,
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
SELF_PUBLISH разрешён только после завершённого пакета и безопасного окна по
DOC-CODEX-SELF-PUBLISH-01@1. Сейчас manual gate ожидается; scoped Git preflight,
commit/push и синхронизация не выполнялись. Никаких утверждений PUBLISHED/GitHub SHA.
Публикация отложена; активный БЛОК 1 не менялся и не ротировался до результата gate.
Финальный отчёт в «Сервер WEB_08» пока не отправляется, потому что TASK не закрыта.

NEXT: результат ручной установки/выбора из обычного Chat → сверка proof →
окончательный PASS/PARTIAL/BLOCKED отдельно для Local и Desktop → closeout карточки →
разрешённый scoped publication gate → полный итоговый handoff в «Сервер WEB_08».

