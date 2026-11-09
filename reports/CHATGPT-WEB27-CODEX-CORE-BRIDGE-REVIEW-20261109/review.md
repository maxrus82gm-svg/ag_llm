# WEB27 — независимая приёмка CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001

**HISTORY:** `H-CODEX-000027`. **Публикация пользователя:** main №566 `80e6a0ff14755b4aba48cc1e037e00f852a990ce`. **Дата:** 09.11.2026.

**ВЕРДИКТ: BOUNDED INDEPENDENT OFFLINE PASS / DOCUMENT ITERATION CLOSED.** Новый fake-only мост Web Chat ↔ Ordinary Chat Core, Turn/RAW и Run Store принят в проверенном ограниченном объёме. **Не** даёт Stage6 DONE, S3b acceptance и разрешения живого GigaChat.

## Независимая проверка

- Сверены опубликованные SHA-256 пяти исходников (`web_alarm/ordinary_chat_bridge.py`, `ultra_chat.py`, `turn_service.py`, `server.py`, `test_web_alarm_ordinary_core_bridge.py`) с локальными Windows SHA: 5/5 MATCH.
- Независимый guarded Windows Python 3.12.10 (`python -B -X utf8 -m unittest`; bridge, ordinary service, Turn service/HTTP/S4B, Stage5 OfflineChatTests + два HTTP-S5 selectors): **109/109 PASS**, exit 0, 62.932 сек. Только loopback для тестового сервера; внешний socket, DNS, чтение credential/.env и live repository storage заблокированы ранним guard.
- Независимый `node --test test_web_alarm_ultra_chat_ui.js`: **52/52 PASS**, exit 0, JS VM/fetch fixtures.
- Независимый strict `guard_probes.py`: **6/6 BLOCKED/PASS** (socket, DNS, credentials, dotenv, live storage, external process).
- Анализ кода: только точный `_FixtureTransport`, любой другой sender возвращает `provider_admission_required`; TEMP allowlist/loopback, STANDARD disabled, stable retry/Turn snapshot и isolated selected-chat context. Known reasoning входит в completion и не суммируется дважды.

## Открытые ограничения

- Мост активируется только через доверенную одноразовую TEST server injection. Постоянный TEST launcher по-прежнему использует старую Stage5 fixture; штатный STANDARD/REAL не включён.
- Фикстурные пределы (32 сообщения, 2048 bytes input, 8192 bytes request/response, 128 output, 8 sec) **не** продуктовые defaults 250k/10k/20k. Per-chat UI, видимый usage и модельная калибровка ещё OPEN.
- S2 pure policy/S3a durable ledger пока не production guard; **S3b/S3c/S4/S13a применимые ворота, Stage6/Stage7/REAL/PAID HOLD**. Legacy Tk/agent RAW с неподтверждённым происхождением отвергаются; решение о подключении отдельно.
- Полный CI, native Tk, браузерный GUI, clean Windows, power-loss и реальные провайдер/OAuth/paid запросы **NOT RUN**.
- Общий накопительный бюджет Workspace и сводная финансовая статистика **DEFERRED**.

**NEXT:** `FOLLOWUP-WUA-ORDINARY-CORE-BRIDGE-ACTIVATION-001` — подключить новый bridge в разрешённый TEST web-only профиль и отдельные настройки/usage каждого чата. Новую TASK назначает пользователь; это не USER GO на live. До первого настоящего GigaChat требуется физический S3b и независимые применимые проверки №20. Слот Codex БЛОК 1 WAITING, 1.1 H27.

Авторские доказательства: `reports/CODEX-WUA-CHAT-ORDINARY-CORE-BRIDGE-001/report.md`, `manifest.json`, `finish_receipt.json`. Наши результаты: `reports/CHATGPT-WEB27-CODEX-CORE-BRIDGE-REVIEW-20261109/independent_results.json`.
