# CLAUDE-RT002-FA-M1-001 — Final Audit Evidence Containment, Security & Regression Hardening

**Исполнитель:** агент 008 (Claude, Opus 5.5). **Verifier:** ChatGPT.
**Статус:** M1 RESULT READY / AWAITING INDEPENDENT VERIFICATION. M1 VERIFIED не объявляется. RT-002 не закрывается, следующий этап не запускался.
**Дата:** 2026-10-14. **Назначение:** пользователь переслал в чат стартовую команду; БЛОК 1 `USER ASSIGNED / READY TO START` прочитан и подтверждён. AMENDMENT не было.

**Ориентир координатора:** `main@264df783…` — локально не сверялся (`DOC-GIT-01@1`: Git не использовался, `.git` не читался). Локальный baseline на старте совпал с концом DIAG-001: `server.py` `44d8cc8a…`, отчёт DIAG-001 `e84f4a1c…`, БЛОКИ 2/3 целы.

## 0. Итог

1. **Root cause (CONFIRMED, FAIL-first).** Без Planner Final Audit работал в режиме `legacy_workspace_compat` и отправлял verifier `git status --untracked-files=all` и `git diff HEAD -- .` **всего** рабочего дерева. В пакет попадали посторонняя незакоммиченная работа пользователя, включая содержимое и имена файлов. Размер пакета зависел от неё, а не от RUN.
2. **Найдено в adversarial-проходе (CONFIRMED, FAIL-first).** Та же утечка существует и в **task-scoped** режиме (Planner ON): требования плана `list_dir`/`find_text`, а также любой путь требования или «файловой цели», указывающий на **каталог**, затягивали `git status`/`diff` всего каталога. Исходная постановка (только «legacy DIRECT») и мой отчёт DIAG-001 эту часть не охватывали.
3. **Исправление** — 9 фрагментов в `server.py`, +52 строки:
   - **единая path-scoped политика** git-evidence для Planner ON и OFF;
   - **без Planner** — режим `run_scoped_v1`: только пути, принадлежащие RUN (мутации, run-owned, verification);
   - **пустой scope** → явный `not_applicable` без запуска Git;
   - **discovery-требования и каталоги** в Git не наблюдаются; READ-scope для них по-прежнему проверяется;
   - **каталог там, где должна быть файловая цель** → critical;
   - **усечение scoped git-evidence** — critical в обоих режимах;
   - **`unattributed_git_status`** вычисляется в обоих режимах;
   - **новый fail-closed случай** `mutating_run_without_scoped_paths`.
4. **Тесты:**
   - новый guarded-набор `test_rt002_final_audit_m1.py`: **25/25 PASS** (FAIL-first: 15 из 20 на baseline);
   - существующие тесты Final Audit/recovery: **99/99 PASS** (Git-зависимые 8 — NOT RUN);
   - 3 устаревших оракула исправлены; доказано, что на baseline-сервере новые оракулы **падают**;
   - мутации: **6 из 6** убиты;
   - S1 69/69, S2 73/73, S0 166/166;
   - offline UI smoke OK;
   - RAW: 8 из 8 `summary.json` совпадают с SHA из отчёта ChatGPT.
5. **Размер пакета на контролируемых фикстурах.** DIRECT без мутаций: было 3 980 / 20 031 / 113 869 / 136 802 B (чистое дерево / 8 / 56 / 200 KiB посторонних изменений), стало **4 091 B во всех случаях**. R-033-образная реконструкция: было 63 184 символа, стало **4 290** — так же, как у R-034.

## 1. Исходная архитектура и причинная цепочка

```
run_agent_task → (FINAL, Dredd ON) → _collect_final_audit_evidence(root, candidate, policy, …, task_plan_evidence)
  task_scoped = task_plan_evidence is dict            # Planner ON
  task_paths = _collect_final_audit_task_paths(…)     # plan artifacts/requirements + mutations + run-owned + verification
  allow_read:
    task_scoped   → _agent_git_status(root, policy, task_paths); diff по task_paths (пусто → not_applicable)
    НЕ task_scoped → _agent_git_status(root, policy)            ← без путей: всё дерево, --untracked-files=all
                     _agent_git_diff(root, [], policy)          ← [] → read_scope "." → git diff HEAD -- .
  evidence["fresh_git_status"/"fresh_git_diff"] = вывод целиком (≤ 128 KiB на поток)
  json.dumps(indent=2) → verification_context → run_verifier_check → HTTP body провайдеру
```

**Следствия:**
- R-033 («привет», Planner OFF): user-блок 62 913 символов (RAW), так как дерево было грязным. R-034: 4 122 символа (чистое дерево).
- Planner ON/OFF фактически были **двумя разными политиками безопасности** evidence.
- Инструкция FINAL сама говорит verifier: «Git status/diff … cannot establish RUN ownership alone». Значит, посторонний diff не нёс доказательной ценности. Владение RUN устанавливается фактами сервера (`mutation_facts`, `run_owned_state`, `write_revision`, tool facts).

## 2. Дефекты, влияние, severity

| ID | Дефект | Влияние | Severity |
| --- | --- | --- | --- |
| D1 | Legacy DIRECT отправлял status и diff всего дерева | Утечка посторонних незакоммиченных данных (содержимое, имена), размер пакета вне контроля RUN (до ~2×128 KiB), разные политики для ON/OFF | **HIGH** (конфиденциальность + стоимость) |
| D2 | Task-scoped: discovery- и каталожные пути требований наблюдались через Git целиком | Та же утечка в Planner ON при требованиях `list_dir`/`find_text` или каталоге в `git_diff` | **HIGH** |
| D3 | Каталог как файловая цель (артефакт и т. п.) наблюдался через Git | Утечка при ошибочном плане; повреждённый контракт не помечался | MEDIUM |
| D4 | Усечение git-evidence в legacy не было critical | Planner OFF — более слабая политика: SUCCESS с неполными обязательными данными | MEDIUM |
| D5 | Мутирующий RUN без путей в scope не отлавливался (теоретическая несогласованность) | В legacy маскировался diff'ом всего дерева; после scoping получился бы аудит без evidence | LOW (страховка) |
| D6 | `unattributed_git_status` только в task-scoped | Разные негативные факты для ON/OFF | LOW |

## 3. Выбранное решение и отвергнутые альтернативы

**Выбрано:** минимизация по умолчанию через **область** (scope), а не через фильтрацию содержимого. Git наблюдает только файлы, состояние которых аудит обязан проверить:
- артефакты контракта;
- мутации и run-owned цели;
- verification-цели;
- файловые требования (`read_file`, `read_file_range`, `verify_file_content`, `python_compile`, файловый `git_diff`).

| Альтернатива | Почему отвергнута |
| --- | --- |
| Маскировать секреты по шаблонам в diff всего дерева | Не универсально (постановка прямо это отмечает); посторонние данные всё равно уходят; маска может испортить обязательное evidence и дать ложный FAIL |
| Оставить status всего дерева «только имена» как негативный факт | Имена тоже чувствительны (тест кладёт маркер в имя файла); без baseline изменения нельзя приписать RUN, а verifier проинструктирован не делать этого |
| Счётчик изменений вне scope | Требует запуска Git по всему дереву, атрибуции не даёт. Отложено как будущий вариант с pre/post-отпечатком (§10) |
| Вообще убрать Git из FINAL в DIRECT | Ослабляет проверку мутаций: собственный diff — evidence содержимого изменений |
| Сделать усечение некритичным везде | Fail-open; противоречит инварианту «обрезанные обязательные доказательства не дают SUCCESS» |
| Включать каталоги discovery «только status» | Имена в каталоге — те же посторонние данные; доказательство discovery — собственный результат инструмента (tool facts + свежесть requirement) |

## 4. Новый контракт evidence

| Поле | Planner ON (`task_scoped_v1`) | Planner OFF (`run_scoped_v1`, было `legacy_workspace_compat`) |
| --- | --- | --- |
| `task_scope.paths` | файлы контракта + RUN-owned + verification | RUN-owned + mutation + verification |
| `fresh_git_status` / `fresh_git_diff` | только по `task_scope.paths`; пусто → `not_applicable` (`no_task_scoped_paths`), Git не запускается | то же; причина `no_run_scoped_paths` |
| discovery `list_dir`/`find_text`, каталоги в требованиях | проверяются по READ-scope, в Git **не** наблюдаются | — |
| файловая цель — каталог | `invalid` → critical | `invalid` → critical |
| усечение scoped git | critical | critical (раньше — нет) |
| `unattributed_git_status` | вычисляется | вычисляется (раньше — нет) |
| мутирующий RUN без путей | critical `mutating_run_without_scoped_paths` | то же |
| `new_file_evidence` | только файлы, созданные RUN (без изменений) | то же |
| `authoritative_tool_evidence` | без изменений (собственный вывод инструментов RUN, уже отправленный провайдеру в запросах Executor) | то же |
| `evidence_semantics.fresh_git_state` | описывает path-scoped контракт; отсутствие данных вне scope — не дефект | то же |

**Критерии достаточности evidence:**
- **read-only / no-mutation** — без Git, факты сервера плюс ответ кандидата; ложные утверждения ловит `candidate_fact_conflicts`;
- **mutation** — собственный scoped diff/status, `run_owned_filesystem_evidence` (хеши), `new_file_evidence`; усечение — critical;
- **verification** — файловые цели требований в Git-scope, discovery — через tool facts и свежесть;
- **legacy DIRECT** — те же правила, что и выше.

Без изменений остались:
- verifier-промпт (`verifier_runtime.py` вне scope);
- лимиты размера;
- freshness / requirement coverage;
- permissions;
- обязательность Final Audit.

## 5. FAIL-first и итоговые регрессии

| # | Прогон | Исходники | Результат | Лог SHA-256 |
| --- | --- | --- | --- | --- |
| 1 | Baseline существующих тестов (guarded, Git подменён, 8 Git-зависимых исключены) | baseline | **99/99 PASS**, exit 0, guard 0, fake-git 4 | `a629ccb8…` |
| 2 | M1 FAIL-first (канонический) | `server.py` baseline `44d8cc8a…` | 20 выполнено, **15 FAIL**; R-034-фикстура = **4122 символа / 4232 B** (= RAW) | `befeb9eb…` |
| 2a | M1 первый прогон с двумя ошибками в тесте (наполнитель ≤ 18 тыс. символов, длина `run_id`) — исправлены до правки кода | baseline | 20 выполнено, 15 FAIL | `2db28fe2…` |
| 3 | После исправления D1/D4/D5/D6 | M1 v1 | 19/20 — 1 FAIL из-за моей фикстуры (план без свежести требования); фикстура исправлена | `91bc5353…` |
| 4 | Существующие тесты после исправления | M1 v1 | 97/99 — **2 FAIL** (устаревшие оракулы, §5.1) | `7391d1a1…` |
| 5 | FAIL-first D2 (каталог / discovery) | M1 v1 | 22 выполнено, **4 FAIL** (subtests) | `aa32b5a2…` |
| 6 | Существующие тесты после D2 | M1 v2 | 98/99 — **1 FAIL** (устаревший оракул recovery) | `bd4d07ff…` |
| 7 | FAIL-first D3 (каталог как файловая цель) | M1 v2 | 23 выполнено, **1 FAIL** | `12696098…` |
| **F1** | M1 финал | `server.py` `3f950f03…`, тест `81865594…` | **25/25 PASS**, gate PASS, exit 0, нарушений 0 (2 блокировки — намеренные пробы) | `076a0245…` |
| F2 | M1 selector (1 тест) | финал | exit **3** (`PARTIAL_SELECTION`) | `7c5709cb…` |
| F3 | M1 нераспознанный selector | финал | exit **1** (`SELECTOR_UNRESOLVED`, `ZERO_TESTS`) | `b0281afc…` |
| F4 | `python -B -m unittest test_rt002_final_audit_m1` | финал | Ran 0, OK (skipped=1) — без guarded runner не приёмка | — |
| F5 | Существующие Final Audit + recovery | финал | **99/99 PASS**, exit 0, guard 0, fake-git 4, исходники в прогоне не менялись | `a758274d…` |
| F6 | S1 `test_rt002_s1_routes.py` | финал | **69/69 PASS**, exit 0 | `6575d238…` |
| F7 | S2 `test_rt002_s2_budget_policy.py` | финал | **73/73 PASS**, exit 0 | `700d8540…` |
| F8 | S0 `test_rt002_s0_kernel.py` | финал | **166/166 PASS**, exit 0, 107,5 с | `aafe3945…` |
| F9 | Offline UI smoke (`UltraApp` в дочернем процессе, AppData перенаправлен, хук: без сети, subprocess и записи вне sandbox) | финал | exit 0, «OK: UltraApp constructed», 0 блокировок | — |
| F10 | Компиляция в памяти `server.py` и 3 тестовых файлов | финал | OK, `.pyc` не созданы | — |

### 5.1 Исправленные оракулы и доказательство их независимости

| Тест | Старый оракул | Новый оракул |
| --- | --- | --- |
| `test_final_audit…test_context_contains_candidate_policy_and_fresh_server_facts` | DIRECT без мутаций **обязан** содержать `" M server.py"` (git всего дерева) — это закреплённый дефект D1 | `run_scoped_v1`, обе git-секции `not_applicable` / `no_run_scoped_paths`, пустой stdout, «server.py» отсутствует |
| `test_final_audit…test_evidence_semantics_separates_run_mutations_from_git_state` | `fresh_git_status.stdout == " M server.py"` | семантика содержит `run_scoped_v1`, status `not_applicable`; прежние утверждения о семантике сохранены |
| `test_final_audit_recovery…test_directory_listing_requirement_reaches_audit_with_freshness` | `task_scope.paths == ["pkg"]` (каталог discovery-требования через Git — D2) | `paths == []`, status `not_applicable`; проверки covered и `target_state_sha256` (свежесть листинга) сохранены |

**Независимость.** Восстановленный baseline-сервер (обратное применение 9 фрагментов даёт ровно `44d8cc8a…`) в изолированной копии репозитория. Все 3 новых оракула на нём **FAIL** (3/3, лог `d99a9a36…`), то есть не повторяют production-дефект. Причины падения: `'legacy_workspace_compat' != 'run_scoped_v1'` и т. д.

### 5.2 Не запускалось — NOT RUN и почему

- **Git-зависимые тесты (8):** `FinalAuditGitScopeTests` (5, `git init` в setUp), `test_non_git_workspace_mutation_reaches_final_pass`, `test_precise_edit_tracks_run_and_reaches_final_audit`, `test_non_git_workspace_hash_mismatch_blocks_verifier` (все с `mock_git=False`), `test_ignored_file_material_remains_available_without_git_diff` (`git init` в теле). Причина: `DOC-GIT-01@1`, разрешения нет. Эквивалентные сценарии (не-Git workspace, мутации, хеши) проверены с полностью подменённым транспортом Git.
- **Реальный Git**, live/платные вызовы, stress, destructive, рабочий RUN Ultra.
- **Независимая приёмка ChatGPT** — ещё не выполнялась.

## 6. Adversarial-проход: контрпримеры

| Попытка | Результат |
| --- | --- |
| Посторонний маркер в содержимом diff, в имени неотслеживаемого файла, в diff соседнего каталога | Нет ни в пакете, ни в **реальном исходящем HTTP-теле** verifier (сквозные тесты с настоящим `run_verifier_check` и фейковым транспортом) |
| R-033-образный RUN с 56 KiB посторонних изменений против R-034 | Пакеты идентичны (4290 символов) |
| Discovery-требование по каталогу (`list_dir`, `find_text`), `git_diff` по каталогу, `find_text` по файлу | **Найдена утечка D2** → исправлено; Git не вызывается, READ-scope проверяется (вне scope → critical) |
| Артефакт плана указывает на каталог | **Найдена утечка D3** → `invalid` + critical, Git не вызывается |
| Мутирующий RUN без путей (повреждённое состояние) | critical `mutating_run_without_scoped_paths` |
| Огромный собственный diff без Planner | critical `fresh_git_diff_truncated` (раньше legacy позволял SUCCESS) |
| Ложное заявление Executor «изменил / проверил / вызвал инструмент» при 0 инструментов | `candidate_fact_conflicts`; в сквозном тесте даже PASS модели не даёт SUCCESS |
| Verdict FAIL | `FinalAuditSemanticError`, SUCCESS нет, Final Audit не отключён |
| Собственная мутация + посторонние изменения в одном дереве | Собственный diff и `new_file_evidence` присутствуют, посторонние отсутствуют; `run_owned_filesystem_evidence.match` = True |
| Planner ON и OFF на одних и тех же фактах | Одинаковые вызовы Git и pathspec |
| READ OFF | Git не запускается ни в одном режиме |
| Не-Git workspace | `available=False`, не critical (как раньше) |
| Байтовый учёт контекста (кириллица, эмодзи) | `context_bytes` == длина UTF-8, ≤ 1 MiB |

**Мутационная проверка.** Текстовые мутации `server.py` в изолированных копиях; реальный файл не тронут (`3f950f03…` до и после):

| Мутация | Exit | FAIL в M1 |
| --- | --- | --- |
| `scope_legacy_direct` (вернуть Git всего дерева без Planner) | 1 | 14 тестов (утечки, размеры, исходящий HTTP, единая политика) |
| `truncation_noncritical_without_planner` | 1 | 1 |
| `discovery_observed_through_git` | 1 | 1 (subtest) |
| `directories_observed_through_git` | 1 | 2 |
| `mutating_run_without_paths_allowed` | 1 | 1 |
| `unattributed_only_with_planner` | 1 | 1 |

Мутации запускались, пока файл теста ещё был в CRLF; по содержанию он идентичен итоговой LF-версии (`81865594…`).

**Не найдено:** путей, где новый алгоритм скрывает нарушение RUN. Все записи Executor идут через инструменты, которые фиксируют `run_owned_state` и manifest. Остаточные риски — §9.

## 7. Размер пакета на контролируемых фикстурах (без денежных оценок)

| Фикстура (тест M1) | До (baseline, FAIL-first) | После |
| --- | --- | --- |
| DIRECT без мутаций, чистое дерево | 3 980 B | 4 091 B (+111 B: явные `not_applicable` и описание контракта) |
| то же, 8 KiB посторонних изменений | 20 031 B | 4 091 B |
| то же, 56 KiB | 113 869 B | 4 091 B |
| то же, 200 KiB (обрезка git 128 KiB) | 136 802 B | 4 091 B |
| R-034 (метаданные RAW, синтетические строки той же длины) | 4 122 символа / 4 232 B — **совпадает с RAW** | 4 290 символов / 4 343 B |
| R-033-образный (те же метаданные + синтетические 56 KiB) | 63 184 символа / 114 121 B | 4 290 символов / 4 343 B |
| Сквозной исходящий user-блок verifier (приветствие, грязное дерево) | — | 4 260 символов |

**Исторический R-033:**
- **фактический provider usage:** Dredd 17 331 + 93 токена (RAW);
- **восстановленные входы:** метаданные R-033/R-034 (разрешения, счётчики, длины);
- **синтетическая оценка:** пакет R-033 стал бы того же размера, что R-034 (≈ 1,7–1,8 тыс. токенов по факту R-034) — ESTIMATED / OFFLINE, не фактическая экономия.

## 8. Файлы и SHA-256

| Файл | Baseline | Итог | Окончания строк |
| --- | --- | --- | --- |
| `server.py` | `44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54` | `3f950f0329b7605eb790ce61245a95985146d649d3d5c805660b57374fb6c401` (9 фрагментов, +52 строки, доказано обратным применением) | CRLF (сохранены) |
| `test_final_audit.py` | `1e7f883ab9579d9775e6f1603dea46dba37f6f95a8eccf5c1ef39846dd383c57` | `87af23a1025353d482a5f3c16b9ff9702ca36473fb309a8459c2af6d3918390b` (2 оракула) | CRLF (сохранены) |
| `test_final_audit_recovery.py` | `8dc022756d5a3b4abb46c86d68f4ea0c9771b4ccba264253843b47b7ade32442` | `880881528c69714f0a9caba86649cc2a48ec7167eb0046caaf89747155b4ff6b` (1 оракул) | LF (сохранены) |
| `test_rt002_final_audit_m1.py` | — (новый) | `818655949997168ff0ba0f5174d85bef36f44bda33aabbce5c51960c09958a65` (735 строк, MANIFEST 25) | LF |
| этот отчёт | — | — | LF |

**Без изменений:**
- verifier_runtime `7db030fe…`;
- planner_runtime `ab6c12c3…`;
- task_planner `c2ad7723…`;
- ultra_budget_policy `bd82618d…`;
- ultra_ui `7bd32cad…`;
- тесты S0/S1/S2.

Web Alarm, Codex, `.gitignore`, `.ultra`, CI и документы не менялись. **RAW:** `summary.json` 8 исследуемых RUN совпадают с SHA-256 из отчёта ChatGPT (8/8). Тесты работают только в sandbox, доступ к `.ultra` запрещён guard-ом.

Новых `.pyc` нет: три совпадения в `__pycache__` датированы 29.09–11.10.

## 9. Остаточные риски и решения для verifier / пользователя

- **R1 (false BLOCKED).** DIRECT-RUN с собственным diff > 128 KiB теперь fail-closed, как task-scoped. Варианты: оставить (рекомендую — единая политика) или ввести постраничную выдачу diff (отдельная задача).
- **R2 (изменение контракта 13).** Каталоги discovery-требований больше не наблюдаются через Git. Документ 13 сейчас говорит о «разрешённых directories» в task scope. Нужен вердикт verifier и правка 13.
- **R3 (промпт verifier).** Инструкция FINAL упоминает только `task_scoped_v1` («Do not require workspace-wide Git state…»). Про `run_scoped_v1` пакет поясняет в `evidence_semantics`. Предложение: добавить `run_scoped_v1` в промпт `verifier_runtime.py` — вне scope, требует согласования.
- **R4 (неучтённые каналы записи).** Если когда-либо появится запись в workspace в обход инструментов, scoped Git её не увидит. Прежний diff всего дерева её тоже не приписывал RUN. Предложение: контентно-нейтральный pre/post-отпечаток workspace (без имён и содержимого) — отдельная задача.
- **R5.** В scoped-файлах RUN по-прежнему видны чужие незакоммиченные правки **этих же файлов** — это необходимо для проверки их итогового состояния.
- **R6.** Вывод собственных инструментов Executor `git_status`/`git_diff` (при VERIFY ON) может попасть в tool evidence (≤ 1000 символов на факт). Эти данные уже отправлены провайдеру в запросах Executor, новой экспозиции нет.
- **R7 (верность фейка).** `FakeGitRepo` эмулирует pathspec-семантику; реальный Git не запускался (NOT RUN).

## 10. Реестр смежных проблем DIAG-001 (вне текущего кодового scope — OPEN)

| ID | Проблема | Статус |
| --- | --- | --- |
| M1 | Final Audit: посторонний git-evidence, маскирование | **Закрыта этой задачей.** Решение — scoping вместо маскирования; см. R1–R7 |
| M2 | Проверка выполнимости плана против разрешений (R-041) | OPEN |
| M3 | Фильтр инструментов и промпт Planner о разрешениях | OPEN |
| M4 | Transport-сбой Planner как «SERVER VALIDATION», новый `logical_call_id` | OPEN |
| M5 | Учёт и UI: `tool_calls`, `PENDING`, «—» при неполном учёте, флаги в RAW | OPEN |
| M6 | «RUN STATUS» в истории Executor | OPEN |
| A1 | Бюджет истории DIRECT (S6b) | OPEN |
| A2 | Инструменты по необходимости | OPEN |
| A3 | Уровни сложности Planner / READINESS | OPEN |
| A4 | Разделы глобального контекста (решение пользователя) | OPEN |
| — | Dredd PERMISSION вне флага «Судья Дредд» | OPEN (DIAG-001, только по коду) |

## 11. DOC IMPACT (только предложения координатору)

- **13:** раздел Fresh Git State. `legacy_workspace_compat` → `run_scoped_v1`; единая path-scoped политика; discovery и каталоги вне Git; каталог как файловая цель → critical; усечение critical в обоих режимах; `mutating_run_without_scoped_paths`.
- **20 §5а / 33.3:** M1 закрывает исследовательский пункт R1 (FOUND) и его исправление; связь с C1/S6a.
- **21:** запись FA-M1 — причины D1–D6, FAIL-first, оракулы, мутации, размеры.
- **36.3:** новый селектор `.venv/Scripts/python.exe -B test_rt002_final_audit_m1.py` (MANIFEST 25, коды гейта 0/1/3); перечень 8 Git-зависимых тестов как NOT RUN без разрешения; кандидаты UL-I05 / UL-I10.
- **34:** CURRENT — M1 RESULT READY.
- **001 / 06:** closeout verifier после проверки.

## 12. NEXT

Независимая проверка ChatGPT (source, тесты, оракулы, мутации). Решения по R1–R3. Остальные пункты реестра (M2–M6, A1–A4) — только по отдельному GO пользователя.

Незакоммичено (коммитит пользователь): `server.py`, `test_final_audit.py`, `test_final_audit_recovery.py`, `test_rt002_final_audit_m1.py`, этот отчёт, ротация `000_Задачи Claude.md`.
