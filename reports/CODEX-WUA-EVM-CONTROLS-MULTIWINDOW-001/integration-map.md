# Integration map — EVM controls and windows

## Единое состояние

`model_registry.py` остаётся источником ID и адаптера. `ModelCards` читает/пишет существующий `ultra/model_settings.json`: `models[model_id].enabled` и общий `revision`. Для старых валидных настроек отсутствие поля означает включено; повреждённое значение запрещает новые отправки. `set_enabled` использует один lock и CAS `base_revision`, не меняет profile, params, descriptions, roles, check history или чаты.

`POST /ultra/model-cards/{id}/enabled` защищён Origin и Ultra Chat write-token. EVM UI меняет состояние через этот маршрут. BroadcastChannel уведомляет открытые вкладки/окна, 8-секундный опрос покрывает пропущенное уведомление и F5. Серверное чтение остаётся источником истины.

## Чат и доказательство API

`UltraConnections` и Ordinary capability filter берут `ModelCards.is_enabled`; сохранённая модель старого чата читается даже если она выключена. Новая отправка выключенной модели запрещается до провайдера. Только принятый ранее idempotency key может пройти в существующий `TurnService` для чтения/завершения без новой физической попытки. При нуле моделей LIVE start прекращается до OAuth. Переключатель сам не вызывает OAuth, catalog или inference.

EVM `Проверить чат` идёт через прежний Ordinary Turn и его admission. REAL SUCCEEDED/FAILED/UNKNOWN с `turn_id` и `settings_version` записываются в прежний checks store с дедупликацией; повтор A после B не сдвигает индикатор. Синтетический ответ не превращается в подтверждённый REAL. Профиль и срок актуальности отделены от enabled; зелёный не возникает от включения.

## Окна

`#evmPins`/`evm.pins`, Ctrl+клик, `⧉`, drag и `ultra/evm_view.json` сохраняют внутренние закрепляемые карточки. `↗` создаёт отдельный browser popup `?evm_window=<connection_id>#evm` с именем на модель; исходная карточка остаётся. Внешняя страница использует те же `fullCard`, маршруты и cookie/write-token браузера, без нового хранилища. Topmost включается только явным нажатием через `documentPictureInPicture.requestWindow` и iframe этой страницы; при закрытии PiP исходное внешнее окно остаётся. Браузер не гарантирует физическое размещение на другом мониторе или число одновременных PiP окон: это OPEN до Windows smoke.
