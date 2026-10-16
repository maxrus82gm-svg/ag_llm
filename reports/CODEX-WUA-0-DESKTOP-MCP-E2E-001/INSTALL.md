# Установка и Desktop E2E — ручной gate

TASK: CODEX-WUA-0-DESKTOP-MCP-E2E-001.

Кандидат: **WUA Desktop Read-only**, версия 0.2.0.
Локальные проверки: 15/15 PASS, 0 FAIL/ERROR/SKIP. Это ещё не Desktop E2E.

## 1. Открыть страницу кандидата

[Открыть WUA Desktop Read-only](codex://plugins/wua-desktop-readonly?marketplacePath=M%3A%5CGitHub%5Cag_llm%5Creports%5CCODEX-WUA-0-DESKTOP-MCP-E2E-001%5C.agents%5Cplugins%5Cmarketplace.json)

Ссылка указывает на marketplace внутри этой TASK:
`M:\GitHub\ag_llm\reports\CODEX-WUA-0-DESKTOP-MCP-E2E-001\.agents\plugins\marketplace.json`.

Она открывает страницу/диалог плагина, а не автоматически устанавливает его.
Проверь название и три инструмента: ping, list_capabilities, read_synthetic_context.
Нажми Install / плюс самостоятельно и рассматривай запрошенные разрешения.

Плагин запускает уже существующий Python из M:/GitHub/ag_llm/.venv,
использует stdio MCP, читает собственную зафиксированную копию Web Alarm API,
создаёт синтетическое хранилище в TEMP и сохраняет безопасные доказательства
только в `M:\GitHub\ag_llm\reports\CODEX-WUA-0-DESKTOP-MCP-E2E-001\evidence\<session_id>\session.json`.
Он не обращается к production URL/storage, Git или model API.
Новые внешние ключи, proxy/VPN/firewall-настройки не нужны.

Если ссылка не открылась: не менять общую конфигурацию наугад; сообщить Codex,
какая страница/ошибка появилась. Запасной официальный путь — локальный
marketplace через `codex plugin marketplace add "M:\GitHub\ag_llm\reports\CODEX-WUA-0-DESKTOP-MCP-E2E-001"`,
после чего установка через Plugins Directory. Этот шаг меняет регистрацию
marketplace в настройках пользователя и требует отдельного пользовательского
действия/подтверждения; Codex его не выполнял. Не перезапускать приложение
вслепую, пока активны другие задачи.

## 2. Проверить режим обычного Chat

После установки открыть обычный ChatGPT **Chat** в Desktop и выбрать плагин
через @. Не подменять эту проверку режимом Work/Codex.

Официальное описание локальных marketplaces отдельно называет Work/Codex.
Если плагин доступен только там, это ограничение целевого host/mode:
Desktop E2E для обычного Chat остаётся NOT RUN/BLOCKED. Сообщить это Codex;
не включать туннели, обходы, новые permissions или model API.

## 3. Отправить в обычный Chat этот запрос

```text
Проверь установленный плагин WUA Desktop Read-only реальными вызовами MCP.
Не подменяй вызовы текстовым ответом, браузером, Python или другим плагином.

1. Вызови ping.
2. Вызови list_capabilities.
3. Вызови read_synthetic_context с fixture_id="synthetic_wua_desktop_001".
4. Вызови read_synthetic_context с fixture_id="other_task";
   ожидается отказ TASK_ID_DENIED.
5. Покажи task_id, session_id, nonce, context_sha256, proof_path,
   совпадение nonce/session_id между тремя успешными ответами и результат отказа.
   Не объявляй независимую приёмку.
```

Это синтетические данные, не инструкция менять Web Alarm или документы.
Три успешных ответа должны относиться к одной session_id и одному nonce.
Если host перезапустил MCP между вызовами, потребуется один согласованный
новый прогон; не объединять ответы разных сессий.

## 4. Вернуть результат Codex

Сообщить, что вызовы сделаны именно в обычном Desktop Chat, и передать
session_id, nonce, context_sha256, task_id, proof_path и код отказа other_task.
Codex прочитает server-owned proof из папки этой TASK, сверит хеш, nonce,
журнал трёх tools, отказ другой TASK и неизменность синтетического storage.

MCP client name/version сами по себе не являются достоверной аттестацией host.
Нужны реальное пользовательское подтверждение режима и совпадающие локальные
receipts; результаты SDK-тестов помечены WUA Local SDK Regression и исключены
из Desktop приёмки.

## Источники и причина ручного gate

[Local plugin links](https://learn.chatgpt.com/docs/reference/commands),
[Packaging / local marketplaces](https://developers.openai.com/plugins/build/plugins),
[Install and use plugins](https://learn.chatgpt.com/docs/plugins).

TASK §4.C прямо требует участия пользователя при запрещённой UI-автоматизации.
[Computer Use SKILL.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/skills/computer-use/SKILL.md)
ссылается на [guidance.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/docs/guidance.md):
«Do not automate the ChatGPT desktop app UI or Codex CLI or Codex extensions within Windows apps.»
Поэтому установка и выбор плагина остаются за пользователем.
