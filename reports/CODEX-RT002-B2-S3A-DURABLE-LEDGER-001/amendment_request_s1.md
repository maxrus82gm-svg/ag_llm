# Запрос отдельного AMENDMENT — текущая TASK не расширялась

Связь: `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`, S1 prerequisite для S3b.

Guarded S1 selector реально выполнил 69 методов: 67 PASS, 2 FAIL, 0 ERROR/SKIP,
0 isolation violations. Шесть pinned архивных fixtures были доступны; ошибка
не связана с отсутствием RAW. В пакет не копировались архивные тексты запросов,
только результаты/метрики и сообщения source inventory tests.

1. `test_production_send_sites_match_inventory_with_multiplicity`: сверх прежнего
   набора найдены UNKNOWN `launcher.py:<import>:import:urllib.request:29`,
   `launcher.py:_get:urlopen:248`,
   `ordinary_chat_service.py:execute_request:getattr.send:308`.
2. `test_every_endpoint_constant_read_is_an_inventoried_send_url`: endpoint host
   literals `model_cards.py:128:18` и `129:16` не классифицированы прежним oracle.

Evidence: `evidence/s1_result.json`, `s1_unittest.txt`, `s1.stdout.txt`.
Это существующие source paths; новая S3a библиотека не добавляет network sites
и не импортируется production runtime.

Запрашиваемый следующий scope (не исполнялся): READ ONLY разбор `launcher.py`,
`ordinary_chat_service.py`, `model_cards.py` и подтверждённых callers; WRITE
`test_rt002_s1_routes.py` и собственный evidence package для обоснованного
обновления inventory/oracles. Нельзя просто пометить UNKNOWN как безопасный;
нужны source/wire/fake/negative proofs и полный guarded selector.

Если разбор требует нового route/роли/scope, изменения `ultra_budget_policy.py`
или общего production runtime, остановить это расширение и получить ещё одно
точное USER GO. Числовые лимиты, физические вызовы и paid mode не разрешаются
ремонтом инвентаризации. Эта запись не назначает новую TASK и не исправляет S1.
