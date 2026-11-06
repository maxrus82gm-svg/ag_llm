# Windows CI evidence supplied in BLOCK 1

Source: baseline card, preserved below. The CI logs and named independent test are absent from the local evidence found.

**Воспроизведение:** после начала отправки вызывается `task.cancel()`. Тестовый транспорт перехватывает `asyncio.CancelledError` и возвращает валидный ответ с usage. Сервис ошибочно возвращает `Outcome.COMPLETED` вместо `Outcome.UNKNOWN_AFTER_START`.

**Доказательства:**
- GitHub Actions `42185342094`, job `127784232360`.
- GitHub Actions `42185590677`, job `127785025580`.
- Независимый отрицательный тест: `reports/CHATGPT-WEB24-CODEX-S4-DEADLINE-REVIEW-20261106/test_independent_deadline.py`.
- Оба независимых запуска: 1 FAIL этого сценария.
- При этом исправленный дедлайн H18 успешно выдержал 120 повторных проверок.

