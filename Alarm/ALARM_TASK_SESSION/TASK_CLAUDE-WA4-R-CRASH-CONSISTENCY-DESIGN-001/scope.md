# Scope — CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001

Исследовательская и проектная TASK (AUD-02b-R + AUD-03). **Production-код, тесты, runner, CI и общая документация не меняются.**

## Source gate (до работы)

- `tools/source_gate.py` → `source-gate.json`: **PASS**. 104/104 файла `web_alarm/*.py`, `test_web_alarm*.py`, `wa4a_acceptance.py` совпадают с итогом `CLAUDE-WA4-R-AUD01T02B-REPAIR-001`. Ожидаемая карта = его `baseline-gate.json` + шесть итоговых SHA из его `gate-e.json` (`8bb8eac3…`). Лишних, отсутствующих и изменённых нет.
- Ориентир постановки: `main@7987487…`, предыдущая публикация №354 `3fd942b…`. Git не использовался: сверка только по байтам с опубликованным комплектом прошлой TASK. Совпадение подтверждено и тем, что 34/23/36.2 указывают те же шесть файлов по №354.
- Повтор gate в конце работы: PASS — ни один исходник не изменился.

## Write-scope

Только `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-CRASH-CONSISTENCY-DESIGN-001/**` и ротация БЛОКОВ 1–3 своей карточки `Документация/000_Задачи Claude.md`.

| Путь | Назначение |
|---|---|
| `report.md` | полный отчёт: карта окон, пробы, варианты, рекомендация, adversarial review |
| `scope.md`, `manifest.json`, `evidence.json`, `source-gate.json` | границы, инвентарь, сводка прогонов, сверка исходников |
| `probes/` | `crash_worker.py`, `reopen_inspector.py`, `test_crash_windows.py`, `test_schema_compat.py` — только TEMP-фикстуры |
| `runs/<label>/results.json`, `summary.json` | сырые результаты runner'а с заменой машинных путей на `<TEMP>`/`<REPO>`/`<USER>`; исходные SHA — в `evidence.json` |
| `tools/` | gate, batch-обёртка над guarded runner, сбор evidence, очистка путей, manifest |

## Не изменялось

- `web_alarm/*.py`, корневые `test_web_alarm_*.py`, `wa4a_acceptance.py`, CI/workflows, schema и миграции.
- Общие документы 08/18/23/24/25/34/36.x/05/06 и др.
- Рабочая область Codex 007, MCP, сеть, V2Ray/Secure Tunnel, live Workspace, production storage, credentials.
- Пробы патчат production-методы **только внутри дочерних TEMP-процессов** (`mock.patch` в `crash_worker.py`); файлы на диске не меняются.
- Запуск — только guarded runner `wa4a_acceptance.py` через копию обёртки `run_gate.py` (`LOCALAPPDATA`/`APPDATA`/pycache → TEMP).
- WARN / GATEWAY REQUIRED / STRICT / Final Audit не включались.
