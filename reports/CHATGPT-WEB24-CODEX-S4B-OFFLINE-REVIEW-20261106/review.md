# WEB24 — H-CODEX-000017 / Stage4B OFFLINE independent review

**Дата:** 2026-11-06. **TASK:** `CODEX-WUA-CHAT-S4B-TURN-OFFLINE-INTEGRATION-001`. **Исходник:** `main@f25ef7e859bb12514d026bab5ddfc9cbdfcb7e94`; родитель `3b9dbec3923de839ce1020df997f4df6ff826c19`.

**VERDICT: PARTIAL / S4B OFFLINE TARGETED PASS, CROSS-STAGE S4A TIMEOUT REGRESSION OPEN.** Это документальное завершение проверки H17, НЕ принятие этапа 4 целиком, не разрешение Stage5/real/paid/OAuth/Colibri.

## Независимые проверки

- Прочитаны свежие №08, 000, 34, 40, очередь №05, краткие №001, №18, постановка, отчёт, `task_record.json`, `manifest.json`, finish receipt, полный профильный Turn/adapter/test source. Codex БЛОК1 WAITING, БЛОК1.1 H17; штатный `finish ROTATED` exit0 (это не verifier PASS).
- Независимо проверено **50/50 файлов манифеста по SHA-256 и UTF-8-размеру**: 21 опубликован с LF, ещё 29 точно совпали после восстановления CRLF; расхождений 0. PIN исходников: `web_alarm/turn_service.py` `66dbb1c74983efa2bc38aa8c11ddd834a84f009de9eda7e1c24e0a9689294805`; `web_alarm/ordinary_chat_test_adapter.py` `fa62abf7268e9e60696d5d6ce85fe2ad4031f4ff884e0ecc83f75650024428f0`; `test_web_alarm_ultra_chat_turn_s4b.py` `c7d3257f24cbd6c6b158b2639abb0137984fd3dcac526e21f9c3d1de6b2e05ed`. CI на Windows нормализует рабочие CRLF при сравнении с Git.
- S4B использует явный offline fixture adapter и TEMP allowlist, общий `ordinary_chat_service` и существующий `TurnService`/RAW/RUN writer, immutable prepared snapshot, durable started/terminal, controlled recovery without replay, bounded usage classifications; в обычном UI и HTTP адаптер НЕ включён. Проверка реализована на исходниках и собственными CI-oracles, не утверждает production sandbox.
- **Новые reviewer tests:** `reports/CHATGPT-WEB24-CODEX-S4B-OFFLINE-REVIEW-20261106/test_independent_s4b.py`, 5 негативных проб: OFFLINE без адаптера не записывает данные; Stage3 TEST не вызывает fake LLM; v2 запись с отключённым адаптером не читается и не изменяется; чужой Workspace root не записывается; pinned source SHA совпадают. Reviewer tests 5/5 PASS в двух отдельных CI-прогонах.
- Windows GitHub Actions `windows-latest`, Python 3.12.10, sparse checkout, только синтетические Workspace. Strict early guard заблокировал физическую сеть, DNS, credential read (по 3 ожидаемых отказа S4A и S4B). Stage3 HTTP использовал лишь loopback. **Реальные provider/OAuth calls 0**.

## GitHub Actions — независимое исполнение, отрицательные результаты не скрыты

| Run | Проверки | Итог |
| --- | --- | --- |
| [42178648349](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42178648349) | S4B 14 + S4A 39 + Stage3 30 + Storage 14 + Run Store 51 | **148 PASS, 0 FAIL** |
| [42179125624](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42179125624) | Reviewer 5 + S4B 14; затем S4A 39 | **Reviewer 5 PASS, S4B 14 PASS, S4A 38 PASS / 1 FAIL**. Downstream tests SKIPPED после красного шага. |
| [42179394007](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42179394007) | Reviewer 5 + S4B 14 + S4A 39 + 20 отдельных повторов deadline + Stage3 30 + Storage 14 + RunStore 51 | **173 PASS, 0 FAIL; deadline 20/20 PASS**. Это НЕ отменяет previous red. |

**Найденный негатив:** `test_ordinary_chat_service.ExecutionContract.test_swallowed_timeout_cannot_publish_late_success`, Windows run 42179125624, job 127764370552: при 10 ms deadline и транспорте, намеренно подавляющем `asyncio.CancelledError`, `execute_request` вернул `Outcome.COMPLETED` / `Execution.RESPONSE_RECEIVED` вместо обязательного `UNKNOWN_AFTER_START`. Одновременный независимый S4B suite 14/14 PASS. **Причина точного таймерного расхождения ещё не доказана**; это нельзя просто назвать тестовым флейком и закрыть повтором. Нужен узкий Stage4 исправительный контракт и независимый negative oracle. Сервис S4A с таким поведением ещё не принимается в полном end-to-end safety gate.

## Оставшиеся границы / NEXT

- `FOLLOWUP-WUA-S4-DEADLINE-UNKNOWN-001`: **OPEN / USER ASSIGNMENT REQUIRED**, отдельный Codex repair в `ordinary_chat_service.py` и `test_ordinary_chat_service.py`, без изменения принятых Turn/Run Store/API/UI; проверить нефиктивную UNKNOWN классификацию и повторить pinned Windows CI с сохранением первой RED. Stage5 BLOCKED до независимой приёмки.
- `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` исторический OPEN (original CI cause UNKNOWN). Полная Ultra/Tk/browser regression, clean Windows portability №37 §2.4, нормальная проекция живого context, B2 accounting, реальные provider calls **NOT RUN**.
- Авторская сверка `595/595` пользовательских файлов, launcher STANDARD и editor baseline — **AUTHOR ONLY**, verifier локально файлы пользователя не исследовал. Пользовательский source commit `f25ef7e` включает постороннюю `.obsidian/workspace.json` вне разрешённого scope, owner UNKNOWN; не удаляли и не откатывали.
- После проверки Stage4 repair: **по утверждённому №37** Stage5 TEST UI→fake LLM, потом Stage6 budget/B2, затем Stage7 только отдельно разрешённый real GigaChat. **Colibri только после завершения и приёмки всего №37**. Stage4B документация закрыта как TECHNICAL PARTIAL; USER GPT→main merge pending.
