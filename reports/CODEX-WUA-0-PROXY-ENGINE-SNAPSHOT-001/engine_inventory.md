# Точный bounded inventory

|Поле|Наблюдение|
|---|---|
|Path label|ENGINE_BINARY_01, exact child executable из filtered local process metadata|
|Wrapper/core|v2rayN.exe PID2012 → sing-box.exe PID21976; snapshot, не постоянный observer|
|Binary type|Windows PE32+ AMD64, basename sing-box.exe, 8 sections|
|Размер|44,773,888 bytes|
|SHA256|`ca74563c93440a2e9cb73eae6a04c109d3f5efce36a385f8261a654e362d2ea3`|
|Исторический hash|Совпадает полностью с 17 октября; исторические PID14456/6984 отличаются|
|PE FileVersion/ProductVersion|Нет|
|PE CompanyName/OriginalFilename/ProductName|Нет|
|Embedded Authenticode table|Offset0 / size0; catalog trust не проверен, signature chain APIs не вызывались|
|Go toolchain claim|go1.25.8|
|Go main path claim|github.com/sagernet/sing-box/cmd/sing-box|
|Go module/version claim|github.com/sagernet/sing-box / v1.13.4; main module sum отсутствует|
|VCS revision/time/modified claims|d09182614c7778c1e0f51d990635c5d4249c437e / 2026-03-26T05:28:33Z / false|
|Build claims|exe, gc, windows/amd64, GOAMD64=v1, CGO_ENABLED=0; 100 dependency entries|
|Source→binary identity|BLOCKED; embedded strings не supply-chain attestation|

Только отфильтрованные build settings сохраняются. Raw `-ldflags`, произвольные build paths, полный dependency dump, CLI arguments и пользовательские configs не публикуются. Список build tags в очищенном snapshot — наличие compiled options, не доказательство активных сетевых каналов или их отключения.

Чтение file identity/size/mtime before/held/after защищает от части случайного drift. Это не защищённая установка и не доказанный TOCTOU-free future launch; перед будущим запуском нужны повторная pin-проверка, protected roots и удерживаемые image/config handles. Идентичность загруженной памяти не исследовалась.

Collector: `collect_snapshot.py <exact-approved-local-executable>`; он допускает один явно переданный local fixed-drive `.exe`, не ищет core. Разрешение path задаёт доверенный оператор этой read-only TASK; функция не является публичным MCP filesystem tool. Core не копировался в проект и не запускался.
