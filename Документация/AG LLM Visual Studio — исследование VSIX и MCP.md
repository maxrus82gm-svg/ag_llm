# Нейрополис Studio — Visual Studio, VSIX и MCP

**RES-NEUROPOLIS-IDE-MCP-001 · 26.11.2026 · OWNER RESEARCH GO · DOCUMENTARY RESEARCH PARTIAL / IMPLEMENTATION NOT RUN / PLANNED, UNASSIGNED.**

Связи: [[AG LLM Connect]], [[43.3_Архитектура агентской системы Blueprint LLM]], [[43_План работ по Blueprint LLM]], [[19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP]]. Публичный бренд: «Нейрополис» / Neuropolis; технические пути сохраняются. LOCAL-PLAN-01 12:36:32+05, PLAN_SHA256 b215ef9882542d5e38590965b8635b8c8039320eaf87f7626f9c7137c97831ee, общий план не изменён. Не новая coding TASK, LIVE GO, установка или разрешение на сетевой доступ. Заморозка ChatGPT Desktop MCP №39 остаётся в силе.

## 1. Цель владельца

Один запрос из Visual Studio запускает в Studio одну LLM или выбранный Blueprint с несколькими локальными/облачными LLM, взаимной проверкой и финальным ответом. По отдельному разрешению — анализ файлов, предлагаемый diff, компиляция и тесты. Оркестрация, история, бюджеты, отмена, выбор моделей и контроль доступа остаются в нашей среде. IDE не управляет непосредственно GPU и Manager.

Предлагаемый маршрут: Visual Studio 2022 (свой VSIX) → защищённый локальный адаптер Studio → единый Turn/координатор → разрешённый Blueprint RUN и Workspace → реестр моделей → облачные адаптеры либо существующий Colibri Bridge → Client → Manager → LLM. Возвращаются итог и выбранные события. Не создавать второй путь к Manager, не дублировать транспорт, Bridge v1 не менять односторонне. Внешний сценарий может выглядеть как виртуальная модель, а не новая физическая LLM.

Три независимых интерфейса:
- Собственный VSIX с tool window, собственным чатом и API Studio — основной кандидат, без зависимости от GitHub Copilot.
- MCP Server Studio: каталог разрешённых сценариев, запуск, статус/результат, отмена. MCP tools не заменяют LLM Copilot и не являются универсальным API генерации токенов; отображение потоков и progress необходимо проверить отдельно.
- OpenAI-совместимый API виртуальных моделей — перспективное дополнение после проектирования API, streaming и auth.
VS Code — отдельный продукт и отдельный SDK.

## 2. Что подтверждено документально

| Возможность | Вывод | Статус |
| --- | --- | --- |
| Собственное расширение | Microsoft предоставляет VSIX SDK, команды, окна и интеграцию с редактором; локальный пакет можно распространять вне Marketplace | DOC VERIFIED [S1,S2,S3] |
| Подпись расширения | Microsoft не требует подписи сборок для самого запуска; собственная подпись возможна для тестов, самоподписанный VSIX не принимается Marketplace. Установщик и политика организации могут предупреждать или блокировать | DOC VERIFIED [S4], конкретная политика NOT RUN |
| MCP в Visual Studio | VS 2022 17.14+ (последний servicing update рекомендуется), VS 2026: подключение через Copilot, mcp.json, stdio/HTTP, правила доверия и разрешений | DOC VERIFIED [S5,S6], установленная IDE NOT RUN |
| Независимый MCP | C# SDK поддерживает stdio/Streamable HTTP; интеграция в свой VSIX либо helper возможна архитектурно, конкретный target framework и версия SDK ещё выбираются | DOC VERIFIED [S7], применимость PARTIAL |
| Локальный HTTPS | .NET поддерживает локальный dev-cert; доверие сертификату необходимо проверять в выбранном runtime | DOC VERIFIED [S8], NOT RUN |
| Мультиагентная интеграция | Технический прототип Studio/Blueprint/IDE, поток и отмена ещё не реализованы и не испытаны | NOT RUN |

## 3. Сертификаты и возможные препятствия

**Подпись VSIX и TLS-сертификат сервера — независимые вопросы.** Для первого эксперимента не покупать сертификат и не публиковаться в Marketplace. Использовать experimental instance, затем локальную установку по OWNER GO. Проверить версию/edition VS 2022, workload Visual Studio extension development, manifest InstallationTarget, SDK/target framework, ограничения WDAC/AppLocker/организации, права и предупреждения установки. Не обходить запреты политики. Публичная публикация, доверенная подпись и управление ключами — отдельный gate.

**Транспорт:** первый кандидат — локальный stdio helper без TLS на участке IDE↔helper либо аутентифицированный loopback API Studio. Named pipe с ACL текущего пользователя также возможен как собственный IPC, не стандартный MCP transport. Разделить stdout протокола и stderr логов; проверять путь/идентичность helper. Для HTTP: bind loopback, контроль Host/Origin, anti-CSRF где применимо, ограниченный токен, запрет неявного переноса credentials при redirect/proxy. Локальность сама по себе не аутентификация.

**HTTPS:** доверенная цепочка или ограниченное приложение-хранилище доверия, SAN для фактического имени/IP, срок действия, ротация и отказ при неверной цепочке/имени. Совместимость .NET Framework и современного .NET проверить отдельно; при необходимости helper с поддерживаемым runtime. Не отключать TLS-валидацию и не импортировать глобальные корни без явного разрешения. Не переиспользовать ключи Manager/Bridge. Внешний туннель, открытый порт и публичный сертификат не нужны первому локальному MVP.

**Данные и полномочия:** по умолчанию local-only, облачная отправка кода только при явной политике/согласии. Раздельные разрешения на чтение solution/selection, запись diff, запуск команд и внешнюю передачу. Проверять границы Workspace, не считать инструкции внутри исходников доверенными. Секреты в защищённом хранилище ОС. Корреляция turn_id/run_id, bounded concurrency, отмена, видимая ошибка, не повторять неизвестный платный запрос. Не выдавать внутренние рассуждения и токены доступа наружу автоматически.

## 4. Проверки для будущего этапа

1. Read-only инвентаризация VS/SDK и существующего Studio Turn/API, без изменения рабочей конфигурации.
2. VSIX в экспериментальной инстанции: окно, выбор сценария, синтетический запрос к mock Studio, поток результата/отмена, установка/удаление/перезапуск. Без реальных моделей и проектов.
3. Negative controls: несовместимый manifest, политика подписи, неверный token/Host/Origin, TLS SAN/CA/expiry если HTTPS, отключение IDE, duplicate/cancel/disconnect. Запрет обхода.
4. По отдельному GO: один реальный локальный запрос через существующий Studio → Client → Manager, без автоматического облачного fallback. Проверка Turn/Run, streaming, usage, cleanup.
5. После готовности Blueprint: несколько LLM, независимая проверка, итоговый ответ, diff preview и отдельное разрешение на применение/сборку.
6. MCP-адаптер: согласование протокола, stdio/Streamable HTTP, права, progress, cancellation и проверка совместимости клиента. Не утверждать замену модели Copilot через MCP.

## 5. Источники (проверены 26.11.2026)

- S1 Microsoft: https://learn.microsoft.com/en-us/visualstudio/extensibility/creating-an-extension-with-a-tool-window
- S2 Microsoft: https://learn.microsoft.com/en-us/visualstudio/ide/finding-and-using-visual-studio-extensions?view=vs-2022
- S3 Microsoft: https://learn.microsoft.com/en-us/visualstudio/extensibility/the-experimental-instance
- S4 Microsoft: https://learn.microsoft.com/en-us/visualstudio/extensibility/signing-vsix-packages?view=visualstudio
- S5 Microsoft: https://learn.microsoft.com/ru-ru/visualstudio/ide/mcp-servers?view=vs-2022
- S6 Microsoft: https://learn.microsoft.com/visualstudio/releases/2022/release-notes-v17.14
- S7 MCP C# SDK: https://github.com/modelcontextprotocol/csharp-sdk/blob/main/docs/concepts/transports/transports.md (main — не зафиксированная версия SDK; перед implementation закрепить release/commit).
- S8 Microsoft: https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-dev-certs

**Вердикт:** принципиальная возможность подтверждена документацией; установленные IDE, политики, SDK, сертификаты, реальный API и многоагентная работа NOT RUN. Не выдавать исследование за готовую интеграцию. Приоритет текущих задач Studio и Multi-GPU не изменяется.
