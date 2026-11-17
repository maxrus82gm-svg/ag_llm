# MANUAL ENGINEERING REVIEW

**Вердикт автора: PARTIAL.** Проверены архитектурные границы и отрицательные сценарии; независимая приёмка впереди.

- Источник переключателя один: существующий `ModelCards` store, lock и revision CAS. Server route включён в прежнюю проверку Origin и write-token. Нового транспорта/менеджера нет.
- Новая отправка выключенной модели отсекается сервером до provider. Replay принятого Turn использует старый idempotency key; новые платные попытки не появляются. Ноль моделей не запускает LIVE/OAuth.
- RAW/Turn/ledger и чат не переписываются переключателем. Сохранённую модель можно прочесть, но нельзя выбрать заново до включения. Ошибки синхронизации EVM не скрывают уже сохранённый Turn.
- REAL status отделён от enabled и от TEST. Дедуп по Turn ID защищает A → B → replay A. UNKNOWN остаётся серым при последнем исходе. Проверка профиля и свежести сохранена.
- Старые внутренние pin, drag, роли, профили, настройки и история не мигрировали. Popup/PiP не меняют state store. Физическое поведение браузера не проверено.
- `ast.parse` для `model_cards.py`, `ultra_connections.py`, `ordinary_provider.py`, `server.py`, `ui.py`: PASS. S1 source reconciliation: PASS. S2 static isolation: FAIL 1, оставлено OPEN.
- Побочные файлы Tkinter Ultra, STANDARD/TEST, пользовательские Workspace/RAW и launcher не менялись. Реальных GigaChat API вызовов: 0.

Риск: Document Picture-in-Picture не даёт обещать несколько одновременных topmost окон без физического теста. Chrome может отказать в popup/PiP по своей политике. Отказ виден пользователю. Нужен Windows smoke и независимый review до FULL PASS.
