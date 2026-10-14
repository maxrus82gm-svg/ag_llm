# CLAUDE-RT002-S1-001 — RT-002/B2 S1: Baseline and Routes

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Независимый verifier:** ChatGPT / LLM_11.
**Статус:** S1 RESULT READY / AWAITING INDEPENDENT VERIFICATION. Не DONE / VERIFIED. Бюджеты, транспорт и контекст не реализовывались; S2 не начат.
**Дата:** 2026-10-14. **Тип:** evidence research + воспроизводимые offline-тесты.

Пометки: [Ф] факт с evidence · [Г] гипотеза · [Н] не проверено · [О] оценка.

## 1. Исходные версии и provenance

**Назначение.** БЛОК 1 был в статусе PREPARED / AWAITING USER ASSIGNMENT. 2026-10-14 пользователь переслал в чат стартовую команду; по действующему правилу персональной памяти пересылка считается подтверждением назначения.

**Исходники** (SHA-256, прочитаны как файлы 2026-10-14 10:19 +05; на момент последнего прогона те же):

| Файл | SHA-256 |
| --- | --- |
| server.py | `44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54` (= версия независимого S0) |
| run_store.py | `a57a250a20ea49ab3cc5b85cd8eaccdc2666baf694209ce4382bb3456d50b8b6` |
| audit_storage.py | `5d91a6f9842b1dd7e79afd69f7cd5bd984ec828c79a39939144c2d87b558851c` |
| planner_runtime.py | `ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e` |
| task_planner.py | `c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346` |
| verifier_runtime.py | `7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228` |
| compressor_runtime.py | `c69ab1d9594b4cb36aeb32703b10de091bea5ce5d876c5962068a9b2fb20940f` |
| gigachat_transport.py | `ee1db75ed04ea432224324d9ffb8271e211985e2d4f3a25f72dff89db251a879` |
| provider_accounting.py | `dd83dbf7a22154347ac6f17ca2110e78757338248bd466f86a0d3599db510902` |
| ultra_ui.py | `7bd32cad56c6f94056a291cc7beb570475be4bb3af88fd6749d66ceb021e547d` |
| context_storage.py | `8cf90ad41afb0d60173ecc8107c2ba9927d3dc9fc3e02607293c2cd043fde757` |
| workspace_runtime_settings.py | `699026e592c27189f55ae80ace3eaf0449e874a887235e24083d9a52126b8c3b` |
| model_registry.py | `2b6a9ea77974eea47cb10c5fb8e8ef5787d6a369826be10fa60d0a84dc318e53` |

**DRIFT относительно разведки RECON-001:** нет, все хеши совпадают. Связь с GitHub baseline `main@e60c196d…` локально не проверялась: Git запрещён, `.git` не читался.

**RAW-доказательства** (только чтение; в модуль и отчёт попадают локаторы и хеши, содержимое не копируется):

| Локатор | SHA-256 | Байт |
| --- | --- | --- |
| R-031 `executor.jsonl` | `a9f8f611…af8f3b` | 723 052 |
| R-031 `server.jsonl` | `f23146df…840f25` | 563 926 |
| R-031 `executor_base.json` | `f3b431ff…7af53` | 35 568 |
| R-031 `summary.json` | `de1f26ca…65afa` | 3 468 |
| R-026 `executor.jsonl` | `2cd20732…b066c` | 735 033 |
| R-026 `summary.json` | `210849cd…b1bb89` | 3 551 |

Полные хеши закреплены в `EVIDENCE_PINS` модуля. Каталоги: `.ultra/audit/chat_b36a4eba…/20261001_182057_e90f93` (R-031) и `…/20260930_233733_1f2fee` (R-026).

**Прочитано:**
- маршрут 08 → 000 → 34 → 18 → 01 → 09/13 → 20 §5а → 21 → 36 → 36.1 → 36.3 — адресно;
- правила DOC-GIT-01, DOC-PARALLEL-01, DOC-TASK-BLOCK1-01, TEST-COLLAB-01, TEST-AREA-01, TEST-ENG-01 — тексты определений;
- `01`, `13`, `21` — только по ссылкам из §5а и материалам разведки; `09` — поиском по ключевым словам.

**Аттестация:** Git-команд и чтения `.git` не было. Платных вызовов, live RUN и сети не было (guard зафиксировал 0 нарушений). Production runtime, Web Alarm, файлы Codex и общие документы не менялись.

## 2. R-031 — воспроизводимая матрица (только RAW, summary не используется)

Executor, 15 calls, все в `stage_1`. P — prompt_tokens, PC — precached_prompt_tokens, C — completion_tokens. «A» = блок `message_16_function` (sha `a473a0bf2680…`), «B» = `message_26_function` (sha `099e8ae6d64a…`), оба по 287 624 B.

| Call | messages | function msgs | request bytes | P | PC | C | крупные блоки |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0 | 40 352 | 5 409 | 0 | 63 | — |
| 2 | 5 | 1 | 42 743 | 5 949 | 0 | 38 | — |
| 3 | 7 | 2 | 48 325 | 7 361 | 0 | 54 | — |
| 4 | 9 | 3 | 49 622 | 7 686 | 0 | 79 | — |
| 5 | 11 | 4 | 50 830 | 8 040 | 0 | 78 | — |
| 6 | 13 | 5 | 52 158 | 8 431 | 0 | 59 | — |
| 7 | 15 | 6 | 53 580 | 822 | 8 000 | 42 | — |
| 8 | 17 | 7 | 341 415 | 68 199 | 5 376 | 78 | A |
| 9 | 19 | 8 | 342 743 | 73 966 | 0 | 79 | A |
| 10 | 21 | 9 | 343 951 | 400 | 73 920 | 58 | A |
| 11 | 23 | 10 | 345 224 | 74 679 | 0 | 59 | A |
| 12 | 25 | 11 | 346 646 | 75 070 | 0 | 42 | A |
| 13 | 27 | 12 | 634 481 | 64 815 | 75 008 | 78 | A, B |
| 14 | 29 | 13 | 635 809 | 131 830 | 8 384 | 79 | A, B |
| 15 | 31 | 14 | 635 066 | 131 782 | 8 768 | 180 | A, B |

**Числа:**
- A присутствует в calls 8–15 (**8**), B — в 13–15 (**3**): всего **11 отправок**.
- Executor по RAW terminals: prompt 664 439, completion 1 066, precached 179 456.
- Вместе с Planner (3 393, `planner.jsonl`) — provider-reported total 668 898.

**Привязка к READ** [Ф]. Сообщения восстановлены как `executor_base.json` + `context_delta` — независимая повторная реализация:
- канонический хеш `messages[16]` и `messages[26]` совпадает с хешем блока в `provider_attempt_started`;
- распарсенные результаты: `path = ultra_ui.py`, `content_sha256 = 7bd32cad56c6…` (совпадает с текущим ultra_ui.py), `_tool_budget.used` = 7 и 12;
- это `tool_finished` tool #7 и #12 (server.jsonl seq 71 и 111): оба — `read_file("ultra_ui.py")`, 238 540 символов, одинаковый content sha.

Хеши самих function messages различаются: в них входят `_tool_budget` и `_verification_state`.

**Механизм и усилители** (сверено с текущим кодом):
- **Механизм накопления** [Ф]:
  - результат инструмента целиком дописывается в `messages` (server.py:5929–5950);
  - тот же живой список уходит в каждом запросе (:4687–4697, :4800);
  - сброса нет внутри stage (:4492; сброс только при смене stage / replan / финальном ответе, :5916, :6320);
  - в DIRECT нет совсем — `stage_context` начинается с `if not lifecycle: return` (:4493). Подтверждено AST-тестом и динамически.
  - Матрица показывает: ни один из 14 tool results не удалён до конца stage.
- **Усилители** [Ф] (не создают накопление, но увеличивают его цену):
  - `read_file` отдаёт до 2 MiB (:141, :1222);
  - повторное чтение того же файла не через подряд — Guard P1 ловит только подряд идущие `read_file` / `list_dir` (:171);
  - stage tool visibility ограничена capability, а не целями, плюс неоднозначные короткие пути (корневой ultra_ui.py вместо fixture);
  - фиксированная надбавка около 40 КБ на call (global context, policy, project, schemas).
- **Не причины** [Ф]: Planner (3 393 токена); context_delta — это экономия хранения, а не запроса; accounting только измеряет.

**Динамическое воспроизведение на текущем коде** (fake provider, без сети):
- DIRECT: `read_file(big.txt, ~210 КБ)` → `read_file(small.txt)` → stop. Маркер большого файла есть в запросах 2 и 3; размеры 12 083 → 221 048 → 222 016 B; `executor_diagnostic_reset` не было.
- Planner ON, две stage: stage_1 читает большой файл, stage_2 без capabilities. Маркер есть только во втором запросе stage_1; ровно один reset с `removed_function_messages = ["read_file"]`; запрос stage_2 — 7 048 B.
  - Последовательность ролей: planner INITIAL → executor stage_1 ×2 → planner READINESS → executor stage_2 → planner READINESS.
  - Большой файл не попал в контекст Planner READINESS (14 007 B).

## 3. Инвентаризация физических LLM-маршрутов

**Полнота:**
- AST-сканирование всех корневых модулей, кроме тестов, плюс `web_alarm/*.py`: вызовы `.post / .send / .stream / .request`.
- Найдено ровно 8 мест отправки через клиент httpx: 7 LLM плюс OAuth. Альтернативных методов отправки нет.
- `httpx` / `requests` / `aiohttp` импортируют только server, planner_runtime, verifier_runtime, compressor_runtime, gigachat_transport (плюс служебные скрипты).
- Тестами это закреплено как точное множество, с негативным контролем.

| # | Источник (функция) | Роль · режимы | Точка входа / вызывающие | Сборка тела | Таймаут · max_tokens · повторы | Источники контекста | Учёт | Класс |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | server.py:573 `ask_gigachat` | — | MCP stdio: `gigachat_ask`, `gigachat_file_task` (`@mcp.tool()`, `mcp.run` при запуске server.py) | :564 | 180 с · 32 768 · нет | prompt вызывающего; file task — до 2 MiB | **нет** (ни attempt, ни usage, ни Run Store) | LEGACY / REACHABLE (MCP) |
| 2 | server.py:3446 `_request_audit_diagnostic` | executor · AUDIT_DIAGNOSTIC | FAIL Final Audit (:6782), lifecycle tick | :3375–3384 | 25 с (`wait_for`) · 160 · нет | **полная копия** executor `messages` + кандидат + вопрос | started / terminal → `_emit` → Run Store (best-effort) | ACTIVE |
| 3 | server.py:4800 цикл Executor | executor · DIRECT, STAGE:id | UI `run_agent_task`; MCP `gigachat_agent_task` (DIRECT, permissions=None) | :4687–4697 | 180 с · 32 768 · без HTTP-повторов; шаги — tool_limit ≤200 (+ interventions), lifecycle 64 только в ON | system (core + policy + global + project), seed (DIRECT: вся история чата; ON: задача), stage context, накопленные function / assistant, schemas | started / terminal → `_emit` (best-effort) | ACTIVE |
| 4 | planner_runtime.py:669 `PlannerSession.call` | planner · INITIAL / READINESS / REPLAN | TaskLifecycle.ask (task_planner.py:283) через `planner_call` (server.py:4365) | :610–617 | 90 с · 8 192 · до 3 попыток на ask (2 без Dredd) | protocol system + JSON-контекст режима; сессия ≤32 сообщений / 128 КиБ | callback → `_emit`; ошибки callback подавляются | ACTIVE (Planner ON) |
| 5 | planner_runtime.py:806 `run_planner` без сессии | planner | единственный production-вызов — server.py:4366, всегда `session=planner_session` | `build_planner_body` :470 | 90 с · 8 192 | raw task + контекст | started / terminal через callback | UNREACHABLE PROVEN (статически, в production-модулях) |
| 6 | verifier_runtime.py:229 `_request_gigachat` | dredd · FINAL, PERMISSION; planner review | server.py:6512 (FINAL), :6005 (PERMISSION); task_planner.py:322 → `run_planner_dredd_review` | :209, :635 | 60 с · 2 048 · нет | FINAL — пакет Final Audit (≤1 MiB); PERMISSION — контекст запроса прав; review — транскрипт Planner + ошибка | started / terminal; **usage теряется при protocol error** | ACTIVE |
| 7 | compressor_runtime.py:365 `_request_gigachat` | compressor · COMPRESS | UI-компрессор сообщения (ultra_ui.py:4152) → `run_message_compressor_task_detailed` | :269 | 180 с · 32 768 · до 2 попыток | шаблон + исходное сообщение + final check | started / terminal → `compressor_logs` + UI-очередь (`put_nowait`, при Full событие теряется); роль `compressor` не принимается run_store | ACTIVE (ручное действие) |
| — | gigachat_transport.py:50 OAuth | — | `get_access_token` | — | 30 с | — | — | ACTIVE, не LLM |
| — | probe_gigachat_models.py (GET models), wa4o_ui_launcher.py (`urlopen` к локальному Web Alarm) | — | служебные / другая подсистема | — | — | — | — | вне production Ultra |

**UNKNOWN:**
- используется ли MCP-сервер на практике;
- поведение OAuth при конкурентных RUN;
- LLM-зависимость `ui_smoke_test` (по коду не вызывает POST, AST не нашёл);
- `Dev-archive`, `_ultra_agent_test`, `sandbox_verify` не сканировались — вне production.

## 4. Границы контекстов и учёта

| Маршрут | Физический запрос в evidence | usage | cached | terminal / прерывание | UNKNOWN | Надёжность |
| --- | --- | --- | --- | --- | --- | --- |
| 1 MCP | нет | нет | нет | нет | расход **не виден** | — |
| 2 Audit diag | блоки + длина + канонический sha | raw | в raw, не агрегируется | completed / timeout / provider_error / transport / parse / cancelled | `usage=None` → unknown_usage_calls | best-effort `_emit` |
| 3 Executor | то же + `executor_diagnostic_context` (полные messages) и context_delta | raw | то же | то же; kill процесса → started без terminal (incomplete) | то же | best-effort: **сбой записи provider attempt не останавливает RUN** (тест) |
| 4/5 Planner | блоки / длина / sha | raw | то же | то же | то же | callback, исключения подавляются |
| 6 Verifier | блоки / длина / sha + `verifier_logs` | raw; **None при protocol error** | то же | parse_error при наличии usage в ответе | ложный UNKNOWN | callback |
| 7 Compressor | блоки / длина / sha | raw в `compressor_logs` | то же | то же | — | отдельный ledger, вне Run Store |

**Run Store** [Ф, тесты]:
- UNKNOWN ≠ 0 — `total_tokens = None`, `complete = false`;
- повторный terminal через API помечается и не учитывается дважды;
- запись в поток в обход API не меняет summary;
- precached не агрегируется.

## 5. Точность HTTP evidence (fake transport)

[Ф] httpx 0.28.1 в `.venv` кодирует тело как `json.dumps(ensure_ascii=False, separators=(",",":"), allow_nan=False)` без сортировки; `Content-Length` равен числу байт тела. `request_snapshot_sha256` считается от `canonical_json_text` (`sort_keys=True`).

**Итог на всех accounted-маршрутах** (2, 3, 4, 5, 6, 7) и на синтетическом теле (UTF-8, tool schemas, произвольный порядок ключей):
- длина равна;
- канонический sha от распарсенного wire равен snapshot;
- **sha самого wire не равен snapshot**.

Совпадение бывает только для тела, уже отсортированного по ключам (контрольный тест).

**Привязка «одно тело ↔ одна попытка»:**
- сегодня возможна только семантически: пересериализовать wire канонически и сравнить с snapshot;
- байтово — нет;
- для маршрута 1 — вообще нет.

**Требование к S3b:** сериализовать тело один раз, хешировать и измерять именно эти байты и отправлять их через `content=bytes` с явными заголовками.

**Чувствительность:** при подмене кодировщика httpx на сортирующий 3 из 4 тестов привязки падают, как и должно быть; контрольный проходит.

## 6. Offline-тесты

**Модуль:** `test_rt002_s1_routes.py`, новый; SHA-256 `20a54a0ea9d3f5dad8ab33533d319d8b5e778fcab8ceec6d18f652afa24a86c0`, LF.

**Команда:** `.venv/Scripts/python.exe -B test_rt002_s1_routes.py` (Python 3.12.10; httpx 0.28.1). При обычном discovery модуль пропускается (setUpModule → SkipTest).

**Изоляция:**
- sandbox `%TEMP%\claude-rt002-s1-*`: LOCALAPPDATA / APPDATA / TEMP переводятся туда до импорта runtime; proxy-переменные и `GIGACHAT_CREDENTIALS` сбрасываются;
- audit hook запрещает:
  - сеть (кроме внутреннего socketpair asyncio);
  - дочерние процессы;
  - запись вне sandbox;
  - доступ к `.git` и к `.ultra` вне sandbox;
- RAW-доказательства копируются в sandbox до guard, после сверки SHA-256 и размера.

**Финальный прогон:**

| Набор | Тестов |
| --- | --- |
| R031RawMatrixTests | 5 |
| R026RawAccountingTests | 3 |
| AccountingSemanticsTests | 5 |
| WireEvidenceTests | 4 |
| RouteTransportTests | 11 |
| StaticRouteInventoryTests | 7 |
| GuardNegativeControlTests | 4 |
| **Итого** | **39** |

- Результат: **39 PASS, 0 FAIL, 0 ERROR, 0 SKIP, exit 0**; isolation_violations 0; evidence_problems 0.
- Время: 7.362 с.
- unittest.log SHA-256 `003188ff64ec0efb7a59e5d75b8bb869cdb6a086bec28e838540644b07434bef` (sandbox `claude-rt002-s1-x8jzkn_p`).

**История прогонов** (первые FAIL сохранены):

| Прогон | Тестов | Итог | Причины |
| --- | --- | --- | --- |
| 1 | 33 | 2 FAIL + 2 ERROR | только дефекты тестов, не runtime |
| 2 | 33 | 33 PASS | — |
| 3 | 39 | 39 PASS | добавлены adversarial-тесты |

Дефекты тестов в прогоне 1:
- R-026: ожидание 17 / 18 / 17 взято по всем потокам, а тест читает только поток Executor (15 / 16 / 15; 2 попытки Planner — в `planner.jsonl`);
- route2: `json.dumps` экранировал кириллицу маркера;
- route3 / 4: в sandbox не было глобального контекста Ultra — runtime корректно отказался; создан штатной `save_agent_global_context`.

**Sensitivity-прогон** (scratch, не в репозитории): 4 выбранных теста, 3 ожидаемых FAIL, exit 1.

**Trigger и независимые oracle:**
- матрица — повторная реализация replay `base + delta` и подсчёт блоков по RAW;
- wire — байты из транспортного слоя httpx;
- маршруты — точное число POST на `CHAT_URL` и пары started / terminal;
- статические утверждения — AST.

**Негативные контроли:**
- изменённая матрица;
- чужое тело;
- неожиданный адрес;
- синтетический лишний `client.stream`;
- 4 нарушения guard: сеть, запись, `.git` / `.ultra`, subprocess.

**NOT RUN:**
- `test_final_audit` целиком — запрещён без изоляции Git;
- live / paid — запрещены;
- конкурентные RUN и kill процесса во время HTTP — не моделировались (см. §7).

## 7. MANUAL ENGINEERING REVIEW

| Claim | Source (code / RAW) | Independent oracle | Result | Remaining uncertainty |
| --- | --- | --- | --- | --- |
| R-031 = накопление внутри одной stage, 8 + 3 | executor.jsonl + executor_base.json; server.py:5929–5950, :4687, :4492 | replay base + delta; канонический sha блоков = sha восстановленных сообщений | подтверждено | R-031 выполнен кодом до S0; механизм сверен с текущими строками и воспроизведён динамически |
| В DIRECT контекст не сбрасывается за весь RUN | server.py:4493 | AST + fake-provider run (маркер в запросах 2 и 3, reset = 0) | подтверждено | — |
| В Planner ON сброс на границе stage удаляет function messages | server.py:4492–4555 | fake run с двумя stage | подтверждено | сброс с последующим повторным чтением (R-027) не моделировался |
| 7 LLM POST, других путей нет | AST по production-модулям | точное множество + негативный контроль | подтверждено для текстового и AST-уровня | динамический import / eval / сторонний SDK не исключены формально; в зависимостях Ultra не найдены |
| `run_planner` без сессии недостижим в production | server.py:4366 | AST всех вызовов | подтверждено статически | вызов из внешнего кода / теста возможен |
| Длина wire = snapshot, хеш ≠ | provider_accounting.py:32–38, 100–127; httpx `encode_json` | захват на транспорте; чувствительность | подтверждено для httpx 0.28.1 | другие версии httpx могут кодировать тело иначе [Н] → S3b должен отправлять собственные байты или закрепить версию |
| Сбой хранения accounting не останавливает платную отправку | server.py:3784–3810 (`required_event` без provider_attempt) | fake run с ошибкой `observe` | подтверждено: SUCCESS, в summary 0 attempts при 1 физическом запросе | — |
| Timeout / 500 → UNKNOWN, не ноль | server.py:4800–4840; run_store | fake run: outcome timeout / provider_error, unknown 1, total None | подтверждено | kill процесса (started без terminal) — по коду incomplete, не прогонялось |
| Verifier теряет usage при protocol error | verifier_runtime.py:262–277, 486–500 | fake response `finish_reason = length` + usage | подтверждено: terminal parse_error, usage None | — |
| Второй terminal R-026 записан в обход API | R-026 executor.jsonl seq 146 / 147; provider_accounting.py:12–19, 140–141 | builder отклоняет исход; запись в обход API не меняет summary | доказано: текущий код такой исход не создаёт, summary расходится с raw | **кто записал — UNRESOLVED**: код на 2026-09-30 мог отличаться; нужны данные Git / координатора |
| «Байты/4» не верхняя граница | 116 RAW calls (разведка) | — | 1 / 116 превышение (Dredd, ×1,244) | выборка мала для Dredd (9 calls) |

**Альтернативные объяснения R-031:**
- «модель зациклилась» — частично верно: повторные `find_text` и чтение, но без накопления цена была бы около 8k на call;
- «accounting завысил» — опровергнуто: RAW terminals = provider usage, дублей нет;
- «большой system prompt» — около 40 КБ постоянно, не объясняет скачков 287 КБ.

**Ложноположительные тесты:**
- wire-тесты проверены sensitivity-прогоном;
- маршрутные тесты требуют точного числа запросов и отказывают на неожиданном адресе;
- guard доказан четырьмя негативными пробами;
- RAW-тесты пропускаются (а не проходят), если данных нет или хеш изменился.

## 8. Findings, blockers, risks, предпосылки S2

**Findings:**
- **S1-F1.** Накопление: полный tool result в живом `messages`; в DIRECT сброса нет вообще.
- **S1-F2.** 7 LLM POST без единого узла; маршрут 1 (MCP) без учёта; маршрут 7 — отдельный ledger.
- **S1-F3.** Учёт best-effort: события provider attempt не обязательные; сбой хранения → платный запрос без записи (доказано).
- **S1-F4.** Verifier теряет usage при protocol error.
- **S1-F5.** Хеш snapshot ≠ хеш wire; длина равна.
- **S1-F6.** R-026 — запись в обход API; атрибуция UNRESOLVED.
- **S1-F7.** precached не агрегируется; «байты/4» не верхняя граница.
- **S1-F8.** Planner review не расходует lifecycle-бюджет; interventions не расходуют tool budget.

**Blockers:** нет.

**Открыто:**
- атрибуция R-026 (`GIT_DATA_REQUIRED`: каким инструментом / версией 2026-09-30…10-01 записан seq 147);
- практическое использование MCP — USER DECISION.

**Риски:**
- маршрут 1 обходит любой будущий бюджет, если S3b его не охватит;
- версия httpx влияет на байты wire;
- компрессор и MCP вне Run Store искажают общий расход.

**Контракты, нужные S2:**
1. Единый authoritative pre-HTTP узел для 7 маршрутов; решение по MCP (подключить или отключить).
2. Durable reserve-before-send; события attempt — обязательные, fail-closed.
3. Единицы: точные wire-байты → консервативная оценка токенов с запасом, не «байты/4» (наблюдаемый максимум ×1,244); сверка с provider usage.
4. Резерв на выход по маршрутам: 32 768 (executor / MCP / compressor), 8 192 (planner), 2 048 (verifier), 160 (diag).
5. Ответственность за UNKNOWN: timeout / 500 / cancel / kill / protocol error (verifier); UNKNOWN держит резерв, а не ноль.
6. cached / precached — отдельная метрика.
7. Хеш отправленных байтов (`content=bytes`) и пин версии httpx.
8. Бюджет не сбрасывается вместе с контекстом (stage reset, replan, repair, recovery).
9. Учёт по вызовам, а не по tool budget: interventions, planner review.
10. Внешние recovery-записи — только через API ledger.

## 9. DOC IMPACT / SHARED DOC DELTA (для координатора)

Общие документы не менялись. Предлагаемые дельты:
- **`21`** — запись S1: версии, матрица 8 + 3, 39 / 39, findings S1-F1…F8, R-026 UNRESOLVED.
- **`20` §5а** — строка S1: статус после независимой проверки.
- **`36.3`** — новая guarded offline-команда и селектор `test_rt002_s1_routes.py` (UL-I01 / I04 / I10 / I11).
- **`13`** — требование обязательной долговечности provider attempt-событий и привязки wire-хеша.

## 10. Итог

**S1 RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Утверждения воспроизводимы (39 / 39 offline), маршруты классифицированы, учёт отделён от предположений, UNKNOWN зафиксированы, для S2 подготовлены 10 контрактов. Бюджеты не реализовывались; S2 автоматически не назначается.

**NEXT:** независимая проверка ChatGPT (source / test / evidence) → решение пользователя по S2.
