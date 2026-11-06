# Снимок постановки `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001` — перенос БЛОК 1 → БЛОК 1.1

| Поле | Значение |
|---|---|
| TASK ID | `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001` |
| Карточка | `Документация/000_Задачи Codex.md` |
| Дата переноса | 2026-11-06 |
| Статус | `SUBMITTED / REVIEW PENDING` — сдано исполнителем; независимая приёмка не выполнена |
| SHA-256 постановки (UTF-8, концы строк LF) | `b0159a94acd82e6c3cd9d45c368961bb34529694e89d8ce320375c83c5827296` |
| Строк постановки | 67 |
| CHAT-ONLY AMENDMENT | нет (заявлено исполнителем) |
| Отчёт | `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/report.md` |
| Инструмент | `tools/task_slot_rotate.py` — побайтовое копирование без пересказа |

Текст между строками-маркерами ниже — побайтовая копия содержимого БЛОКА 1 (концы строк приведены к LF).

<!-- TASK-SNAPSHOT:BEGIN -->
**TASK ID:** `CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001`

# Web Alarm Ultra — Stage4: защита от ложного SUCCESS после внешней отмены

**Исполнитель:** Codex 007  
**Координатор и независимый verifier:** ChatGPT WEB24  
**Приоритет:** HIGH  
**Программа:** №37, этап 4  
**ARCH CLASS:** Ultra Chat / Ordinary Chat / Cancellation Safety  
**FOLLOWUP:** `FOLLOWUP-WUA-S4-CANCEL-SUPPRESSED-001`

## 1. Цель

Устранить обнаруженный независимым Windows CI дефект `ordinary_chat_service.py::execute_request()`.

**Воспроизведение:** после начала отправки вызывается `task.cancel()`. Тестовый транспорт перехватывает `asyncio.CancelledError` и возвращает валидный ответ с usage. Сервис ошибочно возвращает `Outcome.COMPLETED` вместо `Outcome.UNKNOWN_AFTER_START`.

**Доказательства:**
- GitHub Actions `42185342094`, job `127784232360`.
- GitHub Actions `42185590677`, job `127785025580`.
- Независимый отрицательный тест: `reports/CHATGPT-WEB24-CODEX-S4-DEADLINE-REVIEW-20261106/test_independent_deadline.py`.
- Оба независимых запуска: 1 FAIL этого сценария.
- При этом исправленный дедлайн H18 успешно выдержал 120 повторных проверок.

## 2. Разрешённый WRITE-scope

- `ordinary_chat_service.py` — минимальное исправление.
- `test_ordinary_chat_service.py` — новые отрицательные и регрессионные тесты.
- `reports/CODEX-WUA-CHAT-S4-CANCEL-SUPPRESSED-REPAIR-001/` — отчёт, manifest, evidence.
- БЛОК 1/1.1 — исключительно штатным `finish` при сдаче.

Остальные исходники, в том числе `web_alarm/turn_service.py`, `run_store.py`, HTTP, Tkinter, UI, B2 и model registry — READ-ONLY.

## 3. Требуемый контракт

После внешней отмены, даже когда адаптер подавил `CancelledError` и вернул ответ:

- результат — консервативный `UNKNOWN_AFTER_START`;
- `Execution.RESPONSE_RECEIVED`, если ответ действительно получен;
- успешный текст ответа не публикуется;
- достоверный известный usage сохраняется;
- неизвестная стоимость не превращается в ноль;
- повторная физическая отправка не выполняется.

Не нарушить исправление H18: сработавший deadline всегда остаётся истёкшим, даже при неизменном тике часов Windows.

Обычный своевременный ответ без отмены остаётся `COMPLETED`. Отмена до отправки не вызывает транспорт. Исходный request/model binding сохраняется.

## 4. Проверка

Сначала воспроизвести RED на исходной ревизии, затем добиться GREEN на исправлении.

Обязательны адресные проверки внешней отмены с подавлением `CancelledError`, дедлайна с подавленной отменой, своевременного успеха, pre-send cancel, одного transport call, usage, отсутствия повторной отправки и сохранения UNKNOWN в Stage4B.

Выполнить всю релевантную регрессию: S4A, S4B, Stage3, RAW storage, Run Store. Сохранить отрицательные результаты, точные команды, exit codes, версии и SHA.

Работать только на синтетических Workspace. Реальные GigaChat, OAuth, Colibri, платные API и пользовательская история запрещены. Запускатель после тестов должен оставаться STANDARD.

## 5. Завершение

Если исправление выходит за разрешённый scope — остановиться с `PARTIAL / BLOCKED`, не менять чужие файлы.

Если пакет готов — сохранить полный отчёт, manifest, evidence и выполнить штатный `tools/task_slot_rotate.py finish` для данного TASK ID.

Codex не использует Git/GitHub без отдельного разрешения. После сдачи пользователь публикует результат, WEB24 независимо проверяет GitHub-исходники и Windows CI.

**Критерий приёмки:** внешний cancel не может стать ложным SUCCESS; исправленный дедлайн H18 и все соседние инварианты остаются исправными.
<!-- TASK-SNAPSHOT:END -->
