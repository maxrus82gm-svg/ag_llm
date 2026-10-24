# Архитектура и текущее состояние GigaChat Ultra Local Agent



### Ultra RT-002/B2 S2 policy module — 2026-10-14 CURRENT

`ultra_budget_policy.py` и `test_rt002_s2_budget_policy.py` существуют как **pure/offline policy contract, НЕ подключённый к production runtime, платным запросам или UI**. После S2-001 + REPAIR-001/002 ChatGPT независимо просмотрел исходники main@76335ffb83373b6af0dff9f5c0081d250b7d835a (user commit №324) и подтвердил закрытие terminal-event, type-validation, malformed-scope и exact-integer-ceiling находок. **S2 BOUNDED INDEPENDENT SOURCE-REVIEW ACCEPTED WITH EXECUTION LIMIT**; Claude-reported offline: S2 core 73/73 PASS, provenance 74/74 PASS (342 embedded=local), S1 69/69 PASS, S0 166/166 PASS; all 13 mutation controls expected exit 1. ChatGPT did NOT independently execute S2/S1/S0 on this new SHA; no Ultra CI runs at exact SHA. Числовые default limits, reserve, MCP/compressor, precached и правила scope quarantine требуют **USER DECISION**. S3a durable ledger, S3b pre-HTTP guard, S3c pre-mutation reserve, S5 UI ещё НЕ реализованы. Это не live protection и не S13a pass. Каноника 20 §5а, факты 21, тесты 36.3; отчёт `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S2-REPAIR-002/repair_report.md`.



## ultra_ui.py

Основной пользовательский интерфейс.

Текущий UI реализован на:

```text
Tkinter
```

UI включает:

```text
trace / log
CHAT
message input
Workspace sidebar
Chat sidebar
MAIN CHAT model selector
VERIFIER MODEL selector
Compressor panel
Project Context editor
Role Context editors
message context actions
Compression Proposal UI
Original Viewer
```

---

