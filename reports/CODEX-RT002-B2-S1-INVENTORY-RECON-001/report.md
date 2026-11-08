# RT-002/B2 S1 — reconciliation двух FAIL инвентаризации

**TASK ID:** `CODEX-RT002-B2-S1-INVENTORY-RECON-001`  
**Исполнитель / дата:** Codex 007 / 2026-11-08  
**Итог пакета:** **PARTIAL** — S1 AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING; S2 regression 1 FAIL сохранён.  
**Режим:** STRICT OFFLINE / LOCAL ONLY / NOT PUBLISHED.  
**Assigned base:** `main@87edc6c1537722981b5016fa2c33b8bc59cc580c` (№541) из постановки; Git identity не проверялась, Git/GitHub не использовались.  
**Источник истины:** before/final snapshots, exact-byte SHA-256 manifest и raw test evidence.  
**Граница:** авторская проверка узкого S1 repair; не independent VERIFIED, не S3a predecessor acceptance, не S3b/Stage6 DONE или live/paid GO.

## Причина и исправление

Исходные два FAIL H23 воспроизведены до правок полным существующим guarded S1
runner: **69 tests, 67 PASS / 2 FAIL, exit1, ERROR/SKIP=0, guard0**.
Сохранены `evidence/red.stdout.txt`, stderr, result, полный unittest log,
execution argv/exit и исходный source snapshot.

1. Receiver-анализатор ранее видел импорт urllib, urlopen и getattr(send) как
   UNKNOWN, но не замечал настоящий вызов инъектируемого transport.send.
2. Endpoint-flow net не различал два literal metadata поля Provider и send URL.

Изменён единственный рабочий файл `test_rt002_s1_routes.py`. Production, S2,
S3a, Run Store, transport/UI и network settings не менялись.

- Семь LLM POST и один OAuth POST сохранены с прежней кратностью в публичном
  `EXPECTED_SEND_SITES`, который импортирует S2. Новых approved routes нет.
- Полный inventory test сравнивает `EXPECTED_PRODUCTION_SITES`: прежние восемь
  **плюс четыре** reviewed constructions; дополнительные UNKNOWN не фильтруются.
- Launcher urllib import/urlopen получили `LOCAL_HTTP_ORIGIN` после проверки
  HOST, port sources, всех текущих callers и fake GET executions.
- getattr(send) в execute_request — CAPABILITY_CHECK; настоящий await send —
  **POTENTIAL_LLM**, видимая обязательная граница будущего S3b, не safe exemption.
- Metadata exception охватывает ровно два keyword literal nodes в frozen
  Provider construction. Schema, initialization/default checker и endpoint-field
  consumers защищены reviewed AST pins и полным reference census.
- Новые неизвестные `.send`, aliases, getattr, callers и metadata endpoint reads
  продолжают давать RED. Pins — константы после source review, не runtime refresh.

Подробная таблица old/new identities, callers, endpoint origins и ограничений:
[route_reconciliation.md](route_reconciliation.md).

## Источники и зависимости

Адресно прочитаны действующая карточка, №08, №20 §5а, записи S1/S2/H23 в №21,
Stage6 №37, №36.1 и №36.3, строка S1-INVENTORY-DRIFT в №05, WEB25 H23 review
и предыдущий amendment_request_s1. Ограниченная source+author-evidence приёмка
S3a H23 не подменяется independent execution этой TASK.

Изучены текущие launcher _get/_already_running/_self_test/run_web_alarm/main,
standard_port/standard_launch/_profile/load_launch и их references; Provider,
BUILTIN_PROVIDERS, endpoint-field consumers, ModelCards init/run_check/default
checker; ChatTransport/execute_request и OfflineTestAdapter/_FixtureTransport.
Reviewed node/source/line/hash — `evidence/reconciliation_pins.json`.

Профиль — Ultra 36.3; affected UL-I: UL-I10 isolation, UL-I11 exact
collection/source/oracle, граница будущей защиты бюджетных physical routes.
Production/server/UI не менялись: UI smoke не требуется для test-only repair.

## Полные прогоны и отрицательные проверки

Python проекта **3.12.10**, Windows. Точные argv, exits, stdout/stderr, result/log
и source hashes сохранены в evidence. Основной selector запускает именно
существующий S1 main без positional selections, с неизменённым MANIFEST **69**:

```powershell
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/collect.py s1
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/collect.py checks
.venv/Scripts/python.exe -B -X utf8 test_rt002_s2_budget_policy.py
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S1-INVENTORY-RECON-001/run_s3a.py
```

collect.py — parent capture; run_guarded.py добавляет secret-read guard, затем
runpy вызывает исходный test_rt002_s1_routes.py как __main__. Network/process/
filesystem guard самого S1 устанавливается до runtime imports. Не unittest
discovery, не partial selection, не подмена MANIFEST/gate или collectors.

| Слой | Фактический результат |
| --- | --- |
| Исходный RED S1 | 69: 67 PASS / 2 FAIL; exit1; ERROR/SKIP/guard0 |
| Финальный exact S1 | **69 PASS; FAIL/ERROR/SKIP=0; gate PASS / exit0; isolation/evidence problems0; selected=null** |
| Дополнительные checks | **23 PASS** = 18 source mutations + nominal/whitespace control + 4 fake-execution checks; exit0, SKIP/guard0 |
| Oracle weakening: ignore unknown dynamic.send | 23: 1 FAIL, exit1; требуемый RED |
| Oracle weakening: trust launcher without proof | 23: 3 FAIL, exit1; требуемый RED |
| Oracle weakening: ignore endpoint host literals | 23: 1 FAIL, exit1; требуемый RED |
| Guard controls | Socket, DNS, credential environment и credential file заблокированы до I/O; 4/4 expected controls; exit0 |
| S2 exact core regression | **73: 72 PASS / 1 FAIL; ERROR/SKIP/guard/evidence0; gate FAIL / exit1** |
| S3a regression | **35 PASS**, ERROR/SKIP0; exit0; unexpected guard denials0; source unchanged |
| Compile/syntax | S1 и package helpers AST parse + compile без execution/pycache; evidence/syntax.json |
| Source scope | Из 203 baseline source/CMD files один разрешённый S1 изменён, **202 byte-identical** |

Все шесть pinned RAW fixtures найдены и SHA/bytes проверены существующим S1
gate и адресной package проверкой: `evidence/pinned_fixtures.json`. RAW content
в публикуемый пакет не копировался. Точный baseline MANIFEST 69 сохранён.
Не складывать повторные/перекрывающиеся runs в общее число уникальных tests.

18 mutations: дополнительный LLM POST; OAuth POST; client method alias; getattr;
external HOST; external health caller; metadata literal, превращённый в call;
metadata field как URL unknown receiver; indirect send из готового providers
словаря в catalog без нового endpoint literal; второй physical send в execute_request;
новый unknown transport, его alias/getattr; новый execute_request caller;
новый launcher _get caller; новый run_web_alarm caller с URL/userinfo вместо
порта; удаление port validation; дополнительный metadata literal вне reviewed
construction. Каждая запускает **два настоящих inventory/endpoint oracle methods**
с in-memory source; требуется testsRun=2, ERROR/SKIP=0 и хотя бы один FAIL.
Raw inner failure/traceback — `evidence/checks.result.json` / stdout. Внешние
negative checks PASS означают доказанный inner RED; weakening controls отдельно
доказывают, что отключение защиты делает сами проверки красными.

Четыре fake-execution checks: реальные launcher _get и обе его caller functions
с fake urlopen; обе URL-ветви run_web_alarm с fake server/locks; port source
отказы без sockets; ModelCards default checker refusal и отдельный Ordinary
Chat injected memory transport. Первый и второй пункты объединены одним check;
итого четыре метода. Сети, HTTP listener, browser, OAuth или paid model не было.

## Сохранённые промежуточные ошибки

- Первый новый helper отказал на совпадающих basenames root/server.py и
  web_alarm/server.py. Исправлено сохранением relative module paths в in-memory
  source map; оригинальный scanner scope не изменён. `checks_initial.*` сохранены.
- Первый S1 после реализации: 69, 2 FAIL / 1 ERROR. AST pins были рассчитаны
  системным Python 3.13, а profile использует 3.12; secret wrapper также запрещал
  synthetic OAuth fixture. Исправлены pins на проектном Python, inherited secrets
  удаляются без чтения, разрешена только точная строка s1-dummy-credentials.
  `s1_first.*` и промежуточный source snapshot сохранены.
- Первые extra checks: 17, 13 FAIL / 1 ERROR. Inner module fixtures делали SKIP;
  введены правильное isolated flag и обязательные testsRun=2 / SKIP=0. Исправлен
  ошибочный test enum SUCCESS → существующий COMPLETED. `checks_first.*` сохранены.
- Промежуточные 69/69 S1 и 17/17 checks сохранены как intermediate; следующий
  bounded набор 22/22 сохранён как before_final_review. Финальный набор — 23.
- Промежуточный S2: 71 PASS / 2 FAIL. Ошибка route_registry, внесённая расширением
  EXPECTED_SEND_SITES, исправлена в пределах S1 сохранением прежнего публичного
  контракта; полный inventory по-прежнему проверяет все 12 constructions.

## Оставшийся FAIL S2 и STOP границы

`IsolationTests.test_no_production_module_imports_the_policy_yet` запрещает импорт
policy любому module из s1._production_modules(), кроме самого policy. Он видит
OFFLINE `ultra_budget_ledger.py:25`, намеренно использующий S2. Ledger и S2 test
уже присутствовали в before baseline и не изменены; AST _production_modules
тоже совпадает до/после. **Source-level причина существовала до правок S1.**
Отдельный S2 baseline до начала правок не запускался; не заявляется обратное.

Этот FAIL не скрыт исключением ledger из scanner, monkeypatch S2 или новым
production route. S2 WRITE отсутствует, поэтому исправление остановлено.
Требуется [отдельный AMENDMENT](amendment_request_s2.md). До него пакет честно
PARTIAL; зелёный S1 не означает общий S2/S3b predecessor PASS.

## MANUAL ENGINEERING REVIEW

**Проверенные ветви.** Сопоставлены Request→urlopen, все пять _get callers,
обе ветви run_web_alarm и замкнутая main/profile/port цепочка; начальный host
сверен AST pin и fake full_url. capability lookup в Ordinary Chat отделён от
настоящего awaited send; nested owner и multiplicity сохраняются. Metadata
construction отделена по AST identity, без host-wide/file-wide allowlist.
Оставлены receiver-independent endpoint net, неизвестные stacks/imports,
alias/getattr/stream/wrapper tests и исходный exact gate.

**Рассмотренные альтернативы.** Исключить launcher/model_cards целиком либо
объявить UNKNOWN безопасным — отклонено. Сопоставлять только строки или URL —
отклонено из-за alias/multiplicity/reparenting. Выбраны fail-closed AST subtree
pins и полный reference census; benign AST edits требуют осознанного повторного
review, whitespace/line changes не мешают. Публичный S2 inventory восьми
утверждённых routes сохранён, полный S1 набор не урезан.

**Проверка качества тестов.** Изначально найденные module SKIP и Python-version
hash mismatch не замаскированы. Дополнительный oracle вызывает реальные два
test methods, проверяет count/error/skip и сохраняет actual failure chain.
Анализ cache keyed by полные source bytes и module identity, не путём: мутация
не получает старый PASS. In-memory mutations не исполняются как runtime code.
Три weakening controls показывают чувствительность к ослаблению новых ветвей.
При заключительном review добавлен случай indirect metadata send через уже
собранный providers dictionary. Явно закреплены _settings_version/catalog, а
reference census включает enclosing owner scope, чтобы перенос statement в
другую функцию не сохранял прежнее разрешение. Финальные 69/23 и weakening
controls исполнены после этого усиления.

**Изоляция.** Wrapper удаляет inherited credential keys без возврата значения;
secret reads/assignments запрещены, кроме ровно synthetic S1 OAuth fixture.
Его чтения считаются отдельно (не user secrets). Network/process/filesystem
guard до production imports не менялся. S3a использует прежний strict early
guard; task-local worker path задаётся только in memory, тесты/ledger unchanged.
Все persistent writes — собственный пакет и разрешённый S1 source; тестовые
storage/result files — отдельный TEMP. Изменения пользователя не откатывались.

**Границы, гонки и безопасность.** Это static snapshot audit, не физический
pre-HTTP budget guard и не защита от одновременного hostile source replacement.
Pins рассчитаны для project AST Python3.12. LOCAL_HTTP_ORIGIN подтверждает
начальный URL; urllib proxies/redirects не запрещены production и не проверены
live. Arbitrary Python dynamic/config/plugin calls полностью не разрешаются
этим analyser. Authorized injected ModelCards checker также может быть будущей
physical boundary; default refusal не разрешает его live-включение. Для storage
recovery/concurrency использована неизменённая S3a regression35; новых durability
гарантий, policy defaults или protection S3b этот repair не добавляет.

## NOT RUN, OPEN, DOC IMPACT и сдача

NOT RUN: независимый rerun, S0, S2 optional provenance, full-repo/CI, browser/UI/
launcher live smoke, реальный HTTP/GigaChat/OAuth/paid, production integration,
S3b/S3c/S9. STANDARD/TEST CMD не запускались и не переключались; старый пустой
BAT не восстанавливался. Исходные CMD вошли в неизменный baseline.

Все OPEN/owners/следующие решения: [followups.json](followups.json).
Текущая TASK не назначает successor. Остаются H23 independent S3a execution,
Ordinary Chat policy/user decisions, RAW wire retention, adoption/upgrade,
durability/fencing и trusted NOT_SENT proof; repair S1 их не закрывает.

DOC IMPACT: этот авторский пакет и штатная механическая сдача собственной
карточки; №05/20/21/36/37, STANDARD, чужие verdict и архивы не редактировались.
SHARED DOC DELTA для WEB25 после публикации: S1 author69 PASS + 23 extra/18
mutations, 3 weakening RED; S2 full72/73 FAIL, separate amendment needed;
S3a author35 PASS unchanged. Не записывать self VERIFIED или Stage6 DONE.

Raw evidence безопасно минимизировано: home paths заменены на <USER_HOME>,
исходные bytes в private TEMP/task archive; hash mapping —
`evidence/sanitization.json`. Архивные RAW prompts/секреты не публикуются.
Manifest включает source и все package artifacts кроме самого manifest.
Авторская package check подтверждает полноту, hashes, fixtures, collection,
отрицательные результаты и scope; не является independent verdict.

После final package check выполняется только штатный finish с exact TASK ID.
ROTATED/exit0, HISTORY ID и readback фиксируются в finish_protocol.json/closeout.json.
БЛОК1 WAITING, БЛОК1.1 SUBMITTED / REVIEW PENDING; прежний snapshot и БЛОКИ2–4
сохраняются. Report после регистрации HISTORY не меняется. Публикация остаётся
за пользователем; прямая отправка в чужой чат не выполнялась.
