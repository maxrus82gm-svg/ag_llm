# MANUAL ENGINEERING REVIEW

Изменения ограничены runtime owner-lock, same-origin shutdown route, launcher drain, текстом UI и адресными тестами. `ProviderSession` сохраняет прежние TLS/admission/version/ledger checks. Для нового владельца нужен новый grant; старый grant не переиспользуется. Account lock охватывает реальные и синтетические аккаунты отдельно; при отказе конструктора освобождается, при `close()` освобождается после записи CLOSED. При crash ОС освобождает byte lock. Предыдущие файлы grant/RAW/ledger не удаляются.

Shutdown POST использует точный локальный Origin, existing write token и подтверждение; обычный GET не может остановить приложение. Tracker ставится до `server.shutdown()` и отклоняет новые задачи. Второй POST подтверждает уже начатую остановку. Существующий launcher закрывает session и порт в `finally`. Сервер не вызывает EVM disable и не завершает браузер/посторонний Python.

**Риск:** old `ACTIVE` не несёт доказательства OS lock и останется блокирующим — P0 OPEN. Ожидание worker ограничено 20 с; при тайм-ауте состояние запроса может быть UNKNOWN и требует расследования. Отдельные STANDARD/TEST процессы не остановлены кнопкой без доказанной принадлежности. Физического Windows smoke и независимого review не было. Поэтому итог PARTIAL.
