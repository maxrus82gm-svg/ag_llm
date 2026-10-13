# CLAUDE-RT002-S1-RECON-001 — предварительное исследование Ultra перед S1

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Независимый проверяющий:** ChatGPT.
**Статус:** RESEARCH RESULT READY / AWAITING INDEPENDENT REVIEW. Это разведка перед S1, а не S1 и не его приёмка.
**Дата:** 2026-10-13. **Тип:** READ-ONLY RESEARCH. Runtime, тесты, общие документы не менялись; платных вызовов и live RUN не было.

Пометки: [Ф] факт с evidence · [Г] гипотеза · [Н] не проверено · [Р] рекомендация · [О] оценка.

## 0. Baseline и источники

**Исходники (SHA-256, прочитаны как файлы 2026-10-13 21:00 +05):**

| Файл | SHA-256 | Строк |
| --- | --- | --- |
| server.py | `44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54` (= версия независимого S0 166/166 из 20 §5а) | 7238 |
| run_store.py | `a57a250a20ea49ab3cc5b85cd8eaccdc2666baf694209ce4382bb3456d50b8b6` | — |
| audit_storage.py | `5d91a6f9842b1dd7e79afd69f7cd5bd984ec828c79a39939144c2d87b558851c` | — |
| planner_runtime.py | `ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e` | 876 |
| task_planner.py | `c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346` | — |
| verifier_runtime.py | `7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228` | 730 |
| compressor_runtime.py | `c69ab1d9594b4cb36aeb32703b10de091bea5ce5d876c5962068a9b2fb20940f` | 645 |
| gigachat_transport.py | `ee1db75ed04ea432224324d9ffb8271e211985e2d4f3a25f72dff89db251a879` | — |
| provider_accounting.py | `dd83dbf7a22154347ac6f17ca2110e78757338248bd466f86a0d3599db510902` | — |

Все номера строк ниже относятся к этим версиям.

**Документы:** маршрут `08 → 000 → 34 → 18 → 01 → 36 → 36.1 → 36.3 → 20 §5а` — прочитан адресно: правила, текущие статусы RT-002 и S0/S1, профиль Ultra, §5а целиком. Из `18` — тексты DOC-GIT-01@1 и DOC-AGENT-ADDRESS-01@1. Контекст `13` и `21` — по ссылкам из §5а и собственному анализу RT-002, без полного чтения.

**Данные:** локальный Run Store `.ultra/audit` (сырые потоки R-026, R-031 и все `*.jsonl` с provider attempts), `%LOCALAPPDATA%\GigaChatUltra\compressor_logs` (один файл). `.venv\Lib\site-packages\httpx` 0.28.1 — функция `encode_json`.

**Аттестация и нарушение:**
- В самом начале, до чтения правила DOC-GIT-01, я прочитал как файлы `.git/HEAD` и три последние строки `.git/logs/HEAD`.
- DOC-GIT-01@1 прямо запрещает «прямое чтение истории/`.git`». Отмечаю это как нарушение; полученные сведения в анализе не использованы.
- После чтения правила к `.git` не обращался. Git-команд не было.
- Платных вызовов, live RUN, тестов и запуска агентов не было.

## 1. Архитектурная карта передачи контекста

```text
UI (ultra_ui.run_agent_task, :5825) ─┐            MCP stdio (server.py:7167–7236)
                                     │            ├─ gigachat_ask / gigachat_file_task → ask_gigachat  [POST 1]
                                     ▼            └─ gigachat_agent_task → run_agent_task (DIRECT, permissions=None)
run_agent_task → _run_agent_task_impl
  ├─ seed: _select_executor_seed_messages (:3633)  ON → [task]; OFF/DIRECT → вся история чата (без предела)
  ├─ messages = [system(core+policy+global 24 КБ+project 4,4 КБ), seed…]; executor_base_messages (:4490)
  ├─ Planner ON: TaskLifecycle → planner_call → PlannerSession.call            [POST 4]
  │      └─ при отказе плана → planner_review → run_planner_dredd_review       [POST 6]
  ├─ цикл Executor (while True, :4557…):
  │      body = {"messages": messages, functions…} (:4687)  ← ОДИН живой список
  │      client.post (:4800)                                                   [POST 3]
  │      tool → result_for_model = dict(result) + _verification_state + _tool_budget
  │      messages.append({"role":"function", content: json(весь result)}) (:5929–5950)
  │      stage_context(reset) (:4492): «if not lifecycle: return» → в DIRECT сброса нет никогда;
  │      в ON сброс только при смене stage / replan / финальном ответе (:5916, :6320)
  ├─ PERMISSION verifier (:6005) и FINAL verifier / Dredd (:6512)              [POST 6]
  └─ FAIL Final Audit → _request_audit_diagnostic(messages) (:6782 → :3366)    [POST 2]
        fork = deepcopy(messages) — полный контекст Executor
Отдельно: UI-компрессор сообщений → run_message_compressor_task_detailed        [POST 7]
Мёртвый в production путь: run_planner(session=None) (planner_runtime.py:806)  [POST 5]
```

## 2. Места разрастания LLM-запросов

1. **[Ф] Полные результаты инструментов копятся в `messages`.** Ограничения по размеру нет: результат дописывается целиком (server.py:5929–5950).
   - `read_file` отдаёт до 2 MiB (server.py:141, `_agent_read_file` :1222).
   - Другие крупные источники — `git_diff` и `python_compile` (до 128 КиБ вывода) и `read_file_range` (до 64 КиБ за вызов).
2. **[Ф] В DIRECT сброса нет вообще** (server.py:4493). Всё прочитанное живёт до конца RUN.
3. **[Ф] В режиме ON сброс только на границе stage.** Долгая stage копит контекст, как R-031.
4. **[Ф] В DIRECT передаётся вся история чата без предела:** `_select_executor_seed_messages` (:3633) и `load_chat_working_messages`.
5. **[Ф] Фиксированная надбавка каждого executor call — около 37–41 КБ:** global context, project, policy, schemas.
6. **[Ф] Audit diagnostic копирует полный контекст Executor** (:3375); каждый FAIL Final Audit — ещё один полноразмерный call.
7. **[Ф] Interventions добавляют calls, не расходуя tool budget:** guard / evidence gate / tool reserve / verification gate / final repair (:5123 и др.).
8. **[Ф] Ни в одной точке отправки нет предела байтов или токенов запроса.** Поиск `request_*_chars|bytes [<>]` / budget даёт только бюджеты материала Final Audit (:3208).

## 3. Таблица физических LLM-маршрутов (POST на `CHAT_URL`)

Найдены поиском `.post(` по всем `.py` проекта (исключены `.venv`, `Alarm`, `Dev-archive`, тесты). Неочевидные пути отправки (через `send`, `stream` или сторонние SDK) отдельно не искались.

| # | Место | Функция / роль / режимы | Вызывающие | Сборка тела | Учёт | Таймаут / max_tokens / повторы |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | server.py:573 | `ask_gigachat` / без роли | MCP `gigachat_ask`, `gigachat_file_task` (prompt до 2 MiB, MAX_TASK_FILE_BYTES) | :564 | **нет** provider attempt, нет Run Store | 180 с / 32 768 / нет |
| 2 | server.py:3446 | `_request_audit_diagnostic` / executor · AUDIT_DIAGNOSTIC | FAIL Final Audit (:6782), tick AUDIT_DIAGNOSTIC | :3375–3384, полный fork `messages` | started / terminal | 25 с / 160 / нет |
| 3 | server.py:4800 | цикл Executor / executor · DIRECT, STAGE:id | UI, MCP agent; все interventions и repair | :4687–4697, живой `messages` | started / terminal | 180 с / 32 768 / нет HTTP-повторов; число шагов — tool_limit ≤200, lifecycle 64 (только ON) |
| 4 | planner_runtime.py:669 | `PlannerSession.call` / planner · INITIAL / READINESS / REPLAN | TaskLifecycle.ask (task_planner.py:283) через `planner_call` (server.py:4365) | :610–617; сессия ≤32 сообщений / 128 КиБ | started / terminal через callback (ошибки подавляются) | 90 с / 8192 / до 3 попыток на ask |
| 5 | planner_runtime.py:806 | `run_planner` без сессии / planner | в production не вызывается (server всегда передаёт session) | `build_planner_body` :470 | started / terminal | 90 с / 8192 / — |
| 6 | verifier_runtime.py:229 | `_request_gigachat` / dredd · FINAL, PERMISSION, planner review | server.py:6512 (FINAL), :6005 (PERMISSION), task_planner.py:322 → `run_planner_dredd_review` | verifier_runtime.py:209, :635 | started / terminal; **usage теряется при protocol error** | 60 с / 2048 / нет |
| 7 | compressor_runtime.py:365 | `_request_gigachat` / compressor | UI-компрессор сообщения (ultra_ui.py:4152), до 2 попыток | `build_compressor_request_body` :269 | started / terminal **вне Run Store**: compressor_logs + UI-очередь (`put_nowait`, при Full событие теряется) | 180 с / 32 768 / 2 попытки |

Не LLM: OAuth (gigachat_transport.py:50), `probe_gigachat_models.py` (GET models, ручной скрипт), `wa4o_ui_launcher.py` (`urlopen`, локальный Web Alarm).

**Непроверенные участки [Н]:**
- `Dev-archive`, `_ultra_agent_test`, `sandbox_verify` и тестовые файлы не просматривались.
- Используется ли MCP-сервер на практике и с какими permissions — не установлено.
- Поведение `get_access_token` при истечении токена и конкурентных RUN не проверялось.
- Вызов `ui_smoke_test` не изучался — возможна LLM-зависимость, не проверено.

## 4. Пять главных находок

**F-1. Механизм R-031 в текущем коде не изменился.** [Ф]
- Цепочка: полный `read_file` (:1222, до 2 MiB) → `messages.append` всего результата (:5929–5950) → тот же список уходит в каждый следующий запрос (:4687, :4800) → сброса нет внутри stage (:4492–4494) и вообще нет в DIRECT.
- Сырые потоки R-031, без summary: сообщение `message_16_function` (blob `a473a0bf26…`, 287 624 B) есть в executor calls #8–#15 (**8**), `message_26_function` (`099e8ae6d6…`) — в #13–#15 (**3**). Request bytes: 53 580 → 341 415 → 634 481.
- Оба чтения (tool #7 и #12, записи server.jsonl seq 71 / 111) имеют одинаковый content sha `7bd32cad56c6`, 238 540 символов. При этом **хеши самих function messages различаются**: в них входят `_tool_budget` и `_verification_state`.

**F-2. Семь отправок, единого pre-HTTP узла нет.** [Ф]
- Каждая точка сама строит тело, сама считает accounting и сама вызывает `httpx`.
- Ни в одной нет предела запроса или бюджета RUN.
- Точка 1 (MCP) вообще не учитывается, точка 7 учитывается вне Run Store.

**F-3. Accounting — best-effort, а не авторитетный журнал.** [Ф]
- S0 сделал обязательными только `tool_started`, `final_audit_passed`, `run_finished SUCCESS` (server.py:3792–3797). События `provider_attempt_*` при сбое хранилища лишь помечаются `audit_storage_error`.
- Callbacks Planner / Verifier / Compressor подавляют исключения (planner_runtime.py:553–559, 744–750).
- Verifier при `VerifierProtocolError` до возврата usage (verifier_runtime.py:262–277) записывает terminal с UNKNOWN, хотя usage был в ответе.
- `precached_prompt_tokens` не агрегируются.
- Planner Dredd review не расходует lifecycle-бюджет: `tick` есть только для PLANNER, EXECUTOR_OR_DISPATCH, PERMISSION / FINAL_VERIFIER, AUDIT_DIAGNOSTIC.

**F-4. Происхождение второго terminal в R-026 — внешняя запись в обход учёта.** [Ф]; источник — [Г]
- Attempt `…0e8611`: seq 146 `timeout` (ReadTimeout), затем seq 147 `aborted_external_recovery` с mode `EXTERNAL_INTERRUPTION_RECOVERY`; run_failed `external_interruption_recovery`.
- Исхода `aborted_external_recovery` нет в `TERMINAL_OUTCOMES` (provider_accounting.py:12–19), а `build_provider_attempt_terminal` отклоняет неизвестные исходы (:140–141). В `.py` проекта (без `.venv` / `Dev-archive`) и в `Alarm/*.py` такого значения нет.
- Значит, запись сделал внешний восстановительный инструмент, дописав её прямо в поток в обход `record_provider_attempt_terminal`. Поэтому summary R-026 не отражает дубликат.
- Это закрывает открытый в RT-002 вопрос о происхождении дубликата. Кто именно записал — [Н].

**F-5. Привязка байтов и хешей для S3b и оценка единиц.** [Ф]
- `request_snapshot_sha256` считается от канонического JSON с `sort_keys=True` (provider_accounting.py:32–38, 100–127).
- httpx 0.28.1 из `.venv` отправляет `json_dumps(ensure_ascii=False, separators=(",",":"))` без сортировки (`.venv/.../httpx/_content.py:176–183`).
- Итог: **длина совпадает с отправленными байтами, хеш — нет**.
- Оценка «байты/4» по всем 116 сохранённым calls с известным usage:
  - фактический вход (prompt + precached) / оценка — от 0,513 до 1,244;
  - **1 call из 116 превысил оценку**: Dredd FINAL в RUN `20261011_011653_d33022` — 27 046 B, оценка 6 762, фактически 8 411 prompt tokens;
  - по ролям: executor 0,513–0,885 (79), planner 0,802–0,875 (28), dredd 0,805–1,244 (9).
- «Байты/4» не гарантирует предела по токенам; подтверждает требование hard contract B2.

## 5. Предложения для S1

**Обязательные:**
1. Детерминированный offline-скрипт сырого R-031 «8 + 3» по потокам Run Store, без summary, с выводом матрицы calls × большие блоки. Метод воспроизведён в этом исследовании.
2. Инвентаризация семи точек POST и всех вызывающих режимов (таблица §3) плюс **offline-тест полноты**: fake transport перехватывает `httpx.AsyncClient.post` и любой `CHAT_URL`; набор сценариев проходит все режимы; отправка из неизвестного места — FAIL.
3. Граница Chat / Compressor / MCP: явно отметить точку 1 (без учёта) и точку 7 (отдельный журнал) как маршруты, которые S3b обязан охватить.
4. Ledger-состояния по каждому маршруту: started / terminal / UNKNOWN / timeout / cancel / внешняя recovery-запись. Включить находку R-026 (F-4) и потерю usage verifier (F-3).
5. Зафиксировать для S3b: хешировать нужно именно отправленные байты — сериализовать тело один раз и передавать `content=bytes`. Оценка «байты/4» не консервативна (F-5).

**Необязательные:**
- Измерить по Run Store фиксированную надбавку на call по ролям — вход для S2 и 151F.
- Перечень крупных источников function messages: read_file, read_file_range, git_diff, python_compile, list_dir — вход для S4 и S6a.
- Ключ дедупликации чтений — (path, content_sha256, write_revision), а не хеш сообщения (F-1) — вход для S6b.

## 6. Что оставить, что изолировать, что проверять локально

- **Оставить без изменений:**
  - примитивы `provider_accounting.py` (уникальные attempt ID, проверка исходов, измерение блоков);
  - дедупликацию terminal в `run_store`;
  - пределы `PlannerSession`;
  - обязательные durable-события S0;
  - хранение context_delta.
- **Изолировать или упростить:**
  - семь копий кода отправки и accounting → один транспортный узел `send(role, mode, body_bytes, ledger)`;
  - события provider attempt сделать обязательными (fail-closed), как события S0;
  - MCP `ask_gigachat` — либо через общий узел, либо отключить;
  - мёртвый путь `run_planner(session=None)` — пометить или убрать (отдельным решением).
- **Детерминированно и локально, без платных моделей:**
  - матрица R-031 по Run Store;
  - fake-transport полнота маршрутов;
  - сравнение длины канонического и отправленного тела;
  - отсутствие сброса в DIRECT на fake provider;
  - проверка, что recovery-запись не меняет summary;
  - верхняя оценка «байты/4» на сохранённых calls.

## 7. MANUAL ENGINEERING REVIEW

- **Альтернативы защиты:**
  - только предел инструмента — не защищает от истории DIRECT, global context и git_diff;
  - только предел запроса — блокирует RUN вместо деградации, хуже UX;
  - сжатие старых результатов через LLM — лишние calls и потеря evidence;
  - кэш провайдера — непредсказуем: в R-031 precached = 0 у многих соседних calls.

  Вывод: нужен предел запроса как backstop, предел чтения и передача по ссылке — это согласуется с B2 (S3b + S4 + S6).
- **Краевые случаи для будущей дедупликации:**
  - файл изменён между чтениями (write_revision, sha);
  - пометка `_evidence_status = STALE` (:5930) должна сохраниться при ссылке;
  - `read_file_range` многократно по 64 КиБ;
  - различающиеся служебные поля в сообщении.
- **Возможные ошибки моего анализа:**
  - R-031 выполнен кодом до S0 — механизм сверен с текущими строками, но не воспроизведён;
  - Ultra однопроцессная (`ultra_ui.lock`) — параллельные RUN и конкуренция ledger не изучались;
  - поиск точек POST текстовый — косвенные отправки через другие API не исключены полностью.

## 8. DOC IMPACT

Общие документы не менялись. Предложения verifier (решение за ним):
- `21` — фактическая запись разведки S1 (маршруты, 8 + 3, F-4, F-5);
- `20` §5а, строка S1 — ссылка на таблицу маршрутов;
- `13` — требование обязательной долговечности provider attempt-событий.

## 9. Итог

**RESEARCH RESULT READY / AWAITING INDEPENDENT REVIEW.** S1 не выполнялся и не объявляется VERIFIED. Следующую задачу самостоятельно не начинаю.

**Вопрос к координатору (GIT_DATA_REQUIRED, не блокирует):** каким инструментом или задачей 2026-09-30…2026-10-01 была дописана recovery-запись R-026 (seq 147)? Это нужно для полной атрибуции F-4.
