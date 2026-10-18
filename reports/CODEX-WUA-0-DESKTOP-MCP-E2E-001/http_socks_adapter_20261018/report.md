# AMENDMENT 07 — HTTP/SOCKS5 Compatibility & Fail-Closed Adapter Research

TASK `CODEX-WUA-0-DESKTOP-MCP-E2E-001` · Codex 007 · 18 октября 2026,
Asia/Yekaterinburg · координатор «Сервер WEB_10».

**Итог: PARTIAL / SYNTHETIC ADAPTER RESULT READY / AWAITING INDEPENDENT REVIEW.**
Найден и проверен локальный технический кандидат; установка/реальное подключение
и системная безопасность не объявлены. **LOCAL ONLY / GITHUB NOT YET VERIFIED.**

## Обязательные статусы

```text
HTTP INBOUND NOT VERIFIED
SOURCE AUDIT PARTIAL
ADAPTER REFERENCE TEST VERIFIED
NATIVE CLIENT FAIL-CLOSED NOT VERIFIED
V2RAY REMOTE ROUTE NOT VERIFIED
HOSTED TUNNEL NOT STARTED
ORDINARY CHAT E2E NOT VERIFIED
```

Дополнительно **SOURCE PACK BLOCKED**: full own source audit официального клиента
не выполнен без проверенного локального архива. Reference VERIFIED относится
исключительно к данному synthetic Python source/run; независимый review WEB_10
ещё предстоит. Никакого native-Go PASS из результатов адаптера не выводится.

## 1. Вход, полномочия и источники

Прочитаны действующие route 08→000→34→18→01, собственная карточка, профильные
19/23/36/36.1/36.2/37, AM05/AM06 и текущие независимые выводы WEB_10 в 34/19.
`rules_read.json` фиксирует 17 адресных Rule-ID/contract definitions; нормативные
источники этих правил не изменились. `document_route.json` и
`coordinator_findings.json` содержат byte fingerprints и адресные excerpts.

Координаторские записи сообщают bounded publication/source review AM05
(`2a263a6a75999228d542ce579048f65bb8058984`) и AM06
(`c060fdedeede9aa9535d1ca142db4d88496b1295`), plus exact-tag upstream findings.
Это прочитанное canonical evidence; **Codex Git/GitHub не проверял**. Старые
LOCAL ONLY внутри предыдущих отчётов относятся к моменту их сдачи; собственный
AM07 до пользовательского push также LOCAL ONLY. Работа Claude/LLM12 не затронута.

User AM07 разрешает только этот новый каталог, reference adapter и synthetic
loopback tests. Hosted, native networking, real API keys/tunnel IDs/OpenAI
endpoints, V2Ray/DNS/firewall/permissions/launcher/чужие TASK запрещены.

## 2. Gate A — существующий HTTP/mixed inbound

Сохранённый AM05 snapshot: 127.0.0.1:10808/10813, method-only SOCKS5 greeting на
10808 принят без authentication. Это не HTTP CONNECT или remote route proof.
GUI SOCKS/DNS/PROXY policy не доказывает loaded core/outbound.

**Текущий AM07 read-only snapshot:** V2RayN PID 18032 → sing-box PID 27008;
sing-box listen **127.0.0.1:10808 и 127.0.0.1:10814**. Исторический 10813 сейчас
не обнаружен. Через разрешённый CIM текущие `ExecutablePath` и `CommandLine`
недоступны (null), причина не установлена; доступа/прав не повышали. Поэтому
actual config argument/cwd/loaded bytes не прочитаны. Пустой список кандидатов
не означает отсутствие config у процесса.

**HTTP INBOUND NOT VERIFIED.** Нет достаточного доказательства, что действующий
10808/10814 — HTTP или mixed; ни одному из них не назначена схема http:// наугад.
Выбор remote outbound, active DIRECT/bypass и DNS/fallback **NOT VERIFIED**.
В AM07 не было live CONNECT, SOCKS greeting, DNS/HTTP probes или fault injection
на V2Ray. Evidence: `preflight.sanitized.json`, `preflight_attempt01.json`.

## 3. Gate B — официальный tunnel-client

Полная матрица — `source_audit.md`. Версия: official tag v0.0.16, commit
`5f99daabd4aa4a77049e6d81d54a0d8c18335397`. Локальный Windows EXE SHA-256
`4226bb74a72388147882881f29f79801b95e285d731a138071812e3aa6766571` сохранён
как input; заново не исполнялся. Matching commit string не build attestation.

WEB_10 independently exact-tag source review, записанный в 19/34, подтверждает:

- explicit proxy parser требует HTTP/HTTPS, SOCKS URL не допускает;
- explicit route задаёт fixed Go `http.Transport.Proxy`;
- global/component proxy layers существуют; main/secret control-plane и HTTP MCP
  применяют proxy, Unix transport имеет отдельную ветвь;
- optional Cloudflared может запускать самостоятельный EXE; callback HTTP proxy
  главного Go процесса не является его сетевой политикой.

AM06 embedded documentation говорит: explicit proxy overrides environment и
игнорирует NO_PROXY для affected targets; без explicit — HTTP_PROXY/HTTPS_PROXY/
NO_PROXY semantics. Полный exact-source граф OAuth/Harpoon/proxy-health/DNS/
redirects/reconnect/retries/fallback/ALL_PROXY и все defaults здесь **не установлен**.
Строгий process-wide запрет direct одним setting клиента **не доказан**.

`tunnel-client-runtime-source-v0.0.16.tar.gz`, expected SHA-256
`88953678325ffe650cc562bbd0b147e7e8e984b0527aa8b1647b02d6660ce9e0`,
не найден в проверенных dossier/Downloads/attachments. `source_pack_search.json`:
**SOURCE PACK BLOCKED**. Не скачивали GitHub/API/raw mirror и не заменяли bodies
исходников symbol names. Source→installed EXE correspondence остаётся OPEN.

## 4. Gate C — выбранный технический вариант

**Для AM07 выбран отдельный HTTP CONNECT → SOCKS5 reference adapter**, поскольку
готовый live HTTP inbound подтвердить нельзя. Он работает только в собственном
синтетическом стенде. Если позже будет подтверждён уже существующий пригодный
HTTP/mixed inbound, он предпочтительнее по числу компонентов. Сравнение —
`proxy_options.md`; устройство — `adapter_design.md`.

`adapter.py` — отдельный Python prototype, без CLI установки и live entry point:

- bind только 127.0.0.1 на выделенный fixture port;
- ровно один explicit loopback SOCKS endpoint; одна outbound connect строка;
- frozen exact allowlist 1–16 synthetic `.invalid:port`, reject real/IP/URL targets;
- destination передаётся SOCKS5 ATYP=3 domain bytes, локального DNS нет;
- только SOCKS NO AUTH; strict method/reply checks, finite total handshake deadline;
- при отказе/timeout/disconnect/protocol error операция закрывается, direct,
  alternative endpoint/retry/fallback отсутствуют;
- bounded headers/connections/chunks/byte budget/idle/hard lifetime/events,
  tracked sockets, non-daemon workers и cleanup;
- authorization/header/body содержимое не записывается в JSON/events/trace.

**Ограничение совместимости:** это CONNECT-only, не полный forward HTTP proxy.
Absolute-form HTTP GET/POST отвергается 405; нет SOCKS credentials, proxy TLS,
real destinations, production deployment/SLA, полноценного TCP half-close.
CONNECT stream opaque, TLS validation остаётся native client. Следовательно,
нельзя подключить им все native HTTP/OAuth/Harpoon/health paths без дальнейшего
source/transport audit. Ни launcher, ни live V2Ray к нему не подключены.

## 5. Gate D — фактические синтетические тесты

Python 3.12.10 x64, Windows 10.0.19045.0, только stdlib. Финальный запуск:

```text
36 collected / 36 executed
36 PASS / 0 FAIL / 0 ERROR / 0 SKIP
exit 0
70 socket connect attempts, все literal 127.0.0.1 и owned fixture ports
0 isolation violations, 0 remaining ports, 0 worker leaks
0 unexpected adapter/fixture errors; 1 classified expected peer reset
```

Evidence — `attempt03_results.json`; commands/revisions/history — `execution.json`.
Матрица `checks.json`: **31 evidence rows — 19 PASS / 7 BLOCKED / 5 NOT RUN**;
это не 31 сетевой тест и не замена 36 adapter cases.

| Группа | Фактическая проверка |
| --- | --- |
| Success | Реальный двусторонний echo через CONNECT+SOCKS; domain ATYP=3; origin physical peer совпадает с SOCKS forward local port |
| Upstream faults | Собственный bound/non-listening port, SOCKS REP refusal, method timeout/close, bad/truncated method и reply VER/RSV/ATYP/BND length; требуются fault markers |
| No fallback | Ошибки до origin, один upstream attempt; success→disconnect без reconnect; forbidden/IP destination не создаёт target dial |
| Environment | Upper/lower HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY только в test process; positive и refusal cases; decoy route не выбран, environment восстановлен |
| Resource/HTTP | Header size/count/body/duplicates/Host/method, capacity, absolute header deadline под continuous drip, idle/active hard duration, tunnel byte budget |
| SOCKS variants | Fragmented replies, valid IPv4/domain/IPv6 bound address; IPv6 dial не выполнялся |
| Quality | Намеренный local fault→direct только в отдельной mutant роли: обход обнаружен oracle, а не принят за правильный путь |

Финальный trace: driver **36**, adapter **22**, SOCKS fixture **10**, mutant **2**.
Один mutant→origin dial намеренно direct **внутри loopback**. Для настоящего
reference adapter direct/alternate route attempts **0**. Отсутствие connect у
всего компьютера не заявляется.

Python audit guard разрешает только IPv4/TCP, собственные динамические ports и
role edges; DNS/UDP/subprocess/ctypes/nonloopback запрещены до socket execution.
Это guard конкретного Python stand, **не OS egress isolation arbitrary Go EXE**.
Trace показывает API connect attempts, не packet capture. Positive proof также
использует echo и физические socket peers. Нативный tunnel-client не запускался.

### Первоначальные ошибки сохранены

`attempt01_results.json`: **31 = 29 PASS / 0 FAIL / 2 ERROR / 0 SKIP**, exit 1.
На header limit/overload Windows close с непрочитанным входом давал reset раньше
чтения 431/503. Отказ/изоляция были достигнуты, но protocol tests не прошли.
Это **REFERENCE PROTOTYPE DEFECT**, не дефект V2Ray/native клиента. Исходники этой
ревизии и hashes сохранены в `adapter_attempt01.py.txt`, `tests_attempt01.py.txt`.

Исправление: reply + write shutdown + drain максимум 8192 bytes/30ms, без logging/
forwarding. Exact HTTP assertions сохранены. Attempt02 **32/32 PASS** после
добавления env+refusal case; затем manual review расширил реальные triggers
absolute drip/hard duration и valid BND variants: attempt03 **36/36 PASS**.
Повторы только после изменений; исходные красные данные не стёрты.
Ранний assignment-copy codec helper error — отдельный HARNESS DEFECT в
`setup_attempt01.txt`, до любых adapter network tests.

## 6. MANUAL ENGINEERING REVIEW

Полный независимый от автоматического результата собственный анализ —
`manual_engineering_review.md`: Config-before-bind, HTTP reject paths, единственный
upstream connect, fragmented SOCKS/bound-address parsing, exception cleanup,
relay budgets/deadlines, bounded overload reject, actual peer oracle и deliberate
fallback quality control. Разобраны альтернативы, uncovered native paths и
несоответствие CONNECT-only полному HTTP proxy. Независимую приёмку WEB_10 это
не заменяет; installation/system fail-closed не заявлены.

## 7. Сохранность и внешнее расхождение карточки

Новая запись только `http_socks_adapter_20261018/`. Production, чужие TASK, Claude/
LLM12, launcher, конфигурация MCP/V2Ray/OS не менялись нашими действиями. AM05/AM06
исходные материалы сохранены. Live Codex config SHA **до/после именно AM07**:
`2a1745afe7818f69f564ea36d58f17adb1653edec9e711e3e1c8f8ee97565aa2`;
launcher hold `HOSTED_TUNNEL_ON_HOLD_BY_USER` не снят.
Config уже отличался от AM06 hash на момент исходного snapshot AM07; источник
изменения между этапами не устанавливался и исторический config не восстанавливался.
Первый final-artifact validator ошибочно сравнил его с hash AM06 вместо нового
baseline: сохранён `validation_attempt01.txt` / `validator_attempt01.py.txt` как
**HARNESS DEFECT — stale expected hash**. Проверка исправлена; это не изменение
config в AM07 и не ошибка сетевых тестов адаптера.

При сверке **96/97** защищённых inputs совпали. Единственное обнаруженное
расхождение — `Документация/000_Задачи Codex.md`, SHA изменился с
`953a03cf8091a0589da1cdae4d48dfb22d3f072a615435648c01f2c7441fabdf` на
`54164055d772a4b26870c4b0ca5e6688e232ec235820cd2355e8f03cc0ad49f6`.
В текущем БЛОКЕ 1 теперь **CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001** вместо
MCP TASK. **Карточку Codex агент не редактировал**; автор/механизм изменения не
установлен. Она не восстановлена, не ротирована, чужая задача не принята.
Продолжено только прямое user AM07 в собственной папке. `input_drift_event.json`
и `integrity.json` сохраняют evidence; утверждать «все inputs неизменны» нельзя.
Пользователю/координатору нужна отдельная сверка назначения карточки.

## 8. Публикация и следующий разрешаемый gate

`manifest.json` перечисляет безопасный комплект с byte SHA-256, включая original
red snapshots/evidence. Raw private configs/DB, passwords/headers/payloads не
копировались. `.gitignore` читается только как обычный файл; реальный Git index,
global excludes и GitHub completeness **не проверены**. Git/GitHub calls **0**.
Пользователь публикует **только AM07 папку**, проверив точный состав; расхождение
карточки не следует автоматически включать в этот результат.

Следующий шаг WEB_10: independently review опубликованные sources/trace/hashes;
получить exact source archive разрешённым каналом и закончить whole-client source
audit. Затем подтвердить actual loaded V2Ray inbound/outbound/DNS разрешённым
read-only способом, не угадывая по GUI/старому порту. Native faults — только после
доказанной OS/process isolation и отдельного gate. Установка реального adapter,
изменение launcher, hosted и ordinary Chat остаются отдельно закрытыми этапами.

**DOC IMPACT / SHARED DOC DELTA:** общие документы не менялись. Координатору после
review можно зафиксировать AM07: synthetic adapter 36/36, first red retained,
HTTP inbound/source pack/native/remote route unresolved; current 10814 отличается
от historical 10813; отдельно замечено внешнее ошибочное назначение в Codex card.
Этот отчёт пользователь передаёт WEB_10; independent acceptance не объявляется.
