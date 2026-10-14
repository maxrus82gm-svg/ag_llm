# CLAUDE-RT002-S2-REPAIR-001 — Final Policy Contract Hardening

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Verifier:** ChatGPT.
**Статус:** S2 REPAIR RESULT READY / AWAITING INDEPENDENT VERIFICATION. S3a не запускался. Engine по-прежнему ни к чему не подключён.
**Дата:** 2026-10-14.

**Назначение.** Пользователь переслал в чат стартовую команду.
- При первой проверке БЛОК 1 был пуст: «ОЖИДАНИЕ НОВОЙ ЗАДАЧИ», карточка `ebc450a3…`. Работа не начиналась.
- После «проверь еще раз» найдена постановка в БЛОКЕ 1 (карточка `77b81a2c…`).
- AMENDMENT во время работы не было.

**Source из карточки:** `main@d7947ee20035831a2f9ea11a59e3061da8c83b4d` — локально не сверялся: Git запрещён (`DOC-GIT-01@1`), `.git` не читался.

## 0. Итог

1. **F1 подтверждён и исправлен.** 8 из 9 пар «terminal → другой допустимый terminal» и RECONCILED + `cancelled` принимались молча. Новое правило: «одна попытка — один terminal-факт». Отдельно исправлено занижение liability при конфликте: было 1500 вместо 90 050.
2. **F2 подтверждён и исправлен.** Список или словарь в `provider_model_id`/`profile_key` давал `TypeError`. Тем же классом дефекта были `OverflowError`, `UnicodeEncodeError` и `TypeError` на ключах разных типов. Теперь всегда `PolicyValidationError` с путём поля.
3. **Соседние дефекты того же класса исправлены.** Публичные функции падали непредусмотренными исключениями на некорректном вводе:
   - `evaluate_request`: нехешируемый маршрут, огромные числа;
   - `budget_view`: повреждённые записи — 5 видов исключений;
   - `measure_request`, `calibrate_profiles`, `estimate_input_tokens`.
4. **Тесты.** S2 core 67/67 PASS, provenance 68/68 PASS, S1 69/69, S0 166/166. Все 10 мутаций ловятся (5 прежних + 5 новых). Первый FAIL сохранён. Runtime не менялся.
5. **Результаты S2 не ослаблены.** Калибровка, варианты A/B/C и точки остановки RUN не изменились. Ни один из 58 прежних тестов не менялся и не удалялся.

## 1. Baseline и изменённые файлы

До работы хеши совпадали со сдачей S2: `ultra_budget_policy.py` `ad004edc…`, `test_rt002_s2_budget_policy.py` `d2a95deb…`.

| Файл | SHA-256 после | Строк |
| --- | --- | --- |
| `ultra_budget_policy.py` | `d08ce81d8bd4802be90946770782b603ab1f9cc0081435fea95a2bc260adce1c` | 954, LF |
| `test_rt002_s2_budget_policy.py` | `76ec7e2c649ea604b154c8af7ace80cc5001e32781fc231eb594f2fe4d489c42` | 1 660, LF |
| этот отчёт | — | LF |
| `Документация/000_Задачи Claude.md` | ротация БЛОКОВ 1/2/3 | — |

Runtime, S0/S1 и UI не менялись; хеши совпадают:
- server.py `44d8cc8affaf…`;
- planner_runtime.py `ab6c12c3fb02…`;
- verifier_runtime.py `7db030fee149…`;
- compressor_runtime.py `c69ab1d9594b…`;
- provider_accounting.py `dd83dbf7a221…`;
- gigachat_transport.py `ee1db75ed04e…`;
- run_store.py `a57a250a20ea…`;
- workspace_runtime_settings.py `699026e592c2…`;
- ultra_ui.py `7bd32cad56c6…`;
- test_rt002_s1_routes.py `4465d47716e8…`;
- test_rt002_s0_kernel.py `cf9b1d771e7e…`.

Web Alarm, файлы Codex, общие документы и CI не трогались. Новые `.pyc` не созданы: компиляция проверялась в памяти.

## 2. F1 — противоречивые terminal outcomes

### 2.1 Воспроизведение на исходном модуле `ad004edc…` (без runtime)

| Первый terminal | Второй terminal | Было | Должно быть |
| --- | --- | --- | --- |
| completed + usage | timeout | KNOWN, молча | ANOMALY |
| completed + usage | parse_error + тот же usage | KNOWN, молча | ANOMALY |
| completed + usage | provider_error | KNOWN, молча | ANOMALY |
| completed + usage | completed без usage | KNOWN, молча | ANOMALY |
| timeout | cancelled | UNKNOWN, молча | ANOMALY |
| timeout | transport_error | UNKNOWN, молча | ANOMALY |
| completed без usage | timeout | UNKNOWN, молча | ANOMALY |
| completed без usage | parse_error | UNKNOWN, молча | ANOMALY |
| provider_error | completed + usage | RECONCILED | ANOMALY |
| RECONCILED (timeout → completed) | cancelled | RECONCILED, молча | ANOMALY |
| KNOWN (450) | completed с usage 90 050 | ANOMALY, **liability 1500** | ANOMALY, liability 90 050 |

**Root cause.** Дубликат определялся только по usage: «тот же usage или его отсутствие = идемпотентно». Outcome в сравнении не участвовал. В состоянии UNKNOWN любой terminal без usage считался дубликатом. Liability ANOMALY учитывала только usage первого факта.

### 2.2 Факты runtime, на которых основано правило

- Каждая попытка выпускает **ровно один** terminal: флаг `provider_terminal_emitted` в `verifier_runtime.py` и аналоги.
- `run_store.record_provider_attempt_terminal` помечает второй terminal как `duplicate_terminal_ids`, и учёт становится неполным.
- `provider_error` = `httpx.HTTPStatusError`, то есть провайдер ответил. `timeout` / `transport_error` / `cancelled` = ответ не наблюдался.
- В локальных RAW: 342 попытки, 343 terminal-события. Повторный terminal есть ровно у одной попытки — R-026: `timeout`, затем неизвестный `aborted_external_recovery`. Она была ANOMALY и в S2, и сейчас.

### 2.3 Правило (B2 §4: «duplicate terminal идемпотентен, late known корректирует ту же attempt, conflicting usage = anomaly/BLOCKED»)

- Факт terminal = пара (outcome, usage), где usage = None, если провайдер его не дал. Различимые принятые факты хранятся в `AttemptRecord.terminal_events`.
- **Идемпотентна только повторная доставка** уже принятого факта — в любом порядке, включая ранние события RECONCILED-попытки (at-least-once delivery).
- **Единственное уточнение** допустимо для UNKNOWN: тот же outcome (теперь с usage) **или** поздний ответ после «нет ответа» (`timeout`/`transport_error`/`cancelled` → `completed`/`parse_error`/`provider_error`). С usage результат RECONCILED, без usage — остаётся UNKNOWN.
- **Всё остальное → ANOMALY** с пояснением («противоречивый terminal X (с/без usage) после Y в состоянии Z»). ANOMALY поглощающее. Liability = максимум из резерва и **всех** заявленных usage.
- Без изменений: UNKNOWN ≠ 0, поздний known, неизвестный outcome, INVALID usage, terminal до SENT, orphan.

### 2.4 Рассмотренные альтернативы

| Вариант | Решение |
| --- | --- |
| Любой второй terminal → ANOMALY | Отвергнут: ломает идемпотентность повторной доставки и поздний known (B2 §4) |
| Сравнивать только usage (как было) | Отвергнут: это и есть дефект F1 |
| Сравнивать только классы outcome | Отвергнут: пропускает completed ↔ parse_error и конфликт usage |
| Брать последний факт как истину | Отвергнут: молча снижает liability при противоречии |
| **Хранить факты и разрешить одно уточнение** | Принят: минимальная модель, совместимая с B2 и runtime |

Совместимость: новое поле `terminal_events` добавлено в конец dataclass со значением по умолчанию `()`, позиционные конструкторы не меняются.

## 3. F2 — неверные JSON-типы в политике

### 3.1 Воспроизведение (исходный модуль)

- `profiles[0].provider_model_id` или `.profile_key` = `[]`, `{}`, `["executor"]`, `{"a":1}` → **TypeError: unhashable**: проверка `key not in {роли}` и `(model, key) in seen` выполнялась до проверки типа.
- `bytes_per_token = 10**400` → **OverflowError**: `math.isfinite` вызывался до проверки диапазона.
- `revision_label` или `provider_model_id` с одиночным суррогатом (`json.loads('"\ud800"')` его выдаёт) → **UnicodeEncodeError** при вычислении revision.
- Два неизвестных ключа разных типов на любом уровне → **TypeError** в `sorted()`.

### 3.2 Исправление

- Тип проверяется до хеширования.
- Диапазон проверяется до любого преобразования во float; NaN/inf отсекаются тем же диапазоном.
- Общая проверка текста `_text_problem`: непустая строка, не длиннее 200 символов, кодируется в UTF-8. Применяется к label, model id, measure, строкам калибровки.
- Неизвестные ключи сортируются по безопасному repr.
- Все значения в сообщениях выводятся через `_show`: ограниченная длина, суррогаты экранированы, отказ `repr` перехватывается.
- Snapshot возвращается только полностью заполненным, иначе — `PolicyValidationError` с путём поля.

**Свойственный тест.** Каждый из 44 узлов валидной политики (включая контейнеры и корень) заменяется каждым из 15 «JSON-подобных» неверных значений: 660 комбинаций.
- 653 → `PolicyValidationError`.
- 7 законны по контракту, и для них проверена полнота snapshot: `None` в трёх лимитах ролей, `1.5` байт/токен в трёх профилях, пустой список профилей.
- Ещё 40 комбинаций: ключи разных типов, кортеж, суррогат и `None` на каждом из 10 уровней-объектов → всегда `PolicyValidationError`.

## 4. Соседние дефекты того же класса (найдены в review, исправлены)

| Функция | Было (repro) | Стало |
| --- | --- | --- |
| `evaluate_request`, `route_id=[]` | TypeError unhashable | DENY `UNKNOWN_ROUTE` |
| `evaluate_request`, `wire_bytes=10**400` | OverflowError | DENY `INVALID_MEASURE` (предел 1 GiB) |
| `evaluate_request`, `output=10**400`; model — список или суррогат | не отсекалось | DENY `INVALID_MEASURE` (предел 10¹⁰) |
| `budget_view` / `evaluate_request`: запись с `route_id=[]`, `reserved='x'`, usage-dict, `anomalies=5`, model-список при breach, KNOWN без usage, битые `terminal_events` | TypeError / AttributeError | `_record_problem` → `LEDGER_ANOMALY`; читаемый резерв учитывается, некорректные числа — нет |
| Элемент `attempts`, не являющийся записью | AttributeError | аномалия во всех scope (его scope неизвестен) |
| `measure_request`: тело-список, NaN/inf, суррогат, set, object | AttributeError / ValueError / UnicodeEncodeError / TypeError | `PolicyInputError` |
| `calibrate_profiles`: строка в токенах | TypeError | `PolicyInputError` |
| `calibrate_profiles`: bool в байтах | **молча принимался** | `PolicyInputError`; также проверяются отрицательные значения, роль, кортеж вместо строки, `source_sha256` |
| `estimate_input_tokens`: model/role не строка, bool/огромные байты | нестабильно | `PolicyInputError` |

Не обрабатывается намеренно: неитерируемый `attempts` и `snapshot`, не являющийся `PolicySnapshot`. Это ошибки вызова; правильный вызов обязан обеспечить S3b.

## 5. Тесты и evidence

### 5.1 Новые тесты (MANIFEST 58 → 67; с provenance 68)

| Класс | Тест | Что доказывает |
| --- | --- | --- |
| Liability | `test_terminal_event_matrix` | 16 пар (первый, второй terminal) с явными ожидаемыми state и liability и пояснением ANOMALY. Таблица задана вручную, не production-оракулом |
| Liability | `test_reconciled_attempt_accepts_only_replays_of_its_own_events` | повторная доставка любого из 3 ранних фактов идемпотентна; 4 противоречия → ANOMALY |
| Liability | `test_conflicting_claims_never_lower_liability` | конфликт → 90 050, а не 1500; поздний known выше резерва; ANOMALY поглощающее |
| PolicyValidation | `test_reviewer_profile_type_cases_are_policy_errors_naming_the_field` | случаи из находки verifier, ошибка называет поле |
| PolicyValidation | `test_wrong_json_types_anywhere_are_policy_errors_never_crashes` | 660 + 40 комбинаций (§3.2) |
| Calibration | `test_calibration_and_estimate_inputs_are_validated` | 7 битых строк калибровки, неверный sha, 4 битых аргумента оценки |
| Decision | `test_unhashable_or_oversized_measure_is_denied_not_raised` | 6 случаев → DENY с кодом |
| Decision | `test_corrupt_records_block_instead_of_crashing` | 15 повреждений записи → `LEDGER_ANOMALY` |
| WireMeasure | `test_unserializable_body_is_a_policy_input_error` | 6 неотправляемых тел → `PolicyInputError` |

Классы после изменений: Wire 5, PolicyValidation 11, Calibration 9, Liability 15, Decision 18, Synthetic 5, Isolation 4; Provenance 1 только в `--provenance`.

### 5.2 Первый FAIL (до исправления, исходный модуль, новые тесты)

`.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py` → exit 1. Выполнено 67 тестов. В `result.json` 25 записей failures и 80 записей errors: subtests считаются по отдельности, это **не** число тестов. Лог `d4eca6304238713f630df7148b1eb171ec05e3598dbe5d94dc5bd8c7bdfe0f17`.

- Упали только 9 новых тестов; 58 прежних прошли.
- Классы исключений: unhashable list/dict (38), сравнение str/int и float/None (20), OverflowError (4), UnicodeEncodeError (6), AttributeError (4), ValueError NaN/inf (2), TypeError сериализации (2), несуществующее поле `terminal_events` (2) и другие.

После исправления первый же прогон: 67/67 PASS (промежуточных FAIL не было).

### 5.3 Финальные прогоны (итоговые SHA из §1)

| Прогон | Exit | Gate | run / F / E / S | Manifest | Guard viol | Log SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| S2 core | 0 | PASS | 67 / 0 / 0 / 0 | 67 | 0 | `30522ef47e6aee27ba7e114faf5bc3816c9e8f3ac28db0fa05b7faab8f5b46d1` |
| S2 `--provenance` (embedded 342 = local 342, новых 0) | 0 | PASS | 68 / 0 / 0 / 0 | 68 | 0 | `2407dab71b9e3598c7a6fb5a217a426fe0560fe24705f2622a6d3098f9f2802a` |
| S2 selector `test_terminal_event_matrix` | 3 | PARTIAL_SELECTION | 1 / 0 / 0 / 0 | 67 | 0 | `cd32ed1d5fdf…` |
| S2 unresolved selector | 1 | FAIL (`SELECTOR_UNRESOLVED`, `ZERO_TESTS`) | 0 | 67 | 0 | `b0281afc5a8f…` |
| S2 `unittest discover` | 0 | — | Ran 0, OK (skipped=1): не приёмка | — | — | — |
| S1 | 0 | PASS | 69 / 0 / 0 / 0 | 69 | 0 | `dbb532a88843d0a93a0e0f6b5ab46858160203f7becf6774503c9b3c9d3ea42b` |
| S0 | 0 | — | 166 / 0 / 0 / 0 | — | 0 | `50bda17310060dec0cea37c86c6822ddb6adc10660b0631aab823df0de061e88` |

Наблюдения S2 совпадают со сдачей S2:
- калибровка и LOO;
- `bytes/4` (dredd 24, 1.6147);
- точки остановки A/B/C (R-025/026/027/031 = 3/3/3/9, 4/4/4/10, —/8/10/13).

Время: S2 0.9 с, S1 13.0 с, S0 105.0 с. Git-зависимый `test_final_audit` не запускался. Платных, live, stress и destructive прогонов не было.

### 5.4 Sensitivity (мутации в памяти после guards, финальный код)

| Мутация | Exit | Записей FAIL/ERROR |
| --- | --- | --- |
| unknown_is_zero | 1 | 12 |
| reserve_usable_by_work | 1 | 7 |
| bytes_div_4 | 1 | 72 |
| bool_is_int | 1 | 9 |
| no_late_reconcile | 1 | 15 |
| **old_terminal_semantics** (дубликат по usage, как в S2) | 1 | 11 |
| **refine_any_outcome** (UNKNOWN принимает любой outcome) | 1 | 5 |
| **anomaly_liability_first_claim** (liability ANOMALY по первому факту) | 1 | 1 |
| **text_check_disabled** (`_text_problem` всегда None) | 1 | 59 |
| **record_check_disabled** (`_record_problem` всегда None) | 1 | 13 |

Все мутации применены (`MUTATION_APPLIED True`). Скрипт лежит вне репозитория (scratchpad), метод тот же, что в S2.

## 6. Сверка нормативных документов (требование БЛОКА 1)

**Прочитано в этой задаче:**
- целиком: `36` и `36.3`;
- `34`: CURRENT S1 и §5а;
- `13`: R-031, mandatory tool reserve, UTF-8-бюджеты Final Audit, лимиты RUN;
- `01`: limitation R-031 и handoff;
- `08` и `11`: места, относящиеся к бюджету и токенам;
- `18` и `36.1` (правила DOC/TEST) и B2 `33.3` §4 — повторно.

**Целиком не перечитывались:** `01` (1 546 строк), `11` (1 428), `13` (2 135), `08` (708) — читались только разделы, относящиеся к S2.

**Согласованность с S2:**
- `13`: «1 MiB на полный verification context» ↔ `max_verification_request_bytes` = 1 114 112 (1 MiB + 64 KiB оболочки) в A/B/C.
- `13`: «64 lifecycle steps на RUN» — отдельный существующий лимит; лимиты попыток S2 (24/32/48) его не заменяют.
- `01`: «`read_file` допускает до 2 MiB» подтверждает актуальность full-read cap S4 (F-10 из S2).
- `36` §6: неверный счётчик не является доказательством → в §5.2 явно сказано, что FAIL/ERROR считаются записями subtests.

**Устаревшее в общих документах** (не менял, это зона координатора):
- в `34` строка CURRENT говорит «S2 NOT ASSIGNED»;
- в `01` handoff стоит на S0.

## 7. MANUAL ENGINEERING REVIEW

**Просмотренные ветви:**
- `apply_terminal`: все состояния × повторная доставка, уточнение, противоречие, INVALID, неизвестный outcome, terminal до SENT;
- `liability_tokens` для каждого состояния;
- `_refines`;
- `orphan_terminal_record`;
- `validate_policy`: каждый путь к хешированию, сортировке, float и кодированию;
- `_check_keys`, `_int_field`, `_show`;
- `budget_view`: порядок фильтра scope и проверки записи;
- `evaluate_request`: порядок route → measure → ledger;
- `measure_request`, `calibrate_profiles`, `estimate_input_tokens`.

**Гипотезы:**
- *подтверждена:* «второй terminal в runtime невозможен по дизайну» (флаг + `duplicate_terminal_ids`); значит, строгость не ломает текущие потоки — проверено на 342 RAW-попытках;
- *подтверждена:* «на конфликте liability занижалась»;
- *отвергнута:* «достаточно сравнивать только outcome»;
- *отвергнута:* «JSON-парсер не выдаст суррогат» — выдаёт;
- *отвергнута:* «`math.isfinite` безопасен для int» — OverflowError.

**Edge cases под тестами:**
- повторная доставка ранних фактов RECONCILED в любом порядке;
- поздний known выше резерва;
- ANOMALY поглощающее;
- `timeout` → `timeout` с usage;
- `provider_error` → `completed` (противоречие);
- корень и контейнеры политики, заменённые неверным типом;
- int в 400 цифр;
- None, float и кортеж в роли ключей;
- KNOWN без usage;
- запись не того типа.

**Claim → Source → Oracle → Result → Uncertainty**

| Claim | Source | Oracle | Result | Uncertainty |
| --- | --- | --- | --- | --- |
| Противоречивые terminal не принимаются молча | `apply_terminal`, `_refines` | Явная матрица 16 пар + тест повторной доставки; мутации `old_terminal_semantics` и `refine_any_outcome` | PASS; мутации ловятся | Политика строгая — см. риск R-1 |
| Liability при конфликте не занижается | `liability_tokens` | `test_conflicting_claims_never_lower_liability`; мутация | PASS; 1 FAIL под мутацией | — |
| Политика с неверными типами → только `PolicyValidationError` | `validate_policy` | 660 + 40 комбинаций, полнота snapshot | 653 отказа, 7 законных | Покрыты JSON-подобные значения; экзотические Python-объекты с ломаным `__eq__` вне контракта |
| Повреждённая запись блокирует, а не падает | `_record_problem` | 15 повреждений; мутация | PASS; 13 FAIL под мутацией | Проверка структурная, не семантическая (S3a) |
| Новое правило не блокирует реальные RUN | RAW | Реплей всех 342 попыток (scratch-скрипт) | Единственный повторный terminal (R-026) — ANOMALY, как в S2 | Только локальные RAW |
| S2 не ослаблен | Тесты S2 | 58 прежних тестов без изменений, те же наблюдения | PASS | — |

**Остаточные риски:**
- **R-1.** KNOWN + тот же outcome без usage → ANOMALY. Если будущий ledger S3a доставит «облегчённый» дубликат без usage, это ложная блокировка. Требование к S3a — хранить события дословно.
- **R-2.** Первый terminal вида «нет ответа» с usage принимается как KNOWN. Runtime такого не выпускает, решение оставлено.
- **R-3.** `terminal_outcomes` растёт с каждой повторной доставкой (журнал аудита); S3a может ограничить его рост.
- **R-4.** Ошибки вызова (неитерируемый `attempts`, чужой `snapshot`) остаются исключениями.

## 8. FINDINGS / PROPOSALS

- **S3a.** Хранить terminal-события дословно (outcome + usage) и применять их через `apply_terminal`: повторная доставка идемпотентна, противоречие → ANOMALY. Схема записи включает `terminal_events`. Восстановление из хранилища подаёт записи как есть — повреждённая запись даёт `LEDGER_ANOMALY` (это уже обеспечено).
- **S3b.** Вызывать `measure_request` и `evaluate_request` строго по контракту. `PolicyInputError` и DENY трактовать как «не отправлять».
- **Verifier / решение.** R-1 — оставить строгость (предлагается) или трактовать «тот же outcome без usage» после KNOWN как дубликат.

## 9. DOC IMPACT (координатору после проверки)

- `36.3`: селектор S2 и MANIFEST 67 (68 с provenance), коды гейта, метод мутаций.
- `21` и `20` §5а: запись REPAIR-001.
- `34` и `01`: устаревший статус S2 (§6).
- Закрытие `001` и `06` — за verifier.

## 10. NEXT

Независимая проверка ChatGPT. S3a — только по отдельному решению пользователя.

Незакоммичено (коммитит пользователь): `ultra_budget_policy.py`, `test_rt002_s2_budget_policy.py`, этот отчёт, ротация `000_Задачи Claude.md`.
