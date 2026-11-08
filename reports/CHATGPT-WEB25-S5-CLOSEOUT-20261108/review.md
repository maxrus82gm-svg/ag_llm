# WEB25 — Stage 5 OFFLINE, закрытие пользовательской проверки 08.11.2026

TASK: `CODEX-WUA-S5-TURN-CHECK-DIAG-001` / `H-CODEX-000021` и `CODEX-WUA-S5-TURN-UX-RECOVERY-001` / `H-CODEX-000022`. Source: коммит №536 (`c771f1575091a7115cb37cd9f0647cdc1f946f0f`), baseline №535 (`1c43a3cb6f6fa0c1dcd6e96f265a8a33f37a7467`). Статус: **H21 PARTIAL / BOUNDED ACCEPTED; H22 PARTIAL / BOUNDED ACCEPTED. Stage 5 OFFLINE USER SMOKE PASS в ограниченном объёме, DOC ITERATION CLOSED; не FULL/PRODUCTION PASS**.

## Независимое чтение GitHub

WEB25 проверил published SHA-256 всех четырёх рабочих файлов (UI, ultra_chat, JS-тест, новый Python-тест) и отчёта на соответствие авторскому manifest; before/final snapshots также соответствуют исходной/итоговой редакциям. Изучены изменения обработки Turn, проверки статуса, защиты от поздних GET и сохранения выбранного Chat, author evidence/RAW hashes/HTTP и протоколы finish/истории. Авторские финальные тесты: **52 JS PASS, 63 web Python PASS, 2 Tk отдельно PASS**. Независимый повтор тех же 52/63/2 тестов и полное CI WEB25 **NOT RUN**. Исходные RED и Tcl-авария совмещённого Tk/HTTP процесса сохранены.

## Фактический USER GUI smoke, Windows 08.11.2026

На `Start_WebAlarm_Test.cmd` пользователь получил пустой временный Stage5 OFFLINE профиль, создал синтетический Workspace и Chat `01`, `02`. Отправил `привет тест` и получил fake `Ответ на: привет тест` с «Ответ сохранён». Кнопка «Проверить состояние запроса» дала видимый отчёт («Проверка №… завершена. Показано актуальное состояние запроса»), скриншот продемонстрирован в диалоге. Enter отправляет; F5 сохраняет сообщения, историю и выбранный Chat, в т.ч. `02`; возврат в `01` показал независимую историю. Временный результат проверки после F5 исчезает — допустимый ephemeral feedback. **USER GUI SMOKE PASS** в этих границах; нет независимого архивированного server RAW/HTTP trace этой пользовательской сессии.

## Что НЕ проверялось и остаётся OPEN

- Полная browser matrix: отмена, recovery/retry, переключение моделей, keyboard/a11y и 480px не повторялись пользователем; `FOLLOWUP-WUA-S5-FINAL-BROWSER-001` **PARTIAL/OPEN**. Исторический эпизод «отмена → F5 → сообщение исчезло» не доказал удаление RAW; H22 подтвердил на синтетике hash и ошибку возврата в newest Chat, но старого trace нет.
- `FOLLOWUP-WUA-S5-CANCEL-F5-VISIBILITY-001` историческая причина OPEN; `FOLLOWUP-WUA-S5-WORDING-VISUAL-001` 480px OPEN; `OPEN-S5-TK-COMBINED-PROCESS` Tcl abort OPEN; `FOLLOWUP-WUA-S5-CLEAN-WINDOWS-001` §2.4 portable install NOT VERIFIED. Также исторический writer-busy и другие №05 OPEN.
- Пользователь предложил FUTURE UX `FOLLOWUP-WUA-S5-TURN-PER-MESSAGE-UX-001`: показывать компактную проверку **у конкретного сообщения по его Turn ID**, не только внизу для последнего Turn; вместо расплывчатого «актуальное состояние» выводить «Ответ сохранён/Выполняется/Исход неизвестен». NON-BLOCKING Stage6, отдельное назначение позже.
- RAW, видимая история и контекст следующего запроса различаются. Проверка Turn **не** доказывает включение текста в будущий контекст и **не** делает новую физическую отправку. UNKNOWN нельзя автоматически повторять.
- Реальный GigaChat/OAuth, paid/live, Colibri, Stage6 B2, и полный clean Windows deployment НЕ тестировались и НЕ разрешены. Попавшее в №536 изменение `.obsidian/workspace.json` вне технического scope не исправляется в этой документальной итерации.

**Итог:** Stage5 OFFLINE с пользовательским ограниченным smoke принят; F1/F2/F4/F5 подтверждены только в ограниченном source+author evidence scope, F3 историческая часть и F6 visual остаток OPEN. Следующий путь: новая, отдельно назначенная Stage6 RT-002/B2 TASK с №20 §5а, durable ledger/reservation и fail-closed **до каждой физической отправки**, затем Stage7 real GigaChat лишь после 5–6 и отдельного USER GO с лимитами. CODEX БЛОК 1 WAITING, БЛОК 1.1 H22; не перезаписывать. Документация публикуется WEB25 в GPT и требует USER merge в main.
