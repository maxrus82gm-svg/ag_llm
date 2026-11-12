# WEB29 — независимая проверка H-CODEX-000031 / F-01

**Дата:** 2026-11-12. TASK `CODEX-WUA-CHAT-S3B-F01-LAUNCH-GUARD-001`. HISTORY ID `H-CODEX-000031`.
**Вердикт:** PASS / BOUNDED INDEPENDENT OFFLINE для допуска TEST launcher с `--require-test`; H31 DOC CLOSED только в указанной границе.

**Исходники:** пользовательский main №573 `a26b3157f09361d3fe70aaf9781e7efa41a79126`, merge `a492889400a2e50b8204efa6fba5762a9a0f2fcd`; независимый GitHub workflow на `GPT@90f169b376c4aa0fb9d86f9523fd49aadd867b49`.

**Независимый Windows CI:** https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43264689001 — **SUCCESS**; Python 3.12; авторские regression/activation 18/18 PASS + 3/3 новых independent verifier oracles = **21 PASS, 0 FAIL, offline guard violations 0**. Workflow `.github/workflows/gpt-web29-h31-f01-independent.yml`, verifier `reports/CHATGPT-WEB29-H31-F01-CI-20261112/test_independent_f01.py`.

**Факты:** `_require_offline_test` вызывается до dispatch, только под `--require-test`. Разрешены строго две комбинации: `ordinary-core-offline` / `web_alarm/ordinary_test_fixture.py` / пустые args и `stage5-offline` / `reports/CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001/review_fixture.py` / `--web`. Подмена script/args/имени/kind и повреждённый JSON отвергаются до subprocess. Режим `--standard` и общий launcher без флага сохранены. Оба постоянных CMD, TEST-конфигурация, fixtures и H30 artefacts не менялись; проверены опубликованные blob SHA до/после №573.

**Исторические CI-неудачи:** первый run 43264179812 — Windows checkout упал на MAX_PATH до тестов; второй run 43264396591 — неверная комбинация TEMP/LOCALAPPDATA у CI. Исправлены только workflow sparse checkout и temp-env, production-код не менялся. Финальный run 43264689001 SUCCESS; старые FAIL сохранены.

**NOT RUN:** физический CMD/browser/F5 smoke, общий полный CI, настоящие LLM/OAuth/paid, модификация доверенного Python, все pre-HTTP send пути и общий S3b. H30 `H-CODEX-000030` остаётся PARTIAL / independent REVIEW PENDING, не принят этим review.

**OPEN:** локальная резервная копия H30 `codex-wua-s3b-presend-backup-3h_6pzlf` и H31 `codex-wua-f01-launch-guard-backup-ymnr7i3y` — CLEANUP PENDING; удалять только после проверки точных путей на нужном ПК. S3b/real/Stage7 HOLD до отдельных gates и USER GO.

**NEXT:** адресная независимая приёмка H30; затем отдельно назначить минимальную Ordinary S3b fake pre-send bytes/reserve/one-send TASK. Не создавать новую LLM-архитектуру и не запускать real провайдеров.

**USER HARD GATE 12.11.2026:** независимый успешный run → весь документационный closeout (review, task_record, №001/05/06/34/40, БЛОК 4) → один нумерованный атомарный GPT commit → пользовательский merge в main.
