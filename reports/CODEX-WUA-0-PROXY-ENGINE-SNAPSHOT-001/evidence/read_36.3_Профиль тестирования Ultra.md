## Файловая область Ultra (параллельная работа)

По умолчанию Ultra-изменения — только указанные в TASK корневые runtime-модули и соответствующие `test_*.py`, **кроме `test_web_alarm_*`**. Общие runner/CI, `web_alarm/`, общая документация и чужие отчёты не входят в автоматический write-scope. Документация READ-ONLY, если запись в конкретный файл явно не поручена; персональная карточка и собственный отчёт — в своём scope. При обнаружении необходимости нового файла сначала уточнить/зафиксировать расширение, до этого не писать.

**CURRENT:** тесты Ultra находятся в корне; будущая собственная папка и запуск из неё — отдельная миграционная TASK после проверки import/discovery и всех gates, **не CURRENT**. Универсальный шаблон допускается только в адаптированной проектной копии со своим oracle и TEMP. Правила — `DOC-PARALLEL-01@1` (18), `TEST-AREA-01@1` (36.1).



## 1. Какие свойства обязаны сохраняться

| ID | Риск / инвариант Ultra | Как проверять (независимый oracle) |
| --- | --- | --- |
| UL-I01 | RUN identity, TASK/role separation, persisted RAW messages | По отдельности читать persisted run store, task/run IDs, role records; reboot/re-open |
| UL-I02 | Tool access и server permissions важнее текста LLM | Negative forbidden READ/WRITE/DELETE/scope, physical target unchanged, audit denial |
| UL-I03 | Write/backup/verify: SUCCESS только после применённых и проверенных side effects | Byte-level before/after, real trace, receipt/backup, compile/test result; no fabricated action |
| UL-I04 | Planner/Executor/Verifier получают разные контексты и полномочия | Контролировать фактические inputs/outputs по роли без общего hidden provider context |
| UL-I05 | Final Audit / Dredd/verifier не позволяют подделать PASS | Intentional incorrect evidence, stale revision, counterfeit receipt/source; expected BLOCKED |
| UL-I06 | Terminal callback/сохранение результата не превращает corrupted durable facts в SUCCESS | S0/RT-002 tests: late callback tamper, durable terminal recheck, no replay |
| UL-I07 | Crash/restart сохраняет evidence, не исполняет действие снова без authority | Controlled worker exit, own phase marker, fresh process exact store/trace check |
| UL-I08 | Context compression/provenance не подменяет RAW и system instructions | RAW immutable/reference; accepted projection separately; failure leaves recoverable state |
| UL-I09 | UI/launcher/API smoke не маскирует callback/worker error | compile + UI smoke + controlled workflow, tests assert actual state and no partial artifacts |
| UL-I10 | Isolation тестов от реальных Workspace, history, secrets и network | Disposable fixture, explicit scopes, local mock/fake transport, no live external calls |
| UL-I11 | Test results/runner: exact collection, source revision, zero flaky-wash | Independently validated result manifest, target IDs, raw exit and negative controls |

Эти группы — **проектная модель покрытия**; не следует объявлять каждую полностью VERIFIED только потому, что в репозитории существуют похожие tests. При кодовой TASK выбрать affected UL-I и конкретные актуальные selectors; при пробеле добавить тест или зафиксировать TEST GAP.



## 2. CURRENT и известные локальные gates

- **Server Verification Gate**: для изменения существующего Python runtime требуется `python_compile`; для `server.py` или `ultra_ui.py` дополнительно `ui_smoke_test` согласно текущей политике. `git_diff/git_status` остаются диагностикой, не доказательством корректного выполнения и не обходом `DOC-GIT-01@1`.
- **RT-002 S2 (2026-10-14; bounded policy/source-review acceptance):** standalone gated command `.venv/Scripts/python.exe -B test_rt002_s2_budget_policy.py` ⇒ core MANIFEST **73**, and `--provenance` ⇒ **74** (requires local RAW; compares 342 derived records). Ordinary unittest discovery yields zero tests and does **not** count as acceptance. Selector-only exit **3** (partial), missing evidence/manifest/errors/guard violation exit **1**, full guarded core PASS exit **0**. Agent Claude-reported 73/73 and 74/74 PASS; ChatGPT independently checked exactly 73 declared tests match MANIFEST and separate provenance, reviewed repairs including terminal conflicts, invalid JSON types, malformed scope with fail-closed `LEDGER_ANOMALY`, exact integer token ceiling using `float.as_integer_ratio()` (prevents float overflow and underestimation). Source main@76335ffb83373b6af0dff9f5c0081d250b7d835a (user commit №324). **No independent execution** of the new S2 suite / no Ultra CI on this SHA: source acceptance is bounded, not executable suite VERIFIED. S1/S0 agent reruns 69/166 reported only. `ultra_budget_policy.py` pure and not production-enforced. S3a/b/c not started. See 20 §5а and 21; report `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S2-REPAIR-002/repair_report.md`.
- **RT-002 S1 (2026-10-14; bounded evidence/route acceptance):** exact acceptance selector `.venv/Scripts/python.exe -B test_rt002_s1_routes.py` (Python 3.12.10, local pinned RAW R-031/R-026, network-guard sandbox). Full MANIFEST **69**. `result.json.gate.status=PASS` **and exit 0** only when all 69 execute, none skipped, evidence hashes/bytes matched, no guard violations; errors, missing RAW, collection mismatch, empty run → exit 1; partial selectors → exit 3 (not acceptance). Ordinary `python -m unittest test_rt002_s1_routes` yields 0 executed with skip, NOT an acceptance route. Endpoint audit uses AST send-site multiplicity + URL alias/flow by node identity and rejects unaccounted LLM/OAuth endpoint reads, but dynamic environment/config network construction remains a known limit. Claude **reported** 69/69 PASS and S0 166/166 on main@b309b18e87b20775806b1222abd5a7e3eb6bd018 (user commit №318); ChatGPT independently reviewed source/test manifest/findings but **did not run** this S1 suite; no new Ultra CI/Windows run on exact SHA. See 20 §5а, 21, agent Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S1-REPAIR-002/repair_report.md. S1 accepted for bounded research/evidence handoff, NOT independent executable-suite VERIFIED/live.

**RT-002 S0 (offline controlled kernel)**: исторический независимый локальный ChatGPT прогон 2026-10-11 `python -B test_rt002_s0_kernel.py` — 166/166 PASS на зафиксированных исходниках с нулём SKIP/guard violations. Подробности source/evidence — в 34, 13, 20/21. Не считать этим проверенной будущую S1 или live-тайминг callback после реальной аварии.
- **Final Audit**: существующие тесты `test_final_audit.py` и связанные модули проверяют часть verifier/terminal путей. Перед запуском использовать текущий code revision, actual test selectors и permissions; количество cases исторически меняется.
- **Other regression**: UI smoke, context, provider/model registry, server tools, permission/guard и recovery имеют собственные тесты/trace; здесь нет вымышленной общей команды, которая якобы уже запускает их все.

**Ultra Runtime Test Runner в одной кнопке, автоматические on-change инвариантные матрицы и общий CI для Ultra пока не внедрены**. Наличие много тестовых файлов не гарантирует, что они объединены одной командой или имеют одинаковый guard.



## 3. Обязательный сценарий агентской кодовой TASK

```text
1. Получить актуальный TASK/scope и путь 08 → 000 → 34 → 18 → 01
   → проектный профиль 09/13 → 36.1 + 36.3.
2. Прочесть изменяемые исходники, server-owned contracts и existing tests.
3. Обозначить affected UL-I / regression selector / negative boundary.
4. Для bugfix создать минимальный воспроизводимый failing test;
   для новой функции задать expected contract + негативную ветку.
5. Изменить код, отдельно просмотреть diff и миграции/permissions.
6. Обязательный server gate compile/ui smoke (где применим),
   плюс узкие contract/restart/permission tests.
7. При рискованной смене RUN/Verifier/TaskPlan — guarded offline
   regression, source manifest, затем независимая приёмка.
8. Указанием статуса разделить PASS, NOT RUN, INCONCLUSIVE,
   HISTORICAL RESULT, live evidence и отдельные будущие stage gates.
```

**Принцип:** тест запускается локально обычным Python при доступном разрешённом окружении — дополнительную дорогую LLM для каждого PASS не вызываем. ChatGPT/verifier анализирует только важные отклонения и source изменения. Но сам код/diff и контракты просматриваются в любом случае.

