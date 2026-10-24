# Воспроизведение offline broker candidate

Windows x64, существующая `M:/GitHub/ag_llm/.venv/Scripts/python.exe`: Python 3.12.10, jsonschema 4.26.0. MCP regression использует уже установленные MCP/httpx/pydantic; версии сохранены в `evidence/runtime_dependencies.json`. Ничего не скачивать/устанавливать. Отсутствующая зависимость → BLOCKED. Изолированный base Python312 здесь не имеет jsonschema; для прогона использована существующая `.venv`.

Из корня `M:/GitHub/ag_llm`, при разрешении на собственные loopback fixtures:

```powershell
& './.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/broker_suite.py
& './.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/broker_regression.py
```

Оба runner создают **новые** `runs/suite-<time>-<UUID>` / `runs/regression-<time>-<UUID>` в этой TASK. Старые evidence не переписываются. Normal suite exit 0 означает успех offline-проверок. Ожидаемый inner mutation FAIL записывается отдельно, внешний тест PASS подтверждает его обнаружение. При сбое сохранить новую попытку, не заменять её предыдущей зелёной.

Для адресного повторения существует `--select`, например:

```powershell
& './.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/broker_suite.py --select RouteTests.test_direct_mutation_oracle
```

Сопоставить `source_pins.json` с актуальными файлами до интерпретации результата. `broker_test_results.json` закрепляет фактический финальный прогон и точные selectors, а не автоматически выбирает «последнюю зелёную» попытку.

`broker.py --contract <path> --pin <canonical-sha256> --source-pin <source-pin> --output <new-TASK-path>` сохраняет preflight и **всегда возвращает exit 20**. Для вычисления pin применять существующие `common.parse/digest`; source pin — `broker.source_pin()`. Пример вызова с расчётом pins уже исполняется `ContractTests.test_cli_always_exit20_and_output_scope`. Output должен быть новым файлом внутри этой TASK, input — внутри неё или package/configs. Нет команды activate/install/start.

`configs/v2ray.engine.disabled.contract.json` — **контракт требований, не конфигурация V2Ray**. Незаданные данные не заполняются параметрами текущего компьютера. Синтетический пример имеет фиктивные SID, reserved documentation address и placeholder image hashes; его нельзя использовать как discovery/production settings.

`prepare_report.py`, `seal.py` предназначены для закреплённого прогона этой сдачи, не заменяют тесты. `rotate_card.py` — single-use с pinned исходными card/archive metadata; повторять его нельзя. Отката архива усечением/перезаписью не предусмотрено: он append-only; при проблеме ротации сохраняются entry/evidence и B1 для координации.
