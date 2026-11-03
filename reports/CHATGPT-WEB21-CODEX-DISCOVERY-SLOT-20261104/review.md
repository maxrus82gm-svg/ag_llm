# WEB21 — административная сверка закрытия Codex / 04.11.2026

**Scope:** только документация и подготовка персонального слота, без изменения runtime/code/tests, запусков Python/Windows/CI или обращения к локальным LLM. **Источник:** `main@097b88172e165ec08787281b97ad2c0860a7e321` (№497), после принятия пользователем №496. **Статус:** documentary reconciliation prepared; B1 rotation NOT RUN / SLOT HOLD.

## Подтверждено

1. `CODEX-WUA-LOCAL-LLM-DISCOVERY-001` уже независимо ограниченно проверена LLM15 от 02.11: 28/28 опубликованных файлов в предыдущем review, verdict `PASS / BOUNDED DIAGNOSTIC & ARCHITECTURE REVIEW; TASK PARTIAL / DOC ITERATION CLOSED`. В WEB21 **не повторяли** SHA/Windows/inference/runtime и не присваивали второй технический PASS.
2. Постоянный snapshot полного TASK — `reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001/assignment_source.txt`. Содержимое B1 совпадает с ним после нормализации завершающего перевода строки; архив №001 уже содержит вердикт и адрес snapshot. Известный SHA256 snapshot: `287af2ebf4eb1e0dd584135d4ed8c80dc8f943d558e379782d4133e7c3c10587` (из независимой приёмки LLM15, НЕ новый пересчёт).
3. Предыдущий B1.1 — `CODEX-WUA-DOC-WEB19-REPAIR-001`; его текст обнаружен в опубликованном `reports/CODEX-WUA-DOC-WEB19-REPAIR-001/handoff_task.md`. Ни B1, ни B1.1 в этом коммите не редактируются.
4. Состояния и residuals уже занесены в №05 `REG-LLM15-LOCAL-LLM-DISCOVERY-20261102`, №06 `EVT-LLM15-LOCAL-LLM-DISCOVERY-20261102`, №001 Codex, БЛОКИ 2–4 и №34/40; теперь поправлены устаревшие признаки WAITING и отражён USER GO по следующему UI приоритету.
5. `FOLLOWUP-WUA-LOCAL-LLM-COLIBRI-001` и `FOLLOWUP-WUA-LOCAL-LLM-DISCOVERY-ADAPTER-001` не закрыты; таблица №05 исправлена так, чтобы строки оставались внутри раздела очереди. Stage3/Blueprint П1/live/paid не разрешались.

## Блокер и последующее действие

`FOLLOWUP-CODEX-DISCOVERY-SLOT-001` — фактический B1 содержит прошлую завершённую TASK. Правило №18 `DOC-BLOCK1-SLOT-01@1` требует применения штатного `tools/task_slot_rotate.py` только после archive guard, dry-run и отчётного пакета. В этом GitHub-only документном ходе **скрипт не запускался**, никаких фиктивных `ROTATED` или `B1 WAITING` не записано.

После принятия пользователем документационного коммита и `pull` локальный Codex выполняет локальный `check`, `rotate` dry-run, затем `rotate --apply` с `--task-id CODEX-WUA-LOCAL-LLM-DISCOVERY-001`, `--no-chat-amendment` только если пользователь подтверждает отсутствие поправок, а для предыдущего 1.1 при необходимости `--previous-archive reports/CODEX-WUA-DOC-WEB19-REPAIR-001/handoff_task.md --previous-archive-ref №483`. Должны появиться `handoff_task.md` и JSON-протокол; пользователь публикует безопасную ротацию. На ошибке `NO ROTATE` оставить карточку без изменений и сообщить координатору.

**NEXT:** после проверенного `B1 WAITING` пользователь самостоятельно вставляет предложенную в WEB21 `CODEX-WUA-CHAT-UI-INTEGRATION-001`; новая задача до того NOT ASSIGNED. Исполнителю запрещён Git/GitHub без специального USER GO. №37/№43 действуют без изменений.
