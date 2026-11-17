# Маршруты и границы

`EVM → /ultra/chat/live/start → OrdinaryApplicationChatService.start_live → ProviderSession → проверенный OAuth/catalog → capability → Ordinary Turn → RAW/ledger/history`. Новый account lock расположен внутри `ProviderSession`; он не заменяет существующие admission, transport или Turn.

`UI «Завершить Web Alarm» → POST /ui/shutdown` с same-origin, существующим Ultra Chat write-token и точным подтверждением → tracker STOPPING → отклонение новых запросов → `ThreadingHTTPServer.shutdown()` → launcher drain до 20 с → прежний `finally`: server close, session close, port claim release. Конфигурация EVM и модели не меняются; `/ultra/chat/live/stop` не вызывается через UI shutdown.

Повторный POST во время STOPPING возвращает 202 `STOPPING`; после остановки сервера вкладка показывает результат и может быть закрыта вручную. Другие процессы и браузер не затрагиваются.
