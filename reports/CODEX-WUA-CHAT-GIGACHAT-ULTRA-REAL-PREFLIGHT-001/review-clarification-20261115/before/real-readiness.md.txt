# REAL readiness — PARTIAL/BLOCKED, REAL HOLD

| Gate | Статус | Что ещё требуется |
| --- | --- | --- |
| Единственный Ultra Core, registry/serializer/Turn/RAW/ledger reuse | Подтверждено source + bounded авторские OFFLINE | Независимая проверка этой сдачи. |
| Закрытая серверная точка | Реализовано | `ordinary_gigachat_transport.create_real_transport(model_id)` сначала вызывает существующий unconditional deny, даже при его аварийном возврате не строит client. Это не готовый REAL factory. |
| Отказ до secret/cache/OAuth/HTTP | Авторский OFFLINE PASS | Не снимать gate по JSON, env, URL, cached token или VERIFIED-looking профилю. |
| Model contract | PARTIAL | Публичный ID подтверждён; exact executable context/output/reasoning bound и calibration ещё отсутствуют. |
| Account scope/entitlement | UNVERIFIED | Отдельная разрешённая account-проверка. PERS/Freemium нельзя предполагать. |
| Cached usage / S9 | BLOCKED | OpenAPI и `_usage`/`ultra_budget_policy.validate_usage` расходятся. Согласовать единую семантику, совместимость исторического ledger и late/duplicate usage; тесты и независимая приёмка. |
| Version-bearing response model | UNVERIFIED | Согласовать identity binding/version handling, не разрешать произвольный другой model. |
| Reserve/SENT/final bytes/terminal/replay | BOUNDED synthetic PASS | Non-TEMP production ownership/enrollment и restart/fencing остаются OPEN. Не обходить exact TEMP-only gates. |
| OAuth/cache/TLS/proxy/redaction | BLOCKED | Реализовать безопасную адаптацию существующего владельца, account-bound cache и expires_at, отдельный разрешённый OAuth budget без скрытого refresh. |
| Cancel/timeout/crash UNKNOWN | BOUNDED synthetic PASS | Нет гарантии прекращения remote расхода; реальный UNKNOWN не освобождать. Hardware/power-loss NOT RUN. |
| STANDARD/TEST | Существующие ограничения сохранены | STANDARD Pro-only HOLD, TEST synthetic only. Ultra STANDARD не включён. |
| S3b/S3c/S4/S5/C1/C2/S9/S13a | OPEN по применимому scope | Координатор явно определяет ordinary subset по №20 §5а; авторские tests не закрывают полный граф. |
| Независимый Windows review / USER GO | NOT RUN / отсутствует | После публикации пользовательского пакета — независимые GitHub-hosted Windows checks; затем отдельный ограниченный USER GO. |

**LIVE task сейчас не готова к исполнению.** Следующая безопасная работа — согласованный shared accounting contract и закрытый production factory/recovery OFFLINE successor. Текущая задача не просит разрешения на LIVE и не объявляет REAL READY.
