### CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 — 🟨 Безопасное ручное восстановление повреждённого транспортного журнала после аварии (AUD-01T-R) — результат

**TASK:** CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001 (БЛОК 1, USER APPROVED; координатор/verifier — ChatGPT LLM12). Запуск — сообщение пользователя 2026-10-20. Исполнитель — агент 008 (Claude). AMENDMENT не было.

- **Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. LOCAL ONLY. WA4-R PARTIAL; WARN/GATEWAY/STRICT/Final Audit, live storage, W3, сеть, Git — не затрагивались.
- **Причина:** гибель процесса внутри `TransportEventStore.append` оставляет последний JSONL-фрагмент без LF. Чтение и запись после этого намеренно отказывают (fail-closed), а штатного безопасного восстановления не было.
- **Сделано:** новый offline-инструмент оператора `web_alarm/transport_event_recovery.py` (`python -m web_alarm.transport_event_recovery`).
  - `inspect` — dry-run без единой записи и без lock. Вердикты: NO_LOG/HEALTHY → NOOP; TORN_TAIL → план с размерами/SHA/offset/`plan_fingerprint`; CORRUPT_MIDDLE/AMBIGUOUS/BAD_TARGET → REFUSE.
  - `apply --plan-fingerprint --reason` (без `--force`):
    - все отказы — до любой записи;
    - под transport writer lock: свежая сверка плана;
    - архив `original.bin`/`tail.bin`/`plan.json` (эксклюзивно, fsync, чтение и сверка SHA, read-only);
    - temp-префикс проверяется настоящим `read_events()`;
    - повторная сверка источника, атомарный `os.replace`, пост-проверка (при сбое — возврат оригинала);
    - квитанция вне журнала.
  - Повтор — ALREADY_APPLIED без записей.
  - Оборванное событие не восстанавливается: доставка неизвестна.
- **Файлы:** 2 новых — `web_alarm/transport_event_recovery.py` (546 строк), `test_web_alarm_transport_event_recovery.py` (866 строк, 35 методов). Изменённых — 0; `transport_event_store.py`, `store_lock.py`, server, runner не тронуты. Итоговая карта 105 + 2, drift 0.
- **Проверки:**
  - Gate A (зеркало исходного кода): control PASS, trigger FAIL, новый модуль — ImportError; red-final 14 = 12 PASS / 1 FAIL / 1 ERROR.
  - Gate B/C: 35 методов — 34 PASS / 1 SKIP (symlink: нет привилегии, WinError 1314). Покрыто: реальная гибель потомка на 8 фазах; 20 раундов tear/repair при живом читателе (7 реальных WinError 5, ни одного полусостояния); межпроцессный writer, lock timeout, двойное подтверждение; junction/path-swap/hard link; дифференциальный fuzz (400 случаев) против `read_events()`.
  - Мутанты 8/8 убиты; M8 (truncate вместо replace) — только тестами seam, честно.
  - Gate D: focused ×3 (8 модулей, 119 тестов) — r1/r2 0 FAIL; r3 — 1 FAIL + 1 isolation violation в **существующем** тесте `test_web_alarm_aud01t02b_repair…test_concurrent_processes_lose_no_transport_event`. Причина — ложное срабатывание guard runner (`Path.resolve()` даёт `\\?\C:\…\Temp` при гонке mkdir); код не связан с TASK. Воспроизведено на **исходном** коде 2/10 (та же сигнатура), текущий 0/10.
  - **Полный набор: 909 = 907 PASS / 0 FAIL / 0 ERROR / 2 SKIP, isolation 0.** Против прежних 874: удалено 0, смен статуса 0, добавлено 35.
  - Gate E: diff, SHA, байтовый скан, синтетический forensic sample (архив = оригинал, хвост = потерянные байты, журнал = префикс, повтор ALREADY_APPLIED).
- **Findings:**
  - F-T1: flaky guard `\\?\` (runner вне scope);
  - F-T2: читатель во время замены может получить fail-closed «cannot read» — процедуру выполнять при остановленном Web Alarm;
  - F-T3: инструмент держит журнал в памяти целиком.
- **Остаток:** PWR-01 (power loss, fsync каталога); TOCTOU намеренной подмены пути; symlink-тесты NOT RUN.
- **NOT RUN:** живое хранилище/W3, symlink, power loss, CI (организует ChatGPT), Linux/macOS.
- **Отчёт:** `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001/report.md`; рядом `manifest.json`, `evidence.json`, `gate-e.json`, `scope.md`, `forensic_sample/`, `runs/`, `diff/`, `tools/`.
- **SHARED DOC DELTA** (предложение): 23 — AUD-01T-R OPEN → offline-процедура и её пределы; 24/25/05/06/34 — статус «реализовано, на проверке», F-T1…F-T3; 36.2 — новый модуль и мутанты. 18/36/36.1 — NO CHANGE.
- **NEXT:** публикация через GitHub Desktop → независимый review ChatGPT + CI → отдельное решение пользователя о применении на реальных данных.
