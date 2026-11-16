# CHATGPT-WUA-STANDARD-HISTORY-CI-ORACLE-001 — Windows regression fixture correction

**TASK ID:** CHATGPT-WUA-STANDARD-HISTORY-CI-ORACLE-001  
**Date:** 2026-11-16  
**Type:** independent GitHub CI finding / separate tests-only correction  
**Status at authoring:** prior CI FAIL recorded; new Windows CI PENDING; owner physical GUI NOT RUN.

## Observed independent failure

#629 / `CHATGPT-WUA-STANDARD-HISTORY-READ-001`, source `0d48436b8acf7ecba139cce5286f9b07102a4e52`. Windows run [43910083916](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43910083916) executed 53 Python tests: 52 passed, 1 failed at `test_standard_legacy_history_without_test_turn_is_readable_and_unchanged`: outcome `['request','legacy','legacy']` vs expected `['request','legacy','failed']`. The test created a string with two literal backslashes before `n` instead of the actual newline expected by legacy failed-marker detection. The implementation correctly classified that literal text as `legacy`; other tests, including STANDARD legacy history GET, partial history, and REAL HOLD, passed. The JS step was skipped after the Python failure.

General `Web Alarm smoke` [43910084039](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43910084039) stopped at checkout (Windows path too long), before exercising these changes; this is NOT a runtime test failure and is a separate open CI gap.

## Correction scope / REUSE

- Replace exactly two occurrences of incorrect backslash sequence in regression fixture; keep the expected `failed` classification only for a genuine newline.
- Add `test_web_alarm_ordinary_application.py` to `wua-standard-live-offline.yml` push paths. Previously editing the file alone could not rerun the workflow on push.
- No runtime files, data, GigaChat authority, storage format or launchers changed. Preserve #629 read-only STANDARD fix and strict synthetic TEST gate.

## Verification

GitHub Windows `wua-standard-live-offline.yml` automatically runs on GPT push, isolated sparse checkout, no real provider credentials, 4 Python modules plus deterministic Node DOM. Review exact source SHA/log/artifact; report PASS only once completed successfully. Owner manually tests old history via STANDARD after merge, reopening and F5; production RAW and physical browser are NOT part of CI.

**Do not merge until Windows profile passes.** Related owner followup `FOLLOWUP-WUA-STANDARD-LEGACY-HISTORY-001` remains OPEN for physical GUI confirmation.
