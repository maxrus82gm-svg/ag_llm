# History — CLAUDE-WA-013 / RC-6 Repair #4B

- 2026-10-08: постановка — прямой Chat-handoff, подтверждён пользователем («вот тебе еще одна задача»).
- Маршрут прочитан: 08, 18, общий 000, 00_INSTRUCTION, отчёт Repair #4A; 23 §4–§11, §17, §22; 24 (маршрут, таблица RC); 01 (строка Web Alarm).
- Сессия, safety copies (84/84 совпали), baseline.md, исходный полный прогон 547 OK skip 1.
- Воспроизведение: probes/repro_sibling_rollback.py на 165 / 164 / 154; probes/repro_rc4_protected_stage.py.
- Итог воспроизведения: дефект подтверждён и шире — см. context.md.
- Root cause и дизайн: нет persisted факта «RR из-за ABORT до исполнения»; RC-4 без проверки жизненного цикла. Решение — общее правило отката + статус microtask в settlement (отклонены: события как authority, отказ в Resolver, отказ от RR для #4A, запрет активации — DECISION).
- Прототип в scratchpad-копии → полный набор 547 OK (с +5 строками фикстур) → перенос в репозиторий скриптом (r+b, LF, сверка с safety copies).
- Новый модуль 22 теста; чувствительность на 165 — 20 из 22 падают.
- Adversarial: Z1 (24 раунда реальных процессов, оба порядка) — 0 нарушений; Z2 OK; Z3 — downgrade fail-closed; разовый FAIL_CLOSED одного recover не воспроизвёлся в 228 вызовах.
- Финальные прогоны: 569 OK, skip 1 ×2; фокусно 414/414; стресс 27/27; прежние пробы — вердикты как после #4A; compileall / diff-check OK; живое storage 136 / 41, хеш неизменен.
- Отчёт `rc6_repair4b_report.md`; карточка — FOLLOW-UP в БЛОКАХ 2–3 (проверено на диске). RESULT READY / AWAITING INDEPENDENT VERIFICATION.
