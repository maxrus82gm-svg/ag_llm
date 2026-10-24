# Manual engineering review — Codex 007

2026-10-24. Самостоятельный review, не независимый verdict WEB_11.

Просмотрены новые `engine_snapshot.py`, `tests/engine_snapshot_suite.py`, collector/report helpers, изменённые inert fixture branches; прежние `broker.py`, schema, common/security validator и применимые gates. Проведён разбор normal/error paths отдельно от результатов suite.

|Assumption / попытка опровержения|Результат|
|---|---|
|v2rayN означает V2Ray Core|Опровергнуто current child basename + Go module claim; нет автоматического family switch|
|Совпавший historical hash удостоверяет релиз|Опровергнуто: это две локальные read observations, не official release digest|
|Go version/VCS modified=false удостоверяют исходники|Опровергнуто: embedded strings self-reported; соответствующие source/provenance отсутствуют|
|FileVersion/Authenticode можно получить без сети|Version resource local-only API дал null; embedded certificate table отсутствует. Trust/revocation APIs не вызываются, catalog trust не заявлен|
|Parser может выполнить core или прочитать profile|Только bounded bytes/PE/resource APIs, нет loader/process launch/config access. Exact caller-approved path; никакого discovery scan|
|Malformed PE/Go приводит к недопустимым reads|Bounds before struct offsets, max128MiB binary /64KiB Go strings /1MiB version resource; limited section count, varint overflow, recognized inline format only; corruption tests дают отказ|
|PE parser удостоверяет фактическое поведение кода|Нет: это metadata parser, не Windows loader, disassembler или signature validator. Forged metadata возможны даже в корректном PE|
|Метаданные со знакомыми fields можно принять как trust|Exact shape, independently expected inventory hash и постоянные provenance/capability/owner gates. Fake booleans/signature/positive capabilities отвергаются|
|Снятый guard останется незамеченным|Две source mutations в inert copies дают exact expected inner FAIL; unchanged candidate не ослаблен|
|Все отрицательные PE тесты проверяют нужную ветку|Найден coverage gap duplicate-module: изменение длины могло отказать раньше. Исправлен same-length fixture + точный GO_DUPLICATE_MODULE, затем полный proportional rerun44/44|
|Compiled tags доказывают CONNECT/no DNS/no companions|Нет. Их множество задаёт вопросы к source audit, а не поведение current config. Working config не читается|
|Одобрение sing-box можно выдать за совместимость старого contract|Нет. Actual module sing-box против V2Ray selection → family mismatch; hypothetical sing-box selection против старого schema → contract mismatch. Никакой schema translation|
|После static inventory можно безопасно запустить тот же hash|Нет. Возможны TOCTOU/in-place same-user substitution, replacement runtime/config/dependencies, stale process PID/image. Before/after fstat полезен для snapshot, не protected installation proof|
|Прочитанный path соответствует loaded bytes|Только bounded metadata association; память не читается, loaded image byte identity NOT VERIFIED|
|Свойства можно переносить на другой PC|Нет. Реальные C/B SID, ports, upstream, credentials, ownership и WFP должны определяться заново и проверяться; сюда перенесены только безопасные static claims|
|Новый parser требует второго broker stack|Нет. Старый preflight/security validator переиспользован; added two files, operational broker/NPFS/WFP untouched|

**Открытые блокеры:** matching authentic release/source/schema; semantics inbound/outbound/default/error/config loader; protected encrypted upstream/credentials; effective B token+same process socket; native OS policy/isolation. Ни один не снимается Python metadata tests. Core запускать, менять Windows/network или выбирать engine автоматически нельзя.

**Вывод:** exact local file идентифицирован и версия описана как embedded claim. Source/schema/native CONNECT остаются BLOCKED/UNVERIFIED; рекомендован source-only review имеющегося sing-box перед operational decision. Нужный bundle и варианты решения указаны в `next_user_decision.md`.
