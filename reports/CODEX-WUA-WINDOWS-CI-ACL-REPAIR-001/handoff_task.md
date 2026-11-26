# Снимок постановки `CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001` — перенос БЛОК 1 → БЛОК 1.1

| Поле | Значение |
|---|---|
| TASK ID | `CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001` |
| Карточка | `Документация/000_Задачи Codex.md` |
| Дата переноса | 2026-11-26 |
| Статус | `SUBMITTED / REVIEW PENDING` — сдано исполнителем; независимая приёмка не выполнена |
| SHA-256 постановки (UTF-8, концы строк LF) | `b974d4f5edab099b11bb5b24e2104cca981663ca8fb1b762ec124bed2d3d5696` |
| Строк постановки | 308 |
| CHAT-ONLY AMENDMENT | нет (заявлено исполнителем) |
| Отчёт | `reports/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001/report.md` |
| Инструмент | `tools/task_slot_rotate.py` — побайтовое копирование без пересказа |

Текст между строками-маркерами ниже — побайтовая копия содержимого БЛОКА 1 (концы строк приведены к LF).

<!-- TASK-SNAPSHOT:BEGIN -->
Уважаемый агент 007 (Codex)!

# Исправление Windows CI — ACL и подключение Client

**TASK ID:** `CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001`

**Дата:** 26.11.2026.

**Приоритет:** P0 — блокирует независимую техническую приёмку.

**Исполнитель:** Codex 007.

**Координатор:** ChatGPT / WEB 36.

**Источник назначения:** OWNER GO 26.11.2026.

**Рабочая директория:** `M:\GitHub\ag_llm`

**PRIMARY PROFILE:** Web Alarm Ultra / Windows CI.

**SECONDARY PROFILE:** EVM / Colibri Client Bridge.

## 1. Исходное состояние

Координатор выполнил анализ через GitHub.

- main: №677 — `3ee748e19dc0ad1f28f4ed2344c79978b3145bac`.
- GPT: №682 — `4f2d6cb5240f51ff98b1e052e4b104bcacfc61ec`.
- Последний технический коммит: №681 — `d0d8927c94673ea22b675fc1751e3274b31ce170`.
- №682 содержит документационные изменения.

Независимый Windows CI:

- Run ID: `45702959182`.
- Attempt: 2.
- Job ID: `139714802863`.
- Результат: FAILURE.

Две попытки завершились одинаковым результатом:

- 28 PASS.
- 4 FAIL.
- 5 ERROR.
- JavaScript regression — NOT RUN.

Первоначальные отрицательные результаты сохранить.

## 2. Координация и общий план

LOCAL-PLAN-01 выполнен координатором 26.11.2026.

PLAN_READ SHA256:

`b215ef9882542d5e38590965b8635b8c8039320eaf87f7626f9c7137c97831ee`

Integration ID: `WUA-COLIBRI-BRIDGE-001/MVP1`.

Общий этап остаётся IN_PROGRESS.

M1-10 LIVE — HOLD.

Настоящая задача не разрешает изменение общего плана или переход к LIVE.

## 3. Цель

Установить точную причину воспроизводимых ошибок Windows CI и устранить её без ослабления существующих механизмов безопасности.

Восстановить полный проход адресного Windows OFFLINE workflow, включая ранее пропущенную JavaScript-регрессию.

Не проводить повторное исследование всей архитектуры проекта.

## 4. REUSE CHECK

Координатор предварительно проверил существующие механизмы:

**web_alarm/colibri_bridge_transport.py**

- `_windows_private_acl`
- `_private_temp_file`
- `_discover`
- `ReadOnlyColibriTransport`
- `catalog`
- `_fresh`

**test_web_alarm_colibri_bridge_transport.py**

- `protect`
- `DecodeTests`
- `ReadOnlyCatalogTests`

**web_alarm/colibri_binding.py**

- `_read`
- `act`

**web_alarm/launcher.py**

- `_profile`
- `load_launch`

**CI:**

`.github/workflows/gpt-wua-666-safety-gates.yml`

Переиспользовать существующие механизмы. Не создавать новый транспорт, отдельный реестр, альтернативную систему авторизации или параллельную базу тестов.

## 5. Проблема A — Windows ACL

Подтверждённые сообщения CI:

`BridgeFault: unsafe_discovery`

`AssertionError: "identity_mismatch" does not match "unsafe_discovery"`

`AssertionError: "redirect_refused" does not match "unsafe_discovery"`

`AssertionError: 409 != 200`

Восемь неуспешных тестов относятся к Bridge Transport:

- test_discovery_strict_loopback_and_expected_identity
- test_failed_rebind_and_corrupt_store_never_overwrite
- test_managed_binding_restart_stale_reconnect_and_disconnect
- test_only_health_and_models_get_with_empty_body
- test_catalog_projection_is_read_only_and_keeps_stale_targets
- test_discovery_acl_origin_and_launch_identity_refuse_before_http
- test_managed_http_requires_registered_standard_origin_and_write_token
- test_redirect_and_invalid_instance_are_refused

Предварительное направление диагностики:

Функция `protect()` формирует Windows DACL на основании владельца объекта, тогда как `_windows_private_acl()` сравнивает владельца с SID текущего процесса.

Проверить:

- SID текущего процесса.
- Фактического владельца временного каталога.
- Владельцев discovery и token-файлов.
- DACL и наследование разрешений.
- Различия между локальной Windows и GitHub-hosted Windows.
- Момент установки и повторной проверки ACL.

Несовпадение владельцев является рабочей гипотезой, а не доказанной первопричиной.

Сначала воспроизвести проблему на синтетических файлах. Затем установить конкретное условие отказа.

Если ошибка находится исключительно в подготовке тестового окружения — исправлять тестовые fixtures, не production-защиту.

Если доказан дефект production-кода — выполнить минимальное адресное исправление с сохранением всех защитных инвариантов.

Не разрешать посторонние SID ради прохождения теста.

Не отключать ACL-проверку и не подменять её безусловным mock PASS.

## 6. Проблема B — неполный sparse checkout

Подтверждённая ошибка:

`LaunchConfigError: Профиль 'ultra-chat-demo': скрипт не найден внутри проекта.`

Отсутствующий путь:

`reports/CLAUDE-WUA-CHAT-S1-READONLY-UI-001/tools/demo_ultra_chat.py`

Координатор подтвердил наличие этого файла в репозитории.

Исправить состав sparse checkout в:

`.github/workflows/gpt-wua-666-safety-gates.yml`

Добавить минимальную необходимую область файлов с учётом фактических зависимостей скрипта.

Сохранить:

- Поддержку Windows Long Paths.
- Изолированную CI-среду.
- Ограничение выборки исторических архивов.
- `persist-credentials: false`.
- Минимальные permissions.
- Все существующие проверки.

Не заменять sparse checkout необоснованным полным checkout.

Не удалять проверку профиля `ultra-chat-demo`.

## 7. Разрешённая область чтения

- Персональная карточка Codex и её правила.
- №36.1 — TEST-ENG-01 и TEST-FULL-CYCLE-01.
- №36.2 — применимые проверки Web Alarm.
- №18 — изоляция, отчётность и сдача слота.
- Указанные исходники, тесты и workflow.
- Непосредственные зависимости указанных компонентов.

Полные исторические архивы и чужие проекты не исследовать без необходимости.

## 8. Разрешённая область записи

Основная:

- `test_web_alarm_colibri_bridge_transport.py`
- `.github/workflows/gpt-wua-666-safety-gates.yml`

Условная, только при доказанной необходимости:

- `web_alarm/colibri_bridge_transport.py`
- `rt002_multimodel_reconciliation.json` — только при подтверждённом изменении соответствующего source fingerprint, с объяснением и повторной проверкой S1.

Отчётная:

- `reports/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001/`

Персональная карточка:

- `Документация/000_Задачи Codex.md` — исключительно штатная скриптовая сдача собственной TASK.

Расширение write scope — только после согласования.

## 9. Обязательные проверки

Выполнить самостоятельный инженерный анализ по TEST-ENG-01, не ограничиваясь существующими автотестами.

Обязательные группы:

1. Bridge Transport и managed Client Binding — все применимые тесты.
2. Launcher — все применимые тесты.
3. Windows ACL — реальные синтетические DACL и owner SID.
4. Отрицательные проверки неправильного владельца и публичных разрешений.
5. Запрет неизвестной identity, внешних origin, redirect, POST и недопустимого body.
6. Сохранение каталога и UNKNOWN при потере соединения.
7. Сохранение binding при ошибочном reconnect.
8. S1 — статические проверки и применимые полные проверки при наличии защищённых fixtures.
9. S2 FULL — 73 случая.
10. D8 и существующие negative controls.
11. Ultra Chat HTTP и Ordinary Application.
12. JavaScript UI regression.
13. Изолированный launcher smoke согласно штатному регламенту.

Обязательно сохранить ожидаемые отрицательные результаты.

Нельзя исключать падающие тесты или ослаблять assertions для получения зелёного статуса.

Для недоступных проверок указать NOT RUN и причину.

## 10. Ограничения

Строго OFFLINE.

Запрещается:

- Изменять рабочий STANDARD.
- Изменять работающий Client или Manager.
- Запускать, останавливать или перенастраивать реальные модели.
- Менять существующие подключения и пользовательские данные.
- Использовать реальные Bridge-токены.
- Выполнять платные запросы или OAuth.
- Активировать M1-10 LIVE.
- Изменять общий план №34.1.
- Работать с Git/GitHub без отдельного разрешения.
- Выполнять merge или push самостоятельно.

Синтетические рабочие материалы размещать согласно WORKSPACE-ISOLATION-01.

При несовпадении локальной версии с указанным baseline — сообщить BLOCKED, не исправлять устаревшую копию вслепую.

## 11. Критерии завершения

RESULT READY допускается после выполнения разрешённого объёма работ и сохранения:

- Доказанной причины каждого исправленного дефекта.
- Первоначальных FAIL и результатов повторных проверок.
- Точных изменённых файлов и функций.
- Команд, версий среды, exit codes и количества тестов.
- Доказательств сохранения защитных механизмов.
- Перечня OPEN, ограничений и NOT RUN.
- DOC IMPACT.

Отчёт сохранить:

`reports/CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001/report.md`

Также сохранить manifest и безопасные evidence.

При невозможности полного исправления подготовить честный PARTIAL/BLOCKED с установленными фактами.

## 12. Сдача задачи

После завершения итогового пакета выполнить штатную команду:

```powershell
python -B -X utf8 tools/task_slot_rotate.py finish --card "Документация/000_Задачи Codex.md" --task-id CODEX-WUA-WINDOWS-CI-ACL-REPAIR-001 --no-chat-amendment --headless --apply
```

При наличии AMENDMENT использовать установленный регламент их сохранения.

Не переносить БЛОК 1 вручную.

Не присваивать HISTORY ID самостоятельно.

Не изменять БЛОКИ 2–4 и общие реестры.

Итоговый статус:

RESULT READY / AWAITING INDEPENDENT VERIFICATION

NEXT: передать пакет координатору WEB 36 для публикации в установленном порядке и независимой проверки GitHub Actions на новом точном SHA.

Нового LIVE GO данная задача не предоставляет.
<!-- TASK-SNAPSHOT:END -->
