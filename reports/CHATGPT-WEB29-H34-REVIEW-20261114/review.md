# H34 — независимая Windows-приёмка семи GigaChat legacy-send

**Дата:** 14.11.2026. **Проверяющий:** ChatGPT / WEB29.
**TASK:** CODEX-WUA-CHAT-GIGACHAT-REAL-READINESS-S3B-001; **HISTORY:** H-CODEX-000034.
**VERDICT:** **PASS / BOUNDED INDEPENDENT WINDOWS OFFLINE**. Только защищённый synthetic/mock HTTP контур H34, не полный S3b/Stage6 и не REAL/Stage7.

## Источник и инженерная независимая проверка

Авторский результат опубликован в main@db34931753ad1a6af88434a4ffe6b1097032070f (коммит №595); последующие документальные №596–600 не меняли production. CI-only №601 и №602 меняли только .github/workflows/gpt-web29-h34-independent.yml. Подтверждены **16/16 SHA-256** H34 manifest source_before_after с учётом точных LF/CRLF вариантов. Прочитаны shared admission, seven legacy factories, OAuth gate, H33 transport, policy S2, ledger S3a и Run Store owner; независимо проведены positive и negative tests.

Все семь legacy send-site переходят в gigachat_admission._GuardedClient, далее: immutable final bytes → S2/S3a reserve/SENT/readback → H33 httpx.MockTransport → terminal/recovery. Default без server owner отказывает до token/HTTP. get_access_token() требует require_real_authority(), который **безусловно DENY** до обращения к cache, env или сети. Нет настоящего REAL factory. Синтетические caps не коммерческие. Любые непроверенные privileged Python extensions не объявлены защищёнными универсально.

## GitHub Windows — фактически выполненные тесты

Первый диагностический [run 43575611209](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43575611209) зафиксировал **CI SHA oracle FAIL 14/16**: Windows checkout заменил LF на CRLF в двух исходно LF-only файлах. При этом legacy 244+110, regression254+256, safety PASS. Ошибка CI исправлена отдельным CI-only коммитом №602 (SHA сравнивается с оригинальным байтовым содержимым, LF или CRLF нормализацией), product code не менялся. Исторический FAIL сохранён.

Финальный [run 43576129606](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43576129606) — **SUCCESS**, 3 jobs, windows-latest, Python 3.12.10, Node 22. Полные job ID и краткие постоянные результаты — в independent_runs.json; raw logs, result/cases и negative controls — в трёх загруженных artifacts, expiry 28.11.2026.

| Gate | Независимый результат |
| --- | --- |
| SHA-256 source pins | 16/16 MATCH |
| Seven legacy send-site / agent, planner, verifier, compressor, admission | 244 PASS + 110 subtests; unexpected guard 0 |
| Adjacent H29–H33 regression / Turn / RAW / Run Store | 254 PASS + 256 subtests; unexpected guard 0 |
| S2 dedicated standalone | 73 PASS |
| H25/H34 isolation quality | 52 PASS + 6 subtests |
| No-owner denial of seven source sites | 1 PASS + 7 subtests |
| Mutations disabling budget, wire, terminal gate | 3 expected RED / 0 errors |
| Node UI regression | 57 PASS |
| Compile and synthetic Tk UltraApp constructor | PASS; unexpected guard 0 |
| Historical S1 exact R031/R026 RAW | NOT RUN in GitHub checkout; author S1 69 PASS separately |

Наборы пересекаются и **не суммируются**. Неприменимое source-only и сетевое подтверждение не выданы за реальные вызовы.

## Остаточные обязательные ворота и NEXT

**OPEN / NOT RUN:** реальные OAuth/API/paid, TLS/proxy/account-specific model availability and caps/usage/reasoning, full all-route S3b/S3c/S9/S13a, old audit/adoption, ledger capacity, host power loss/fencing, RAW privacy, физический CMD/Chrome/F5 и USER UX. Tk cleanup warning сохраняется. Отказ legacy provider observer может оставить UI summary неполным при сохранённом S3a факте; это отдельный observability gap. Результат не разрешает новую production-миграцию, очистку backup или платные запросы.

**Отдельные статусы:** TECHNICAL PASS (bounded OFFLINE); CI WINDOWS PASS (3/3 jobs); REAL APPLICATION NOT RUN; USER UX NOT APPLICABLE к неизменённому UI H34, будущий физический пользовательский smoke PENDING; RELEASE / LIVE HOLD.

**NEXT:** один проверенный реальный модельный контракт и отдельная инженерная подготовка доверенного server REAL factory/authority на существующих H34/H33/S2/S3a, с полным учётом обязательных predecessor gates; независимые тесты и пользовательский физический TEST/GUI, первый короткий LIVE только по отдельному явному OWNER GO (endpoint/model/attempts/caps/output/timeout/stop/recovery). Не добавлять второй chat core, OAuth cache или ledger. Пользователь самостоятельно принимает GPT→main. Авторский H34 backup не удалён.

Это независимое заключение, не авторская самопроверка.
