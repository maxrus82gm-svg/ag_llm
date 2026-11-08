# Stage 6A — долговременный OFFLINE ledger RT-002/B2 S3a

**TASK ID:** `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`  
**Автор / дата:** Codex 007 / 2026-11-08  
**Статус:** PARTIAL / RESULT READY / AWAITING INDEPENDENT REVIEW  
**Scope:** OFFLINE S3a; production routes, transport, policy и числовые defaults не менялись.  
**Assigned base:** `main@ce1e71cd01e64758273259848cad250f08171b94` из постановки. Git/GitHub не использовались; фактическая Git identity не проверялась.  
**Source version:** точные локальные SHA-256 в `evidence/baseline.json`, `evidence/source_final.json` и manifest.  
**Граница вывода:** авторский bounded результат; не Stage6 DONE, не S3a INDEPENDENT VERIFIED и не S3b READY FOR LIVE.

## Что сделано

Новый `ultra_budget_ledger.py` предоставляет `BudgetLedger.initialize`, `reserve`,
`mark_sent`, `mark_not_sent`, `terminal`, `recover`. Все решения используют
существующие S2 AttemptRecord/reserve_attempt/mark_sent/mark_not_sent/
apply_terminal/evaluate_request/budget_view через evaluate_request. Денежные
тарифы, реальные provider calls и новые политики не добавлены.

Бюджетные facts находятся в расширении `budget_ledger` существующего Workspace
индекса Run Store. Чтение, проверка остатка, переход и durable commit выполняются
под существующим `run_store._index_lock` — тем же OS-backed Ultra writer lock.
Второго lock-owner или отдельного Web-бюджета нет. `run_store.py` менять не
потребовалось: его load/save сохраняют дополнительные поля индекса и используют
проверенные atomic/fsync/readback/generation механизмы. Usage summaries остаются
projection и не участвуют в разрешении нового резерва.

Новый `test_rt002_s3a_ledger.py`: 35 OFFLINE случаев с отдельными TEMP roots,
двумя реальными Python-процессами, process death, fault injection, identity,
NOT_SENT/UNKNOWN/late/duplicate/conflict и совместимостью Run Store.
Других рабочих файлов не меняли; helpers/evidence — только внутри папки TASK.

## Проверка зависимостей

- №20 §5а сохраняет S2 → S3a → S3b. №20 §14 задаёт identity/usage/UNKNOWN contract.
  №37 Stage6, §2.4 и §4 требуют общего состояния, переносимости и отдельного
  решения по Ordinary Chat. Текущий USER GO разрешил только S3a OFFLINE.
- №21: S0 independently accepted OFFLINE; S1 и S2 имеют bounded source-review
  acceptance с ограничением самостоятельного исполнения. Это не общий live PASS.
- Реальный профильный S2 standalone selector: **73 PASS, 0 FAIL/ERROR/SKIP**, gate
  PASS, exit 0, isolation violations 0, core MANIFEST 73. Сохранены stdout,
  result.json и полный test log. Не подменялся пустым unittest discovery.
- Шесть pinned архивных fixtures S1 доступны; source/fixture verification gate
  не сообщил evidence problems. Guarded standalone S1 реально выполнил 69 tests:
  **67 PASS, 2 FAIL, 0 ERROR/SKIP**, exit 1, isolation violations 0.
- S1 FAIL относится к текущему source inventory: UNKNOWN sites в `launcher.py`
  и `ordinary_chat_service.py`, два endpoint-host literals в `model_cards.py`.
  Это существующий код, а не новый ledger network route. Точные locators и
  минимальный запрос отдельного scope — [amendment_request_s1.md](amendment_request_s1.md).
  Исправления S1/production не выполнялись. Зависимые production/S3b работы STOP.

S2 source не менялся. Его реальные numeric/user decisions, отсутствующий
Ordinary Chat scope/profile и production enforcement не утверждены этим отчётом.

## Формат, операции и гарантии

Версия ledger и enrollment marker — 1. Authority: упорядоченные события
`reserve`, `mark_sent`, `mark_not_sent`, `terminal` в индексе Run Store.
Состояния AttemptRecord реконструируются через S2; отдельная writable projection
расхода не вводится. Event-list digest обнаруживает повреждение; canonical index
и generations проверяются существующим Run Store. Неизвестная версия, битый
JSON, missing state/index/marker, неправильная identity, unsafe path и lock/I/O
failure дают LedgerDenied. Отсутствие журнала не считается нулевым бюджетом.

При reserve сохраняются точные S2 serialized UTF-8 wire bytes и их identity,
raw validated policy, context, run/chat/turn/logical_call binding. provider_attempt_id
уникален в пределах Workspace. Равный reserve/event не добавляет резерв/расход
и возвращает replayed receipt; конфликт данных того же ID отклоняется.
Policy revision, scope type и final_audit flag закреплены для lifetime scope.

Дополнительно закреплён source hash S2 engine (нормализован только CRLF). Иначе
после обновления estimator/ROUTES replay старых bytes мог бы изменить старую
liability. Неизвестный engine требует миграции и даёт отказ; старые резервы
не пересчитываются молча на более выгодных правилах. Числовую политику не меняли.

`mark_sent` — долговременный факт до потенциального HTTP. Receipt не является
самостоятельным правом отправки. Future S3b обязан проверять свежесть перехода,
state и exact bytes; replayed SENT нельзя физически отправлять повторно.
Crash в gap SENT→HTTP сохраняет обязательство консервативно.

NOT_SENT освобождает резерв только из RESERVED с explicit trusted pre-send
proof locator. Это интерфейс для будущего доверенного S3b, не доказательство
сети само по себе. Попытка NOT_SENT после SENT приводит к S2 ANOMALY и не
освобождает бюджет. SENT без terminal и UNKNOWN держат резерв при restart.
Поздний usage уточняет прежний attempt; противоречивые terminal/usage сохраняют
максимальное обязательство через S2 ANOMALY и блокируют новый reserve scope.

## Матрица обязательных OFFLINE-проверок

| Требование | Доказательство |
| --- | --- |
| 1 durable reserve/restart | Отдельный Python child recover возвращает один attempt и тот же liability; exact index snapshots |
| 2 duplicate attempt | replayed=True, index bytes/revision не меняются, attempt count 1 |
| 3 conflicting identity | Тот же ID с другим wire/text отклонён; второго резерва нет |
| 4 two processes last reserve | Два subprocess под общим lock: ровно один ALLOW; отдельно attempt cap и token liability cap |
| 5 crash before/after commit | Child os._exit(79) по двум барьерам; после committed reserve остаётся и новый не проходит; до commit reserve отсутствует. fsync/write/lock faults дополнительно |
| 6 SENT/UNKNOWN | Timeout None держит резерв; новый объект/process не освобождает; retry cap остаётся занят |
| 7 NOT_SENT proof | Без proof отказ; proven pre-send releases; после SENT — ANOMALY, не нулевой расход |
| 8 late usage | Тот же pa_id переходит UNKNOWN→RECONCILED, count 1, liability известного usage |
| 9 duplicate/conflicting terminals | Идентичный terminal без записи; другой usage даёт ANOMALY с liability не ниже reserve/claims |
| 10 corrupt/version/unsafe/fsync/lock | Набор corrupt/missing файлов, versions включая bool, checksum, unknown events; Windows audit/root junction и hardlink; наружные bytes неизменны |
| 11 invalid policy/profile/estimate | Неизвестная/плохая policy, пустые profiles, body без max_tokens, неизвестный Ordinary Chat route и несовпадающие wire bytes дают DENY без commit |
| 12 move | Rename собственного TEMP Workspace с тем же ID сохраняет два резерва; foreign Workspace ID отказывается |
| 13 old Run Store | Ledger survives create/update/append/index-generation paths; старые summary bytes и records не меняются ledger reserve. 51 прежний Run Store test PASS |

Cases и параметры перечислены в `test_rt002_s3a_ledger.py`, результаты и
case IDs — `evidence/final_s3a.xml`, `evidence/final_tests.xml`.

## Тесты и raw evidence

Основная команда: `.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S3A-DURABLE-LEDGER-001/run_checks.py test_rt002_s3a_ledger.py -q`.
Guard ставится до imports; дети того же Python получают early guard через
PYTHONPATH. Нет credential reads, Git metadata, реальных socket/DNS sends.
Отдельные controls подтверждают блокировку socket, DNS и access-token read
до I/O. Raw control log отделён от test guard log, где denied events = 0.

| Прогон | Результат |
| --- | --- |
| S2 standalone core | 73/73 PASS, exit0, guard0/evidence0 |
| S1 standalone | 69: 67 PASS / 2 FAIL, exit1, guard0/evidence0; repair вне scope |
| Первый S3a | 29: 13 PASS / 16 FAIL — synthetic fixture request limits превышали fixture RUN budget; код корректно отказал |
| Второй S3a | 29: 25 PASS / 4 FAIL — verification attempts fixture не согласован с last-attempt cap; fallback mock запрещал также generation commit |
| Следующий S3a + Run Store | 80 PASS, exit0, после исправления только фикстур |
| Расширенный S3a + Run Store | 85 PASS = 34 новых + 51 прежний; exit0, без FAIL/ERROR/SKIP |
| Финальный S3a после дополнительной проверки invalid/missing root | 35 PASS, exit0, 0 SKIP; прежний Run Store не менялся |
| Три финальных mutation controls | 3/3 ожидаемых exit1: игнорировать DENY, обнулить UNKNOWN, игнорировать checksum. Каждый целевой oracle стал красным |
| Syntax/compile | Новый module/test и helpers проверяются без записи pycache; `evidence/syntax.json` |

Не суммировать перекрывающиеся runs. Отдельные непересекающиеся слои: 35 S3a,
51 Run Store, 73 S2; S1 — FAIL. Конкретные commands, counts и exits сохранены в
`evidence/test_summary.json` и stdout/stderr/XML. Первые FAIL не удалялись.

`evidence/committed/` содержит enrollment и пять exact-byte index snapshots:
reserve → SENT → UNKNOWN → поздний RECONCILED → противоречивый ANOMALY. Trace
связывает source SHA, file SHA, revision, attempt state, liability и duplicate
no-write. Это synthetic data. Старые pre-engine-pin snapshots явно отделены
как промежуточная версия. RAW архивных S1 fixtures в публикуемый пакет не копировался.

Личные home paths в публикуемых logs заменены на `<USER_HOME>`; оригинальные
bytes сохранены в частном TEMP task archive, mapping/hashes —
`evidence/sanitization.json`. Никаких токенов/API credentials в package нет.

## MANUAL ENGINEERING REVIEW

**Порядок/гонки.** Общий writer lock охватывает прочтение всех scopes, evaluate,
reserve и publication; нет разрыва check→commit для двух процессов. `recover`
также читает под lock. Same-event replay возвращается только после проверки
всего ledger. Новые reserves нельзя разрешать из best-effort usage summary.

**Partial I/O.** Используется существующий temp-write/flush/fsync/replace/readback
Run Store; на sharing violation — штатная generation. Потеря подтверждения
после commit возвращает DENY вызывающему, но новый процесс видит committed
reserve. До commit нет разрешённой попытки. Маркер enrollment пишется первым:
crash между marker/index может оставить blocked initialization, а не скрытый
ноль. `recover` это обнаруживает, но не чинит автоматически.

**Совместимость.** `_validate_index` сохраняет дополнительные поля. Existing
writers загружают index внутри того же lock и не теряют ledger. Summary и
record formats не менялись. Новые пути находятся в audit root и проходят
существующую unsafe-file/reparse/hardlink проверку; root ancestors проверяются
до resolve. Path/ledger не содержит привязки к устройству, source pin допускает
CRLF-only перенос. Старые app versions, не сохраняющие unknown index fields,
требуют отдельного compatibility gate и здесь не обещаются.

**Выбор архитектуры.** Отдельный journal с отдельным mutex отвергнут из-за
второго owner и разрыва конкурентных решений. Использование summary как authority
отвергнуто: best-effort accounting не является резервом. Выбран index extension
с immutable enrollment witness; witness не содержит баланса и не второй ledger.
Зависимость от private Run Store helpers явная, source/version pinned в evidence;
публичный adapter можно вводить позже отдельным совместимым изменением.

**Аномалии/восстановление.** S2 state machine не дублируется. Legit late known
usage может уменьшить UNKNOWN estimate по принятым S2 правилам, противоречие
не уменьшает обязательство. Source pin защищает от молчаливого re-estimation
после смены policy engine. Checksum не является authentication против владельца,
переписавшего целиком store/marker: hostile full rollback требует внешних
authority/backup/fencing контрактов. Две активные клонированные копии одного
Workspace на разных root/машинах не имеют общего OS lock — не поддерживаются
как одновременные бюджетные владельцы. Перенос требует quiesce старого root.

**Границы.** Fresh enrollment допускается только при пустом audit store; это
осознанный отказ обнулять исторический расход, а не migration implementation.
Для существующего Workspace с историей нужен approved adoption protocol.
4096 events и существующий Run Store byte bound — предел формата, не spending
policy; на исчерпании DENY, без compaction/reset. Реальное power loss, directory
fsync/Windows durability beyond process death и враждебные TOCTOU перестановки
не доказаны этими tests. Эти ограничения сохранены в OPEN.

**Самостоятельно найденные пробелы.** В тесте lock первоначально ошибочная
сигнатура WorkspaceBusyError давала TypeError; oracle исправлен и проверяет
точный WorkspaceBusyError. Добавлены missing index/marker, S2 engine migration,
token-cap two-process race и invalid root. Это не изменения approved policy.

## NOT RUN, OPEN, DOC IMPACT и NEXT

NOT RUN: S0 rerun, S2 optional provenance (core 73 self-contained), whole-repo
regression/CI, real providers/OAuth/paid, production integration/S3b/S3c/S9,
историческая migration/adoption, cross-machine cloned-owner fencing, настоящая
аппаратная потеря питания. Независимая приёмка нового S3a ещё не проводилась.

Открытые вопросы и owners: [followups.json](followups.json). Отдельно требуется
AMENDMENT для S1 inventory. Предлагаемые Ordinary Chat route/role/scope и
порядок будущего S3b: [ordinary_chat_contract.md](ordinary_chat_contract.md).
Новые routes/scopes, numeric settings, политика и общий runtime вне scope не
менялись. Зависимая integration остановлена; отдельный запрос не означает GO.

Scope: два новых рабочих файла плюс собственная report directory. Все 11
контролируемых existing files (включая run_store, S2/S1 tests, server, Ultra/UI,
CMD) должны совпасть с before hash. Общие документы, STANDARD, реальные
Workspace, .obsidian, CI/workflows не менялись. Пользовательские launcher
профили не переключались и не запускались; восстановления STANDARD не требовалось
и production smoke не заявлен. Git/GitHub — NOT USED.

DOC IMPACT: авторский package и штатные finish artifacts. Нормативные документы
и independent verdict не редактируются. SHARED DOC DELTA координатору:
сохранить PARTIAL, S1 2 FAIL, bounded S3a evidence, Ordinary Chat USER DECISIONS
и ограничения adoption/upgrade/fencing; не объявлять Stage6 DONE или S3b live-ready.

После проверки полноты выполняется штатный finish с exact TASK ID, без нового
назначения. Его HISTORY ID, ROTATED/exit0, БЛОК 1 WAITING, БЛОК 1.1 SUBMITTED /
REVIEW PENDING и readback — `finish_protocol.json` / `closeout.json`.
Самостоятельная публикация и прямая отправка в чужой чат этой TASK не разрешены;
пользователь получает полный локальный пакет для независимой проверки.
