# AMENDMENT — пользовательский handoff PR №12

Получен в чате 2026-10-12 после локальной полной регрессии. Это данные пользователя, не результат чтения Git/GitHub агентом. Указанные SHA и CI результаты независимо не проверялись. Ниже handoff сохранён дословно. Просьба временно остановиться в его конце отменена последующим сообщением пользователя: «продолжай».

---

Astra, передаю актуальный handoff по Draft PR №12 для задачи `ASTRA-WEB02-TEST-ARCH-001`.

**SOURCE REVISION:**
- Repository: `maxrus82gm-svg/ag_llm`
- `main`: `2d05cc40fe2d9beae16a70458cb29bb03f904f97`
- Draft PR №12, branch `GPT`: `d07e603eeb5a2a831739bd7a168bd158d25e95f5` (commit #288).
- PR не объединён. Production-код не изменялся.

**Незакрытые findings:**

**F1 — RC-5 Closeout / Windows**
Естественно воспроизведён `CloseoutError → TaskStoreError → PermissionError / WinError 5` при перемещении TASK. В одном сценарии перемещение не произошло, TASK осталась активной, данные сохранились — безопасный fail-closed подтверждён.

Но в CI `38234408864` выявлен другой случай: перемещение ACTIVE → COMPLETED состоялось, после чего Windows отказала в сохранении `task.json`. Конечное состояние: `completed` directory, статус `PLANNED`, повторное чтение подтверждает состояние. Это потенциально восстанавливаемое `MOVED_STATUS_PENDING`, но независимое доказательство дальнейшего recovery в данном прогоне отсутствует. Не считать автоматически PASS.

Source: `test_web_alarm_projection_concurrency.py`, `web_alarm/task_store.py`, `web_alarm/closeout.py`.

**F2 — Direct TaskStore completion vs MutationExecutor**
При конкурентном прямом `TaskStore.complete_task` и записи через `MutationExecutor` воспроизводились `FileNotFoundError` при чтении `task.md`, snapshot и записи `events.jsonl` по старому пути `tasks/active/...`.

Последний PR CI `38234416619`: полная регрессия 750 тестов, 749 PASS, 1 FAIL — именно этот concurrency test. Отдельный 80-раундовый тест также завершился FAIL.

Пока не доказано, что произошла незаконная физическая мутация, однако fail-closed и конечное состояние требуют отдельной проверки.

Source: `test_web_alarm_mutation_executor.py`, `web_alarm/mutation_executor.py`, `web_alarm/operation_store.py`, `web_alarm/event_checkpoint_store.py`, `web_alarm/manifest_store.py`.

**F3 — WA-017 Crash-safe completion**
Ранее тест аварийного завершения Closeout выдавал `FAILED:CloseoutError` вместо ожидаемого `REJECTED`. В коммите #287 добавлен только диагностический сбор error chain и состояния TASK, без ослабления assertions. В двух последних отдельных наборах по 80 раундов WA-017 — PASS, но первоначальная причина остаётся недоказанной.

Source: `test_web_alarm_reliability_wa017.py`.

**Задача для твоего исследования:** учти F1–F3 в матрице покрытия. Предложи независимые invariant oracles для `pre-move failure`, `post-move/status-pending`, конкурентной mutation и crash/restart. Не дублируй имеющиеся тесты и не подменяй ошибки Windows универсальным PASS.

Доступ к Git/GitHub по-прежнему ограничен `DOC-GIT-01`. Пользователь может синхронизировать локальную рабочую копию с веткой `GPT`, но это не разрешение агенту выполнять Git-операции.

В связи с окончанием лимита сохрани текущий анализ, матрицу покрытия, реализованные тесты и оставшиеся шаги в своём отчёте по регламенту. После восстановления лимита продолжишь с сохранённой точки.

Production-код, существующие CI и PR №12 не изменять. Итог передать ChatGPT для независимого аудита.
