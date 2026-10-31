# WEB18 — независимая проверка Stage2 / REVISE

**Дата:** 2026-10-31. **TASK:** `CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001`, Claude 008. **Проверяемые байты:** `main@c555312dbdcb5bd3e85e0bebebb9d708f578b6cb`, коммит №473 (предшественник `cd25b8d6ef71dc3a266adfb6945d30aa3cc8f66d`). **Вердикт:** **REVISE / PRODUCT NOT ACCEPTED; DOC ITERATION CLOSED** — подтверждён статическим анализом путь возможной записи вне Workspace. Это не утверждение, что инцидент уже случился на пользовательских данных.

## Независимо подтверждено

- Полная постановка сохранена в `reports/CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001/handoff_task.md` и в БЛОКЕ 1.1 Claude; БЛОК 1 — WAITING, БЛОКИ 2–4 автор не изменял.
- Независимо пересчитаны SHA-256 всех **8/8** новых/изменённых инженерных файлов по `manifest.json`, включая исходные CRLF у `ultra_ui.py`, `web_alarm/server.py`, `web_alarm/ui.py`; байтовые размеры совпали.
- Проверены фактические записи в `evidence/gate_all.json`: **1078 разных тестов** (1076 PASS, 2 SKIP; 0 FAIL/ERROR), и `gate_focused.json`: **122 разных теста** (120 PASS, 2 SKIP), оба по авторским протоколам с `runner_exit=0`, `isolation_violations=0`.
- `gate_js.json`: авторский 140/140; `mutants.json`: 39 уникальных mutants `KILLED`, четыре авторских controls PASS. Эти данные внутренне согласованы, но тесты не перезапускались независимым verifier. GitHub Actions run на точном SHA №473 не найден. Не заявлен independent runtime / physical Windows PASS.
- Прочитаны новые writer, Web HTTP gates, Tk wrappers и тесты; web write token не является Stage1 read token. Run Store, Tk readers и clean-Windows portability остаются вне этого review.

## F-01 — путь message_context допускает вложенный junction/symlink (подтверждённый source defect)

**Сценарий без конкурентной подмены.** В синтетическом Workspace с существующим Chat и RAW заранее подменить `.ultra/chats/<chat_id>/message_context` на directory junction/symlink к отдельному синтетическому каталогу. Вызвать `restore_message_raw(root, chat_id, message_id)` либо `create_message_context_variant(...)`.

**Почему это возможно по опубликованному коду:** `_chat_writer` → `_require_chat_for_write` проверяет Chat/его `metadata.json`, но не вложенный `message_context` и `variants` (`context_storage.py`, ~2021–2070). `_restore_message_raw` создаёт `state.json` через `_atomic_write_json(_message_context_root(...))` (~1143–1161). `_create_message_context_variant` аналогично пишет `variants/<id>.json` (~1079–1142). `_atomic_write_text` (~88–103) вызывает `path.parent.mkdir(parents=True, exist_ok=True)` и запись по пути, следуя родительскому directory junction. Глобальная блокировка Workspace не защищает чужой каталог, на который уже указывает такая ссылка. Имеющийся `PathSafetyTests.test_links_in_the_written_path...` (~769–811) покрывает `ultra/chats/chat/messages`, но не `message_context`/ `variants`. Поэтому заявленная сквозная проверка no-follow для всех writers не выполнена.

**Влияние:** возможность записи вне разрешённого Workspace и нарушение Stage2 §4.2, §7 п.6. Это статически доказанный путь; независимое исполнение на Windows не выполнялось и наличие вредоносной ссылки в реальном проекте не утверждается. Конкурентная подмена папки *после* проверки — отдельный уже описанный автором residual same-user race, не причина этого finding.

**Нужное исправление и проверка:** все writers context state/variants должны отвергать pre-existing junction/symlink в каждом родительском каталоге до создания или замены файла; проверить целевой путь/identity, безопасный отказ `unsafe_storage_link`; на одноразовом синтетическом fixture фиксировать SHA/дерево *чужого* каталога до и после `restore`, `create`, `activate`. Проверить как source, так и Windows junction, POSIX symlink где разрешено; две роли writer/reader и старое корректное поведение. Добавить негативный oracle/mutant, адресную и общую регрессию. Не испытывать на живых Workspace. Привязка №05: `FOLLOWUP-WUA-S2-CONTEXT-PATH-001`, successor `UNASSIGNED` до решения пользователя.

## Закрытие и границы

Итерация технической сдачи и review архивируется с **REVISE**, не выдаётся за принятый продукт и не разрешает этап 3/live/paid. БЛОК 1 уже освобождён агентом при сохранённой постановке и readback; БЛОК 1.1 не очищать. Новую repair TASK пользователь назначает отдельно; после её исполнения необходима независимая проверка точных исходников и отчёта. Дополнительно OPEN: два symlink SKIP, real GUI/Tk Windows, UNC/subst/POSIX, самостоятельная full regression, Stage1 N1–N30, P9 Run Store и Tk reader P1–P6. №05/№06/№001/№34/№40 и карточка Claude связываются этим verdict. Изменения кода по этому review **не выполнялись**.
