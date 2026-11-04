# WEB23 — независимый ограниченный review Run Store v2 перед Stage 3

**Дата:** 2026-11-04  
**Verifier:** ChatGPT WEB23  
**TASK ID:** `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001`  
**HISTORY ID:** `H-CODEX-000012`  
**Опубликованная версия:** `main@e3253b41502ac2d76c61c0faf7a5b660e2cc7eb9` (коммит 507).  
**Вердикт:** **PASS / BOUNDED SOURCE + AUTHOR EVIDENCE** по исправлению двух выявленных Run Store prerequisites и механизму явного восстановления. **Независимый Windows/CI/runtime НЕ ВЫПОЛНЕН**; полная эксплуатационная сертификация не заявляется.

## 1. Проверенные источники

Адресно прочитаны в GitHub: `run_store.py`, `test_run_store_v2.py`, `test_web_alarm_ultra_chat_turn.py`, `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/` (`task_record.json`, `handoff_task.md`, `report.md`, `manifest.json`, финальные и исходные негативные оракулы, `evidence/results_summary.json`, `evidence/finish*.json`, `evidence/conservation_after_finish.json`). Проверен commit-file scope; сторонние `.obsidian/graph.json` и `.obsidian/workspace.json` попали в пользовательскую публикацию и не приписываются исходникам TASK.

Опубликованные SHA-256 побайтово совпали с зафиксированными для `run_store.py` (`dbfd491183a13e550ca1d690245e6bd1cda7784d45f58b9ed16ad9cb28c0a63e`), `test_web_alarm_ultra_chat_turn.py` (`fc1bd907a96b44be011c9b2f1abffd21dc02da597885640074e54193aa3c0320`), `handoff_task.md` (`eb98519ca41ad905e424c1cc30665e4004058d8a5cbba240bc59d6401a9156e0`) и `report.md` (`8e75a054da63baf6795fa3e073797a37158fb3bd1d510e5def21926da2a4db27`). Проверка проводилась над исходными байтами GitHub, а не над отображаемой Markdown-копией.

**EOL-оговорка:** опубликованный `test_run_store_v2.py` имеет 38 597 байт / SHA-256 `dde134f2d9f2e2fd657ce822cf7da05b3244a6c088c3fb60bd36f24ded4e2dab`, тогда как авторский manifest указывает 38 598 байт / `4250c32cc302ccbdc8df4472fc4940699a1db90c04e2f0b19d163f3ad92f17bf`. Независимое воспроизведение показало: единственное добавление CR перед LF на строке 479 точно восстанавливает авторский SHA. Это эквивалентное изменение перевода строки вне кодового литерала, но **строгий исходный SHA для этого одного опубликованного файла не совпадает**; нельзя заявлять 100% побайтовое соответствие всего manifest и запуск тестов на точных GitHub-байтах. При следующей независимой проверке использовать именно опубликованную версию и фиксировать её SHA.

## 2. Проверка исправления двух prerequisites

- **Audit-path:** `_audit_location` строит лексический путь без доверительного обхода `audit`; `_checked_path` проверяет промежуточные сегменты через существующий `context_storage` anchor, отказывает для reparse/junction/hardlink/не-регулярных файлов. Открытые дескрипторы дополнительно проверяются по конечному пути. Исходный авторский Windows oracle фиксирует внешний write при junction, финальный — `refused=true`, только `untouched.txt` вне Workspace, marker unchanged.
- **Single writer:** `append_run_record` теперь удерживает общий OS `_index_lock` на интервале sequence/offset/stream/index/fsync/readback. Исходный oracle имел `[1,1]`, финальный — `[1,2]`, 2 записи, непрерывные offsets 0/147 и SHA по индексу. Отдельный тест нагрузки выполнял три процесса по 12 событий.
- **Interrupted append:** `append.pending.json` с подтверждённым prefix, явный `recover_run_records`, отказ на неизвестных orphan/torn/invalid-intent, отсутствие автоматического replay. Проверены исходники и адресные авторские негативные тесты. Безусловная гарантия against same-user TOCTOU и power-loss вне заявленного scope.

## 3. Реальные авторские результаты (не независимый runtime)

- Prerequisite RED до правки: **1 PASS / 2 FAIL**, exit 1; после правки: **3 PASS**, exit 0.
- Финальные Run Store/audit тесты: **62 PASS**, exit 0.
- Python regression: первый **165 PASS / 1 ERROR / 5 SKIP**, WinError 10053 в folder-picker; повтор на финальном source **166 PASS / 5 SKIP**, exit 0.
- Node UI: **158 PASS**, exit 0.
- Итог без суммирования повторов: **389 PASS / 5 SKIP**, 0 FAIL / 0 ERROR в финальной выборке. Это авторская Windows 10/Python 3.12.10/Node 22.20.0 фиксация. Независимые Windows/Node/Python/CI не запускались.
- Preservation: авторский readback **601/601 user storage неизменно**, отдельная внешняя editor-state delta `.obsidian/workspace.json` не откатывалась. Verifier реальный локальный filesystem не читал.
- Finish: JSON receipt фиксирует `ROTATED`/exit 0, БЛОК 1 `WAITING`, БЛОК 1.1 точная TASK; `H-CODEX-000012` и существующая `task_record.json` проверены на опубликованной версии. Веб-координатор БЛОКИ 1/1.1 не изменял.

## 4. Итог, открытые вопросы, разрешённый NEXT

**Принято в ограниченном source+author-evidence scope:** исправление `FOLLOWUP-WUA-P9-AUDIT-PATH-001` и `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001`. Полное `VERIFIED_CLOSED` по независимым Windows или всему продукту **не заявляется**. Сохраняются `FOLLOWUP-WUA-P9-INDEPENDENT-RUNTIME-001`, `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001`, `FOLLOWUP-WUA-S3-TURN-IMPLEMENTATION-001`, прежние Tk/staging/portability и прочие действующие OPEN из №05. Five native symlink SKIP не отменяют выполненные Windows junction/hardlink tests. Отдельные риски: TOCTOU same-user, power-cut/network-share durability, внешние writers без shared lock, максимальный размер компонента 64 MiB, lock-free readers на partial append.

**Stage 3 Turn/HTTP/mock/TEST composer:** **NOT IMPLEMENTED, HOLD**. Следующее рекомендуемое независимое испытание — адресный Windows/CI прогон pinned `main@e3253b4` на disposable fixtures: 3 prerequisite, 62 Run Store/audit, критические negative recovery/concurrency, а затем applicable regression. Только после review этого gate и отдельного назначения пользователя готовить полноценный Stage 3 TASK. GigaChat/Colibri/Ollama, paid/live, Blueprint P1, WA4-R и Desktop MCP не разблокированы.

**DOC closeout:** запись review в существующей `task_record.json`, короткие №001/05, FOLLOWUP №05, event №06, нынешний №34, профиль №37, координация №40 и БЛОКИ 2–4 Codex. Чужой активный слот Claude P9 с `NO_TASK_ID` не меняется. Документационная версия готовится только в ветке `GPT`; пользователь решает `GPT → main` и последующую локальную синхронизацию. Это не self-verification собственных документационных правок.
