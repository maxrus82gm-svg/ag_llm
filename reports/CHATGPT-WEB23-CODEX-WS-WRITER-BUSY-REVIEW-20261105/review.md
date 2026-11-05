# WEB23 — независимая проверка H-CODEX-000014

**Дата:** 2026-11-05. **TASK:** `CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001`. **HISTORY:** `H-CODEX-000014`.
**Опубликованный источник:** `main@194d731f9af4a84e45d00b36bec766f2ac42dd8b` (одна авторская публикация).
**Verdict:** **PARTIAL / BOUNDED SOURCE + AUTHOR EVIDENCE.** Документальная итерация закрывается; исправление исходного CI timeout **НЕ принято как FIXED**.

## Проверено независимо

1. В актуальном GitHub прочитаны №08, общий №000, текущий №34/40, №05/№001, точная запись `task_record.json`, report и выборочное evidence. Сверены TASK и HISTORY ID, авторская ротация/БЛОК 1 WAITING. Хеши UTF-8 источников из GitHub совпали с author manifest/record: `context_storage.py` SHA-256 `8b5bed4e6832572d9af816899642bf4a3287d455ee4be4f67326c0130cce8f64`, `test_ultra_chat_storage.py` `345f7c763125628bbfa5450ddd4782650adf2f5a7073f3dd03bc92f8482718ee`, report `0706425047d31e749fef93b4cc58c4fe28b268e68eb1047d737a89e1eb0d3a57`, assignment `445554a5bd6e811292aee1bf2c8a0f7b95b9ae4e15ba842593f577ebbd27213f`.
2. Кодовый diff относительно предшествующего `292ba1ec` просмотрен адресно. Runtime: импорт `errno`; `_try_lock_byte` теперь повторяет только `EACCES/EAGAIN`, неожиданные `OSError` пробрасывает. Timeout 10 секунд, polling, native lock/unlock, no-follow/identity и RAW publish не менялись. Test diff: UTF-8 child `-X utf8`, весь stderr вместо `[-800:]` и три negative/regression tests; исходный двухпроцессный selector и его oracle не ослаблены.
3. Просмотрены исходные RED `error_classification_red.txt`, timeline `timeline_analysis.json`, `afterrepair/summary.json`, report и отдельные результаты с persisted evidence. Controlled wait: 904 отказа `EACCES` за ~10.0035 с; конкурент 20 раз повторно получал lock, суммарный измеренный body ~9.966 с. Это объясняет, как возможен bounded timeout без одного 10-секундного holder, **но не устанавливает конкретную причину исторического CI**.
4. Авторские результаты (не independent executions): 261 PASS / 5 SKIP (без дублирования перекрывающихся наборов), 26 отдельных subtests PASS; исходный selector после ремонта 5/5 PASS, four-process stress PASS. По отчёту пользовательские storage 595/595 unchanged. Сведения о запуске и сохранности взяты из evidence автора.

## Ограничения и находки

- Исходный [Windows CI FAIL 42040238153](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42040238153) был реальным. Неизвестны первоначальные holder timing, errno и причина замедления. Независимое выполнение новой Windows CI/полной регрессии **NOT RUN** в этой проверке. Сведения автора о 261 PASS/5 SKIP не приравниваются к независимому PASS.
- Изменённый авторский git commit содержит также `.obsidian/graph.json` и `.obsidian/workspace.json` вне инженерного write-scope. Источник редакторского изменения неизвестен; сохранность по этому признаку не подтверждаем, не откатываем без user GO. Автор сам указал `.obsidian/workspace.json` delta. Это packaging/working-tree замечание, не подтверждённая порча Ultra storage.
- В тесте `test_child_interpreter_matches_the_utf8_pipe_even_with_legacy_locale` имеется `os.environ.pop('PYTHONIOENCODING', None)` внутри `patch.dict`; для окружения с заданной переменной это меняет родительское окружение до выхода из теста. Некритичный test-hygiene followup, не blocker основной bounded review.
- TEST Stage 3 остаётся TEST; не включать Standard sending, Colibri, real LLM, MCP/paid/Stage4. Linux/network FS/power-loss/native UI NOT RUN.

## Решение / NEXT

**DOC ITERATION CLOSED / TECHNICAL PARTIAL.** Принять ограниченные диагностику и исправления классификации ошибок/child stderr как опубликованный результат. Сохранить `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` **OPEN**, привязать `CODEX-WUA-S3-WS-WRITER-BUSY-REPAIR-001` / `H-CODEX-000014`, не назначать successor автоматически. Следующее адресное продолжение после USER GO: повтор исходного конкурентного Windows CI на точной новой версии с полным stderr, measured wait/hold/errno/fsync, сохранностью RAW и отделением допустимого bounded busy от livelock/fairness policy; не повышать timeout/не добавлять неидемпотентный retry без решения контракта. `H-CODEX-000014` не переиспользовать для новой TASK.

**Verification scope:** GitHub source/diff/hash/readback + inspection of author evidence only. **Independent new runtime:** NOT RUN. **Documentation publication:** GPT branch, user acceptance pending.
