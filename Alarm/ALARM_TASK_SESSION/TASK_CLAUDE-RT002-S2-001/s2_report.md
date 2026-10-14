# CLAUDE-RT002-S2-001 — RT-002/B2 S2: Budget Policy & Conservative Estimation

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Verifier:** ChatGPT.
**Статус:** S2 RESULT READY / AWAITING INDEPENDENT VERIFICATION. S3a/S3b/S3c/S5 не начаты.
**Дата:** 2026-10-14. **Назначение:** пользователь переслал в чат стартовую команду; постановка — БЛОК 1. AMENDMENT во время работы не было.
**Source baseline из карточки:** `main@b68e5926b79f9a5ba6c479269ac9455081ea85d2` — локально не сверялся: Git запрещён по `DOC-GIT-01@1`, `.git` не читался.

## 0. Итог в пяти строках

1. Создан чистый policy engine `ultra_budget_policy.py`. В production его никто не импортирует (это доказано тестом), enforcement не включён.
2. Разделены единицы: точные wire bytes, консервативная оценка токенов, резерв выхода (`max_tokens`), физические попытки, provider usage. Деньги не вычисляются.
3. Mock calibration на 342 реальных попытках из локальных RAW. `bytes/4` недооценивает пакеты Dredd в 24 из 37 случаев (худший фактор 1.615). Калиброванная нижняя огибающая с margin 0.1 даёт 0 недооценок в leave-one-out.
4. Умолчаний нет. Предложены три набора лимитов A/B/C на выбор пользователя. На реплее 41 записанного RUN каждый набор останавливает тяжёлые R-025/026/027/031 (C пропускает R-025) и не блокирует ни одного обычного RUN.
5. Guarded offline suite: 58/58 PASS, provenance 59/59 PASS, S1 69/69 PASS, S0 166/166 PASS. Пять мутаций валят suite. Хеши runtime не изменились.

## 1. Изменённые файлы

| Файл | Статус | SHA-256 | Строк |
| --- | --- | --- | --- |
| `ultra_budget_policy.py` | новый | `ad004edc7fddb70024eb8efd25eb0dce997362bf2a55b94fc0a67a3eeb026055` | 819, LF |
| `test_rt002_s2_budget_policy.py` | новый | `d2a95debf35023cea84969711a2c47896f50e09daf7fe4050fa494a21693ccd2` | 1 436, LF |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S2-001/s2_report.md` | новый | этот отчёт | LF |
| `Документация/000_Задачи Claude.md` | ротация БЛОКОВ 1/2/3 | — | — |

**Runtime не менялся.** Хеши до и после работы совпадают, а suite проверяет их сам (поле `production_hashes`):

| Файл | SHA-256 |
| --- | --- |
| server.py | `44d8cc8affaf…` |
| planner_runtime.py | `ab6c12c3fb02…` |
| task_planner.py | `c2ad7723b0ec…` |
| verifier_runtime.py | `7db030fee149…` |
| compressor_runtime.py | `c69ab1d9594b…` |
| provider_accounting.py | `dd83dbf7a221…` |
| gigachat_transport.py | `ee1db75ed04e…` |
| run_store.py | `a57a250a20ea…` |
| audit_storage.py | `5d91a6f9842b…` |
| workspace_runtime_settings.py | `699026e592c2…` |
| model_registry.py | `2b6a9ea77974…` |
| context_storage.py | `8cf90ad41afb…` |
| ultra_ui.py (READ) | `7bd32cad56c6…` |
| test_rt002_s1_routes.py | `4465d47716e8…` (не менялся) |
| test_rt002_s0_kernel.py | `cf9b1d771e7e…` (не менялся) |

Из write-scope (`server.py`, `planner_runtime.py`, `verifier_runtime.py`, `compressor_runtime.py`, `provider_accounting.py`, `gigachat_transport.py`, `run_store.py`, `workspace_runtime_settings.py`) **ничего не изменено намеренно**. S2 — это контракт без подключения; любое подключение к send sites и есть S3b. Временные файлы вне репозитория (scratchpad): `extract.py`, `sensitivity.py` и другие. Два `.pyc`, созданных `py_compile` в `__pycache__/`, удалены.

## 2. Что прочитано (и чего не перечитывал)

- **В этой задаче:**
  - БЛОК 1;
  - B2 `33.3_Круглый стол - итоговый план.md` (sha `c331ffadff32…`): строка S2, §4 Safety budget, строки V-11/Budget/Accounting, открытые вопросы;
  - `18`: DOC-ENGINEERING-ROLES-01, DOC-PARALLEL-01, DOC-GIT-01, DOC-TASK-BLOCK1-01;
  - `36.1`: TEST-COLLAB-01, TEST-AREA-01, TEST-ENG-01, TEST-DEV-01;
  - исходники `model_registry` и места `max_tokens` по маршрутам;
  - локальные RAW Run Store и `compressor_logs` (только чтение).
- **Ранее в этой же сессии (задачи S1):** 20 §5а, 21 (серия 151), 34, 36.3, 09 (обзорно), S1-отчёты и `test_rt002_s1_routes.py`.
- **Ограничение:** документы 08, 01, 36, 11 и 13 в рамках S2 целиком не перечитывались. Если verifier считает обязательным полный повторный проход маршрута `08 → … → 36.3`, это открытый пункт.

## 3. Техническая модель S2

### 3.1 Единицы: что измеряется точно, что оценивается

| Величина | Поле | Природа |
| --- | --- | --- |
| Размер запроса | `wire_bytes`, `*_bytes` | **Точно.** UTF-8 байты финального тела, сериализованного так же, как httpx 0.28.x (`json.dumps(ensure_ascii=False, separators=(",",":"), allow_nan=False)`). Snapshot с `sort_keys` — другой объект (факт S1). |
| Хеш запроса | `wire_sha256` | **Точно**, по тем же байтам |
| Резерв выхода | `output_reserve_tokens` | **Точно**: это параметр запроса `max_tokens` (executor/MCP/compressor 32768, planner 8192, verifier 2048, audit diagnostic 160) |
| Вход в токенах | `*_tokens_est` | **Оценка.** Консервативная, по модели и роли; не гарантированная граница токенайзера |
| Обязательство (liability) | `*_liability_tokens` | Производная величина: оценка + резерв, пока попытка в полёте или UNKNOWN; после known — фактические processed-токены провайдера |
| Попытки | `*_attempts` | **Точно.** Физические попытки, включая retry, replan, repair и diagnostic |
| Provider usage | `Usage` | Факт провайдера. `precached_prompt_tokens` хранится отдельно; отсутствие поля = None, а не 0 |
| Деньги | — | **Не вычисляются.** Тарифа нет, и тариф precached неизвестен |

### 3.2 Маршруты (инвентаризация S1 → политика)

| route_id | роль/профиль | scope | класс | достижимость |
| --- | --- | --- | --- | --- |
| executor | executor | RUN | WORK | ACTIVE |
| audit_diagnostic | executor | RUN | OPTIONAL_DIAGNOSTIC | ACTIVE |
| planner_session | planner | RUN | WORK | ACTIVE |
| planner_direct | planner | RUN | WORK | UNREACHABLE_PROVEN |
| verifier_final | dredd | RUN | **MANDATORY_VERIFICATION** | ACTIVE |
| verifier_permission | dredd | RUN | WORK | ACTIVE |
| planner_review | dredd | RUN | WORK | ACTIVE |
| compressor | compressor | COMPRESSOR_JOB | WORK | ACTIVE |
| mcp_chat | mcp | MCP_SESSION | WORK | LEGACY_REACHABLE |
| oauth | auth | NOT_BUDGETED | AUTH | ACTIVE → `NOT_APPLICABLE` |

Модуль политики знает маршруты, но не имена call sites. Таблица `route_id → (модуль, владелец)` закреплена в тесте (`ROUTE_SEND_SITES`) и сверяется с `s1.EXPECTED_SEND_SITES`. Привязывать физический send site к константному route_id предстоит S3b (см. F-1).

### 3.3 Оценка входных токенов (`estimate_input_tokens`)

- `CONSERVATIVE_CALIBRATED`: `ceil(wire_bytes / bytes_per_token)`, где профиль (модель, роль) — это нижняя огибающая наблюдённых bytes/token, делённая на `(1 + margin)` и **округлённая вниз** до 4 знаков.
- `HARD_BOUND_ASSUMPTION`: `tokens = wire_bytes`. Действует только при допущении A-BYTE: каждый токен, включая токены шаблона чата, покрывает не меньше 1 байта JSON-тела. Допущение не нарушено ни на одной из 340 известных пар (минимум 2.4772 байт/токен), но доказательством оно не является. Граница очень грубая: переоценка 2.5–7×. Включается только явно (`missing_profile: HARD_BOUND`).
- `NEEDS_CALIBRATION`: профиля нет, а политика запрещает hard bound. Решение: DENY с понятной причиной, без оптимистичного PASS.
- **Breach rule.** Если в этом scope провайдер сообщил вход больше оценки (одного `prompt_tokens` достаточно), профиль (модель, роль) больше не используется: дальше работает HARD_BOUND или NEEDS_CALIBRATION.
- Оценка не разбирает отдельно system, history, tool schemas и служебные структуры. Все они входят в wire bytes и неявно учтены калибровкой по реальным пакетам. Изменение доли tool schemas или языка — это риск сдвига отношения; от него защищают margin и breach rule (см. §9, риски).

### 3.4 Обязательства одной попытки (переходы B2 §4)

`reserve_attempt` → RESERVED → `mark_sent` → SENT → `apply_terminal` → KNOWN_TERMINAL | UNKNOWN_TERMINAL → (поздний known) RECONCILED. `mark_not_sent` допустим только из RESERVED (доказанный NOT_SENT от S3b). Любой другой переход ведёт в ANOMALY.

| Состояние | Liability |
| --- | --- |
| RESERVED, SENT, UNKNOWN_TERMINAL | оценка входа + `max_tokens` |
| KNOWN_TERMINAL, RECONCILED | prompt + precached + completion; при отсутствии precached — `max(prompt, оценка) + completion` |
| ANOMALY | max(резерв, known, если usage есть) |
| NOT_SENT | 0, попыткой не считается |
| неизвестная строка состояния | считается ANOMALY: резерв сохраняется, новые отправки блокируются |

### 3.5 UNKNOWN и неполный usage

| Ситуация | Правило |
| --- | --- |
| timeout, transport_error, cancelled после SENT, без usage | UNKNOWN_TERMINAL, liability = полный резерв (**UNKNOWN ≠ 0**) |
| completed/parse_error **с** валидным usage | KNOWN (parse_error с usage — известная стоимость) |
| completed без usage | UNKNOWN_TERMINAL |
| usage: bool, отрицательное число, нецелое, `total ≠ prompt + completion`, `precached: null`, нет одного из счётчиков | INVALID → ANOMALY → `LEDGER_ANOMALY`, новые отправки в scope запрещены |
| precached отсутствует | None, не 0; вход = max(prompt, оценка) |
| поздний known после UNKNOWN | RECONCILED; корректируется та же попытка |
| повторный terminal с тем же usage или UNKNOWN | идемпотентно |
| повторный terminal с другим known usage | ANOMALY (конфликт); liability не снижается |
| terminal без резерва (orphan) | ANOMALY, scope блокируется |
| terminal до SENT | ANOMALY |
| неизвестный outcome | ANOMALY |

**Что известно после terminal:** outcome, usage (prompt/completion/precached, если переданы), был ли breach. **Что остаётся неизвестным:** usage для UNKNOWN, фактическая цена, судьба запроса после transport error. **Что нужно от S3a:** durable хранение этих состояний и переходов, приём поздних и повторных terminal, восстановление после crash с проверкой корректности состояний (S2 уже трактует неизвестную строку состояния как ANOMALY).

### 3.6 Решение `evaluate_request` — одна физическая попытка

Порядок проверок и коды:

1. `UNKNOWN_ROUTE` → DENY; OAuth → `NOT_LLM_TRAFFIC` / NOT_APPLICABLE.
2. `INVALID_MEASURE` → DENY. Срабатывает на отрицательный или нулевой резерв, bool или нецелые байты, пустую модель, не-SHA хеш. Нужно, потому что measure, собранный вручную, мог бы снизить liability.
3. COMPRESSOR/MCP в режиме DENY → `ROUTE_DISABLED_BY_POLICY`.
4. Любая аномалия учёта в scope → `LEDGER_ANOMALY`, consequence `NO_NEW_SENDS`.
5. `REQUEST_BYTES_EXCEEDED`; `NEEDS_CALIBRATION` (немедленный DENY); `REQUEST_TOKENS_EXCEEDED`.
6. `RUN_LIABILITY_EXCEEDED` или `VERIFICATION_RESERVE_PROTECTED`: committed (known + in-flight + unknown + anomaly) + новая liability + защищённый резерв > лимит.
7. `RUN_ATTEMPTS_EXCEEDED` или `VERIFICATION_RESERVE_PROTECTED` (по попыткам).
8. `ROLE_ATTEMPTS_EXCEEDED` — только для не-обязательных попыток.

Все причины возвращаются вместе и на русском. Если отказано обязательному Final Audit, consequence = `NO_SUCCESS_WITHOUT_AUDIT`: RUN не может завершиться SUCCESS без аудита.

### 3.7 Резерв верификации — не обход лимита

- `verification_reserve_tokens/attempts` лежат **внутри** `max_run_liability_tokens/attempts`. Валидация требует, чтобы резерв был меньше лимита, иначе на работу не остаётся бюджета.
- WORK, OPTIONAL_DIAGNOSTIC и прочие попытки dredd обязаны оставить резерв нетронутым. Использовать его может только `verifier_final` (MANDATORY_VERIFICATION), и даже он не выходит за общий лимит.
- У Final Audit отдельные лимиты на один запрос (`max_verification_request_bytes/_input_tokens_est`). Без них пакеты аудита R-029/R-030 (165–172 KB) блокировались бы рабочим лимитом запроса. Это закреплено тестом.
- Лимиты попыток по ролям не применяются к Final Audit и не учитывают его попытки. Иначе PERMISSION/PLANNER_REVIEW молча выключили бы аудит. Final Audit при этом считается в лимите попыток RUN.
- Если Final Audit выключен пользователем, резерв равен 0; на оценку и прочие решения это не влияет.

### 3.8 Policy snapshot

- `validate_policy(raw)` → `PolicySnapshot`. Схема: `schema_version` (только 1; иное — отказ, совместимость fail-closed), `revision_label`, `run{…}`, `estimation{profiles[], missing_profile}`, `output_reserve` (только `MAX_TOKENS`), `compressor`/`mcp` (`DENY` | `BUDGET` с 4 лимитами), `read{max_full_read_bytes}`.
- Строго: все секции обязательны (**неявных умолчаний нет**); неизвестные поля запрещены (опечатка или чужая единица); только целые без bool; диапазоны до структурных потолков (1 GiB, 10¹⁰ токенов, 10⁶ попыток — это потолки, не defaults).
- Перекрёстные правила: резерв < лимит; лимит на запрос ≤ лимит RUN. Профили: bytes/token конечно и лежит в (0, 64]; samples ≥ 1; source_sha256 = 64 hex; без дубликатов.
- Все ошибки собираются вместе, на русском, с путём поля. `revision_sha256` — sha256 нормализованного JSON: идентичность снимка для будущей привязки резерва (B2 §4).
- `preflight_run` (контракт UI preview для S5) выдаёт предупреждения:
  - `RESERVE_ZERO_WITH_FINAL_AUDIT`;
  - `RESERVE_ATTEMPTS_ZERO_WITH_FINAL_AUDIT`;
  - `RESERVE_BELOW_ONE_MAX_VERIFICATION`;
  - `HARD_BOUND_FALLBACK`;
  - `MCP_DISABLED`;
  - `COMPRESSOR_DISABLED`.

### 3.9 Независимость Planner / history / Final Audit

В политике нет ни одного переключателя Planner или history (тест `test_policy_has_no_switch_for_planner_history_or_final_audit`). Final Audit входит только как `RunContext.final_audit_enabled` и меняет лишь размер резерва (тест `test_final_audit_flag_changes_only_the_reserve`). Полный фактор-тест V-11 2×2×2 с effective snapshots относится к S5/S10.

### 3.10 Контракт S4

`evaluate_full_read(snapshot, file_bytes)`: если файл больше лимита — DENY `FULL_READ_EXCEEDS_CAP` с подсказкой «поиск или чтение диапазона», без тихой обрезки. Ни к чему не подключён.

## 4. Решения и рассмотренные альтернативы

| Решение | Альтернативы | Почему так |
| --- | --- | --- |
| Отдельный чистый модуль без I/O | Встроить в `server.py`/`provider_accounting.py` | Встраивание означало бы частичный enforcement в платном runtime (запрещено). Чистая функция тестируется offline и подключается в S3b одной точкой |
| Байты точно + калиброванный делитель | `bytes/4`; токенайзер | `bytes/4` опровергнут данными (§6). Токенайзер GigaChat локально недоступен; нельзя выдавать неизвестное за точное |
| Нижняя огибающая + margin | Медиана; квантиль; регрессия | Медиана и регрессия недооценивают половину случаев. Огибающая с margin 0.1 даёт 0 недооценок в LOO |
| Округление делителя вниз | `round()` | `round()` может сдвинуть делитель вверх и недооценить калибровочную точку (воспроизведено, §8.3) |
| `NEEDS_CALIBRATION` по умолчанию | HARD_BOUND по умолчанию | HARD_BOUND слишком груб и всё равно держится на допущении; выбор за пользователем |
| Резерв выхода = `max_tokens` | Квантиль completion | Провайдер вправе вернуть до `max_tokens`; квантиль не консервативен |
| Резерв аудита внутри лимита | Резерв сверх лимита | Резерв сверх лимита — это скрытый обход |
| Отдельные лимиты запроса для Final Audit | Общий лимит запроса | Общий лимит ложно блокировал нормальные R-029/R-030 (тест) |
| INVALID usage → ANOMALY и стоп | Считать 0 / игнорировать | B2: null и bool ≠ 0; противоречивый учёт не даёт безопасно продолжать |
| Мелкие scope COMPRESSOR_JOB/MCP_SESSION | Включить их в RUN | Они физически вне RUN (S1). Отдельный scope и явный DENY лучше тихого обхода |
| Привязка маршрутов в тесте, не в модуле | Метки в модуле | Метка `ask_gigachat` в модуле нарушила инвариант S1 (§8.3). Имена call sites принадлежат runtime и S3b |

## 5. Границы S2

**Сделано в S2:** контракт политики и оценки, семантика liability и UNKNOWN, валидация снимка, решение для одной попытки, preview-предупреждения, контракт full-read, mock calibration, offline-доказательства.

**Не сделано (и не объявляется):**
- **S3a** — durable reserve/terminal ledger, persistence, crash/concurrency, authoritative fail-closed storage. В S2 история попыток — это список в памяти вызывающего.
- **S3b** — вызов `evaluate_request` перед каждым физическим POST, отправка именно `serialize_request_body` (`content=`), привязка route_id к send site, доказанный NOT_SENT.
- **S3c** — резерв до tool mutation.
- **S4** — подключение full-read cap.
- **S5** — UI, сохранение настроек, рестарт, effective snapshot живого RUN.

Подготовленный engine **не является** работающим fail-closed production guard. Сегодня ни один платный запрос через него не проходит.

## 6. Mock calibration

**Данные.** Извлечены read-only из локальных Run Store (`provider_attempt_started/terminal`; при наличии нескольких terminal берётся первый) и `%LOCALAPPDATA%/GigaChatUltra/compressor_logs`. Строки содержат только числа и locator: run, sequence, route, model, wire_bytes, outcome, prompt, precached, completion.
- **Итог:** 342 попытки = 41 RUN + 1 compressor job.
- **Outcome:** completed 315, parse_error 25, provider_error 1, timeout 1. Известный usage — у 340 попыток.
- **Набор:** встроен в тест, `DATASET_SHA256 = 8a3ea10b75280ece550138af9a912b161997e17f5f3f17c894686961babf90ce`.
- **Provenance-режим** заново извлекает данные из RAW: embedded 342 = local 342, новых строк 0.
- **Ошибка извлечения, исправлена:** первая версия считала хранилища дважды (459 строк) из-за рекурсивного и корневого glob. После дедупликации — 342 строки; уникальность ключей проверяется.

**Огибающие bytes/token (margin 0), GigaChat-3-Ultra:**

| Профиль | n | min | медиана | max | делитель при margin 0.1 |
| --- | --- | --- | --- | --- | --- |
| dredd | 37 | 2.4772 | 3.2156 | 4.9671 | 2.2519 |
| executor | 203 | 4.5184 | 7.3635 | 7.7928 | 4.1076 |
| planner | 99 | 4.4426 | 4.7118 | 5.0998 | 4.0387 |
| GigaChat-3-Pro / compressor | 1 | 6.1322 | — | — | NEEDS_CALIBRATION (n < 5) |
| MCP | 0 | — | — | — | NEEDS_CALIBRATION |

**bytes/4:** недооценивает dredd в 24 из 37 попыток; худшее отношение факт/оценка — 1.615. Executor и planner не недооценивает (их тексты плотнее в байтах).

**Leave-one-out** (недооценок / медианная переоценка):

| margin | planner | executor | dredd |
| --- | --- | --- | --- |
| 0.0 | 1 / 1.06× | 1 / 1.63× | 1 / 1.30× |
| 0.1 | 0 / 1.17× | 0 / 1.79× | 0 / 1.43× |
| 0.2 | 0 / 1.27× | 0 / 1.96× | 0 / 1.56× |

**Цена консервативности:** для executor оценка входа в среднем в 1.79 раза больше факта. Liability одной попытки executor всё равно определяется резервом выхода 32768.

**Hard bound A-BYTE** (tokens ≤ bytes) выполняется на всех 340 известных попытках.

## 7. Синтетические RUN (реплей записанных RUN через engine)

`simulate_run` проходит записанные попытки по порядку: решение → резерв → SENT → terminal с записанным usage (timeout — без usage). Лимиты A/B/C — **варианты для решения пользователя, не умолчания**.

| Параметр | A | B | C |
| --- | --- | --- | --- |
| max_request_bytes | 262 144 | 524 288 | 1 048 576 |
| max_request_input_tokens_est | 48 000 | 96 000 | 200 000 |
| max_verification_request_bytes | 1 114 112 | 1 114 112 | 1 114 112 |
| max_verification_request_input_tokens_est | 120 000 | 160 000 | 240 000 |
| max_run_liability_tokens | 160 000 | 240 000 | 480 000 |
| max_run_attempts | 24 | 32 | 48 |
| verification_reserve_tokens | 40 000 | 48 000 | 64 000 |
| verification_reserve_attempts | 2 | 2 | 3 |

Где останавливаются тяжёлые RUN (номер попытки / всего; причины):

| RUN (факт: попыток, processed known) | A | B | C |
| --- | --- | --- | --- |
| R-025 (5; 221 513) | 3/5: BYTES + TOKENS + RESERVE | 4/5: RESERVE_PROTECTED | доходит до конца |
| R-026 (17; 1 036 828) | 3/17: BYTES + TOKENS + RESERVE | 4/17: RESERVE_PROTECTED | 8/17: RUN_LIABILITY |
| R-027 (25; 2 273 631) | 3/25: BYTES + TOKENS + RESERVE | 4/25: RESERVE_PROTECTED | 10/25: RUN_LIABILITY |
| R-031 (16; 848 354) | 9/16: BYTES + TOKENS + RUN_LIABILITY | 10/16: RUN_LIABILITY | 13/16: RESERVE_PROTECTED |

- **Обычные RUN:** 31 RUN (приветствия R-032…R-035 и бенчмарки B1/B2/B3, включая live) завершаются при всех трёх вариантах, как и прочие записанные RUN (R-029, R-030 и 4 без меток).
- **R-029/R-030** (SUCCESS с Final Audit) проходят. При общем лимите запроса вместо отдельного лимита верификации оба теряют Final Audit на последней попытке (тест).
- **UNKNOWN в реплее:** таймаут R-026 оставляет полный резерв: committed > суммы known.
- **Размер резерва (факт для решения).** Liability 32 наблюдённых Final Audit — 5.4k…78.2k токенов. Резервы A/B/C (40k/48k/64k) покрывают 30 из 32. R-029 (75 559) и R-030 (78 211) больше любого из них. Если работа исчерпает лимит до границы резерва, Final Audit такого размера получит DENY `NO_SUCCESS_WITHOUT_AUDIT`, а аудит размера R-033 пройдёт (тест). `preflight_run` предупреждает об этом кодом `RESERVE_BELOW_ONE_MAX_VERIFICATION`.

## 8. Тесты и evidence

### 8.1 Suite и команды

`test_rt002_s2_budget_policy.py` — guarded offline. Использует гейт S1: `evaluate_gate`, MANIFEST, коды выхода 0/1/3, `sys.addaudithook`-guards (сеть, subprocess, запись вне sandbox, `.git`/`.ultra`), отдельный TEMP sandbox. Хеши production проверяются до и после; если runtime-модуль импортирован до guards, это отказ.

```
.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py               # acceptance: MANIFEST 58
.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py --provenance  # + ProvenanceTests (59), читает локальные RAW
```

Классы:
- WireMeasureTests — 4;
- PolicyValidationTests — 9;
- CalibrationTests — 8;
- LiabilityTests — 12;
- DecisionTests — 16;
- SyntheticRunTests — 5;
- IsolationTests — 4;
- ProvenanceTests — 1 (только `--provenance`).

Покрытие сценариев постановки §8:
- короткий и крупный запрос, разные структуры content/tool schemas, bytes ≠ tokens (Wire*);
- неизвестная модель и изменённый профиль (`test_unknown_model_needs_calibration_or_hard_bound`, `test_breached_profile_is_not_trusted_again`);
- нехватка резерва для output и Final Audit (`test_reserve_*`, `test_verification_reserve_*`, `test_candidate_reserves_*`);
- retry и replan (`test_attempt_budget_counts_retries_replans_and_unknown_attempts`);
- UNKNOWN после timeout или ошибки, повторный terminal, cached/precached (Liability*);
- различия маршрутов, MCP и OAuth (`test_routes_and_scopes`, `test_route_registry_matches_the_s1_inventory`);
- границы, overflow, malformed конфигурация, единицы, отрицательные и чрезмерные значения (PolicyValidation*, `test_malformed_measure_is_denied_not_trusted`);
- отсутствие ложной блокировки (`test_small_greeting_request_is_allowed`, `test_greetings_and_live_benches_complete_under_every_candidate`);
- неизменность RAW и evidence (`test_policy_evaluation_does_not_mutate_inputs`);
- отсутствие side effects (guards + production hashes + `test_no_production_module_imports_the_policy_yet`).

### 8.2 Финальные прогоны (итоговые SHA модулей из §1)

| Прогон | Exit | Gate | run / F / E / S | Manifest | Guard viol | Log SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| S2 core | 0 | PASS | 58 / 0 / 0 / 0 | 58 | 0 | `26eb1bc4203eca08116a3531a63bcd9504c39a16421be72a1f9ff2972519eac7` |
| S2 `--provenance` | 0 | PASS | 59 / 0 / 0 / 0 | 59 | 0 | `50a8a6d225c022815d4a06d39e15ab1fe0f8ab411efaba77a74195a09cde2400` |
| S2 selector (1 тест) | 3 | PARTIAL_SELECTION | 1 / 0 / 0 / 0 | 58 | 0 | `ea3a0734eeee…` |
| S2 unresolved selector | 1 | FAIL (`SELECTOR_UNRESOLVED`, `ZERO_TESTS`) | 0 | 58 | 0 | `b0281afc5a8f…` |
| S2 `unittest discover` | 0 | — | Ran 0, OK (skipped=1): обход гейта не даёт PASS | — | — | — |
| S1 `test_rt002_s1_routes.py` | 0 | PASS | 69 / 0 / 0 / 0 | 69 | 0 | `541835887a6aad187a2da0119ca4ee6241b390fed06467414b48dfa41ecadc33` |
| S0 `test_rt002_s0_kernel.py` | 0 | — | 166 / 0 / 0 / 0 | — | 0 | `d826cb1f617197f278c5c64bf89ec89f2ac0adc8c43686cecc320cacdb70b144` |

Время: S2 ≈ 0.76 с, S1 13.4 с, S0 105.6 с. Git-зависимый `test_final_audit` не запускался. Платных, live, stress и destructive прогонов не было.

### 8.3 История FAIL (сохранена, поздний PASS её не стирает)

| # | Прогон | Результат | Причина → действие |
| --- | --- | --- | --- |
| 1 | S2, 51 тест | 2 FAIL (`test_reserve_is_not_a_bypass_of_the_run_cap`, `test_verification_reserve_is_protected_from_work_but_available_to_final_audit`), log `609181c4…` | Ошибка арифметики ожиданий в тестах (150000/190000 вместо 170000/195000). Исправлены ожидания, код не менялся → 51 PASS `0d01a778…`, затем 53 PASS `577a253d…` |
| 2 | S2 sensitivity v1 | раннер отказал: «Runtime modules imported before guards» | Мутация применялась до guards → переписано на import hook (мутация после guards) |
| 3 | **S1 регрессия при новом модуле** | **1 FAIL из 69**: `test_ask_gigachat_is_reached_only_from_mcp_tools`, log `c56b590e3dbb…` | Текстовый инвариант S1 запрещает `ask_gigachat` вне `server.py`, а метка `send_site` в модуле его содержала. Тест S1 вне write-scope и не менялся. Метки убраны из модуля, привязка перенесена в тест S2 → S1 69 PASS `8b858730…` |
| 4 | S2, репродукторы review | 56 тестов, 10 записей FAIL, log `456702c2…` | Три дефекта, найденных в review (§9): округление делителя, неизвестное состояние записи, лимит роли dredd против Final Audit |
| 5 | S2 после исправления | 1 FAIL `test_attempt_budget_counts_retries_replans_and_unknown_attempts`, log `350642d9…` | **Моя регрессия:** новая ветка «неизвестное состояние» захватила NOT_SENT. Добавлена явная ветка → 56 PASS `cceedd39…`, provenance 57 PASS `4c1271ff…` |
| 6 | S2, репродукторы review | 58 тестов, 8 FAIL + 3 ERROR, log `778df8c7…` | Ручной measure с отрицательным резервом получал ALLOW с liability −29 756; нет предупреждения о размере резерва → исправлено → 58 PASS `12a7ed93…` |

S0 до финала тоже прогонялся дважды, оба раза 166/166 (`4f7c289e…`, `fcf9ff40…`).

### 8.4 Sensitivity (мутации после guards, на финальном коде)

Скрипт `sensitivity.py` лежит вне репозитория. Он ставит import hook, который мутирует `ultra_budget_policy` в памяти при первом импорте раннером, то есть уже после установки guards. Каждая мутация должна дать gate FAIL.

| Мутация | Exit | Записей FAIL/ERROR |
| --- | --- | --- |
| `unknown_is_zero` (liability UNKNOWN = 0) | 1 | 10 |
| `reserve_usable_by_work` (все WORK-маршруты объявлены верификацией) | 1 | 7 |
| `bytes_div_4` (оценка = ceil(bytes/4)) | 1 | 68 |
| `bool_is_int` (bool принимается как int) | 1 | 6 |
| `no_late_reconcile` (поздний known игнорируется) | 1 | 2 |

Все мутации применены (`MUTATION_APPLIED True`). На предыдущей версии (53 теста) результат был тем же: 10 / 5 / 8 / 4 / 2.

## 9. MANUAL ENGINEERING REVIEW

**Просмотренные ветви.**
- `validate_policy`: каждый путь ошибки и сборка `RunLimits` только при отсутствии None.
- `estimate_input_tokens`: три режима и breach.
- `calibrate_profiles`.
- `validate_usage`: все ветви INVALID и MISSING.
- `AttemptRecord.liability_tokens` и `estimate_breached`.
- Все переходы `mark_sent`/`mark_not_sent`/`apply_terminal`, включая повторы и конфликты.
- `budget_view`: каждое состояние и чужой scope.
- `evaluate_request`: порядок проверок, выбор кода резерва, роль, consequence.
- `preflight_run`, `evaluate_full_read`.

**Дефекты, найденные в этом review и исправленные** (каждый сначала воспроизведён тестом, см. §8.3):
1. Метка `server.py:ask_gigachat` в модуле нарушала инвариант S1 → имена call sites убраны из модуля.
2. `round(bpt, 4)` мог увеличить делитель: синтетическая пара 247716 B / 100000 T давала оценку 99 999 < 100 000 → округление вниз.
3. Запись с нераспознанным состоянием не попадала ни в одну корзину: liability 0, ALLOW. Также ANOMALY без пояснений не блокировала → обе ситуации теперь ANOMALY и `LEDGER_ANOMALY`.
4. Лимит попыток роли dredd исчерпывался на PERMISSION/PLANNER_REVIEW и блокировал Final Audit: общая настройка неявно выключала обязательную роль → лимит роли не применяется к MANDATORY_VERIFICATION и не учитывает её попытки.
5. Measure, собранный вручную, с `output_reserve_tokens = −30000` → ALLOW с отрицательной liability → `INVALID_MEASURE`.
6. Собственная регрессия при исправлении 3 (NOT_SENT как аномалия) поймана существующим тестом и исправлена.

**Найдено и исправлено раньше в этой задаче:**
- Ложная блокировка Final Audit R-029/R-030 рабочим лимитом запроса → отдельные лимиты верификации.
- Резерв в `budget_view` зависел от route scope → упрощено.
- Отдельный код резерва для попыток.
- Breach фиксируется уже по одному `prompt_tokens`, когда precached не передан.

**Гипотезы.**
- *Подтверждена:* `bytes/4` не является верхней границей (Dredd).
- *Подтверждена:* wire ≠ sorted snapshot (S1) — измеряются именно wire-байты.
- *Подтверждена на данных:* A-BYTE.
- *Отвергнута:* «одного рабочего лимита запроса достаточно» — Final Audit крупнее рабочих запросов.
- *Отвергнута:* «резерв A/B/C покрывает любой наблюдённый аудит» — не покрывает R-029/R-030.
- *Отвергнута:* «медиана bytes/token годится для оценки» — недооценивает около половины случаев.

**Edge cases под тестами:**
- точные границы bytes и tokens (=, +1);
- резерв 0 и попытки 0;
- `missing_profile` HARD_BOUND и DENY;
- usage: null, bool, total mismatch, отсутствие precached;
- поздний known, конфликтующий known, orphan, terminal до SENT, неизвестный outcome;
- NOT_SENT после SENT;
- чужой scope (попытки RUN не протекают в compressor job);
- мутирование входов.

**Claim → Source → Oracle → Result → Uncertainty**

| Claim | Source | Oracle | Result | Uncertainty |
| --- | --- | --- | --- | --- |
| Wire bytes измеряются точно | `serialize_request_body` | Байт-в-байт с `httpx.Request(json=…)` на разных телах | PASS | Проверен только httpx 0.28.1; S3b должен отправлять `content=` |
| `bytes/4` не граница | 342 попытки | Сравнение с provider usage | 24/37 dredd недооценены, max 1.615× | — |
| Калиброванная оценка покрывает наблюдения | Огибающая, margin 0.1 | Все 340 строк + LOO | 0 недооценок | Эмпирика, не доказательство; другие модели, языки и схемы могут сдвинуть отношение |
| UNKNOWN ≠ 0 | `liability_tokens` | Тесты + мутация `unknown_is_zero` | 10 FAIL под мутацией | — |
| Резерв не обход | Валидация + `evaluate_request` | Тесты + мутация `reserve_usable_by_work` | 7 FAIL под мутацией | Классификацию маршрута должен гарантировать S3b (F-1) |
| Нормальные RUN не блокируются | Реплей 41 RUN | 31 обычный × 3 варианта | 0 блокировок | Реплей не моделирует изменение поведения агента после отказа |
| Тяжёлые RUN останавливаются | Реплей | `EXPECTED_BLOCKS` | Совпадает | Цифры зависят от выбранного варианта |
| Нет production side effects | Guards, хеши, AST | `isolation_violations`, `production_hashes`, тест импорта | 0 нарушений, хеши равны | Guards на audit hooks не песочница ОС |
| Final Audit не выключается ролями | `evaluate_request` | `test_dredd_role_cap_never_silently_disables_final_audit` | PASS после исправления | — |

**Открытые риски:**
- Breach обнаруживается только постфактум: одна попытка может превысить оценку, после чего liability корректируется по факту, а профиль отключается.
- Чистая функция не защищает от гонки двух параллельных решений (это S3a).
- Executor-резерв 32768 делает liability грубой для малых запросов.
- Калибровка — одна модель, три роли, данные до 2026-10-11.

## 10. FINDINGS / PROPOSALS

- **F-1 (S3b, PROPOSAL).** `evaluate_request` доверяет `route_id` вызывающего. Объявив рабочий запрос как `verifier_final`, можно тратить резерв. S3b должен ставить константный route_id в каждом из 7 send sites и доказывать это статическим тестом по образцу S1 (таблица `ROUTE_SEND_SITES` уже есть).
- **F-2 (S3b).** Отправлять ровно `serialize_request_body(body)` через `content=` и сверять `wire_sha256` с резервом, иначе смена версии httpx разведёт измеренное и отправленное.
- **F-3 (S3a).** Запись ledger должна хранить поля B2 §4, которых нет в чистом `AttemptRecord` S2: RUN/lineage, logical call, role/mode, `policy revision_sha256`, body hash. Восстановленные состояния нужно проверять (S2 трактует неизвестные как ANOMALY). Атомарный reserve-before-send — с одним writer.
- **F-4 (S3b, плановое изменение контракта).** `test_no_production_module_imports_the_policy_yet` намеренно упадёт при подключении в S3b; там его нужно заменить проверкой подключения.
- **F-5 (решение).** Резерв выхода = `max_tokens`; у executor 32768 на попытку, и это доминирует в liability (у приветствия ≈ 8.3k вход + 32768). Варианты:
  - (а) оставить;
  - (б) отдельной runtime-задачей снизить `max_tokens` executor (влияет на полноту ответа);
  - (в) квантиль completion — не рекомендуется, не консервативно.
- **F-6 (решение).** Резерв Final Audit в A/B/C меньше двух наблюдённых аудитов (R-029/R-030, ≈ 78k). Варианты: резерв ≥ 80k; принять риск `NO_SUCCESS_WITHOUT_AUDIT`; ограничить размер аудиторского пакета (отдельный runtime-scope).
- **F-7 (решение).** MCP `ask_gigachat` не учитывается (S1). Калибровки нет: MCP — 0 точек, compressor — 1. Политика даёт DENY или BUDGET с отдельным scope; при BUDGET без профиля нужен HARD_BOUND или калибровка.
- **F-8.** Precached-токены входят в liability как processed (консервативно). Тариф precached неизвестен, денежный лимит не обещается.
- **F-9 (на проверку verifier).** `precached_prompt_tokens: null` трактуется строго (INVALID → ANOMALY → стоп scope). Альтернатива — считать null «не сообщено» (None) с той же консервативной liability: меньше ложных остановок при изменении формата провайдера.
- **F-10.** Значение full-read cap (S4) не калибровалось. В тестах стоит синтетическое 65 536 — это не предложение по умолчанию.

## 11. USER DECISIONS

1. Набор лимитов: A, B, C или собственный (таблица §7).
   - A — строже всех: тяжёлые RUN останавливаются на 3-й попытке.
   - B — середина.
   - C — пропускает R-025 и останавливает остальные позже.
2. `margin` калибровки и `min_samples`. Наблюдения:
   - 0.1 — минимальный margin с 0 недооценками в LOO;
   - 0.2 — запас прочности ценой примерно +10% переоценки;
   - `min_samples` 5 исключает compressor с n=1.
3. `missing_profile`: DENY (предлагается) или HARD_BOUND.
4. MCP и compressor: DENY или BUDGET с лимитами (F-7).
5. Размер резерва Final Audit (F-6).
6. Резерв выхода и судьба `max_tokens` executor (F-5).
7. Лимиты попыток по ролям: None (нет) или значения. Они никогда не касаются Final Audit.
8. Трактовка `precached: null` (F-9).
9. Значение full-read cap для S4 (F-10).

## 12. DOC IMPACT (для координатора после независимой проверки)

- **20 §5а:** статус S2 и ссылка на этот отчёт; S3a — только после приёмки и решения пользователя.
- **21:** запись S2 — модель единиц, калибровка (числа §6), варианты A/B/C, findings F-1…F-10.
- **36.3:** профиль Ultra — команды S2-suite, MANIFEST 58 (+1 provenance), коды гейта, метод sensitivity.
- **13:** архитектура Ultra — новый модуль `ultra_budget_policy.py` (контракт, не подключён).
- **001 / 06:** closeout verifier.
- **B2 (33.3):** без изменений (immutable). Открытый вопрос «model-specific byte/token bounds and defaults (S2)» закрыт калибровкой по границам; defaults остаются USER DECISION.

## 13. Параллельная активность, Git, незакоммиченное

- Во время работы менялись `web_alarm/ui.py` (12:31) и `test_web_alarm_operator_ui.js` (12:33), а также ряд документов (05, 06, 08, 18, 20, 21, 34, 36, 36.1, 36.3, `000_Задачи Codex.md`). Их меняли другие участники; я их не трогал (DOC-PARALLEL-01). Инвентаризация S1 включает `web_alarm/*.py`; финальный S1 PASS отражает состояние на момент прогона.
- Git не использовался, `.git` не читался. `GIT_DATA_REQUIRED` не возникло.
- Незакоммичено (коммитит пользователь): `ultra_budget_policy.py`, `test_rt002_s2_budget_policy.py`, этот отчёт, ротация `000_Задачи Claude.md`.

## 14. NEXT

Независимая проверка S2 (ChatGPT): source, тесты, evidence, мутации, решения пользователя по §11. S3a самостоятельно не начинаю.
