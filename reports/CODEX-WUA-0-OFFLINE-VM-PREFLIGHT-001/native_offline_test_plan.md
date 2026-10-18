# Gate E — future native offline plan, execution NOT AUTHORIZED

**NATIVE CLIENT EXECUTION NOT STARTED.** В данной TASK — 0 тестовых запусков
EXE, 0 VM, 0 сетевых probes, 0 reference-suite reruns. Эта таблица — контракты
будущих испытаний, не результаты. **16/16 cases NOT RUN.**

## Общие preconditions для каждой строки

Все I01–I12 из isolation contract получили независимый PASS на том же VM GUID/
config/assets и отдельный USER GO. Официальный exact source audit закрыл режим
startup, endpoint overrides, credentials и disabled children. Нет hosted config,
реальных keys или tunnel_id. Только внутренняя guest loopback-лаборатория.
Нельзя угадывать CLI flags: точные argv/config schema и порядок startup нужно
получить из проверенных v0.0.16 sources и offline CLI docs и приложить к новому
gate. Если mode требует реальную auth, source defaults нельзя направить к
fixture или появляется обязательный внешний component — соответствующий case
BLOCKED, без запуска и без обхода launcher hold. Это существенный незакрытый
execution detail, поэтому текущий design/test plan PARTIAL.

В guest новый disposable checkpoint для каждого case либо доказанная полная
очистка с повторным preflight. Fixture baseline: literal `127.0.0.1`, OS-selected
owned ports, pinned process identity, no DNS and no remote upstream. `.invalid`
в CONNECT/SOCKS authority служит только строкой fake protocol; её не отправляют
в resolver. IPv6 case использует `::1` отдельно. Фиктивные HTTP/HTTPS control-plane,
MCP, OAuth/Harpoon endpoints реализуются только в мере поддержанного native mode;
фиктивные сообщения не содержат реальных credential. Если потребуется локальная
TLS trust fixture, отдельная future TASK одобрит её disposable test-only trust
chain без изменения host trust store; её keys не публикуются. Сейчас CA не создана.

Независимый oracle: passive guest process/socket/DNS observer + fixture transcript
+ host/hypervisor config continuity. Client stdout и Python/reference guard не
являются oracle. Сначала отдельный synthetic witness связывает oracle с owned
loopback connect/refused connect, controlled child и намеренно неучтённым owned
loopback dial. Наблюдатель обязан увидеть все эти события. Это проверка coverage,
не тест внешнего egress. Не добавлять public-IP/DNS canary.

## Cases

В колонке evidence: R означает общий receipt contract, PC — process census,
NET — независимый network-attempt trace, FX — fixture transcript. Для каждой
строки сохранять источник/хеш native argv и исходного checkpoint.

| ID | Fixture / действие | Независимый oracle и expected result | STOP / evidence / cleanup |
|---|---|---|---|
| N01 bytes & offline startup | В выключенной VM и после boot сверить EXE 22,591,488 B / SHA-256 `4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571`; только после preflight выполнить approved local version/startup mode | Host+guest asset hashes; cached version не засчитывается как native вызов. Ни одного неизвестного процесса/соединения | Mismatch → не запускать; R+PC+NET; stop owned subject, OFF |
| N02 HTTP CONNECT happy path | Native с explicit HTTP proxy к своему CONNECT fixture, fake origin внутри guest | FX видит CONNECT/correlation ID; NET показывает ровно одобренный loopback route, origin не достигается в обход fixture | Real endpoint/unknown dial → STOP; R+FX+NET; terminate/reap/close |
| N03 SOCKS5 compatibility | Одобренный explicit SOCKS5 URL и отдельный local SOCKS fixture | Проверить native validation: WEB_10 ожидает rejection HTTP(S)-only до dial; не называть отказ неисправностью. Если accepted — исследовать protocol/route. Callback adapter — отдельный case/source | Unexpected route или невозможно безопасно задать scheme → STOP/BLOCKED; R+FX+NET |
| N04 refusal | Заранее зарезервировать и закрыть owned proxy port, origin оставить слушать | NET видит только отказ к proxy; FX origin не получает direct; retries в пределах source-derived budget | Второй route/unknown endpoint → FAIL+STOP; R+NET+FX; OFF |
| N05 timeout | Proxy принимает, не отвечает, bounded lifetime | NET/FX подтверждают timeout phase и конечную остановку/ошибку; нет direct fallback | Budget exceeded или event loss → STOP; R+FX+NET; close stalled sockets/reap |
| N06 abrupt close | Proxy reset/EOF на handshake и после CONNECT отдельно | FX фазовые метки, NET/PC; нет bypass/reconnect к origin напрямую | Attempt direct → FAIL, даже если VM сдержала; close all case sockets |
| N07 retry policy | Scripted 429/503/Retry-After на fake control-plane/health | FX timestamps/attempt count сравнить с audited policy и общим deadline; ответы не содержат реальных URLs | Unlimited retries/late child → STOP; R+FX+NET+PC; fresh checkpoint |
| N08 policy loss | При active/idle соединении изменить **guest synthetic** proxy config/health, если native поддерживает reload | NET различает established flow vs new dial; не допускается переключение на default/direct | Reload unsupported → BLOCKED соответствующей ветви, не симуляция; R+before/after policy hashes+NET |
| N09 env override | По отдельности и конфликтно HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY/NO_PROXY=* и lowercase variants — только guest synthetic ports/authority | Независимый allowed proxy и forbidden own-loopback listener; NET сравнить с audited precedence. No local DNS. Полный subcase ledger, не выдать 1 case за все combinations | Unexpected fallback/bypass → FAIL+STOP; R+redacted env names/values(local-only)+FX+NET |
| N10 redirects | Local 30x same-origin/cross-synthetic-origin/scheme change/redirect loop; все destinations owned loopback или строка `.invalid` без resolution | FX+NET показывают route каждого hop; секреты/headers не утекли; redirect bound соблюдён | Unmapped hostname → остановка до resolver либо BLOCKED режима; не разрешать внешний fetch; reset fixtures |
| N11 alternative route/direct attempt | Fake response/config указывает **собственный запрещённый loopback listener** вместо proxy; отдельно passive intent observation default destinations | NET должен обнаружить unregistered direct attempt, даже если FX ничего не записал. Попытка = FAIL client policy. Нельзя придумывать реальный public destination для canary | Любой неожиданно инициированный nonloopback/DNS intent → FAIL/STOP внутри изоляции; R+NET. Если mode не допускает безопасный stimulus — BLOCKED |
| N12 DNS | Passive resolver trace с mapped literal endpoints; при разрешённом source branch только private fake resolver внутри guest | Выявить даже отклонённый query/lookup intent, включая children. Не настраивать host DNS; отсутствие packets не равно отсутствию lookup | Любой real query target/неполный resolver oracle → STOP/BLOCKED; R+NET+PC; remove only synthetic guest state |
| N13 IPv6/UDP/other transport | Owned `::1` endpoint, own-loopback UDP witness только для проверки observer; native branches — лишь source-confirmed modes | Отдельные process/dial/DNS/UDP/IPv6 records. No NIC означает containment всего guest, а не доказательство отсутствия попыток | Unknown transport, QUIC/helper outside approved modes → STOP/BLOCKED; R+NET+PC |
| N14 children | Approved synthetic local STDIO child; наблюдать весь native tree. Cloudflared disabled и отсутствует в input package | PC independent create/exit/parent identity; каждый approved hash/argv известен, zero unexpected children, NET включает descendant | Browser/Cloudflared/unapproved helper → STOP, не запускать “для проверки”; R+PC+NET; reap tree inside guest |
| N15 observer/config failure | Controlled stop observer и отдельно offline config digest drift **без создания NIC/внешней edge**; сначала witness, потом только separately approved native case | Host-side stop owned VM, no auto-resume; missing evidence остаётся inconclusive/BLOCKED, не PASS subject | Host stop unavailable → не начинать case; R+host state/change timestamps; OFF/quarantine |
| N16 cleanup & restore | После stop/reap проверить endpoints/processes, power-off, export sanitized results, возврат clean checkpoint и новое readback | PC children=0; owned fixture listeners=0; config/media/disk identities соответствуют; guest/host evidence согласовано | Residual PID/flow/unknown checkpoint → quarantine, не следующий case; R+cleanup receipt; повторный preflight до другого запуска |

Для N04–N10 должны различаться отказ **до syscall**, попытка и отказ ОС,
установленный socket и данные FX. Даже корректно изолированная VM не исправляет
некорректный fallback клиента. Для неактивированных OAuth/Harpoon/Cloudflared
ветвей писать NOT RUN; покрытие startup одной ветви не закрывает все компоненты.

## Завершение будущего испытания

Сумма PASS/FAIL/ERROR/BLOCKED/NOT RUN и число **настоящих native executions**
ведутся отдельно от числа subcases/fixtures/witnesses. Первые FAIL и исходные
hashes сохраняются; rerun только после объяснённого изменения/гипотезы.
Никакого `REAL CLIENT FAIL-CLOSED VERIFIED` по одному happy path, VM config,
22/22 reference или успешному CONNECT. V2Ray remote route и обычный Chat E2E
вообще не входят в этот offline gate и остаются NOT VERIFIED.
