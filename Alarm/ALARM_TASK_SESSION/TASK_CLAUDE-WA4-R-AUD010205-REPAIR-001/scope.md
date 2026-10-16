# Scope — CLAUDE-WA4-R-AUD010205-REPAIR-001

Ограниченный ремонт AUD-01, AUD-02 и AUD-05 из `CLAUDE-WA4-R-R006-INDEPENDENT-AUDIT-001`. Зафиксировано **до первой правки исходников** (2026-10-16).

## Baseline gate (пройден до правок)

- Все 102 pinned-исходника R-006 (`checks.json` / `versions.json` → `final_full_source_sha256`) совпадают с локальными байтами. Расхождений только в EOL нет, отсутствующих файлов нет.
- В `web_alarm/*.py` и `test_web_alarm*.py` нет файлов вне pinned-карты.
- Контрольный пакет R-006: 64/64 файла манифеста совпадают; `manifest.json` = `b14c366452547de2d4a102a5c50b4c7da0ad01dc539e7ded629f1a3fee46f84e`.
- Целевые файлы не менялись с момента аудита (их SHA равны pin R-006 и снимку аудита).
- Git не использовался, рабочие файлы сверены по байтам.

## Разрешённые изменения (write-scope)

| Файл | SHA-256 до ремонта | Назначение |
|---|---|---|
| `web_alarm/event_checkpoint_store.py` | `7d094e81b5a40dbced420af9a51c04b6e5b7b4eb4050d96bca0ba01495274aad` | AUD-01: разбор строк только по физическому LF (с совместимостью CRLF) и экранирование U+0085/U+2028/U+2029 при записи |
| `web_alarm/operation_store.py` | `bb7eaf40dd2280fcd5a38d33fe85d2d97ff19733740719d15fa02cf4e6854360` | AUD-02: в `begin()` проверять читаемость истории под уже удерживаемыми lock до первой durable-записи |
| `web_alarm/projection.py` | `1d788d2153621fb0aba9ed19ac2dbb3b74758bb78e3a4548c08dab295bf09af0` | AUD-05: блокер `HISTORY_UNREADABLE` (в gate closeout — `PROJECTION_HISTORY_UNREADABLE`) |
| `test_web_alarm_aud010205_repair.py` | новый | адресные regression-тесты |
| `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-AUD010205-REPAIR-001/**` | новый | отчёт, evidence, manifest, scope, baseline, проверочные скрипты |
| `Документация/000_Задачи Claude.md` | — | только ротация БЛОКОВ 1–3 после результата |

Точные байты до ремонта — в `baseline/web_alarm/` (SHA выше). Откат: скопировать эти три файла обратно и удалить `test_web_alarm_aud010205_repair.py`.

## Вне scope (не изменяется)

- `web_alarm/closeout.py`, `mutation_executor.py`, `server.py`, `task_store.py`, `manifest_store.py` и прочие модули `web_alarm`.
- `web_alarm/transport_event_store.py`: найден аналогичный дефект framing (плюс отсутствие проверки оборванного хвоста). Это отдельный модуль и глобальное хранилище transport-evidence, поэтому его ремонт — **STOP / требуется отдельное согласование**. Дефект воспроизводится как FINDING без правки кода.
- AUD-03 (окно crash между INTENT и событием) и AUD-04 (lock до валидации в ManifestSnapshotStore/CLI) — вне ремонта, по постановке.
- `wa4a_acceptance.py`, CI/workflows, общие runner'ы, документы 23/24/25/36.2 и другие общие документы.
- Рабочая область Codex (`reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/`, MCP-плагин, `C:\Users\REX\.codex\config.toml`) — не читается и не меняется.
- Production storage и live Workspace — тесты только на disposable TEMP.

## Пересечение с Codex 007

БЛОК 1 Codex (`CODEX-WUA-0-DESKTOP-MCP-E2E-001`) прямо запрещает ему изменять `web_alarm/*.py` и материалы WA4-R; существующий runtime Web Alarm для него только для чтения. Пересечения по записи нет.

Остаётся риск чтения: если Codex перечитает `web_alarm/` во время ремонта, он увидит исправленную версию. Каждая правка файла выполняется одной атомарной записью.
