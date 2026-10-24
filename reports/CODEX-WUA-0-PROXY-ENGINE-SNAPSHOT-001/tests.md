# Проверки и воспроизведение

Из `M:/GitHub/ag_llm` с существующей `.venv` (Python3.12.10/jsonschema4.26.0):

```powershell
& './.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/engine_snapshot_suite.py
```

Не устанавливать зависимости. Runner использует сохранённый очищенный snapshot в этой TASK и inert PE byte fixtures; настоящий core не читает/не запускает, сеть и children запрещает audit hook. Новый каталог каждой попытки; прежние results не переписываются.

Финал: `runs/suite-20261024-175139-adb7977b/result.json`, **44/44 PASS, 0 FAIL/ERROR/SKIP** = **25 новых metadata tests + 19 прежних pure broker contracts**. Полные IDs/tracebacks/source pins/runner output сохранены. Initial `suite-20261024-174910-d3b101ce` тоже 44/44 PASS и оставлен как исходный результат.

|Новый слой|Независимый negative oracle|
|---|---|
|PE/Go static parser|Фиксированные inert bytes/ручные ожидаемые значения против corruption, truncation, impossible bounds, ambiguity, duplicate-module exact reason|
|Pin/release/version/schema|Изменение hash/claim после controller pin → точный отказ; неизвестная version и fake source/schema approval отдельно отвергаются|
|Capabilities/owner/signature|Положительные claims не меняют BLOCKED; требуют конкретного rejection reason|
|Contract/selection|Существующий validator отвергает source/schema/endpoint/direct/fallback/default/second-proxy mismatch; sing-box family не подменяется на V2Ray|
|Mutation контроля pin|Ровно один удалённый inventory-pin guard в копии кода; inner oracle FAIL1/ERROR0|
|Mutation capabilities|Ровно один удалённый untrusted-capability guard в копии; inner oracle FAIL1/ERROR0|

Mutation results лежат в `mutant-INVENTORY_PIN_MISMATCH/` и `mutant-UNTRUSTED_CAPABILITY_CLAIM/` финального run. Outer PASS означает обнаружение ожидаемого inner FAIL. Даже mutant не включает настоящий runtime: постоянные activation gates остаются false. Это проверка чувствительности metadata validation, не Windows/security penetration test.

При manual review исправлен тестовый coverage gap: duplicate-module replacement первоначально уменьшал длину file fixture и мог давать PE bounds отказ. Финальный тест сохраняет 5120 bytes и требует GO_DUPLICATE_MODULE. Старый PASS не скрыт и не выдаётся за первоначальное доказательство этой ветви. Неожиданных initial FAIL в этой TASK нет.

Pure regression импортирует прежний test module без изменения его source; только runtime OUT переназначен в текущую TASK. Исключены два старых теста с subprocess/loopback (`test_cli_always_exit20_and_output_scope`, `test_remote_schema_reference_is_refused_without_dial`), route suite и настоящие SDK/NPFS tests **NOT RUN**. Прежние результаты 33/63/24 из B4 не добавляются к нынешним 44.

Source snapshots до каждого run и `source_pins.json` позволяют воспроизвести именно эту ревизию. Правки source после run делают evidence stale; `prepare_report.py`/`seal.py` проверяют соответствие. Больших/ненужных network regressions не выполнялось, так как изменены только metadata parser/gate.
