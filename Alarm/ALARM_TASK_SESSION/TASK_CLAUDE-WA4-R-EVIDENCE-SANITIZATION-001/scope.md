# Scope — CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001

🟨 Безопасная анонимизация диагностических отчётов Web Alarm Workspace.

Зафиксировано **до первой записи в репозиторий** (DOC-PARALLEL-01), 2026-10-21. Источник постановки — БЛОК 1 `Документация/000_Задачи Claude.md` (перенесён пользователем из карточки Codex, куда он был ошибочно вставлен; карточку Codex Claude не трогал).

- **ARCH CLASS:** Web Alarm Workspace / тестовые доказательства и безопасность публикации (WA-I12 «корректное evidence»).
- **PRIMARY PROFILE:** 36.2 + 36.1 (`TEST-EVID-01`, `TEST-EVID-ARCHIVE-01`). **SECONDARY:** 23 — только чтение, runtime не меняется.
- **Проверяемый пакет (только чтение):** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001/` (151 файл по его `manifest.json`).

## Запись (только новые файлы)

| Путь | Назначение |
|---|---|
| `web_alarm/evidence_sanitizer.py` | Новый offline-инструмент: `scan` / `stage` / `verify`. Runtime его не импортирует. Размещён в штатной области Web Alarm (36.2 «Файловая область»), как и `transport_event_recovery.py` |
| `test_web_alarm_evidence_sanitizer.py` | Новые тесты в общей базе (подхватываются `wa4a_acceptance.py all`) |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001/**` | Отчёт, manifest, обезличенные сводки инвентаризации и прогонов, служебные скрипты |
| `logs/test-evidence/web_alarm/CLAUDE-WA4-R-EVIDENCE-SANITIZATION-001/**` | Локальный изолированный архив по `TEST-EVID-ARCHIVE-01`: сохранённые оригиналы и очищенные копии. `logs/` исключён в `.gitignore` — **не публикуется** |
| `Документация/000_Задачи Claude.md` | Только штатная ротация БЛОКОВ 1–3 в конце |
| TEMP | Синтетические фикстуры, прогоны runner, зеркала для мутантов |

## Не трогать

Исходный пакет TAIL-RECOVERY и прочие пакеты (только чтение), `wa4a_acceptance.py`, `.github/`, остальной `web_alarm/` (store/server/API/recovery), общие документы, карточки других агентов, живое хранилище (`%LOCALAPPDATA%\WebAlarmWorkspace`), сеть, firewall/MCP, Git/GitHub (DOC-GIT-01), PR №17. Публикация очищенных материалов и любые необратимые действия — только по отдельному USER GO.

## Тесты

Только guarded runner `wa4a_acceptance.py` через `.venv` (Python 3.12.10), выход в одноразовый TEMP, обёртки из `tools/` этой TASK. Значения — только синтетические.
