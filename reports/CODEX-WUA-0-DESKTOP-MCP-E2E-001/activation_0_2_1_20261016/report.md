# WUA Desktop Read-only 0.2.1 — разрешённая установка

TASK: CODEX-WUA-0-DESKTOP-MCP-E2E-001. Codex 007. 16 октября 2026,
Asia/Yekaterinburg. Разрешение пользователя получено в текущем чате.

**УСТАНОВЛЕНО / ENABLED В КОНФИГУРАЦИИ. DESKTOP E2E NOT VERIFIED.**
Подхват версии 0.2.1 работающим Desktop и доступность в ordinary Chat не подтверждены.
Обычных ChatGPT MCP-вызовов в данном этапе: **0**.

## Что выполнено

- Проверены все 1 675 файлов против sealed candidate_manifest.json AMENDMENT 04:
  код, настройки и зависимости совпадают побайтно. Исходный кандидат не изменён.
- Существующие синтетические receipts исходного кандидата сохранены на месте.
  Для установки создана чистая копия только файлов manifest в package/plugin/.
- Сохранены исходная конфигурация, отдельный WUA-кэш 0.2.0 (47 файлов) и
  исходный dedicated WUA marketplace.json. Конфигурация сохранена в Windows
  DPAPI-зашифрованном виде, без plaintext секретов или конфигураций других подключений.
  Расшифрование обратно в памяти дало точное совпадение исходных байтов.
- Первая команда установки выявила незарегистрированный в CLI WUA marketplace:
  plugin not found; отрицательный результат сохранён в plugin_install.json.
- Штатной командой codex plugin marketplace add зарегистрирован только локальный
  WUA-источник данной TASK. Его source.path указывает на чистую копию кандидата.
- Штатная codex plugin add вернула version=0.2.1 и installedPath ниже.
  Последующий scoped CLI readback вернул installed=true и enabled=true.

```text
C:/Users/REX/.codex/plugins/cache/wua-desktop-e2e-local/wua-desktop-readonly/0.2.1
```

Установленный пакет совпадает с sealed manifest, без старых receipts.
Нативный установщик удалил прежний WUA-кэш 0.2.0 при обновлении; его 47 файлов
полностью сохранены в wua-cache.before.zip. Это не обновление других плагинов.

## Проверки границ

Все прямые MCP-настройки, включая существующую WUA STDIO-запись, совпадают
по semantic hash до/после. Глобальный required не добавлялся и не менялся.
За исключением WUA marketplace-регистрации, остальные настройки config.toml
совпадают по semantic hash. Контрольные суммы report.md, candidate_manifest.json
и integrity.json AMENDMENT 04 сохранены.

На первой контрольной точке после установки индекс метаданных остальных
plugin caches совпал с исходным. Позднее обнаружены обновлённые timestamps
18 файлов .codex-remote-plugin-install.json внешнего каталога. Это отдельно
зафиксировано в other_cache_recent_metadata.json: нельзя утверждать неизменность
всех cache metadata на протяжении всего этапа. Связь с scoped CLI list или
фоновым refresh приложения не установлена. Чужие маркеры не редактировались
и не откатывались; MCP-конфигурации других подключений не изменены.

Production Web Alarm, сеть, права, Git/GitHub и документы/задачи Claude
не изменялись. GUI, Desktop и существующие MCP-процессы не автоматизировались,
не перезапускались и не завершались агентом. Инструменты WUA не вызывались
из Codex для имитации ordinary Chat gate.

## Точный откат

- config.before.dpapi — точные исходные байты config.toml, защищённые DPAPI
  текущего Windows-пользователя. Секреты не выводятся при проверке/восстановлении.
- wua-cache.before.zip — исходные 47 файлов WUA 0.2.0; SHA каждого файла сверён.
- marketplace.before.json — исходный WUA-only catalog.
- manage_activation.py rollback — сухая проверка PASS, изменений не выполняет.
- manage_activation.py rollback --apply — только по явному запросу на откат:
  удаляет исключительно новый WUA-кэш 0.2.1, восстанавливает 47 файлов 0.2.0,
  исходные config.toml и dedicated WUA catalog; сверяет результат побайтно.

Скрипт отказывается перезаписывать конфигурацию или WUA-кэш, если они изменились
после проверенного состояния. После появления новых receipts сначала нужно
сохранить их и пересмотреть rollback plan. Другие MCP/кэши не восстанавливаются.
Работающий Python может удерживать файлы: откат следует выполнять после
завершения использующих WUA сессий, без принудительного завершения других задач.

Откат сейчас не применялся. Baseline, installation_verification.json,
rollback.dry_run.json и CLI результаты находятся в этой папке.

## Следующий ручной gate

Официальная документация требует перезапустить Desktop для подхвата обновлений
локального плагина. Единственное действие для активации: **в безопасное окно,
после завершения активной работы Claude/других агентов, полностью закрыть
и снова открыть ChatGPT Desktop**. Агент этот шаг не выполнял.

Затем ordinary Chat должен выполнить четыре настоящих MCP-вызова. Готовый
запрос, ожидаемый proof_path и независимый verifier checklist — DESKTOP_GATE.md.
Три успешных вызова и отказ other_task должны быть сверены независимым verifier
с server-owned receipt. Local Codex, SDK, host-test и CLI installed=true
не заменяют этот результат.

Общий TASK не закрыт; независимая приёмка не объявлена. Итоговый полный отчёт
в «Сервер WEB_08» передаётся после фактического ручного результата. Публикация
в GitHub не выполнялась и остаётся вне этого разрешения.

## Источники и evidence

Использованы OpenAI Docs и Plugin Management. Поиск публичного плагина не дал
точного WUA-совпадения; установка сделана из подготовленного локального catalog,
без установки сторонних плагинов и без изменения plugin permissions.

- [Package your plugin](https://developers.openai.com/plugins/build/plugins) —
  local marketplaces, cache и перезапуск после обновления.
- [Plugins](https://learn.chatgpt.com/docs/plugins) — новые сессии и поддерживаемые поверхности.
- [Desktop-only plugins](https://developers.openai.com/plugins/deploy/desktop-only) —
  локальный исполнитель и bundled dependencies; доступность ordinary Chat требует проверки.
- Локальные codex plugin --help / plugin add --help / marketplace add --help
  подтвердили точные поддерживаемые команды установленной версии CLI.
