# Адресное предложение координатору WEB22

STATUS: REQUEST FOR SEPARATE USER TASK / NOT ASSIGNED / NOT APPLIED.

Нужен отдельный разрешённый ремонт существующего Run Store перед продолжением Stage3. Основание: текущая TASK §4.4, §6 и §9; `FOLLOWUP-WUA-P9-AUDIT-PATH-001`, `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001`. В текущем write-scope `run_store.py` read-only.

Конкретный scope для рассмотрения: `run_store.py`, соответствующие тесты `test_run_store_v2.py`, имеющиеся prerequisite-оракулы `test_web_alarm_ultra_chat_turn.py` и отдельный отчётный пакет. Общие storage primitives — только если новое поручение отдельно разрешит их изменение. Не менять provider/B2/Blueprint/launcher, не делать реальные запросы.

Требования: no-follow проверка `.ultra/audit`, всех вложенных chat/run/index-generation путей и открытых файлов/receipt locators; сохранность внешних целей при junction/symlink/hardlink/traversal; единый проверяемый writer или явный bounded отказ второго писателя одного RUN; атомарный порядок stream/index, уникальные sequence и достоверные offsets/hashes; ошибки обязательной фиксации не превращать в SUCCESS. Crash/restart, Windows replacement, normal RUN и существующая P9 индексная регрессия обязательны.

`proposed_run_store_NOT_APPLIED.patch` — точечный review-only diff двух обнаруженных механизмов: проверить audit directory внутри общего Workspace lock и сериализовать `append_run_record` тем же lock. Он **не применён/не исполнен** и сам по себе не объявляется полным path hardening: вложенные пути, file handles и частичный stream/index append требуют отдельного review и тестов. Материалы исходной функции и SHA сохранены в `before/` и `evidence/proposal.json`.

После независимой приёмки prerequisite repair пользователь назначает продолжение Stage3 с текущими `turn_contract.md`, `risk_test_matrix.md` и сохранёнными RED. Новый RUN/Turn store не является допустимой заменой ремонта.
