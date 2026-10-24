# 🟨 Устранение девяти ошибок независимой Windows-проверки защитного механизма Web Alarm (`CLAUDE-WA4-R-FT1-CI-REPAIR-001`)

**ARCH CLASS:** Web Alarm Workspace / WA4-R Reliability / Test Harness Security. **PRIMARY PROFILE:** 36.2; **SECONDARY:** 23 (AUD-01T-R). **Платформа:** Windows 10 Pro 19045, Python 3.12.10 (`.venv`), guarded runner `wa4a_acceptance.py` через `tools/run_gate.py` и прямой `unittest`; всё в одноразовом TEMP. Git/GitHub, CI YAML (только чтение), live storage, сеть не использовались.

## 1. Итог

| | |
|---|---|
| Статус | **RESULT READY / AWAITING INDEPENDENT VERIFICATION** (не DONE/VERIFIED). WA4-R остаётся PARTIAL |
| Классификация | **TEST/HARNESS DEFECT в моём тесте `test_web_alarm_runner_guard.py`**, не ослабление guard и не дефект runner |
| Первопричина | Все workflow задают `TMPDIR = TEMP = TMP = runner.temp`. `tempfile` (Python 3.12.10, `_candidate_tempdir_list`) берёт **первым `TMPDIR`**, затем `TEMP`, `TMP`. Тест переопределял для своего дочернего процесса только `TMP`/`TEMP`; в CI ребёнок унаследовал `TMPDIR`, и его guard (`_audit_temp = _canon(tempfile.gettempdir())`) защищал **TEMP раннера**, а не свой `inner`. Все «внешние» фикстуры теста лежат в `base/outside` — внутри TEMP раннера, поэтому 8 операций законно получили `allowed`; заблокированными остались ровно 4, которые отвергаются при любом корне (явный `\\?\` вне/внутри, устойчивый `$Deleted`, `.git`) → **4 записи журнала вместо 12** = девятое падение. Локально `TMPDIR` не задан → PASS |
| Куда шла запись | Доказано зондом (`tools/probe_child_root.py`, `runs/probe-child-root-ci-env.json`): в CI-окружении у ребёнка `gettempdir` и корень guard = TEMP родителя, запись в `<BASE>/outside/probe.txt` → `allowed`, **файл физически создан** внутри TEMP раннера; с `TMPDIR = inner` → `blocked`, файла нет. Ни одна запись не вышла за TEMP раннера (корень guard там и был) |
| Исправление | Только `test_web_alarm_runner_guard.py`: (1) ребёнку задаются все три `TMPDIR`/`TEMP`/`TMP`; (2) ребёнок сообщает фактический корень своего guard и `tempfile`, родитель **проверяет, что это его `inner`** — иначе тест не отличает защиту своего TEMP от чужого; (3) новый метод воспроизводит CI-окружение у родителя независимо от хоста. `wa4a_acceptance.py` (guard) **не менялся** |
| Тесты | RED на исходных байтах в CI-окружении — **ровно как CI**: те же 8 подслучаев + `4 != 12`, `FAILED (failures=9)` (runner и прямой запуск). GREEN: 7/7 прямой запуск и guarded runner, в локальном и CI-окружении. Мутанты **9/9 убиты в обоих окружениях** (C1–C3 этой задачи, A1–A6 прежние). Focused в форме CI: **46 = 45 PASS / 1 SKIP, isolation 0** (CI: 45, 9 FAIL, 1 SKIP). Полный набор в CI-окружении: **989 = 987 PASS / 0 FAIL / 0 ERROR / 2 SKIP, isolation 0** |
| Изменённые файлы | `test_web_alarm_runner_guard.py` (+ эта папка; ротация карточки и запись `001`) |

## 2. Исходные факты CI (из постановки и 34; сырые логи CI локально недоступны)

- [CI #40112070376](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/40112070376), source №412 `59d2a36c…`: manifest 295/295 PASS, source hashes 4/4 PASS, focused **45 tests, 9 failures, 1 SKIP** в `…test_every_escape_from_temp_is_still_refused_and_writes_nothing`: `allowed` вместо `blocked` у `sibling`, `dotdot`, `dotdot_slashes_case`, `junction`, `replace_out`, `mkdir_out`, `race_injection_outside`, `deleted_once_outside` + общий oracle 4 вместо 12; full 988 SKIPPED.
- [CI #40111613262](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/40111613262): сбой сверки байтов `closeout-001.md` — стадия уже исправлена verifier-ом; вероятная причина — Windows-checkout переводит LF опубликованного файла в CRLF (мой пакет в LF, manifest хранит LF-байты). Вне scope этой TASK, не исследовалось глубже.
- Локальные байты 4 исходников до работы совпадают с финальными байтами FT1-ARCHIVE-RETRY (`source-baseline.json` против её `source-final.json`: 0 расхождений из 110), то есть с теми, что CI признал 4/4.

## 3. Воспроизведение (сначала без изменений)

| Прогон | Исходник | Окружение | Итог |
|---|---|---|---|
| `red-ci-env-runner` | исходный | CI (`TMPDIR=TEMP=TMP`) | 6 методов: 5 PASS / **1 FAIL** — ровно 8 подслучаев CI + `4 != 12`; isolation 0 |
| `direct/red-direct-ci` (зеркало исходных байт) | исходный | CI | `Ran 6`, **`FAILED (failures=9)`**, те же 8 подслучаев |
| `mutL/original-test` | исходный тест | локальное (`TMPDIR` нет) | 6/6 PASS — объясняет локальный PASS |
| `mutC/original-test` | исходный тест | CI | 9 failures |
| `probe-child-root-local-env` | исходный guard | локальное | старая и новая сборка env: корень = `inner`, запись наружу `blocked` |
| `probe-child-root-ci-env` | исходный guard | CI | **старая сборка env: корень = TEMP родителя, запись `allowed`, файл создан**; новая: корень `inner`, `blocked`, файла нет |

Ни одна другая переменная не участвует: единственное различие RED/GREEN-окружений — наличие `TMPDIR` у родителя.

## 4. Исправление (минимальное) и почему именно так

```text
child():  env.update(..., TMPDIR=inner, TMP=inner, TEMP=inner, ...)        # все кандидаты tempfile
CHILD:    сообщает {"guard": sitecustomize._audit_temp, "gettempdir": tempfile.gettempdir()}
child():  assert normcase(guard) == normcase(inner) и то же для gettempdir   # на каждом вызове ребёнка
новый тест: родитель с TMPDIR=TEMP=TMP=<base> (форма CI) → корень inner, запись наружу blocked, файла нет
```

- **Guard не менялся** и не расширялся: он правильно защищал тот корень, который ему дало окружение процесса; ошибкой было окружение, собранное тестом. Вторая реализация проверки путей не создавалась.
- **Отвергнутые альтернативы:** (а) удалить `TMPDIR` из env ребёнка — тоже работает, но зависит от того, что кроме `TMPDIR/TEMP/TMP` ничего не влияет; явная установка всех трёх + проверка фактического корня надёжнее и самопроверяема; (б) брать корень guard из отдельной переменной runner-а — изменение `wa4a_acceptance.py` без необходимости (см. §9 P3); (в) выносить `outside` за пределы TEMP раннера — запись вне disposable TEMP недопустима.
- **Oracle теперь ловит неверно выбранную защиту:** без проверки корня тест мог бы снова «проверять» guard чужого TEMP (мутант C2).

## 5. Тесты

`test_web_alarm_runner_guard.py` — 7 методов (было 6): прежние 6 без изменения ожиданий + `test_child_guard_protects_its_own_temp_even_when_the_parent_sets_tmpdir`. Проверка корня выполняется в **каждом** вызове ребёнка (в т.ч. в гонке и во всех 12 запретных операциях).

**Мутанты** (`tools/build_mirror.py`, зеркало в TEMP, точная замена; `runs/mutL` — локальное окружение, `runs/mutC` — CI-окружение):

| Мутант | Что ломает | Локально | CI-окружение |
|---|---|---|---|
| `final` | контроль | 7/7 PASS | 7/7 PASS |
| `original-test` | опубликованный тест | 6/6 PASS | **9 failures** (= CI) |
| C1 | ребёнку не задаётся `TMPDIR` (исходный дефект) | убит (1) | убит (7) |
| C2 | C1 + снята проверка корня | убит (2) | убит (11) |
| C3 | guard расширяет корень до родителя TEMP | убит (7) | убит (7) |
| A1–A6 | прежние: без снятия префикса, снятие явного `\\?\`, без повтора `$Deleted`, `$Deleted` по написанию, проверка записи выключена, `.git` удалён | все убиты | все убиты |

Числа в скобках — failures runner-а (подтесты), каждый мутант — exit 1, isolation 0 (в зеркале runner тоже мутирован, поэтому оракулом служат выводы самих тестов).

**Фактические побочные эффекты проверены, не только исключения:** запретные операции — список `outside` после прогона (`gone`, `new` — только то, что создала сама инъекция), отсутствие `f*.txt` в `inner`; новый тест — `outside` пуст, `inner/f2.txt` создан; зонд — существование файла после записи.

**Гонка F-T1** проверена в составе тестов (3 000 решений guard на прогон, 0 ложных нарушений) в обоих окружениях и в каждом прогоне выше; длинных серий повторов без новой гипотезы не проводилось.

## 6. Регрессия

| Прогон | Окружение | Итог по методам |
|---|---|---|
| `green-runner-local` / `green-runner-ci` | локальное / CI | 7/7 PASS, isolation 0 / 7/7 PASS, isolation 0 |
| `direct/green-direct-local` / `green-direct-ci` | локальное / CI | `Ran 7`, OK / `Ran 7`, OK |
| `focused-ci` — `test_web_alarm_runner_guard test_web_alarm_transport_event_recovery` (команда CI) | CI | **46 = 45 PASS / 0 FAIL / 1 SKIP (symlink), isolation 0** — Archive Retry не затронут |
| **`full-ci` — `all`** | CI | **989 = 987 PASS / 0 FAIL / 0 ERROR / 2 SKIP (symlink, нет привилегии), isolation 0, exit 0** |

## 7. MANUAL ENGINEERING REVIEW

- **Не стал ли guard fail-open:** guard не менялся (SHA `9473b76f…` до и после); мутанты A1–A6 и C3 убиты в обоих окружениях; все 12 запретных операций блокируются с корнем `inner`, проверенным фактически.
- **Дочерние процессы и вложенные TEMP:** корень guard каждого процесса = `tempfile.gettempdir()` этого процесса, т.е. определяется **его** окружением (`TMPDIR` > `TEMP` > `TMP`). Runner: родитель и дети наследуют одно окружение → один корень. Поиск по `test_web_alarm*.py`, `web_alarm/*.py`, `wa4a_acceptance.py`: окружение TEMP детям задаёт только этот тест (сужая корень); других путей смещения корня в существующих тестах нет. Дальнейшее — §9 P3.
- **Race/TOCTOU и пограничные пути:** без изменений относительно FT1-ARCHIVE-RETRY (guard не тронут); тест гонки зелёный в обоих окружениях. Guard по-прежнему не граница безопасности против враждебного кода (TOCTOU, управление env).
- **Не принимает ли harness обходы:** новая проверка корня делает конфигурационную ошибку громкой (тест падает с фиксированным сообщением), а не тихо зелёной/красной.
- **Источник истины:** исход операции из ребёнка + число строк журнала guard + фактические файлы — независимы от кода решения guard.
- **Совместимость:** прежние 6 методов — те же операции и ожидания; full — §6.
- **Почему проще:** одна строка окружения + один assert корня + один тест; без новых механизмов и без изменения guard/CI.

## 8. Защищённые файлы — не изменены

`wa4a_acceptance.py` `9473b76f…`, `web_alarm/transport_event_recovery.py` `7f5e8407…`, `test_web_alarm_transport_event_recovery.py` `e8dc4e20…` — байты до и после совпадают (`source-baseline.json` / `source-final.json`, manifest `repository_files_unchanged_checked`). CI YAML, общая документация, БЛОК 4, контракты `ARCHIVE_UNPROVEN`/повторного `apply`/receipt — не трогались.

## 9. Риски / предложения

- **P3 (PROPOSAL, не реализовано):** корень guard следует окружению процесса; дочерний процесс, которому тест задал другой `TMPDIR/TEMP/TMP`, получает guard с другим корнем (сейчас так делает только этот тест — сужая). Если нужно, runner может передавать корень явно (например, переменная, которую guard сверяет с `gettempdir()` и допускает только сужение). Это изменение `wa4a_acceptance.py` и контракта runner — нужен GO.
- Сырые CI-логи/artifact `12566414945` локально не изучались (Git/GitHub запрещены): вывод опирается на факты постановки, точное локальное воспроизведение CI-окружения и совпадение всех 9 симптомов.
- Ограничения прежней задачи сохраняются (symlink SKIP, PWR-01, Linux, live/production NOT RUN; F-S1 — известный флейк `folder_picker`).
- **Готовность к независимому Windows CI:** да — ожидаемо focused 46 = 45 PASS / 1 SKIP; full 989 (= 988 + 1 новый метод).

## 10. DOC IMPACT / SHARED DOC DELTA (координатору)

- **34 / 06:** причина 9 FAIL #40112070376 — `TMPDIR` в CI + неполное переопределение TEMP в тесте; guard не ослаблен; исправлено в тесте; ждёт нового Windows CI.
- **36.2:** правило для тестов с вложенным TEMP: задавать все кандидаты `tempfile` (`TMPDIR`, `TEMP`, `TMP`) и проверять фактический корень ребёнка; база full = 989; `test_web_alarm_runner_guard.py` — 7 методов.
- **05/23/24/25:** без изменений до независимого PASS (статус F-T1 и Archive Retry — по итогам verifier).

## 11. Комплект

`source-baseline.json`, `source-final.json`; `runs/` — только через `web_alarm.evidence_sanitizer`, LF (`runs/runs-map.json`, `runs/census.json`; `runs/direct/*` — прямые запуски; `runs/probe-child-root-*.json` — зонд корня); `tools/` — `probe_child_root.py`, `direct_run.py`, `build_mirror.py` (C1–C3, A1–A6, `original-test`), `run_mutants.py`, `run_gate.py`, `census.py`, `snapshot.py`, `collect_runs.py`, `make_manifest.py`, `rotate_task.py`; `manifest.json`; ротация — `rotation.json`.

## 12. Ротация карточки

`tools/rotate_task.py`, квитанция `rotation.json`: precheck OK (БЛОК 1 = эта TASK, окна 5/5, предыдущая своя запись `001` прочитана по квитанции FT1-ARCHIVE-RETRY и заканчивает файл); **A** — запись `001` (постановка дословно, факт `closeout-001.md`, вытесненные строки `CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001`) 26 279 B со смещения 745 783, readback MATCH, прежние байты неизменны; **B** — новые строки сверху БЛОКОВ 2–3, окна 5/5, БЛОК 1 → `Статус: ОЖИДАНИЕ НОВОЙ ЗАДАЧИ` / `TASK: —`; Правила и **БЛОК 4 побайтно неизменны** (`2cd5bada…49af8`).
