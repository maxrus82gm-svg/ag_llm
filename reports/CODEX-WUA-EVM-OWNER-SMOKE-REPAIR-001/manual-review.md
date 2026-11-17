# MANUAL ENGINEERING REVIEW

Авторский verdict: **PARTIAL** до физического F-01 и отдельного LIVE GO. Объём проверен по пользовательскому действию → UI → сервер → Turn/evidence.

- EVM модель включается независимо от провайдера и API proof. `ModelCards` store, revision CAS, каталог Ultra Chat и запрет новых Turn не заменялись. При нуле моделей старые чаты/RAW/ledger остаются читаемыми; проверено соседним selector.
- LIVE start по-прежнему использует EVM → существующий Ordinary provider. Из модального check нет автоматического подключения и нет автоматической отправки; два явных подтверждения разделены. Никаких trial quota не введено. 24-часовой session contract не менялся.
- Check использует текущие Origin/write-token/Turn/admission. Pre-send отказ не красит API; completed REAL FAILED красит, REAL SUCCEEDED зеленит, UNKNOWN серый. Повтор Turn ID не обновляет старую историю. Синтетический ответ не может стать подтверждённым REAL.
- S2 разрешает только точный пересмотренный AST `ordinary_provider`; прямой непроверенный импорт `ultra_budget_policy` всё ещё отвергается. S1 точный pin `ModelCards.run_check` обновлён без удаления gate.
- F-05 исправлен только в тестовом cleanup. Tkinter Ultra, штатные launcher, STANDARD/TEST, `model_registry.py`, общий чат bridge и budget runtime файлы не менялись. SHA-сверка защищённых файлов в `source_compare_h41.txt`.
- Физический Windows отказ владельца не воспроизведён из-за Computer Use URL-policy stop. Скриншотная/DOM проверка не выдаётся за реальное перемещение окна.

Возможный риск: при отдельно и заново подтверждённой проверке после завершённого UNKNOWN создаётся новый диагностический Turn; это новый платный запрос, о чём UI предупреждает. Автоматического retry нет. Более сильная межсеансовая дедупликация check как отдельная архитектурная работа не внедрялась.
