# Windows CI evidence supplied in BLOCK 1

Source: baseline card, preserved verbatim below. The original CI log is not present in the locally found evidence.

**Зафиксированный отрицательный результат:**

- GitHub Actions run `42179125624`, job `127764370552`.
- Тест `test_ordinary_chat_service.ExecutionContract.test_swallowed_timeout_cannot_publish_late_success`.
- При deadline 10 ms и транспорте, подавляющем `asyncio.CancelledError`, получен `Outcome.COMPLETED` вместо ожидаемого `Outcome.UNKNOWN_AFTER_START`.
- Предыдущий run `42178648349` — 148 PASS.
- Последующий run `42179394007` — 173 PASS, включая 20 повторов проблемного теста.

