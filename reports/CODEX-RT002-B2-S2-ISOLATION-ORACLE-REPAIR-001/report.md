# S2 isolation oracle — OFFLINE ledger и запрет production policy imports

**TASK:** `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001`  
**Исполнитель / дата:** Codex 007 / 2026-11-08  
**Статус:** **AUTHOR RESULT READY / INDEPENDENT REVIEW PENDING (WEB26)**.  
**Режим:** STRICT OFFLINE / LOCAL ONLY / NOT PUBLISHED.  
**Assigned base:** `main@0ee846a1159c690d2bc29eab46fca807e4027541`; фактическая Git identity не проверялась, Git/GitHub NOT USED.  
**Provenance:** before/final snapshots, source_preflight и exact-byte SHA-256 manifest.  
**Граница:** все обязательные авторские OFFLINE gates этой TASK PASS; не независимая приёмка S3a, не S3b/Stage6/Stage7/live GO.

## Причина и результат

Исходный FAIL воспроизведён **до правок** полным штатным guarded S2 selector:
73 tests, **72 PASS / 1 FAIL**, ERROR/SKIP0, exit1, isolation violations0.
Имя: `IsolationTests.test_no_production_module_imports_the_policy_yet`.
Raw stdout/stderr, result/unittest log, argv/exit и исходный source SHA сохранены
как `evidence/red.*` и `before/test_rt002_s2_budget_policy.py`.

Прежний oracle запрещал policy import каждому файлу S1 source census. В нём
есть новый standalone OFFLINE ledger, который намеренно использует чистую
policy library. Наличие файла в census не доказывает production enforcement.
Это подтверждено исходниками, исходным RED и WEB25 independent H24 review.

Изменён **только `test_rt002_s2_budget_policy.py`**: один существующий isolation
test использует статический local import graph, добавлены его чистые helpers.
MANIFEST **73**, calibration ROWS/digest, route registry, output limits и
production snapshot list сохранены. Policy, ledger, S1/S3a tests, runtime,
transport, UI, Run Store и сетевые настройки не менялись.

Единственное допускаемое OFFLINE исключение связано с точной module identity
и фиксированным AST hash всей утверждённой реализации ledger. Новая реализация,
копия с другим именем либо production → ledger → policy дают RED. Все остальные
локальные модули, включая новые и пока не вызываемые, считаются консервативными
production candidates; UNKNOWN не объявляется безопасным.

Фактический graph: **82 local modules / 80 conservative roots / 6 reviewed
entrypoints / 1 exact OFFLINE capsule / 0 incoming ledger edges / 0 production
paths to policy**. Exact graph и hashes его 82 sources сохранены в evidence.

Подробная классификация, entrypoints, aliases, metadata query и граница
доказательства: [import_review.md](import_review.md).

## Зависимости, preflight и scope

Адресно прочитаны текущая карточка/БЛОК4, №08, №20 §5а, текущие H24/S1/S2
записи №21/34/37, №36.1/36.3, относящийся FOLLOWUP №05, H24 report/review и
amendment_request_s2. Independent Windows H24 S1 69 + extra23 принят в прежних
ограниченных пределах; independent S3a runtime по-прежнему OPEN.

До implementation сверены **203 source/CMD файла**: S1 — exact published SHA
из independent review WEB25, остальные — неизменный baseline H24. **Drift=0**.
Это локальная hash сверка, не Git checkout/HEAD verification. Все 82 graph
sources входят в этот baseline и остались byte-identical. Из 203 исходных
контрольных файлов изменён один разрешённый S2 test, **202 неизменны**.

Фактические entrypoints прослежены по root MCP server, Start_Ultra.cmd, обоим
постоянным Web Alarm CMD и web_alarm CLI/server/launcher. CMD не запускались,
профили STANDARD/TEST не переключались, старый пустой BAT не восстанавливался.

Affected profile: Ultra 36.3, UL-I10 isolation / UL-I11 exact source/collection/
negative oracle и граница будущего S3b. Изменение test-only: server/UI smoke не
требовался. Ни общий runtime, ни политика, ни production routes не расширялись.

## Проверки — точные результаты

Python проекта **3.12.10**, Windows. Основные команды:

```powershell
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/collect.py s2
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/collect.py quality
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/collect.py s1
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/collect.py s1_extra
.venv/Scripts/python.exe -B -X utf8 reports/CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001/run_s3a.py
```

collect.py только фиксирует результаты child. Wrapper вызывает исходный
standalone main S2/S1 через runpy, без selectors/изменения collection или gate.
Secret guard устанавливается до импорта, inherited credential keys удаляются
без чтения; разрешена только существующая точная synthetic S1 OAuth fixture.
Сам штатный network/process/filesystem guard ставится до production imports.
S1 extra использует **неизменный H24 recon_checks.py**, output остаётся в новой
TASK. S3a использует прежний strict early guard и task-local worker/output path,
изменяемый только в памяти. Evidence H24 не перезаписывались.

| Прогон | Counts / результат |
| --- | --- |
| Первичный полный S2 RED | 73: 72 PASS / 1 FAIL; ERROR/SKIP0; gate FAIL / exit1; guard0 |
| Финальный полный S2 core | **73 PASS, FAIL/ERROR/SKIP0; gate PASS / exit0; isolation/problems0; selected=null** |
| Полный S1 guarded | **69 PASS**, FAIL/ERROR/SKIP0; gate PASS / exit0; isolation/evidence0; selected=null |
| S1 extra reconciliation | **23 PASS**, FAIL/ERROR/SKIP0; exit0, guard0; H24 tests не менялись |
| S3a regression | **35 PASS**, FAIL/ERROR/SKIP0; exit0, unexpected guard0; source unchanged |
| Новые import quality tests | **47 PASS**, 43 expected inner RED + 4 safe PASS; ERROR/SKIP0; exit0, guard0 |
| Weaken: suppress all issues | 47: **43 FAIL**, ERROR/SKIP0, expected exit1, guard0 |
| Weaken: omit transitive ledger edge | 47: **1 FAIL**, ERROR/SKIP0, expected exit1, guard0 |
| Weaken: bypass capsule AST hash | 47: **1 FAIL**, ERROR/SKIP0, expected exit1, guard0 |
| Guard controls | Socket, DNS, credential env/file — **4/4 blocked before I/O**, exit0 |
| Syntax / compile | S2 и package helpers AST parse + compile без execution/pycache; evidence/syntax.json |

Точные argv/exits/source SHA — `*.execution.json`; полные stdout/stderr и
unittest/result/XML — evidence. Не суммировать перекрывающиеся прогоны как
уникальные tests. S2/S1 здесь — полные standalone selectors, не discovery,
не partial runs и не пропуск неизвестных/missing fixtures.

S1/S1-extra/S3a исполнялись на неизменных source hashes. Последующее усиление
S2 import oracle их код/зависимости не меняет; после него заново исполнены
затронутые S2, все 47 quality и три weakening controls. Эти финальные S2 runs
связаны с exact final S2 source SHA. Source preservation проверен после всех runs.

## Отрицательные доказательства и инженерный review

### MANUAL ENGINEERING REVIEW

**Проверенный порядок.** Source census → named local dependency discovery →
package identities/initializers → import bindings и alias/re-export expansion →
capsule AST verification → conservative candidate roots → graph walk до policy.
Cycle detection не даёт бесконечного обхода; unknown resolution формирует issue.
Физические imports и inspected exec strings не исполняются ради графа.

**Непропускаемые RED.** Прямые import/from/aliases; production → ledger → policy;
new bridge/consumer; relative imports и package initializers; dynamic loaders,
aliases/getattr/module dictionaries/re-exports; escaped loaders; literal exec;
unknown names/packages/exec/file loaders; protected names/submodules/paths;
изменённая capsule/clone; shared dependency → policy; cycles; local stdlib shadow;
missing policy; star/unknown fromlist и relative builtin import; попытка расширить
входной домен pinned metadata spec query.

Каждый quality case запускает **реальный существующий S2 isolation test method**,
требует testsRun=1 и ERROR/SKIP0, сохраняет actual assertion traceback и audit.
Для разрешимых цепочек отдельно требуется реальный policy_path, а не только
диагностика имени. Два cases создают файлы в собственном TEMP, проверяют
обнаружение pkg.child через __import__ fromlist и затем безопасный/опасный child.
Все 47 результатов — `evidence/quality.result.json`; компактная матрица —
`evidence/negative_matrix.json`. Внешний PASS negative test означает доказанный
inner RED. Отдельные weakening runs подтверждают, что ослабление oracle делает
эти проверки красными; это не expectedFailure и не искусственный SKIP.

**Отвергнутые альтернативы.** Удалить ledger из S1 census, разрешить все импорты
по имени файла, проверять только direct imports, считать все новые модули safe
или исключить shared dependencies — отклонено. Выбран exact reviewed capsule
с запретом любой production reachability; library storage deps не наследуют
его исключение. Unknown local/external import roots требуют review. Два текущих
external roots httpx/mcp и stdlib не скрывают локальные shadow modules.

**Самостоятельно найденные gaps.** Первые 33 quality PASS расширены до 36 после
проверок loader namespace/getattr alias/escape. Затем добавлены builtin level/
fromlist, file loaders и реальные file discovery cases. Закрыты скрытый child
из fromlist, relative builtin ambiguity, metadata helper/registry escapes и
protected dotted names. Промежуточные 33/36/44 quality и ранний S2 PASS сохранены
отдельно; финальные 47/73 получены после усиления. Это source-review findings,
не заявленные первичные runtime FAIL. Единственный исходный S2 RED не удалялся.

**Metadata query.** Существующий find_spec(provider.adapter) не объявлен общим
safe import. Он связан с H24 S1 pinned Provider/factory/call references и
конечным текущим доменом builtin adapter/None; новые внешние обращения к Provider,
BUILTIN_PROVIDERS/_adapter_state требуют review. Любой другой unknown spec query
отказывает; literal spec query учитывается консервативно как import target.

**Границы и риски.** Это snapshot-level static oracle. Он не интерпретирует
произвольный обфусцированный Python, runtime monkeypatching, native/third-party
internals, OS subprocess dispatch или враждебную одновременную подмену sources.
Неподдерживаемые распознанные import mechanisms fail closed; новые loaders и
plugins требуют review. Hash pin привязан к project AST Python3.12 и требует
осознанного обновления при reviewed ledger/source/interpreter изменениях.
Это усиление прежнего import oracle, не runtime security enforcement. S3b
должен отдельно защищать physical pre-HTTP boundary; library import PASS не
разрешает платный запрос, live activation или изменение числовой policy.

## NOT RUN, OPEN/NEXT, DOC IMPACT и сдача

NOT RUN: независимый WEB26 replay; S2 optional provenance; S0; whole-repo/CI;
UI/browser/launcher live smoke; real HTTP/GigaChat/OAuth/paid/real model inference;
production budget integration/S3b/S3c/S9; независимая приёмка S3a.
Реальных provider calls в TASK — **0**. Git/GitHub — **NOT USED**.

Все OPEN/owners/следующие решения — [followups.json](followups.json). Старые H23/H24
ограничения сохранены: Ordinary Chat policy и numeric USER decisions, independent
S3a runtime, RAW wire retention, adoption/upgrade, capacity, power-loss/fencing и
trusted NOT_SENT proof. Успех этой TASK не закрывает их. Новая TASK не назначалась.

DOC IMPACT: собственный report/evidence и штатная механическая сдача карточки.
Общие №05/06/20/21/34/37, чужие verdict и БЛОКИ2–4 автором не редактировались.
SHARED DOC DELTA для WEB26: original S2 72/73 → author73/73; S1 69 + extra23 и
S3a author35 preserved; quality47 (43 RED/4 PASS), weakening3 expected RED;
oracle repair готов к независимой приёмке, продукт Stage6/Stage7 не объявлен DONE.

Manifest охватывает source и весь package, кроме самого manifest. Home paths в
публикуемых logs заменены на <USER_HOME>; исходные bytes сохранены content-addressed
в private TEMP task archive, hash mapping — `evidence/sanitization.json`.
Архивные RAW prompts и credentials в пакет не копировались. Private raw logs
проверяются по SHA, а не молча перезаписываются при повторной подготовке.

После package check выполняется штатный finish с exact TASK ID; report после
регистрации HISTORY не меняется. Протокол/exit/HISTORY/readback —
finish_protocol.json/closeout.json. БЛОК1 должен стать WAITING, БЛОК1.1 —
SUBMITTED / REVIEW PENDING; прежний snapshot и БЛОКИ2–4 сохраняются. Пользователь
публикует пакет; прямая отправка в чужой чат и самостоятельная Git-публикация
не выполнялись. Независимый вердикт остаётся за WEB26.
