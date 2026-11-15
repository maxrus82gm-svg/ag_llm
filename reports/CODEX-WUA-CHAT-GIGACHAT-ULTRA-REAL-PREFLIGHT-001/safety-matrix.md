# Change → risk → selector → gap

ARCH CLASS: Web Alarm Ultra transport / существующий Python core. Профиль 36.2, обязательные 36/36.1; S1/S2/S3a из Ultra используются как зависимости, не переписываются.

| Риск / требование TASK | Реальное покрытие в этой сдаче | Граница |
| --- | --- | --- |
| Неавторизованный REAL, до cache/env/token/HTTP | Новый RealPreflightTests (7 методов), в том числе cached token и gate-regression fallback | Никакой выдачи production authority. |
| Неизвестная модель / отсутствующий contract / подмена caps | RealPreflightTests; ServerAdmissionTests.test_unknown_profiles_caps_endpoint_model_zero_http; test_owner_policy_profile_endpoint_tamper_after_sent_zero_http | Synthetic caps не становятся REAL. |
| Exact bytes, admission, один POST, usage/history/reopen Ultra | UltraHTTPTests.test_ultra_exact_wire_reservation_usage_history_and_restart; HTTPTransportTests; application exact wire test | httpx.MockTransport, не провайдер. |
| Journal failure / false acknowledgement | H34 forged reserve/SENT, capacity failure, terminal fake-ack; application terminal failure | Не hardware power-loss. |
| Timeout/UNKNOWN/replay/restart | Новый Ultra timeout; H33/H34/application timeout tests; S3a crash_before/crash_after и duplicate/late tests | Не remote cancellation guarantee. |
| Cancel | H34 before reserve / after reserve / token cancellation suppression; application cancel during HTTP; Ordinary execute_request cancellation suite | Никакого refund/нулевого расхода после SENT. |
| Erroneous response / секреты | H33 statuses/malformed/redaction; новый provider-error canary проверяет все файлы synthetic root, result/history | Сырой provider error не сохраняется. Реальных секретов в tests нет. |
| Per-chat модель/settings/history | H36 ModelPersistenceTests/PermanentProfileTests; H29 PerChatTests; Node 69 | OWNER GUI этой TASK NOT RUN; прежний owner PASS не присвоен повторно. |
| TEST не может выполнить REAL | Exact OfflineHTTPFixture/admission tests, actual TEST profile activation и global early guard | Нет browser/env REAL switch. |
| STANDARD Pro-only HOLD | Actual ApplicationTests + Node UI tests; unchanged factory/server/launcher | Ultra не добавлена в STANDARD. |
| Usage/cache/reasoning | Исправленный accounting_oracle: billing/shared full-input semantics, invalid old vector, unknown-cache reserve fallback, actual Turn no replay | Старый RED сохранён как ошибка оракула; shared cached contract совместим. Optional cached forwarding в Ordinary и real reasoning остаются отдельными ограничениями. |
| Полнота send inventory / отсутствие bypass | Dedicated S1, dedicated S2, isolation quality, in-memory authority bypass expected RED | Первые S1 FAIL сохранены; итоговая сверка обязательна. |

Команды/OS/версии/counts/logs перечислены в evidence/*.result.json. Наборы пересекаются; counts не суммировать. Guard установлен до imports production; env GIGACHAT_* удалены у child, DNS/external sockets/credential reads/Git/non-Python process/repository-live storage запрещены. Localhost используется только синтетическим local HTTP/self-pipe. В engineering tests внешних HTTP-запросов нет; публичная документация читалась отдельно.
