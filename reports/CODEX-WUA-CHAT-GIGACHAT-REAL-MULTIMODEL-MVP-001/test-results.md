# Авторские тесты — результаты

Acceptance children: Python 3.12.10 / httpx 0.28.1. Node v22.20.0. External provider/OAuth calls 0.
Наборы пересекаются; counts не складывать. Точные команды и cases находятся в одноимённых JSON/stdout/stderr.

| Evidence | Exit | Фактические counts |
|---|---:|---|
| expanded_protocol.result | 1 | {"test:passed": 13, "subtest:passed": 16, "test:failed": 1} |
| final_affected.result | 0 | {"test:passed": 180, "subtest:passed": 222} |
| final_protocol_usage.result | 0 | {"test:passed": 82, "subtest:passed": 150} |
| initial_protocol.result | 0 | {"test:passed": 7, "subtest:passed": 7} |
| mutant_reserve_red.result | 1 | {"test:failed": 1} |
| mutant_version_red.result | 1 | {"test:failed": 1} |
| protocol_complete.result | 0 | {"test:passed": 16, "subtest:passed": 16} |
| protocol_final_candidate.result | 0 | {"test:passed": 14, "subtest:passed": 16} |
| regression_final.result | 4 | {} |
| regression_initial.result | 4 | {} |
| regression_repaired.result | 1 | {"test:passed": 245, "subtest:passed": 329, "test:failed": 1} |
| regression_selected.result | 1 | {"test:passed": 158, "subtest:passed": 258, "test:failed": 5} |
| s1_final.result | 0 | {"run": 69, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| s1_initial.result | 1 | {"run": 69, "failures": 3, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| s1_reconciled.result | 0 | {"run": 69, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| s2_final.result | 1 | {"run": 73, "failures": 1, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| s2_final_exact.result | 0 | {"run": 73, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| s2_reconciled.result | 0 | {"run": 73, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| sealed_protocol.result | 0 | {"test:passed": 17, "subtest:passed": 16} |
| sealed_s1.result | 0 | {"run": 69, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |
| sealed_s2.result | 0 | {"run": 73, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0} |

UI: evidence/ui.stdout.txt — initial 69 PASS/1 helper FAIL; evidence/ui_final.stdout.txt и ui_complete.stdout.txt — 70 PASS, 0 FAIL/cancel/skip.
S1 historical RAW local runner реально выполнен и pins проверены; GitHub availability/independent run NOT RUN.
regression_selected: 5 исходных FAIL (contract/optional usage/parent cmd guard), regression_repaired: 245 PASS +329 subtests /1 stale retired-BAT FAIL; final_affected: 180 PASS +222 subtests. После финальных response-version/cached изменений повторён final_protocol_usage; после probe-only refinement — sealed_protocol.
mutant_version_red/mutant_reserve_red — ожидаемый RED по вторичной durable binding/reserve проверке, 1 failure каждый; источники не мутировали.
Неверные имена файлов regression_initial/regression_final дали exit4/0 collected, это ошибки command selection, не тестовый PASS.
Physical CMD child отказан guard; native CMD/Chromium/user UX/clean Windows/TLS handshake/LIVE NOT RUN. Полный B2 independent NOT RUN.
