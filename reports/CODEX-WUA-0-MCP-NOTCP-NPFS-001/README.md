# Локальный STDIO ↔ NPFS кандидат

TASK `CODEX-WUA-0-MCP-NOTCP-NPFS-001`. Только current-user synthetic fixture. Это не установка, production gateway или разрешение на tunnel.

Из корня `M:\GitHub\ag_llm` с уже установленным окружением:

```powershell
./.venv/Scripts/python.exe -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/run_npfs.py
./.venv/Scripts/python.exe -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/npfs_regression.py
```

Первый runner собирает `Shared.cs + Relay.cs` и `Shared.cs + Gateway.cs` существующим `Framework64/v4.0.30319/csc.exe`. Сборка x64/C#5, `/noconfig /nostdlib+ /warnaserror+`; четыре явно указанные локальные Framework references. Никаких restore/download/установок. Полные команды находятся в `runs/<attempt>/build.json`. Второй runner исполняет существующие SDK/security selectors без записи в историческую TASK.

Каждый запуск создаёт новый `runs/attempt-...` либо `runs/regression-...`; прежние результаты сохраняются. `--select NpfsTests.test_...` допускает адресную диагностику и не заменяет полный suite. Полный набор занимает около полутора минут на проверенной машине. Прерывать можно только процессы собственного запуска; runner и Windows Job Object завершают owned children. Жёсткий watchdog новых executable — 40 секунд, bridge — 30 секунд, frame deadline — 2.5 секунды; fixture создаётся заново для каждого случая.

Сборки находятся в `build/`, исходники — в `integrations/wua_chatgpt_mcp/npfs/`. Gateway намеренно рассчитывает checkout root относительно `reports/<TASK>/build/`, допускает только эту TASK/runs и фиксированные `.venv/Scripts/python.exe` / `npfs/gateway_worker.py`. Копирование gateway в произвольный каталог не является поддерживаемой установкой. Relay не запускает Python; его Unicode path проверяется отдельно.

Все grant keys генерируются runner в памяти и передаются только своим процессам через одноразовое окружение. Они не сохраняются в JSON, argv, отчётах или stdout. `fixture.json`, `gateway.json`, synthetic API state, nonce и receipts не являются настоящими credentials. Не использовать этот способ доставки grant для hostile same-user production: защищённый launcher/credential delivery остаётся gate.

Требования: Windows x64, существующий .NET Framework compiler, Python/MCP из данного проекта и возможность создать собственный local NPFS fixture/job. На другой платформе или при отказе этих API — остановка; нет автоустановки или ослабления policy. Ничего не менять в Windows accounts/WFP/V2Ray/сети для прохождения suite.

`report.md`, `tests.md`, `pipe_security.md`, `topology.md`, `manual_engineering_review.md`, `next_user_go.md`, `checks.json` и `manifest.json` образуют handoff. Независимая проверка WEB_11 ещё требуется; GitHub-публикация исполнителем не выполнена.
