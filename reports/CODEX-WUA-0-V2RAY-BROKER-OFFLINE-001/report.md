# CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001

**2026-10-24 — Codex 007. RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_11. LOCAL ONLY.**

Подготовлен исполняемый offline-кандидат выделенного брокера. F2 закреплён в проверяемом контракте: CONNECT listener и upstream socket должен владеть один B-owned engine process. Wrapper → пользовательский SOCKS отвергается. **Реальный F2 пока не закрыт:** подходящая версия V2Ray, её исходники/схема, Windows identity B и WFP enforcement не подтверждены. Нативный конфигурационный синтаксис не выдумывался.

## Фактически реализовано

В `integrations/wua_chatgpt_mcp/` добавлены только семь новых файлов:

- `broker.py`: strict preflight, source/config binding, структурированные synthetic health/owner observations, постоянный отказ активации.
- `broker_fixture.py`: ограниченная синхронная Python-модель; один процесс принимает CONNECT и сам соединяется с собственным loopback receiver. Это не V2Ray.
- `configs/broker.v1.schema.json`: версия 1 контракта, один inbound/один next hop, default DENY, запрет DIRECT/fallback/второго proxy/DNS/UDP/IPv6/companions/health dials/telemetry.
- `configs/broker.v1.synthetic.example.json`: полностью синтетический структурно корректный пример, без реальных SID/адресов/ключей.
- `configs/v2ray.engine.disabled.contract.json`: незаполненный disabled template; намеренно не проходит preflight до привязки integration. `native_config=null`.
- `tests/broker_suite.py`: 33 проверки структуры, модели маршрута, отказов и mutations.
- `tests/broker_regression.py`: адресная регрессия прежнего кода в собственном byte-exact mirror.

Новый модуль вызывает существующий `security_contract.validate`, использует strict parsing/hash/UUID из `common`, CONNECT client/header/receive из `route_simulation`. Старый NPFS, CONNECT→SOCKS adapter, diagnostics и security backend не переписывались. Отдельная короткая проверка путей необходима потому, что прежняя `common.owned_path` закрепляет другие TASK roots; расширять разрешения старого NPFS ради нового отчёта не требовалось. Абстрактного engine loader, service manager или второго base topology validator нет.

## Подтверждённые проверки

|Проверка|Результат|Evidence относительно этой папки|
|---|---|---|
|Финальные broker tests|33/33 PASS, 0 FAIL/ERROR/SKIP|`runs/suite-20261024-131413-2a8f10b2/result.json`|
|Прежний MCP через реальный SDK и synthetic WebAlarmApi|63/63 PASS|`runs/regression-20261024-130416-724b2ebc/result.json`|
|Прежний strict/security suite|24/24 PASS, 0 FAIL/ERROR|тот же regression result|
|DIRECT mutation|реальный прямой GET дошёл до собственного receiver при отказавшем broker; policy observer отметил FAIL|`direct-mutant-*/mutation.json` в финальном suite|
|Owner mutation|удалённый combined PID/SID guard дал ровно 1 ожидаемый inner FAIL, 0 ERROR|`owner-mutant-*/mutation.json` в финальном suite|
|Прежние activation gates|NPFS/toolkit/WFP остаются BLOCKED; static read + прежний pure preflight|`legacy-gates-*/checks.json` в финальном suite|
|Защищённые предыдущие файлы|79/79 byte/hash unchanged|`evidence/protected_inputs_check.json`|

Положительный route-test сопоставляет случайный request UUID, phase/session, receiver receipt и sender PID из `GetExtendedTcpTable`. Этот PID совпал с PID собственного Python worker, который владеет CONNECT listener. Receiver и observer находятся в родительском процессе; worker не получает ключ HMAC receiver. Ключ создаётся в RAM и не сохраняется. Публикуются synthetic nonce и HMAC, но не ключ. HMAC проверен во время прогона; offline-проверяющий может сверить сохранённые correlation/PID/source pins и повторить тест, но не независимо пересчитать прежний HMAC без удалённого ключа.

Отказы проверены для listener/upstream refusal, reset, timeout, partial response/CONNECT, redirect и неверного nonce. Есть настоящий controlled port takeover: новый listener принадлежит PID тест-контроллера; подменённый ответ отвергнут. Проверяются config/source drift, чужие PID/SID/endpoints, replay, stale receipt, observer epoch/session/generation, подмена всего профиля, поддельные approvals и метаданные версии. Повторный запуск той же fixture directory запрещён exclusive claim до bind; новый запуск использует новые UUID/каталог.

Тесты не сводятся к self-reported booleans: DIRECT mutation имеет настоящий локальный сетевой эффект и независимый receiver. Owner mutation проверяет именно структурированный guard, **не настоящий Windows token B**. Обе mutation-копии остаются только в TASK evidence; production candidate не ослаблялся.

## Initial FAIL и исправления

Сохранены все пять попыток suite и source snapshots; точные selectors/tracebacks — `broker_test_results.json`.

1. `suite-20261024-130051-c7a15ba3`: 26 collected, 25 PASS, 1 FAIL. Code defect: CLI под `-I` не находил `common`. Исправлен import root собственного package; первичная ошибка сохранена в `evidence/cli_initial_failure.json`.
2. `suite-20261024-130117-4d2211c1`: 26 collected, 25 PASS, 1 ERROR. Test harness defect: у memory-копии owner mutant отсутствовал `__file__`. Добавлен путь исходника; owner guard/oracle не ослаблены.
3. Следующие 29/29, 32/32 и финальные 33/33 PASS сохранены отдельно. Рост набора связан с findings инженерного review, а не сокрытием initial FAIL.

## Совместимость и граница доказательств

`engine_compatibility.md` фиксирует отсутствие локально подтверждённых V2Ray version/source/schema. В старом разрешённом evidence обнаружен **sing-box.exe за v2rayN**, а не подтверждённый V2Ray core. Исторический hash сам по себе не выбирает engine, не подтверждает его текущий запуск и не доказывает CONNECT capability. Другой движок автоматически не подставлялся; рабочие profiles/subscriptions/credentials не читались.

Python audit hooks и bounded loopback fixtures ограничивают написанный нами тестовый код. Это **не OS sandbox** и не доказательство невозможности внешнего выхода произвольного native process. В настоящей Windows-политике ещё нужны effective token, C-only P, B-only R:Q, запрет дочерних/companion flows, IPv4/IPv6/DNS/UDP, arbitration/loopback, stop on observer loss и pre-existing flows. Реальные retries/redirects/resolution/options выбранного V2Ray не исследованы без его source. Подробнее — `security_boundary.md`, `manual_engineering_review.md`.

```text
BROKER_PROFILE_STRUCTURALLY_VALID — только bound synthetic example
ENGINE_VERSION_SOURCE_BLOCKED
ENGINE_CONFIG_COMPATIBILITY_BLOCKED
B_IDENTITY_NOT_PROVISIONED
B_EGRESS_OWNER_NOT_VERIFIED
V2RAY_LIVE_ROUTE_NOT_VERIFIED
WFP_NATIVE_ENFORCEMENT_NOT_VERIFIED
HOSTED_TUNNEL_ON_HOLD_BY_USER
ORDINARY_CHATGPT_E2E_NOT_VERIFIED
can_apply=false; can_start_tunnel=false
```

## Сохранность, документация и сдача

Нативные V2Ray/tunnel/WFP вызовы: 0; новые accounts/ACL/службы: 0; обращения к OpenAI Platform: 0; Git/GitHub operations: 0. Использованы только собственные временные процессы и собственные loopback ports. Нет host-wide сканирования процессов/соединений: TCP table читалась read-only для поиска конкретного собственного PID/flow, посторонние строки не сохранялись. Это не утверждение о трафике других приложений на компьютере.

Старые NPFS tests с native pipe/ACL не повторялись в этом scope. Их исходники/контракт остались неизменны; текущая regression проверяет MCP и strict profile. Все 54 файла regression mirror скопированы без изменения из исходных мест; старые report roots разрешаются внутрь текущей TASK, прежние evidence не перезаписываются.

DOC IMPACT: общие `01/19/34/37` не изменены. Координатору предлагается отразить новый offline broker candidate с сохранением F2/live/WFP BLOCKED. В общем `18`, DOC-VERIFIER-BLOCK4-01@2 всё ещё описаны полные B2/B3; собственная приоритетная USER GO 2026-10-23 и текущая TASK требуют compact five + append-only 001. Предложение: заменить только описание B2/B3 на «до пяти кратких задач/итогов; полные TASK/AMENDMENT/factual result в персональном 001 до очистки B1»; B4/архив verifier в 06 оставить по действующему контракту. Сам общий документ не правился.

Ротация выполняется отдельным `rotate_card.py`: append-only полный исходный B1 и factual result; readback только добавленного диапазона; затем B2/B3 по пять строк и B1 `ОЖИДАНИЕ НОВОЙ ЗАДАЧИ`. B4 сохраняется побайтно. Точный результат — `evidence/card_rotation.json`; итоговая целостность — `evidence/final_integrity.json`, `manifest.json`. При отказе ротации receipt явно BLOCKED, B1 не очищается.

Фактическая ротация завершилась `CARD ROTATION VERIFIED`: добавлено и сверено 26,551 новых байт; старых байт архива прочитано/переписано 0. B1 освобождён, B2/B3 по пять строк, B4 SHA256 до/после `bc2e8067af2d9a0af34644cf0855b224b66281b0f63fe59f7d932b613331ad1a`. Это административная ротация завершённого offline-этапа, а не независимая приёмка и не разрешение live-запуска.

Независимая приёмка не объявлена. Публикация и передача WEB_11 выполняются пользователем. Следующий безопасный шаг — независимый review текущего offline-комплекта и адресная передача локальных versioned V2Ray source/schema/binary metadata; реальные сетевые действия требуют отдельного USER GO и доказанной лабораторной изоляции (`next_user_go.md`).
