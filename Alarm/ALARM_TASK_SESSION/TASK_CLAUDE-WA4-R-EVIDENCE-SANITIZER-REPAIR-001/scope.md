# Scope — CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001

🟨 Исправление fail-open ошибок механизма безопасной публикации диагностических отчётов (F-ES-01, F-ES-02).

Источник — БЛОК 1 `Документация/000_Задачи Claude.md` (2026-10-23). Постановка в карточке обрывается в §11 («RED → GREEN и»); форма сдачи взята из правила карточки о копируемом блоке `text`.

- **ARCH CLASS:** SECURITY / EVIDENCE INTEGRITY / FAIL-CLOSED REPAIR. **Профиль тестов:** 36.2 (+ 36.1).
- **Source baseline (сообщение координатора):** `main@8a6345886aa8ed2f21d143d8c261d01ede2ec675`. Git не использовался; локальный `web_alarm/evidence_sanitizer.py` до правки — SHA-256 `1b4fb52e1e2736ac3c7ccd97c534a3acc1aba3ea5b2fe2481ea42f23e8cc4201` (совпадает с финальной ревизией прошлой TASK; приватная копия для RED — только в TEMP); `test_web_alarm_evidence_sanitizer.py` до правки — `215d0fb2c62bb68ae2a097f6524061cdbfa5d7646a4d3417696315bf1045cebf`.

## Запись

| Путь | Что |
|---|---|
| `web_alarm/evidence_sanitizer.py` | исправление |
| `test_web_alarm_evidence_sanitizer.py` | постоянные регрессии (тот же модуль) |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001/**` | отчёт, manifest, очищенные evidence, служебные скрипты |
| `Документация/000_Задачи Claude.md` | только свои БЛОКИ 1–3 (БЛОК 4 — нет) |
| `Документация/001_История выполненных задач Claude.md` | только дописать новую собственную запись + точечный readback |
| TEMP | синтетические фикстуры, прогоны runner, зеркала мутантов, приватные сырые копии выходов прогонов, подготовка реального пакета для проверки совместимости |

`logs/` в этот scope не входит: приватные сырые копии — только в TEMP.

## Только чтение

Правила/БЛОК 1/БЛОК 4 карточки; 08, 34, 01 (релевантные разделы); 18 — `DOC-GIT-01`, `DOC-TASK-READ-SCOPE-01`, `DOC-TASK-BLOCK1-01`, `DOC-LOCAL-REPORT-HANDOFF-01`, `DOC-VERIFIER-BLOCK4-01@2`, `DOC-PARALLEL-01` (`DOC-HISTORY-ACCESS-01@1` в 18 не найден — FINDING); 36/36.1/36.2; пакет `TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001` и собственная прошлая папка отчёта — для проверки совместимости на реальных данных. Архивы `001` Claude/Codex не открываются (кроме дописывания и readback своей записи в конце).

## Запрещено

БЛОК 4, чужие карточки и архивы, общая документация, CI workflows, transport recovery, Web Alarm Ultra, MCP/V2Ray, runtime-сервисы, живые данные, Git/GitHub (включая чтение), публикация.
