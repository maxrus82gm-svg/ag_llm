# ULTRA / RT-002 FA-M1 — независимая проверка ChatGPT

**TASK:** `CLAUDE-RT002-FA-M1-001` · **ARCH CLASS:** Ultra / Final Audit · **Verifier:** ChatGPT (агент 007) · **Дата source-review:** 2026-10-14 · **Дополнение по параллельности:** 2026-10-15.

**STATUS: SOURCE REVIEW COMPLETED / EXECUTABLE VERIFICATION NOT RUN / M1 AWAITING INDEPENDENT VERIFICATION.** Это самостоятельный отчёт о прочитанном исходном коде, а не замена отчёта Claude и не разрешение на M2, RT-002 closeout, live или rollout.

## 1. Исходники, ревизии и разграничение с WEB_07

- Закреплённая ревизия M1: `main@5c426e50b45abd60a3eb94d63037ba3c50e5f040` (пользовательский коммит №332).
- На момент дополнительной проверки актуальный HEAD: `main@03acbe8a7206545e0f9f1c30e1f36c1bddfa7e11` (№335). После №332 были №333, №334 и №335: сравнительный GitHub-diff показывает изменения **только** `.obsidian/graph.json`, `.obsidian/workspace.json`, `Документация/34_TACTICAL_CONTEXT.md`. Ни Ultra production, ни M1 тесты не менялись.
- Git blob SHA M1 = SHA текущего main: `server.py` `f2ae47d5459b439834d597f6d36f11c0fc52c096`; `test_rt002_final_audit_m1.py` `d7f9caba888d01f0ecb0eecc9bd057943471fd7f`; `test_final_audit.py` `ecf5daec5ef6825e39762eb81c3b0077f6902e67`; `test_final_audit_recovery.py` `c365c9d530dd435822fbed6f7abb9d5726789bb8`; `verifier_runtime.py` `4c6b7b08a50cd6698822c7eaba27718c91d9d11e`.
- Отчёт исполнителя: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-FA-M1-001/report.md`. Исторический диагностический отчёт: `reports/ULTRA-SIMPLE-RUNS-20261014-001/diagnostic_report.md`. Это отдельные доказательства; не смешивать SOURCE REVIEW, результаты Claude и независимое исполнение тестов.
- WEB_07 / Web Alarm: `web_alarm/`, корневые `test_web_alarm_*`, `reports/CODEX-WA4-R-004-F1-CLOSEOUT-GATE/` и собственный review/тактический handoff. Общие документы, особенно `34`, — потенциально конфликтные и **этим отчётом не изменяются**. Web Alarm F1/F2/F3 не объявляются проверенными через тесты Ultra.
- После нового GitHub-публикационного шага местные рабочие копии могут отставать от main. **Не принуждать WEB_07 делать Pull посреди активной TASK** и не смешивать его неподтверждённые локальные правки с этим документальным изменением.

## 2. Что подтверждено чтением кода и diff (не запуском)

1. В `server.py` убран legacy fallback Final Audit, в котором Planner OFF вызывал `_agent_git_status(root, policy)` без файловых путей и `_agent_git_diff(root, [], policy)`, потенциально забирая `git status/diff` всего дерева. Теперь при непустом наборе файлов используются `_agent_git_status(root, audit_policy, task_paths)` и `_agent_git_diff(root, task_paths, audit_policy, allow_missing=True)`; при пустом scope два явных `not_applicable` без Git-процесса.
2. Режимы теперь `task_scoped_v1` (Planner ON) и `run_scoped_v1` (Planner OFF). Без Planner scope формируется из серверных мутаций, RUN-owned и verification-путей, без импорта чужого содержимого из всего дерева.
3. `list_dir`/`find_text` и требования discovery не расширяют Git-pathspec; READ-scope остаётся проверяемым. Файловая цель, которая **на момент построения scope** является каталогом, помечается invalid, если это artifact/RUN-owned путь. Проверки на каталоги для evidence-requirements пропускают включение в Git.
4. При `write_revision > 0` без наблюдаемых RUN-путей устанавливается critical `mutating_run_without_scoped_paths`. Усечённый scoped Git status/diff становится критичным при обоих режимах. `unattributed_git_status` вычисляется для обоих режимов, когда Git действительно применим.
5. Кодовые изменения M1 опубликованы в №332: для `server.py` GitHub показывает +103/-51 строк (чистое +52). Заявление Claude о побайтовом восстановлении прежнего baseline и 9 конкретных локальных фрагментах остаётся **executor-reported**, пока не выполнена собственная baseline-реконструкция.
6. В `test_rt002_final_audit_m1.py` найдено ровно **25** селекторов MANIFEST; все 25 тестов существуют, дубликатов нет (учтены и обычные, и `async def` методы). Модуль содержит искусственный dirty-tree маркер, fake Git и fake HTTP; проверяется также исходящее тело FINAL-запроса verifier. **Наличие/качество oracle по source не равно PASS независимого выполнения.**

## 3. Findings и границы security-приёмки

### P1 / Potential TOCTOU — файл превращается в каталог между двумя проверками

`_collect_final_audit_task_paths()` проверяет `resolved.is_dir()` до вызова Git. Затем `_agent_git_status()` проверяет пути через `_validate_verify_paths(..., allow_directory=True)`, а `_agent_git_diff(..., allow_missing=True)` косвенно также устанавливает `allow_directory=True`. Между этими фазами параллельный процесс может заменить обычный/отсутствующий файл каталогом. Git-pathspec каталога теоретически захватит посторонние дочерние имена/изменения. **Это вывод по коду, НЕ воспроизведённый runtime-дефект.** Нужны adversarial test со сменой типа файла между фазами, проверка outbound verifier и fail-closed; real-Git disposable fixture — лишь при отдельном разрешении, с исключением общих ресурсов WEB_07.

### P2 / Семантика инструкции Dredd отстаёт от нового режима

`verifier_runtime.py` в FINAL-промпте запрещает требовать workspace-wide Git только если `task_scope is task_scoped_v1` (около строк 148–150). Новый `run_scoped_v1` прямо не указан. Это подтверждённое текстовое несоответствие, но **не доказательство ложного verdict модели**. Файл вне M1 write-scope; необходимо отдельное разрешение и задача для Claude, не самостоятельный патч ChatGPT.

### P3 / Недостаточная независимая исполняемая evidence

Claude сообщает: M1 **25/25**, Final Audit/recovery **99/99** (8 реальных Git-тестов NOT RUN), mutation testing **6/6**, S1 **69/69**, S2 **73/73**, S0 **166/166**, UI smoke OK, RAW hashes **8/8**. Эти цифры здесь **EXECUTOR-REPORTED ONLY**. Собственного Windows-прогона на pinned SHA не было: Desktop Commander `DESKTOP-SC96D3U` и `DESKTOP-43PAEBO` были offline. GitHub CI не запускался, реальный Git для M1 не выполнялся, сети/платных LLM вызовов не было.

### P4 / Остаточные продуктовые ограничения

Собственный scoped diff более 128 KiB сейчас даёт critical: это fail-closed, но потенциально ложный BLOCKED при больших законных правках (Claude R1). Git не умеет выделять авторство изменения чужой правки **в том же scoped файле**: владение должно подтверждаться серверными mutation/receipt/byte facts, а не одним Git diff. Переход к новому семантическому контракту документа `13` (Claude R2) и возможный pre/post-отпечаток (R4) — отдельные решения, не часть данного отчёта.

## 4. Условия перехода к M1 VERIFIED

1. На доступном изолированном хосте сверить sha исходников с pinned M1, запретить live/network/Git subprocess, подготовить private TEMP и выполнить **точный gated selector** `.venv/Scripts/python.exe -B test_rt002_final_audit_m1.py`. Зафиксировать exit, actual collection, 25/25, zero SKIP/guard violations, `result.json`, raw unittest log, hashes. Не подменять команду обычным `unittest`: он не даёт тот же gate.
2. Адресно проверить исправленные Final Audit/recovery oracle против baseline (их ожидаемые красные проверки), negative/false-claim cases и отсутствие утечки в зафиксированном outgoing verifier HTTP body. Исключённые Git-зависимые тесты именовать NOT RUN, а не PASS.
3. Отдельно предъявить/опровергнуть P1 через тест, который в точке между сбором scope и Git-фазой меняет тип пути; после этого дать решение по P2 (расширение verifier_runtime вне текущего scope) и P4 / 128 KiB. Любые coding changes назначить Claude/Codex с отдельным GO.
4. До независимого executable gate, решения рисков и согласованного DOC IMPACT не объявлять M1 VERIFIED, не закрывать RT-002 и не переходить к следующей стадии от имени этого отчёта.

## 5. Правила параллельной работы и публикации

**WRITE SCOPE данного результата — только этот новый файл.** Не менять `server.py`, `verifier_runtime.py`, `test_*.py`, `.obsidian/`, `Документация/34_TACTICAL_CONTEXT.md`, карточки Claude/Codex, файлы Web Alarm, чужие отчёты, workflows/CI. GitHub-фиксация документа не исполняет код, не обновляет локальную копию WEB_07 и не устанавливает ему обязанность синхронизироваться до окончания активной работы. Основа: `DOC-PARALLEL-01@1`, `DOC-GIT-01@1`, `DOC-ENGINEERING-ROLES-01@1`, `DOC-COMMIT-01@1`.

**Blueprint LLM / инженерная идея:** в будущей блочной модели полезно выделить параметризуемый блок `Evidence Scope` — явные owner RUN/role, разрешённые файлы/семантические источники, bounded output, fail-closed и версии контрактов. Это **PROPOSAL / NOT APPROVED**; не план реализации и не изменение Blueprint-документов.
