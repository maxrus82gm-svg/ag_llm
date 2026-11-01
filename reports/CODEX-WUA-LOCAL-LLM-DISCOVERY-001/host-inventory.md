# Host inventory — 01.11.2026

TASK `CODEX-WUA-LOCAL-LLM-DISCOVERY-001`. Источники: evidence/host_inventory.json, hardware_extra.json, http_inventory.json. Все показатели — разовый снимок, не benchmark. **Диагностическая машина 192.168.0.9/24; целевой сервер 192.168.0.77 — другая машина.** Адрес запуска Web Alarm Ultra с другого клиента не установлен; локальная папка проекта сама по себе не доказывает, где запущен пользовательский Ultra.

| Компьютер | Проверенный факт | Граница |
| --- | --- | --- |
| 192.168.0.9 | Windows 10 Pro 19045 x64; текущая shell/файловая диагностика | Только этот host обследован ОС-методами |
| 127.0.0.1 текущей машины | Ollama HTTP отвечает на 11434; 8000 закрывает HTTP без ответа | Это loopback машины .9, не loopback .77 |
| 192.168.0.77:8000 | GET /health, /v1/models, /openapi.json: по одному запросу, timeout около 2 с каждый | NOT ACCESSIBLE FROM DIAGNOSTIC HOST; причина не установлена. Не доказано, что host выключен, служба отсутствует либо firewall виноват |
| 127.0.0.1:8000 на .77 | NOT VERIFIED | Удалённый loopback через LAN URL не обследуется; административного доступа не было |

## Ollama на диагностической машине

- API, CLI и Windows installed-app metadata согласованно показывают **0.40.13**. CLI обнаружен в `%USERPROFILE%/AppData/Local/Programs/Ollama/ollama.exe`; registry metadata — пользовательская установка Ollama. Это наблюдаемый install layout, не история установщика/обновления.
- `ollama app.exe` PID 20620 → `ollama.exe` PID 24684, безопасно извлечённый глагол `serve`. Подходящей Windows-службы в доступном перечне не найдено; другие startup/container/WSL-механизмы не исключены.
- Listener **127.0.0.1:11434**. Он не привязан к LAN-интерфейсу в этом снимке; доступность с другой машины не испытывалась. Настройки bind/автозапуска не менялись.
- GET /api/tags: **deepseek-r1:8b**, digest `6995872bfe4c521a67b32da386cd21d5c6e819b6e0d62f79f64ec83be99f5763`, **5 225 376 047 байт**; GGUF, qwen3 family, 8.2B, Q4_K_M, runner ggml. В /v1/models тот же ID. Это inventory metadata, не доказательство inference.
- API сообщает capabilities `tools`, `thinking`, `completion` и context_length 131072. Вызовы tools/reasoning/structured output/images и фактическое runtime context window **NOT VERIFIED**. Из имени модели нельзя вывести все возможности.
- GET /api/ps: **пустой список**. Зарегистрированная на диске модель сейчас не показана как загруженная. Модель не запускалась и не выгружалась.
- В стандартном локальном каталоге models найден один manifest deepseek-r1/8b; partial blobs не найдены, процесс pull не наблюдался. Это ограниченное свидетельство о .9 на момент снимка. Статус дополнительной модели на .77/в других каталогах/другом аккаунте **NOT VERIFIED**.
- OLLAMA_HOST/MODELS/NUM_PARALLEL/MAX_LOADED_MODELS/KEEP_ALIVE/CONTEXT_LENGTH не заданы в **процессе диагностической shell**. Это не чтение окружения уже работающего сервера; его реальные параметры параллелизма/очереди не установлены. Общий дамп окружения не делался.

## Порт 8000 и Colibri

На .9 сокет `[::]:8000` принадлежит **Manager.exe, PID 5156**. Путь исполняемого файла/версия доступными непривилегированными методами не получены. GET /health, /v1/models, /openapi.json завершились `RemoteDisconnected`, без HTTP status/JSON; это не ответ 404 и не доказательство отсутствия маршрута.

Идентичность **Colibri**, Colibri version/engine/model directory/число моделей/очередь/аутентификация и связь с Ollama **NOT VERIFIED**. Команд coli/colibri/llama-server в PATH диагностической shell и Colibri в просмотренных install entries не найдено; отсутствие на .77 из этого не следует. Гипотеза JustVugg/colibri пришла из постановки и не подтверждена установленными файлами. Manager.exe не объявляется Colibri, прокси или LLM-engine.

## Ресурсы .9

| Ресурс | Наблюдение |
| --- | --- |
| CPU | Intel Core i5-12400F, 6 cores/12 logical, разовый LoadPercentage 30%; MaxClockSpeed 2500 MHz — CIM field, не измеренная частота |
| RAM | 33 374 584 KiB visible ≈31.83 GiB, free 15 322 240 KiB ≈14.61 GiB |
| GPU | NVIDIA GeForce RTX 3070 Ti; nvidia-smi: total 8192 MiB, used 3583 MiB, utilization 2%, driver 610.88 |
| GPU оговорка | Win32_VideoController сообщает около 4 GiB из-за ограничения поля; для памяти использован nvidia-smi. Занятая VRAM не приписывается Ollama/Colibri |
| Диски | NVMe Samsung 970 EVO Plus 500GB; SATA Samsung 850 EVO 500GB; SATA HDD WDC 2TB и ST2000DM008 2TB; ST3250620AS 250GB MediaType Unspecified. HealthStatus Healthy — не проверка производительности/SMART полного scope |
| Свободно на томах | C ≈15.99 GiB, D ≈32.50 GiB, F ≈57.16 GiB, G ≈378.58 GiB, M ≈58.35 GiB. Соответствие каждого тома physical device отдельно не устанавливалось |

Ресурсы .77 неизвестны. Одновременная загрузка Ollama+Colibri и скорость **NOT VERIFIED**: disk size GGUF не равен VRAM residency, нужны KV cache/context/CPU offload и конкурирующие приложения. В момент снимка свободно около 4609 MiB VRAM; обещать размещение обеих моделей оснований нет. Порт 8000 на .9 уже занят; новую службу там не запускали.

Минимальные разрешаемые действия на целевом сервере перечислены в server-side-checklist.md. Это предложение для отдельного разрешения, не скрытая выполненная диагностика .77.
