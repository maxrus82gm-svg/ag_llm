# Граница доказательств

|Уровень|Что проверено|Что не доказано|
|---|---|---|
|Generic configuration|Exact schema, strict old topology validator, one next hop, no direct/fallback, pins, disabled state|Поддержка полей настоящим V2Ray|
|Synthetic attestation|PID/SID/endpoints, controller pins, session/epoch/generation/expiry/replay/companions rejected on mismatch|Windows LookupAccountSid/effective token, подпись доверенного OS observer|
|Локальная Python-модель|Worker owns listener+outgoing TCP flow, receiver receipts; bounded faults and controlled takeover|B Windows account, remote route, TLS/proxy authentication, real engine behavior|
|Python audit hooks|Написанный нами код ограничен owned loopback TCP4; DNS/UDP/IPv6/extra child paths rejected|OS containment произвольного native/ctypes/скомпрометированного процесса|
|WFP/toolkit/NPFS gates|Прежние исходники не изменены; static blocked contracts и pure preflight|Native policy arbitration, cross-SID enforcement, boot/restart/pre-existing flow teardown|

Source/config hashes — контроль неизменности относительно доверенного test controller, не code signing и не защита от same-user/admin замены файла/интерпретатора/зависимости. Runtime dependency versions сохранены, но их supply-chain не верифицировался. Путь проверяет own scope, local drive, reparse/offline/cloud attributes; есть TOCTOU между проверкой пути и открытием. Это не trusted installation boundary. До реальной активации требуются защищённые владельцем deployment roots/ACL, file handles/config binding и process identity, исследованные независимо.

Receiver HMAC key существует только в parent RAM и не передаётся worker. Process memory текущего пользователя не является изоляцией от same-user attacker. На диск сохраняются synthetic nonce/correlation/HMAC/PID, не API keys/passwords. HMAC нельзя независимо пересчитать из очищенного receipt после завершения; для проверки фактического запроса служат source pins, correlation, socket PID и повторяемый test.

Read-only `GetExtendedTcpTable` — snapshot с возможным race/PID reuse. В нашем bounded fixture удерживается Popen handle живого собственного worker; сохранены только связанные с ним/receiver строки. Это не continuous observer и не токен B. Потеря observer, уже открытые сокеты, наследованные handles, process token changes, debugger/injection, remote/DNS/UDP/IPv6 обходы остаются системными gates.

Нет безопасного operational installer/uninstaller в этой сдаче; `can_apply=false`, `can_start_tunnel=false`, native_health UNKNOWN без исключений. Fake `approval=true`, signature-looking JSON, заявленная версия/хеш не создают доверия. Неверная JSON/shape/pin → reject, ошибка зависимости/неожиданная exception → остановка процесса без активации. CLI всегда exit20. Автоматической смены endpoint/proxy/движка/credentials нет.

Реальный engine не запускать, пока отдельно не доказана OS-level изоляция и не получен USER GO. Нельзя объявлять host fail-closed на основании положительных Python tests или source-only WFP backend.
