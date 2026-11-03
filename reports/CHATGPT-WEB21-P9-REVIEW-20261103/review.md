# WEB21 / 2026-11-03 — независимая ограниченная приёмка Run Store P9

**TASK:** `CLAUDE-WUA-CHAT-RUNSTORE-P9-001` · **Автор:** Claude 008 · **Verifier:** ChatGPT WEB21 · **Источник:** `main@8b96f6d7eaa7faee5f5017b087eb4999537b9127` · **Вердикт:** **PASS / BOUNDED SOURCE + PUBLISHED AUTHOR EVIDENCE; independent runtime NOT RUN**.

**Смысл:** исправление потери записей общего Run Store v2 при параллельных писателях принято в исследованной области; это **не** независимый Windows runtime PASS, не проверка полного многописательского RUN, не завершение Stage3 №37 и не разрешение live/paid.

## Точное происхождение

- Авторский пакет: `reports/CLAUDE-WUA-CHAT-RUNSTORE-P9-001/report.md`, `manifest.json`, `evidence/`, `tools/`, опубликован в `main`.
- Исходник `run_store.py`: Git blob `3d70e1bc25d51ff50436d7d91ba0597e6a4a5408`, SHA-256 `f63d7d15670a290355fa034d21d9e979d890e11d7bf52b02bbb1598a00cab12e` (точное совпадение).
- Тест `test_run_store_v2.py`: Git blob `635c96ceb55ad3034c5127e27be0958b26d70d00`. Размер Git blob 23936, в manifest — 23937. Одно добавление `CR` перед `LF` в строке 172 опубликованного текста даёт **точный** авторский SHA-256 `9f7f90f29932d75fbfaf51956ccf1f51f377e4110922fde1d0bd1c8ff1509d82`. Это реконструируемое различие EOL, не доказательство независимого запуска теста на текущем blob.
- **Сверка манифеста:** 26/26 позиций (`changed_files` 2 + `files` 24): 25 SHA-256/размеров совпали непосредственно, 1 — после описанной реконструкции одного `CR`. Проверка выполнена на опубликованных текстах; полный bytewise runtime/CI не запускался.
- Полный исходный БЛОК 1 без редактирования сохранён отдельно: `reports/CHATGPT-WEB21-P9-REVIEW-20261103/assignment_source.md`, UTF-8 SHA-256 `6ecf62b02134e79c0cab7dc068ac1eeecaad1456b3a65be152efdd17876de1ea`. Между штатными маркерами карточки он присутствовал, CHAT-ONLY AMENDMENT в найденном авторском пакете не указан. Технический `handoff_task.md` в пакете автора отсутствует вследствие `NO ROTATE`.

## Самостоятельная проверка source / oracle

1. Прочитаны `_index_lock`, `_require_index_lock`, `_save_index`, `ensure_task_index_entry`, `ensure_run_index_entry`, `update_run_summary_index`, `create_run_summary`; запись общего индекса выполняется под общей реентерабельной блокировкой `context_storage`, публикация без удержания блокировки запрещена.
2. Прочитаны P9-тесты: конкуренция двух/четырёх процессов, повтор/конфликт идентичностей, поколение индекса, таймаут, вложенные вызовы, крах процесса, повреждение, junction `.ultra`, чтение во время compaction. Эталон сравнивает опубликованные записи/номера с возвращёнными ID, а не только отсутствие исключений.
3. Авторские JSON-evidence независимо открыты и сопоставлены: автономный `reproduce_before_fix.json` — **5/5** сценариев с дефектом; `reproduce_after_fix.json` — **0/5**; `red_on_base.json` — 21 тест / 8 FAIL; `pytest_focused.json` — 21/21 PASS; `gate_all.json` — 1078, 1076 PASS / 2 SKIP, exit 0, isolation violations 0; `mutants.json` — 6/7 KILLED, M05 SURVIVED как вложенно эквивалентный вариант (это объяснение автора, не отдельный формальный proof).
4. **Не выполнялись verifier:** Python/pytest/Windows/CI, физические filesystem-junction пробы, полный Stage3, network, настоящие Workspace, Tk/Web E2E, live/API. Авторские прогоны не называются нашими независимыми.

## Остатки и gates

- `FOLLOWUP-WUA-P9-AUDIT-PATH-001`: `.ultra/audit` как junction может направлять файловую запись за Workspace; заявлено авторским A2, подтверждается source без no-follow. Не исправлено в P9; до Stage3 нужен отдельный security gate/решение по угрозам и негативный Windows oracle.
- `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001`: `append_run_record` остаётся под контрактом **один писатель на один RUN**. Параллельные отправители того же RUN не проверены; архитектурная граница для Stage3/Blueprint P4.
- `FOLLOWUP-CLAUDE-P9-SLOT-001`: БЛОК 1 не содержит обязательной отдельной строки `**TASK ID:**` и `task_slot_rotate.py check` по авторскому отчёту дал `INVALID/NO_TASK_ID`. Исходный БЛОК 1 сохранён дословно; **без запуска штатного `check/rotate` мы не очищаем БЛОК 1 и не перезаписываем 1.1**. Карточка = SLOT HOLD, несмотря на технический bounded verdict.
- `FOLLOWUP-WUA-P9-INDEPENDENT-RUNTIME-001`: независимый Windows/CI full/selected regression остаётся NOT RUN и не может служить обоснованием Stage3.
- `FOLLOWUP-WUA-S2-CHAT-STAGING-001`, Tk readers P1–P6 и Stage3 gates остаются открыты; legacy duplicate index_generations до P9 не восстанавливаются автоматически; приватный lock API в `context_storage` — нефункциональный архитектурный долг. Актуальность других этапов №37/№43 не повышается этой проверкой.

**Closeout:** техническая итерация P9 документально закрывается в `GPT` с ограниченным PASS, при сохранённых OPEN. **CARD SLOT HOLD** до разрешённой механической ротации после архивного readback; `main` не изменяется без merge пользователя. История: №05 `REG-WEB21-P9-REVIEW-20261103`, №06 `EVT-WEB21-P9-REVIEW-20261103`, №001 Claude (03.11), №34/40 и БЛОКИ 2–4 Claude. Отдельного кода, тестов и CI в этом документальном коммите нет.
