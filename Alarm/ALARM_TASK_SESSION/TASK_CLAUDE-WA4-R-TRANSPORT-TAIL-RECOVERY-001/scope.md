# Scope — CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001

🟨 Задача: безопасное ручное восстановление повреждённого транспортного журнала после аварии (`AUD-01T-R`). Внутренний код finding: Audit 01, Transport events, Residual recovery gap. Файл записан **до первой правки production-кода**.

## Gate A — source / baseline

- `tools/source_gate.py` → `source-gate.json`: **PASS**. 105/105 файлов совпадают с `source-final.json` опубликованного ремонта `CLAUDE-WA4-R-CRASH-CONSISTENCY-REPAIR-001` — он прошёл независимый W1 Windows CI 874/OK по 34. Drift/missing/unexpected — пусто.
- Ориентир координатора `main@8ab1c7d6c03c829ed6bd82290a700c0048fd24ab`; Git не использовался (DOC-GIT-01).
- Точные байты файлов, которые может затронуть TASK (`transport_event_store.py`, `store_lock.py`, `test_web_alarm_transport_event_store.py`), — в `baseline/`.
- **EOL-событие (вне scope, сообщается по Gate E):** персональная карточка `000_Задачи Claude.md` в рабочей копии целиком перешла с LF на CRLF (10024 из 10025 строк). Содержимое после нормализации CRLF→LF с подставленным слотом ожидания в БЛОКЕ 1 совпадает побайтно с итогом моей прошлой ротации (`01c20408…`) — история не повреждена. Изменились только БЛОК 1 и концы строк (вероятно, Git autocrlf при Fetch/Pull). Ротация сохранит действующий CRLF.
- Платформенные факты (`probes/probe_windows_primitives.py`, TEMP, синтетика):
  - `fstat`/`lstat` identity совпадает;
  - `os.replace` поверх файла, открытого читателем, → `PermissionError` (WinError 5), оригинал цел;
  - `os.replace` поверх read-only → `PermissionError`;
  - `O_EXCL` работает;
  - junction создаётся без прав администратора и обнаруживается по reparse-атрибуту; `Path.resolve()` идёт сквозь него;
  - symlink требует привилегию (WinError 1314) → symlink-тесты SKIP;
  - fsync каталога невозможен → **без заявлений о power-loss durability (PWR-01)**.

## Контракт восстановления (до реализации)

Новый модуль `web_alarm/transport_event_recovery.py`. Это offline-инструмент оператора: без live API, без автозапуска, не вызывается из server/store. Запуск — только `python -m web_alarm.transport_event_recovery`, **storage root задаётся явно** (умолчания нет).

1. **`inspect` (dry-run, без единой записи, без lock, без mkdir).**
   - Классификация:
     - `NO_LOG`, `HEALTHY` (в т. ч. пустой) → NOOP;
     - `TORN_TAIL` → план;
     - `CORRUPT_MIDDLE`, `AMBIGUOUS`, `BAD_TARGET` → REFUSE.
   - Префикс — до последнего LF. Каждая полная строка проверяется **тем же правилом, что `TransportEventStore.read_events()`**.
   - Хвост — непустые байты после последнего LF, без LF. Подтипы: `JSON_TRUNCATED`, `COMPLETE_JSON_WITHOUT_LF` (включая `…}\r`), `INVALID_UTF8`, `BLANK`. Ни один хвост **не дописывается и не восстанавливается как событие**: доставка неизвестна.
   - `AMBIGUOUS`:
     - NUL-байты в хвосте — не похоже на гибель процесса посреди одного `write` (power loss / сбой носителя);
     - конфликт `event_id` в префиксе (один id, разная identity).
   - Любая повреждённая полная строка → `CORRUPT_MIDDLE` (tail-salvage никогда не применяется).
   - Выдача: только размеры, SHA-256, offset, число строк, подтипы, риск. Ни содержимого событий, ни payload.
   - `plan_fingerprint` = SHA-256 канонического плана: канонический root, относительный путь, размер/SHA источника, offset/rows/SHA префикса, размер/SHA/подтип хвоста, версия формата плана.
2. **`apply --plan-fingerprint <fp> --reason <текст>`** (без `--force`). Последовательность:
   1. проверка цели;
   2. `InterProcessLock` транспортного writer (тот же путь, timeout → STOP);
   3. повторный inspect **под lock** и сверка fingerprint (stale/foreign → STOP);
   4. архив — новый каталог попытки `transport_recovery/<fp16>/<attempt>/`:
      - `original.bin` (полные исходные байты), `tail.bin` (точный хвост), `plan.json` (намерение);
      - всё — эксклюзивное создание, fsync, повторное чтение и сверка SHA, затем атрибут read-only; архив никогда не правится и не перезаписывается;
   5. временный файл префикса в каталоге `transport/` (эксклюзивно, fsync, сверка), проверка **настоящим `TransportEventStore.read_events()`** на этом файле;
   6. повторная проверка идентичности/байтов источника непосредственно перед заменой;
   7. `os.replace` (атомарно; читатель видит либо старый fail-closed файл, либо валидный префикс);
   8. сверка результата (байты = префикс, `read_events()` = те же `event_id` по порядку);
   9. `receipt.json` в каталоге попытки — отдельно от transport events; если не записан, это сообщается.
3. **Повтор/восстановление самого восстановления.**
   - Каждая попытка — новый каталог; оборванные попытки остаются как forensic-след.
   - Если журнал уже равен префиксу плана и для плана есть проверенный архив оригинала → `ALREADY_APPLIED` без мутации журнала.
   - Иначе — fingerprint не совпадает → STOP.
4. **Цель.**
   - Корень должен быть каноническим: абсолютный путь = `resolve(strict=True)`, нет junction/symlink/alias в цепочке.
   - `transport/`, файл журнала, `locks/…`, `transport_recovery/…` — не reparse-точки.
   - Идентичность файла (st_ino/st_dev) сверяется до и после чтения и перед заменой.
   - Не тот корень (нет `transport/`) → REFUSE.

Lock order: только транспортный lock (лист); другие локи не берутся. Пока он удерживается, writers ждут; lock-free читатели безопасны (см. факт о `os.replace`).

## Write-scope

- **Production:** новый `web_alarm/transport_event_recovery.py`. `transport_event_store.py` и `store_lock.py` менять **не планируется**: их константы путей и `read_events()` используются как есть, поэтому поведение на здоровом журнале не меняется побайтно. Server/API/models/runner/CI — не трогаются.
- **Тесты:** новый `test_web_alarm_transport_event_recovery.py`; `test_web_alarm_transport_event_store.py` — только при необходимости.
- **Evidence:** только эта папка; синтетика в TEMP. Живое хранилище, сеть, Git — запрещены.
- **Карточка:** только ротация собственных БЛОКОВ 1–3 (с сохранением CRLF).

## Не входит

AUD-02c, AUD-04, PWR-01 (power loss / fsync каталога), W3, WARN/STRICT/gateway, MCP/WUA/WEB_10, server API для восстановления, autoheal.
