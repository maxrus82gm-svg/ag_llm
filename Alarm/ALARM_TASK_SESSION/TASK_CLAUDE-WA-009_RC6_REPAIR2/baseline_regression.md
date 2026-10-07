# Baseline regression

- ВАЛИДНЫЙ baseline: Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RC6-REVERIFY/full_regression.txt — 439 OK (skip 1) на runtime commit 160; runtime-байты на старте Repair #2 идентичны (git diff --quiet 07c4667 HEAD -- web_alarm test_web_alarm_*.py -> 0).
- baseline_regression_INVALID_overlapped_edits.txt — НЕ baseline: прогон шёл параллельно с первыми правками, subprocess-тесты RC-4 импортировали rollback_service.py между двумя правками (NameError). Сохранён только как след.
