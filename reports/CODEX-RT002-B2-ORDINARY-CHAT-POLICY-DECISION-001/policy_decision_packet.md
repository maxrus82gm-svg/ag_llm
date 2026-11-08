# Ordinary Chat — пакет бюджетных решений для владельца проекта

**TASK:** `CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001`  
**Автор / дата:** Codex 007 / 2026-11-08. **RESULT READY — DECISION PACKET**, независимая проверка WEB26 ожидается.  
**Режим:** STRICT OFFLINE; только анализ. Production, tests и нормативные документы не изменены.  
**Approval:** частично согласован проектный принцип Workspace envelope (CHAT-A01); **A/B/C и абсолютные числа не утверждены**.  
**Activation:** OFF. Этот документ и JSON — предложения, не действующая конфигурация и не разрешение S3b/live.

## 1. Подтверждённое текущее состояние

| Объект | Подтверждённый факт и граница |
| --- | --- |
| S1 | WEB25 independently: 69/69 guarded + 23/23 reconciliation PASS; семь LLM POST и один OAuth POST сохранены, Ordinary injected send виден как POTENTIAL_LLM. Не полное динамическое runtime enforcement. [S04, S17] |
| S2 | WEB26 independently: 73/73 core + 47/47 import quality PASS; weakening RED 43/1/1. Pure library, не production HTTP guard. [S05] |
| S3a | **Последующая** WEB26 independent CI acceptance: Actions 42498405794, 35/35 ledger + 51/51 Run Store PASS, три expected RED 2/1/9, guard 6/6. Bounded OFFLINE predecessor принят; старое «independent NOT RUN» в H23/H25 историческое. [S06, S07] |
| Ordinary Chat | Общий text core с injected ChatTransport; текущий адаптер fake-only. Route/role ordinary_chat и scope ORDINARY_CHAT_SESSION **отсутствуют** в S2. Калибровки Ordinary Chat нет. [S08, S12–S16] |
| Production budget enforcement | S3b не реализован. Общий durable ledger существует, но его наличие не защищает физический HTTP. S3c/S9 и Stage7/live остаются HOLD. [S01–S03] |

Назначенная база: main@90ecf12e76bb48ff7fe1e08cc94d4b764f8d8858. Git/HEAD не
читались. Четыре ключевых source pins S1/S2/S3a совпали с independent reviews
(raw SHA либо ровно CRLF→LF для CI pins); [source_preflight](evidence/source_preflight.json).
Факты о CI взяты из сохранённого review/independent_runs, а не из нового HTTP
запроса. Доступность Actions/артефакта сейчас не перепроверялась.

**Согласовано в этом чате:** один общий лимит Ordinary Chat на Workspace с
теми же пределами, что у выбранной session, без умножения бюджета через новые
Chat. [Дословное согласование CHAT-A01](chat_amendment_01.md). В контракте ниже
это L для обязательств и N для attempts; пределы одного запроса остаются
пределами одного запроса. Реализация двух уровней сейчас отсутствует.

## 2. Evidence и происхождение чисел

Полный адресный [реестр S01–S27](evidence/source_registry.json) содержит пути,
SHA-256 и точные строки/символы. Основные документы: №20 §5а/§14 (S01), свежая
запись №21 (S02), №37 Stage6/7 (S03), independent S1/S2/S3a reviews (S04–S07),
код policy/ledger/core (S08–S15). [Расчётная выписка](evidence/calibration_facts.json)
получена AST-чтением S2 literals и арифметикой; тесты/production не исполнялись.

В S2 embedded dataset **342 строки / 42 run locators / 340 строк с известным
prompt usage**; dataset SHA-256:
`8a3ea10b75280ece550138af9a912b161997e17f5f3f17c894686961babf90ce`.
Это производные числа прежних агентских/Compressor запросов, не RAW prompts.
**Ordinary Chat rows = 0**, включая модель Ultra: другая роль/форма тела не
становится Ordinary-профилем от совпадения названия модели. [S09, S18]

| Legacy model / profile | n | Минимум bytes/(prompt+precached) | Дивизор с margin 10% | Вывод |
| --- | ---: | ---: | ---: | --- |
| GigaChat-3-Ultra / executor | 203 | 4.5184 | 4.1076 | Только legacy executor evidence |
| GigaChat-3-Ultra / planner | 99 | 4.4426 | 4.0387 | Только legacy planner evidence |
| GigaChat-3-Ultra / dredd | 37 | 2.4772 | 2.2519 | Только legacy verification evidence |
| GigaChat-3-Pro / compressor | 1 | 6.1322 | Не usable profile | n<5 уже в прежнем анализе; margin не заменяет данные |
| Любая модель / ordinary_chat | **0** | **Неизвестен** | **null / UNCALIBRATED** | Нет основания разрешить production send |

Legacy leave-one-out: без margin — по одному underestimation в трёх крупных
группах; при 10% и 20% — ни одного в этих наблюдениях. Это не статистическая
гарантия на новом model/role/template. Простое bytes/4 недооценивало 24 dredd
наблюдения, worst actual/estimate ≈1.6147. Все 340 обучающих строк здесь имеют
известный precached; два неизвестных prompt не становятся нулевыми. [S08–S09, S18]

Legacy S2 A/B/C — **старые кандидаты, не defaults**:

| Legacy | request bytes | input est cap | RUN liability | RUN attempts | Защищённый Final Audit reserve / attempts |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 262144 | 48000 | 160000 | 24 | 40000 / 2 |
| B | 524288 | 96000 | 240000 | 32 | 48000 / 2 |
| C | 1048576 | 200000 | 480000 | 48 | 64000 / 3 |

Эти legacy-кандидаты останавливали тяжёлые записанные RUN в mock replay;
нормальные legacy greetings/benches проходили. Это **не** Ordinary Chat replay.
Ни один legacy protected reserve не покрывает самые большие R-029/R-030
Final Audits после исчерпания work-пула: по divisor2.2519 и output2048 нужны
**75559 / 78211** liability tokens. Этот факт запрещает переносить Ordinary
лимиты на агентскую проверку или уменьшать её reserve. [S09, derivation JSON]

## 3. Матрица A/B/C и рекомендация

Ниже **новые числовые предложения**, рассчитанные как более узкие envelopes
от legacy-кандидатов. Уровень доверия: высокий к арифметике/происхождению,
**низкий к пригодности для реального Ordinary Chat**. Данных о его длине,
стоимости, tokenizer/template overhead и поведении пользователей здесь нет.

| Предлагаемый параметр | A — консервативный | B — сбалансированный | C — исследовательский |
| --- | ---: | ---: | ---: |
| Максимум final wire UTF-8 bytes | 65536 (64 KiB) | 131072 (128 KiB) | 262144 (256 KiB) |
| Максимум оценки входных tokens | 16000 | 32000 | 64000 |
| Максимум body.max_tokens / output reserve | 1024 | 2048 | 4096 |
| Session liability L | 80000 | 120000 | 240000 |
| Session attempts N | 12 | 16 | 24 |
| **Общий Workspace Ordinary envelope** | **L=80000, N=12** | **L=120000, N=16** | **L=240000, N=24** |
| Одновременных in-flight на один Chat | 1 | 1 | 1 |
| Margin / минимальный corpus на model+ordinary profile | 20% / 20 | 20% / 20 | 20% / 20 |
| Missing/unknown profile | DENY | DENY | DENY |

**CHAT-A01 утверждает равенство Workspace/session limits, а не абсолютные числа
этой таблицы.** Чаты делят общий envelope: два Chat не получают по L каждый
сверх W=L. Это не лимит всех LLM проекта: существующие RUN/MCP/Compressor
бюджеты остаются отдельными и не получают разрешения из Ordinary quota.

Происхождение **каждого** числа записано в [policy_candidates.json](policy_candidates.json):

- bytes = legacy A/B/C request bytes /4 — инженерное уменьшение начального
  envelope, не измеренный Ordinary optimum;
- input A=48000/3, B=96000/3; C=2×B=64000 (ниже legacy C/3);
- output=0.5/1/2×legacy verifier_final max_tokens2048. Это UX-гипотеза диапазона
  длины ответа, а не применение verifier profile к чату;
- session L/N = половина соответствующих legacy RUN L/N. Это самостоятельный
  новый grant; деньги/резерв существующего RUN никуда не переводятся;
- W=L и workspace attempts=N — согласованный принцип без new-Chat multiplier;
- inflight1 — предложение сериализовать один Chat, не результат benchmark;
- margin20% уже исследовался S2, но на других ролях; min_samples20=4×legacy5 —
  более высокий **предлагаемый** floor, не доказательство доверительной вероятности.

Все пределы применяются одновременно. При полном input/output reserve одна
UNKNOWN-попытка держит A=17024, B=34048, C=68096 tokens. Только по L помещаются
**4 / 3 / 3** такие попытки, а не обещанные пользователю 12/16/24 ответа.
Attempts cap — отдельное ограничение; фактический known usage может отличаться.

Иллюстрация B (не установленный profile): при 131072 bytes и legacy executor
divisor4.1076 exact-ceil **31910** input tokens; при условном divisor2.4 — 54614,
то есть request будет отвергнут cap32000; при HARD_BOUND assumptions — 131072,
тоже отказ. Поэтому один bytes cap не определяет число допустимых tokens.
Точные целочисленные сценарии A/B/C — поле illustrations_only в JSON.

**Рекомендация исполнителя: B для обсуждения**, с missing_profile=DENY и без
активации. A уменьшает пиковый input/output и grant, но чаще прерывает длинный
контекст; C увеличивает потенциальную экспозицию и объём RAW без доказанного
Ordinary workload. Приоритет минимальной экспозиции может обосновать A; C
имеет смысл только для отдельно контролируемого исследования после калибровки.

## 4. Предлагаемый route/scope/session contract

**Предложение, кроме явно согласованного CHAT-A01; не зарегистрированный route.**

Route=`ordinary_chat`, role/profile_key=`ordinary_chat`, scope=`ORDINARY_CHAT_SESSION`.
Никакого alias к executor/mcp_chat/planner/dredd. Text-only: tools, Full Read,
код, агентские mutations и скрытый Compressor не разрешаются этим маршрутом.
Запрос агента должен иметь собственный RUN и сохранять весь его Final Audit.

### Identity и один owner

Workspace ID → общий Ordinary budget epoch/grant → Chat ID → Chat session ID →
Turn ID → logical_call_id → provider_attempt_id. Общий authority — существующий
Workspace Run Store/ledger под тем же writer lock; Web/Tk — клиенты одного
сервиса, не отдельные кошельки или независимые counters.

Session создаётся доверенным core один раз на Chat/его budget lifecycle.
Scope ID — `oc:` + SHA-256 канонического набора Workspace/Chat/session IDs:
стабильные 67 символов, без абсолютного пути, UI-label или времени открытия.
Hash — идентичность, не secret и не право на отправку. Сервер проверяет полное
binding, принадлежность Chat к Workspace и текущий grant; UI/LLM их не выбирает.

Нужен versioned typed binding Ordinary вместо фиктивного run_id: workspace,
budget_epoch, chat, session, turn, logical_call и attempt, policy revision,
model/profile/serializer identity. Старый RUN binding сохраняется отдельно.
Выдавать session_id за run_id ради прохождения текущей схемы нельзя.

### Два уровня admission — согласованный принцип CHAT-A01

До commit одновременно проверить session и общий Workspace Ordinary epoch:
`session_committed + new_liability ≤ L`, `workspace_committed + new_liability ≤ W=L`,
и оба attempt ceilings N. Один atomic reserve учитывается на двух уровнях под
одним lock/commit, **не двумя независимыми ledger и не двумя физическими calls**.
Агрегат считает все Ordinary Chat/session/model и не теряет закрытые/скрытые Chat.
Повторное чтение того же attempt не удваивает списание. Параллельные разные Chat
делят остаток; отдельной гарантированной доли каждого Chat не предлагается.

F5, reopen, restart, повтор доставки события, смена UI/модели, скрытие/архив/удаление
Chat в интерфейсе не обнуляют счётчик и не выдают новый grant. Иные Workspace
имеют отдельные IDs/envelopes: это не обещание глобального счёта по аккаунту
провайдера или общей денежной границы всех Workspace. Клон того же Workspace
не является новым независимым кошельком; active-active пока не поддерживается.

### Lifetime, rollover, reset и policy changes — предложение U1/U4

Не вводить автоматический TTL/ежедневный reset. Session сохраняется до явного
контролируемого закрытия; закрытие запрещает новые sends, но не стирает долг.
Истечение UI lease/таймера — не expiration liability. Known usage накопительно
учитывается по физическим попыткам, UNKNOWN держится до trusted reconciliation.

Новая session/Chat не пополняет Workspace grant. Rollover/top-up — только явное
решение владельца с audit и перенесёнными известными/неизвестными обязательствами.
Новый L — абсолютный утверждённый envelope с учётом carry, а не L поверх уже
потраченного. Нельзя «закрыть» UNKNOWN и получить чистый budget epoch.

Активный session snapshot immutable. Уменьшение доступного grant/revocation
может остановить будущие sends, не переписывая старые attempts. Новая policy
revision требует отдельного контролируемого перехода: старые facts и estimate
не пересчитываются выгоднее, перенос carry проверяется до новой попытки. Если
commitment выше нового L — DENY. Повышение бюджета тоже требует явного grant.
Текущий ledger закрепляет policy revision на scope; такой переход **не реализован**.
Контролируемый переход закрывает прежнюю session для новых sends и при смене
frozen revision создаёт новый session ID; Workspace carry включает старые
session/attempts. Само появление нового ID не даёт дополнительных средств.

### Retry, model switching и receipts

Идентичная доставка reserve/event со старым attempt_id — replay, не право
снова отправить. Каждый physical retry получает **новый provider_attempt_id**
и новый резерв; старый UNKNOWN остаётся. Retry прежнего неизменного запроса
может сохранить logical_call_id и связь с прежним Turn; новый текст/модель/body
создаёт новый logical call и Turn. Никакого автоматического paid retry.

Model switch не меняет budget session/Workspace grant; профиль должен быть
разрешён для фактического provider model ID и Ordinary role. Нет профиля —
DENY, а не fallback на старую модель/роль. Уже отправленный attempt сохраняет
оригинальные model/policy/wire facts. История RAW, включение сообщения в контекст
следующего запроса и бюджетные обязательства — **три отдельных слоя**.

Trusted S3b owner допускает один свежий reserve→mark_sent переход к физическому
I/O, проверяет replayed/state/exact wire hash и не отдаёт UI расходуемый permit.
Mark_sent повторно, потерянный ACK или crash gap SENT→HTTP не дают auto-resend.
После рестарта orphan SENT держится консервативно; нельзя одновременно
использовать receipt из двух UI или threads. Эти guard свойства ещё предстоит
реализовать и independently проверить.

## 5. Предлагаемые profiles и эксплуатационные правила

В JSON `bytes_per_token=null`, samples Ordinary=0, active=false, user_approved=false.
Это намеренно **не** объект текущей policy schema. Требуется отдельный profile
на effective provider/model+ordinary role+wire/template/calibration provenance;
alias UI-model недостаточен. В registry шесть включённых GigaChat IDs, но
registration/enabled не означают calibrated/reachable/authenticated. [S08, S15]

Предлагаемый алгоритм профиля: нижняя огибающая фактических final-wire bytes /
(prompt+precached), делённая на 1.2, divisor округлять вниз до 4 decimals;
estimate — точный integer ceiling bytes/divisor, как текущий S2, без float
округления вниз. Принимать только проверенные пары bytes/usage с provenance,
distinct attempt IDs, минимум20 samples на модель/роль и разнообразием RU/EN,
истории/JSON/escaping/длины. Unknown cached usage исключать из обучающего набора;
runtime liability при null cache остаётся консервативной. Samples20 не задают
вероятностную гарантию, и 20 повторов одной строки не доказывают покрытие.

Никакого автоматического bytes/4 или переноса executor/divisor в Ordinary.
По умолчанию missing_profile=DENY. HARD_BOUND в S2 — **допущение** tokens≤wire
bytes, зависящее от chat-template/tokenizer overhead, не доказанная универсальная
граница. Предлагается его не включать; исключение требует отдельного явного
решения, ограниченного calibration scope и собственного budget/GO.

**Как получить первый corpus:** сейчас реального Ordinary evidence нет.
Можно использовать будущие разрешённые offline provider-usage artifacts или
проверенный matching tokenizer/template, если такие источники появятся. Любой
live calibration — отдельная TASK после проверки guard, с явным API/моделью/
лимитами/данными и USER network/paid GO; не обход через executor и не скрытый
«первый запрос». Samples20 можно накапливать из нескольких явно разрешённых
corpora/grants; это не разрешение 20 API calls и не обязанность уложить их в
один B session с N16. Synthetic samples проверяют механику, не валидность модели.

В request body обязателен positive max_tokens ≤ выбранного output cap; reserve
равен **целому запрошенному max_tokens**, даже если ожидается короткий ответ.
Измеряется весь final JSON UTF-8: system/history/current message и overhead,
не одни буквы пользователя и не sorted canonical snapshot вместо wire. HTTP
адаптер должен отправить те же immutable bytes; model context/output limits
и доступность API требуют отдельного подтверждения до live. [S08, S12]

Обязательства: RESERVED/SENT/UNKNOWN держат estimate+output; trusted known usage
уточняет тот же attempt. Если cached field отсутствует, validated usage хранит
precached=None и сохраняет max(known prompt, input estimate) плюс completion.
Явный raw precached:null — INVALID в текущем S2, а не ноль: ANOMALY/отказ,
сохранённое обязательство. Противоречивые terminals дают ANOMALY/max liability и запрет
новых sends. При estimate breach профиль следует карантинировать для Ordinary
Workspace epoch до review/recalibration, чтобы другой Chat не использовал уже
опровергнутый divisor. Это расширение существующего per-scope breach поведения.
В N временно входят RESERVED/in-flight и UNKNOWN наряду с известными attempts;
только proven NOT_SENT освобождает этот attempt quota. Его ledger events всё
равно занимают storage capacity; отмена UI не доказывает NOT_SENT.

MCP и Compressor сохраняют отдельные scopes/решения и по умолчанию не получают
allow из Ordinary. Автокомпрессия/repair/diagnostic — отдельные physical attempts
и учёт, не бесплатная часть чата. Full Read/S4 и Planner/Executor/Verifier/
Final Audit не ослабляются. OAuth — отдельный AUTH, не LLM token spend и не
универсальный обход; future guard связывает route сервером. Локальная LLM тоже
не получает автоматический unlimited режим: нужны model/profile/capacity
decisions и своё разрешение backend; текущий реестр не содержит local models.

Tokens/estimates/liability — не рубли. Тарифы, exchange rates, фактический billing,
модельные окна и money cap в этой OFFLINE задаче **не проверялись/не вычислялись**.
L ограничивает admission по зарезервированным/известным обязательствам, а не
гарантирует фактический счёт: empirical estimate может быть превышен. Более
высокий trusted usage сохраняется полностью, даже сверх L; новые sends блокируются,
profile уходит на review. Нельзя подрезать факты до reservation ради красивого остатка.
Timeout/deadline не ограничивают счёт провайдера и не освобождают резерв;
8 секунд/8192 bytes/128 output текущего fake fixture не предлагаются как реальные
defaults. Operational deadlines требуют отдельного согласования и fail-closed
таймеров при интеграции. [S01 §14, S08, S14]

## 6. Fail-closed сценарии и риски хранения

### Отрицательные сценарии для будущей приёмки (SPEC, не исполнены этой TASK)

| Сценарий | Требуемый результат |
| --- | --- |
| Нет route/profile/model/estimate, malformed policy/IDs | DENY до physical send; никакой подмены executor/mcp |
| F5/reopen/новый Chat/смена модели после исчерпания W | Тот же Workspace остаток, DENY без нового grant |
| Два Chat одновременно претендуют на последний остаток | Одна atomic двойная проверка session+Workspace; максимум один ALLOW |
| Два UI повторно предъявляют receipt / lost commit ACK | Не более одного I/O; replay не send permit |
| Cancel/timeout/disconnect после SENT | UNKNOWN/hold; повтор — новый attempt с новым reserve |
| Доказанный pre-LLM NOT_SENT | Release только из RESERVED **до durable SENT**, trusted owner; UI string/cancel не proof |
| Поздний trusted usage / duplicate / conflict | Тот же ID; идемпотентность либо ANOMALY без выгодного списания |
| Policy/model change с pending UNKNOWN | Старые facts/carry сохранены; grant не обнуляется |
| Исторический audit без ledger / missing/corrupt marker | DENY/adoption, не чистый нулевой счёт |
| Capacity/lock/fsync/replace/readback failure | Никакого physical LLM send; recovery без auto-resend |
| Backend API/diagnostics/export пытаются вернуть wire body | Минимальная metadata projection, body не выдаётся по умолчанию |
| Новый physical adapter/Checker/MCP/Compressor alias | Отдельный inventoried/guarded путь либо DENY |

Существующие S2/S3a имеют related bounded OFFLINE proof; новый route, два уровня
quota, новый binding и physical guard **не тестировались и не реализованы**.

### Риски и момент обязательного решения

| Риск / текущий факт | До S3b OFFLINE implementation | До реальных данных/live / существующих Workspace |
| --- | --- | --- |
| **RAW wire_utf8** в общем index и generations, plaintext JSON; повторный policy/body overhead | Допустимо оставить текущий формат только для synthetic disposable fixtures; зафиксировать границу, не подключать реальные prompts | USER data contract: содержание, read scope, diagnostics/export, backup, retention; предлагаем versioned immutable encrypted/managed artifact reference + digest/счётные facts, а не полный body в общем index. Нужны отдельные migration/tests; это пока не реализовано |
| **4096 events** на весь Workspace ledger, не Chat; **64 MiB** bound сериализованного Run Store JSON | Capacity failures должны иметь отрицательные guard tests, без reset/auto-free | Headroom/retention/compaction и migration должны быть приняты до использования истории, которую формат не выдерживает; ранний explicit DENY допустим, скрытый reset нет |
| **Historical audit**: initialize отказывается от непустого audit, даже если кажется «старым» | Можно ограничить новую TASK свежими synthetic roots | До adoption реальных existing Workspace — backup/read-only inventory, proven carried liabilities, versioned migration/rollback. Отсутствующий ledger не доказывает нулевой прошлый расход |
| **Engine source pin / policy revision pin** | Route/schema extension меняет engine identity; нужны fresh synthetic migration/compatibility tests и повторная acceptance изменённых версий | Старый marker нельзя переписать/удалить ради allow. Комментарий/route/source update тоже может сделать pin несовместимым |
| **Recovery / corrupt / missing facts** | Сохранить fail-closed semantics и 0 send на ошибке | Операторский recovery protocol с доказательствами; никаких optimistic frees и auto-replay |
| **Single owner / clone fencing** | Общий existing writer lock в одном root, без второго owner; два UI — один authority | Один активный Workspace owner. Active-active клоны/машины исключить до отдельного fencing proof; перенос только после остановки старого владельца и со всей identity/index/marker историей |
| **Trusted NOT_SENT / SENT gap** | Контракт и negative tests обязательны до guard acceptance | Proof формирует pre-HTTP owner, не UI/LLM; release только из RESERVED до durable SENT. Строка PROVEN_PRE_SEND_NOT_SENT сама по себе не evidence. Crash после durable SENT может удержать резерв без фактического HTTP — это допустимая консервативность |
| **Hostile rollback/power loss** | Сохранить bounded claims: process-crash tests не hardware guarantee | Hash/checksum не authentication; single-owner и backup/restore trust явно согласовать. Power-loss/TOCTOU/fencing не объявлять доказанными |

При N и максимальном bytes envelope сумма только wire bodies составила бы
A=786432 bytes (0.75 MiB), B=2097152 (2 MiB), C=6291456 (6 MiB); типично три
events на attempt дают 36/48/72 events. Это **арифметические сценарные envelopes**,
не прогноз traffic/store и не гарантия, что все запросы допустимы по token cap.
JSON escaping, policy copies, summaries, generations и backups добавляют объём;
late/conflict/NOT_SENT тоже добавляют events. Новые epochs не очищают 4096.

Нельзя просто заменить wire_utf8 хешем: нынешний replay восстанавливает request
из body и пересчитывает S2. Нужны versioned format/immutable reference, точные
счётные facts и migration proof; mutable ссылка на текущий текст Chat не годится.
Retention реального текста и способ управления ключами/backup пока не утверждены;
автоматическое удаление/compaction не предлагаются этой TASK.

Пустой audit сам по себе тоже не доказывает отсутствие всех прежних физических
вызовов: S1 исследовал legacy MCP send без Run Store accounting. Для existing
Workspace недостающие исторические facts обозначаются UNKNOWN/неустановленным
baseline, а не восстанавливаются выдуманными нулями. Поэтому первая допустимая
implementation TASK предлагается только на свежих synthetic roots; adoption
реальных данных требует отдельного доказанного начального состояния/решения.

## 7. USER APPROVAL REQUIRED — оставшиеся решения

**Уже согласовано, повторно не спрашиваем:** CHAT-A01, общий Workspace Ordinary
envelope равен выбранному session envelope, без new-Chat multiplication.
Остальные вопросы ниже — для решения **после** независимого review, не скрытые GO.

| ID | Короткий вопрос владельцу | Рекомендуемый ответ / варианты | Статус |
| --- | --- | --- | --- |
| U1 | Утвердить отдельные ordinary_chat route/role, ORDINARY_CHAT_SESSION и общий Web/Tk owner с долговечной Chat session? | **Да, text-only**, без alias к агентским ролям; inflight1/Chat. Либо уточнить contract до реализации | PENDING |
| U2 | Какой envelope взять за основу: A, B, C или свои значения? | **B как proposal**: 128KiB / input32k / output2048 / L120k / N16, W=L и workspace N=N. A для меньшей экспозиции, C только исследовательский. Все числа UNCALIBRATED | PENDING — B не утверждён |
| U3 | Принимать Ordinary profile только после отдельного corpus, с missing=DENY, margin20%, samples≥20 и без borrowing старых ролей? | **Да**. HARD_BOUND — только отдельное explicit exception/bench GO, не default. Нужны реальные matched usage или проверенный offline tokenizer; fake sample не calibration | PENDING |
| U4 | Запретить автоматический TTL/reset/rollover, менять grant/policy только явно с carry старых обязательств? | **Да**; F5/новый Chat/модель не выдаёт средства, UNKNOWN не исчезает. Иной календарный grant требует отдельной спецификации carry | PENDING |
| U5 | До отдельного решения по RAW storage/retention оставить разработку только на synthetic prompts? | **Да**; для real data рекомендовать versioned managed/encrypted body artifact, metadata-only diagnostics, согласованные access/backup/retention. Текущий inline body не считать уже разрешённым для real prompts | PENDING |
| U6 | Ограничить первую S3b TASK fresh disposable Workspace и single-owner; existing audit/клоны допускать только после migration/fencing решения? | **Да**. Это позволяет offline guard development, сохраняя HOLD на перенос настоящей истории | PENDING |

Выбор U2 не разрешает API/paid, не заполняет bytes_per_token и не регистрирует
route. Samples20 не выдаёт разрешение на двадцать запросов. Реализация и live
сценарий требуют отдельных назначений; пользователь может утвердить часть
пакета, оставив остальные пункты HOLD.

## 8. S3b READINESS — точные предпосылки и gates

| Gate | Состояние сейчас / требуемое действие |
| --- | --- |
| №20 §5а: independently accepted S1 + S3a для S3b; принятый S2 contract | **READY в прежнем bounded OFFLINE scope**, fresh S3a CI закрыла прежний independent OPEN. Не общее production разрешение |
| Ordinary policy/schema/binding/session/Workspace envelope approval | **HOLD**: только CHAT-A01 согласован; U1–U4 pending. Этот packet готов к review/решениям |
| Explicit S2 scope dispatch/profile/validation extension | **NOT IMPLEMENTED**. Текущий unknown route DENY; простое добавление scope опасно: non-RUN else выбирает compressor иначе mcp. Нужны явная Ordinary ветка и unknown-scope DENY, новый policy/context contract; никаких фиктивных RUN/MCP IDs |
| S3a hierarchical admission / typed binding / policy-engine compatibility | **NOT IMPLEMENTED**. Два ceiling проверяются одним transaction; current revision/engine pins не позволяют скрытую замену. Новые версии требуют regression/independent acceptance, включая old-store denial/migration |
| H25 isolation oracle transition | **Требует отдельного scope/GO**: текущий accepted test запрещает production policy imports. Нельзя добавлять исключение по имени guard. Будущая TASK должна заменить invariant на доказанное обязательное guard coupling всех sends с негативным bypass proof |
| Physical S1 coverage | Перед реализацией адресно пересверить семь существующих LLM sites + Ordinary injected adapter, MCP/Compressor/diagnostics и authorized checker extension. Не утверждать all-route S3b на одном happy-path Chat. OAuth permission/auth отдельно |
| Exact-wire gate | Build final body once, validate/measure/hash, durable reserve, fresh durable SENT, один I/O этими bytes; любой DENY/storage fault → 0 LLM sends. Cancellation/duplicate/cross-UI/crash/capacity/late usage проверки обязательны |
| Accounting and UI projections | Source-authenticated terminal/usage, original attempt identity, duplicate/conflict/UNKNOWN, полный scope aggregate; S9 acceptance по S1+S3a. UI не authority, RAW/history/context отдельно. S3c обязателен перед агентскими mutations, S4/S5 по графу |
| Calibration / privacy / existing-data rollout | Для synthetic S3b tests допустим явно synthetic profile в disposable roots. **До real prompts/live** нужны настоящая calibration либо explicit bounded assumption, storage/access/retention, rollout/adoption/owner решения |
| New implementation and Stage7 authorization | **NO GO** текущей TASK. Нужны отдельная implementation TASK, independent full physical guard acceptance и затем explicit live scenario с моделью/количеством/лимитами/данными по №37 Stage7 |

Порядок следующей работы: WEB26 review → решения пользователя → отдельная
спецификация/реализация изменений S2/S3a и повторная приёмка затронутых версий →
отдельная S3b TASK на полном physical coverage (synthetic OFFLINE) → связанные
S3c/S4/S5/S9 gates по №20 → independent Stage6 acceptance → отдельный Stage7 GO.
Контролируемая calibration strategy должна быть утверждена до первого реального
вызова; отсутствие corpus не оправдывает обход через чужой route.

## 9. OPEN/NEXT и адреса будущих работ

Полный машинный список: [followups.json](followups.json). Это **локальные NEXT
предложения**, а не назначенные TASK и не изменение №05:

- NEXT-OC-APPROVAL: WEB26 review и U1–U6; CHAT-A01 уже записан.
- NEXT-OC-CONTRACT: после USER GO — явный S2/S3a versioned route/scope/binding/
  hierarchical quota contract; поведение старых stores и profiles без reset.
- NEXT-OC-CALIBRATION: план matched Ordinary corpus, данные/провайдер только по
  отдельному разрешению; до него current ordinary profile остаётся null/DENY.
- NEXT-OC-DATA: RAW storage/privacy/retention и historical adoption; single-owner
  rollout, bounded durability и fencing отдельно от source checksum.
- NEXT-S3B-ALL-ROUTES: отдельное назначение guard, coupled isolation-test changes,
  все physical branches, независимая отрицательная и crash/concurrency matrix.
- NEXT-S3A-EVIDENCE: координатору сохранить адресные durable CI доказательства
  до указанного expiry артефакта **2026-11-22**, если ещё не сохранены; текущий
  review/independent_runs уже durable. Не переоткрывает bounded S3a acceptance.

Эта TASK не выполняет ни одну из этих реализаций. Новых runtime/test/normative
изменений, HTTP/LLM/Git операций нет. Сдача packet и HISTORY — отдельный
механический closeout; пользовательские решения остаются явно размеченными.
