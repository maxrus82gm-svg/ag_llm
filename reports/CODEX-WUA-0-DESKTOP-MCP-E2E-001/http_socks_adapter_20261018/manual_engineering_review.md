# MANUAL ENGINEERING REVIEW — AM07

Codex 007; собственный source/adversarial review поверх automatic suite. Не
независимая приёмка WEB_10, не native Go/V2Ray/OS security certification.

## Scope, источники и порядок операций

Прочитаны текущие нормативные definitions (17 addressed Rule-ID/contract), card,
route/profiles, AM05/AM06 и новые координаторские выводы в 34/19. Точное upstream
тело official code локально отсутствует; чтение пересказа координатора и symbols
не повышено до собственного full source audit. Exact-tag и local EXE разделены.
Read-only CIM/listener inventory не превратился в protocol probe: текущие paths/
command line недоступны, значит loaded config не установлен. Старые GUI snapshots
не использованы как current runtime state. Исторический порт 10813 отделён от
текущего 10814. Никакой live probe, перезапуск или обход разрешений не выполнялся.

## Просмотренные ветви собственного adapter.py

1. `Config.__post_init__` выполняется до socket activity. Loopback literal, int
   против bool, finite timeouts, resource bounds, immutable exact `.invalid`
   allowlist проверены. Hostname localhost не допускается как скрытый resolver.
2. `_request`: абсолютный header deadline, byte/field/line limits, strict ASCII/
   CONNECT/authority/Host, duplicates/body framing rejection. Неполный/слишком
   большой/запрещённый запрос не открывает SOCKS connection. Header values только
   в локальной памяти, не в events или upstream protocol.
3. `_socks`: ровно одна connect строка на fixed endpoint. `recv_exact` обрабатывает
   fragmentation/EOF/total deadline; NO AUTH и reply VER/RSV/REP/ATYP checked.
   Домен передаётся ATYP=3. BND_ADDR IPv4/domain/IPv6 считывается по длине и никогда
   не применяется как remote target. Любой handshake failure освобождает socket
   до `_handle` rejection; retry/alternate/direct paths в коде отсутствуют.
4. `_relay`: оба направления только по уже открытым socket, chunk/budget/idle/
   hard-duration bounds; active stream не продлевает hard limit. EOF/timeout/
   reset закрывает туннель, не создаёт новый route. Whole-stream half-close
   намеренно не реализован; TLS/HTTP payload не интерпретируется/не логируется.
5. `_accept`/`stop`: semaphore cap до thread creation, finite backlog, event cap,
   tracked sockets и недемонические workers. Stop закрывает listener, дожидается
   accept thread, затем закрывает handler sockets и join; no kill чужих процессов.
   Это bounded prototype, не production load/stress proof.
6. `_reply`: финальный protocol fix отправляет отказ, shutdown write и выполняет
   bounded discard/drain (8KiB/30ms). Это не forwarding и не изменение allowlist.
   При flooding ресурс ограничен; гарантированное получение status злонамеренным
   не читающим peer не заявляется. Основной fail-closed — отсутствие target dial.

## Проверка тестового стенда и oracle

Audit guard поставлен до fixture sockets; запрещает DNS/UDP/native subprocess/
ctypes, nonloopback и чужие ports, а также неправильные role edges. Это API guard
данного Python процесса, не защита arbitrary native code. Все методы создания
сокетов в просмотренном source используют socket API с этим guard. Становиться
OS egress boundary для Go он не может.

SOCKS fixture не делает DNS: exact domain/port проверяются и сопоставляются с
созданным origin. Физический local port forward socket сравнивается с peer port
origin; fake headers не могут изготовить такой proof. Fault tests требуют marker
METHOD_RECEIVED/FAULT_REPLY и HTTP outcome, не просто отсутствие success. Отказы
Windows bound/non-listening могут дать 502/504; оба точных допустимых HTTP исхода
сопровождаются одним SOCKS connect attempt и нулём origin contacts.

Неожиданные fixture/adapter exceptions, audit violations, port/thread leaks делают
run красным. Peer resets классифицируются только как ConnectionReset/Aborted
либо при собственном teardown; неизвестные OSError не скрываются blanket pass.
Финал имеет один ожидаемый peer reset, ноль fixture/internal errors. Ошибки
сохраняются как type+frames без request/header/error-message data.

Quality control `test_31` — настоящий местный SOCKS accept/close, затем намеренный
direct dial только к своему origin ролью mutant. Oracle обнаруживает именно
второй путь, SOCKS forward list пуст. Такое разрешение не выдано роли adapter.
В финальном trace 70 connect attempts: driver 36, adapter 22, socks 10, mutant 2.
Все literal 127.0.0.1. Единственный intentional direct — mutant→origin; adapter
direct/alternative dial count 0. Это не выдаётся за отсутствие direct на всём ПК.

## Первоначальный красный результат и исправление

`attempt01_results.json`: 31 collected, 29 PASS, 0 FAIL, **2 ERROR**. На Windows
header-limit/overload close с непрочитанным входом приводил к reset до чтения 431/
503. Маркеры показывали отказ и нулевой upstream/origin, но protocol assertion
не прошла. Классификация: **REFERENCE PROTOTYPE DEFECT / Windows reject-close**,
не native tunnel-client/V2Ray defect. Первые source snapshots и их matching SHA
сохранены в `adapter_attempt01.py.txt`, `tests_attempt01.py.txt`.

Исправлен bounded graceful reject, exact status assertions не ослаблялись до
«любая ошибка». Добавлен отрицательный env+refusal case; attempt02 **32/32 PASS**.
Manual review затем выявил test gaps absolute deadline под continuous header drip,
hard duration под активным трафиком, valid domain/IPv6 BND replies. Добавлены
действительные triggers этих ветвей; attempt03 **36/36 PASS** без повторных
изменений adapter source. `tests_attempt02.py.txt` сохраняет старую ревизию.
Случайная ошибка имени codec при первоначальном assignment-copy helper сохранена
в `setup_attempt01.txt` отдельно как HARNESS DEFECT, до network tests.
Первый final-artifact validator также использовал исторический AM06 config hash
как expectation вместо нового AM07 startup baseline. Он отказал до manifest;
полный исходник/relevant AssertionError сохранены отдельно. До/после AM07 config
равен `2a1745afe7818f69f564ea36d58f17adb1653edec9e711e3e1c8f8ee97565aa2`:
изменение между этапами не является внутрисеансовой мутацией. Исправлено именно
ожидание валидатора, не config/permissions. Старый config не восстанавливался.

## Рассмотренные альтернативы и открытые риски

- Существующий HTTP/mixed inbound был бы проще адаптера, но текущий loaded config
  не подтверждён. Пробовать CONNECT через live V2Ray запрещено — не сделано.
- Расширить прототип до обычного HTTP proxy, real domains/auth/SOCKS credentials/
  retries: сейчас не нужно и изменит поверхность безопасности. Оставлен CONNECT
  only, отказ вместо неподдержанного пути. Все native paths сначала source audit.
- Локальный adapter fail-closed не закрывает обход в tunnel-client, Cloudflared,
  custom transports и direct/DNS policy V2Ray. Native isolation/remote route
  остаются отдельными BLOCKED gates.
- Вне нашей папки во время работы изменилась карточка Codex: текущий B1 содержит
  CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001. Это не поручение брать Claude task.
  Автор/механизм не установлен; карточка не восстановлена и не правилась нами.
  Input drift сохранён отдельно; все остальные 96 защищённых inputs неизменны.

## Итог

ADAPTER REFERENCE TEST VERIFIED в точной границе данного synthetic source/run.
SOURCE AUDIT PARTIAL / SOURCE PACK BLOCKED; HTTP INBOUND NOT VERIFIED; NATIVE
CLIENT FAIL-CLOSED NOT VERIFIED; V2RAY REMOTE ROUTE NOT VERIFIED. Native/hosted/
ordinary Chat не исполнялись. Готовность к установке, release или системная
безопасность не объявляются. Полный результат передаётся пользователю для
публикации **только AM07 папки** и независимого review WEB_10.
