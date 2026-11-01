# Минимальная диагностика на 192.168.0.77 — требует отдельного разрешения

Эти действия **здесь не выполнялись**. Вызвать на самом целевом компьютере пользователем либо отдельно авторизованным агентом. Не открывать удалённый административный доступ, не устанавливать агента и не передавать секреты ради проверки.

## Сначала определить ОС и реальный процесс

На Windows: `Get-NetIPAddress -AddressFamily IPv4`; `Get-NetTCPConnection -State Listen` с фильтром LocalPort 8000/11434; для полученных PID прочитать только Name/ExecutablePath и безопасные флаги host/port/model, **не полный CommandLine с возможными ключами**. Из VersionInfo/installed-app metadata получить версию; команды неизвестного Colibri бинарника не запускать до подтверждения назначения. Выяснить, является ли listener Colibri, reverse proxy, контейнером, WSL либо другой программой. На Linux аналогично `ss -ltnp` только нужных портов и пакетная version metadata; недостаток прав явно отметить, не выполнять sudo автоматически.

## Ограниченные HTTP GET на самом сервере

Только после подтверждения конкретного listener выполнить с bypass proxy, без redirects/auth:

```text
curl.exe --noproxy "*" --max-time 3 http://127.0.0.1:8000/health
curl.exe --noproxy "*" --max-time 3 http://127.0.0.1:8000/v1/models
curl.exe --noproxy "*" --max-time 3 http://127.0.0.1:8000/openapi.json
```

Сохранить status/content-type, ограниченный безопасный JSON, engine/schema/version; не публиковать cookies/headers/examples с keys. Ошибку 401 не обходить подбором auth. Если подтвердится Ollama на 11434, отдельно разрешить GET /api/version, /api/tags, /api/ps и /v1/models по её **фактическому** bind. Для сравнительной проверки LAN нужен второй явно разрешённый клиент и точный URL, не общий port scan.

## Ресурсы и установка

CPU/cores, total/free RAM; GPU/driver/VRAM через установленный штатный read-only tool (например nvidia-smi, если он уже есть); тип/свободное место дисков. Для моделей — catalog metadata, loaded set, manifest names и partial-download file metadata в подтверждённом каталоге. Две разнесённые по времени проверки размера partial помогают установить активную загрузку, но не являются универсальным download API. Не читать prompts/ключи и не дампить всё окружение или логи.

Для Colibri отдельно подтвердить product/vendor, version/build, engine backend, model path/formats, native API/schema, bind/auth, documented queue/concurrency/cancel; их связь с Ollama вывести из фактических процессов/config refs, не из общего имени модели. Подтвердить название скачиваемой модели/статус у пользователя и по inventory. Не запускать pull/serve/generate, не выгружать модель и не менять параметры.

После этого — отдельный небольшой согласованный inference smoke при необходимости. В данном исследовании такого разрешения/запуска нет. До ответов server-side identity, hardware, capabilities и download status остаются NOT VERIFIED.
