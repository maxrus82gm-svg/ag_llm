# Уточнение H37: ошибочный cached-usage blocker отозван

**TASK:** CODEX-WUA-CHAT-GIGACHAT-ULTRA-REAL-PREFLIGHT-001. **HISTORY:** H-CODEX-000037.  
15.11.2026; авторское исправление по замечанию независимого ревью. Нового задания, номера истории и ротации слота нет. REAL HOLD сохраняется.

Предыдущий вывод был ошибочным: автор прочитал описание total в OpenAPI, но не сверил значение prompt с профильным руководством. Старый RED демонстрировал неверный тестовый вектор, а не дефект shared accounting. Его результат и исходник сохранены, вывод явно отозван.

## Четыре поля и две разные величины

Проверены [руководство «Подсчёт токенов», редакция 17.07.2026](https://developers.sber.ru/docs/ru/gigachat/guides/counting-tokens) и [официальная OpenAPI](https://developers.sber.ru/docs/files/openapi/gigachat/api.yml). Проверка 15.11.2026 — только чтение публичной документации; account/API/OAuth не вызывались.

| Поле | Семантика |
| --- | --- |
| prompt_tokens | Новые, оплачиваемые входные токены; cache уже вычтен. |
| completion_tokens | Токены генерации ответа. |
| precached_prompt_tokens | Повторно использованный вход, исключённый из оплаты; участвует в полном контексте. |
| total_tokens | Оплачиваемое количество: prompt + completion. Повторно вычитать precached нельзя. |

OpenAPI менее подробно определяет prompt; руководство уточняет его. Противоречия между источниками не установлено. Пример руководства: **1/4/37/5**. Из этой семантики следуют полный вход **38**, вход плюс ответ **42**, оплачиваемые токены **5**. Эти величины нельзя выдавать за одну метрику или автоматически переводить в деньги. По одному usage нельзя доказать все model-specific reasoning/caps/account условия.

Исправленный пример **7/5/2/12** означает оплачиваемые 12, полный вход 9 и вход плюс ответ 14. Если первоначально подразумевался полный вход 7, корректен **5/5/2/10**. Старый **7/5/2/10** вычитает cache второй раз и обоснованно отвергается обоими текущими parsers. При отсутствующем cached полный вход неизвестен; нельзя приравнивать отсутствующее поле к нулю.

## Что уже делает существующий код

- `ordinary_chat_service._usage` сохраняет prompt/completion/total и проверяет сумму; для данной документированной арифметики совместим без изменения.
- `ultra_budget_policy.validate_usage` проверяет ту же сумму и сохраняет optional cached.
- `AttemptRecord._input_of`, `known_input_tokens` и `liability_tokens` при известном cached используют полный вход плюс output. Это консервативный контур нагрузки/резервирования; он **не является оплачиваемым total**.
- При отсутствующем cached policy оставляет `None` и использует максимум net prompt и сохранённой резервной оценки. Эта fallback — не точное измерение контекста и не сумма тарификации.

**Изменение shared accounting/formula/schema, миграция исторического ledger по исходному замечанию не требуются.** Общий S9/REAL gate этим ограниченным подтверждением не закрывается.

## Отдельная особенность Ordinary-интеграции

Сквозной MockTransport → Ordinary → Turn → ledger тест показал: `ordinary_chat_service.Usage`/`BridgeUsage` не переносят `precached_prompt_tokens`; `TurnService._ordinary_terminal` передаёт только три основных поля. Поэтому с provider fixture 7/5/2/12 billing в истории корректен (12), но ledger получает cached=None и сохраняет reserve-input + 5, а не точный полный вход 9 / нагрузку 14. В первом запуске резерв был 732, итоговая liability 737; это оценка, **не 737 оплаченных токенов**. После reopen повторного POST нет.

Pure policy уже корректно обрабатывает переданный cached; H34 legacy `_GuardedClient.post` также явно переносит поле после проверки. Данная Ordinary особенность — ограничение точности передачи дополнительной метрики, а не несовместимость shared arithmetic. Если понадобится exact cached/full-context в Ordinary, нужен отдельно согласованный narrow integration scope; в этом уточнении production-код менять запрещено. Без доказанного консервативного real estimation её также нельзя объявлять готовой REAL-калибровкой.

## Испытания и сохранность

Все Python-проверки через существующие early OFFLINE guards, без реальных credentials или внешней сети:

| Evidence | Результат |
| --- | --- |
| accounting_expected_red | Прежний 1 FAIL сохранён неизменным; ошибочная интерпретация отозвана. |
| accounting_corrected | Первый уточняющий набор: 4 PASS, 1 FAIL, 3 subtests; обнаружена непередача optional cached. Полный oracle и FAIL сохранены. |
| accounting_corrected_final | **5 PASS + 3 subtests**, exit 0, guard 0. Обе корректные семантики, invalid old vector, missing-cache fallback, actual Turn/history/ledger/reopen. |
| accounting_s2_recheck | **73 PASS**, exit 0, FAIL/ERROR/SKIP/isolation 0; policy не изменена. |
| accounting_hold_recheck | **54 PASS + 123 subtests**, exit 0; 3 точных ожидаемых guard probes, unexpected 0. H37 REAL HOLD и Ordinary сохранены. |

Точные команды, case IDs, counts, elapsed, stdout/stderr — `evidence/<stage>.*`. Эти наборы пересекаются. Новые оракулы размещены в существующем `accounting_oracle.py`; root runtime/tests не менялись. Проверены actual billed history, persisted ledger usage/state и отсутствие resend; ошибочное требование exact cached в Ordinary не было подменено заявлением о передаче поля.

`review-clarification-20261115/package_before.json` фиксирует все 117 исходных артефактов H37. `before/` сохраняет прежние report, manifest, task_record, closeout, oracle и другие изменённые документы; original RED/logs/finish/snapshot неизменны. История текущей report-ссылки обновляется с тем же H37, с предыдущим отчётом по сохранённому SHA; БЛОКИ 1/1.1/2–4 и assignment не меняются. Квитанция `correction_closeout.json` и manifest фиксируют финальную сохранность.

**Итог:** cached arithmetic COMPATIBLE, ошибочный shared blocker WITHDRAWN. Provider/account/caps/reasoning/TLS/OAuth/production recovery и независимая REAL-приёмка остаются OPEN; LIVE не запускался. Независимый verifier оценивает исправление отдельно. По последующему USER GO выполнено только локальное чтение HEAD/status/diff/log. HEAD и последний исходный H37 commit — `81df1fc9e793f87f7533af3b1d69367b17b3bb79`, сообщение `615`. Исправление **UNCOMMITTED**, собственного commit SHA пока нет; запись Git, push/merge не разрешены и не выполнялись. Протокол — review-clarification-20261115/git-readback.json.
