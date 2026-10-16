# Следующий manual gate — прямое STDIO-подключение

TASK: CODEX-WUA-0-DESKTOP-MCP-E2E-001. AMENDMENT 02.
Прямая пользовательская запись wua_desktop_readonly уже зарегистрирована.
Эта инструкция заменяет прежний шаг регистрации marketplace. Длинные пути и
аргументы пользователь больше не вводит.

## Единственное действие для активации

В ChatGPT Desktop: Settings → MCP servers → **Restart**.
Сделать это в удобный момент для текущей работы. Агент не перезапускает приложение
или существующие MCP-процессы самостоятельно. Если WUA не появляется в списке,
сообщить об этом: не вводить новую конфигурацию и не менять permissions.

Документированный шаг Restart описан в
[OpenAI Docs](https://learn.chatgpt.com/docs/extend/mcp).

## Проверка успешности — именно обычный Chat

После активации отправить в обычный ChatGPT-чат следующий короткий запрос:

```text
Проверь подключение WUA Desktop Read-only (wua_desktop_readonly) настоящими
MCP-вызовами: ping, list_capabilities, read_synthetic_context с
fixture_id="synthetic_wua_desktop_001". Затем запроси read_synthetic_context
с fixture_id="other_task" и покажи реальный код отказа. Верни session_id,
nonce, context_sha256 и proof_path. Если tools недоступны, сообщи об этом
без имитации результатов. Не используй SDK или терминал вместо MCP-инструментов чата.
```

Передать агенту 007 настоящий результат. Он сверит ответ с отдельным server
receipt. Session ID предыдущего SDK-теста не использовать как ответ Chat.
SDK-проверка по зарегистрированным значениям уже PASS (3 вызова), но ordinary
Chat после регистрации ещё не проверен, Desktop E2E NOT VERIFIED.

Если tools недоступны, сохранить отсутствие как результат и отдельно сравнить
с новым локальным Work/Codex. Успех Work не заменяет исходную цель обычного Chat.
Не требуется новый marketplace, туннель, расширение прав или настройка сети.

Прямое указание пользователя запрещает UI-автоматизацию. TASK §4.C и
[Computer Use SKILL.md](C:/Users/REX/.codex/plugins/cache/openai-bundled/computer-use/26.1007.71326/skills/computer-use/SKILL.md)
ссылаются на guidance: «Do not automate the ChatGPT desktop app UI».
Поэтому Restart и настоящий Chat-запрос остаются ручным gate.
