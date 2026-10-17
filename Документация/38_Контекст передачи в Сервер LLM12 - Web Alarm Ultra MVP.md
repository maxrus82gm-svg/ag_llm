# Передача контекста → «Сервер LLM 12» — Web Alarm Ultra MVP
**Дата:** 2026-10-17. **Назначение:** самостоятельный handoff для нового рабочего чата LLM12. **Статус:** CONTEXT ONLY / NO IMPLEMENTATION GO.
**Проверенный публичный источник до handoff:** `main@9ed88027acfbb0527421611fabbbb3a416dda0b0` (документационный коммит №356). **Отдельно:** новый результат Claude от 2026-10-17 — только сообщение пользователя, `LOCAL ONLY / NOT SYNCED`.

## 1. Разделение рабочих потоков
- **LLM12 — планирование нового Web Alarm Ultra MVP**: интерфейс Ultra, реестр подключений, GigaChat-first чат, после него Blueprint LLM node и Codex adapter. Не присваивать себе активную WA4-R reliability-приёмку или MCP-туннель.
- **WEB_09 — Web Alarm Reliability / WA4-R + независимая проверка Claude**: отдельный инженерный контур. Claude 008 самостоятельно исполнил `CLAUDE-WA4-R-AUD01T02B-REPAIR-001` и сдал локальный отчёт; пользователь ещё не опубликовал этот набор файлов в GitHub. Следующая стадия — публикация пользователем, GitHub source/evidence review и независимая проверка, не новый coding GO.
- **Codex 007 — отдельное исследование WUA Desktop Read-only MCP**; OpenAI Secure MCP Tunnel и V2Ray — отдельная feasibility-ветка. Не считать успешный локальный MCP bridge подтверждением доступа из обычного ChatGPT Desktop.

## 2. Главная цель LLM12
Внутри уже существующего Web Alarm создать **отдельную вкладку Ultra**, где пользователь выбирает сохранённое подключение GigaChat и доступную модель, ведёт диалог, получает настоящий ответ сервера и сохраняет историю. Первую итерацию начинать mock-first; реальная сеть/авторизация/возможные API-затраты требуют отдельного user GO. Это **не** замена или перенос старой Tkinter Ultra целиком.

**Обязательная проектная последовательность концепции из 37:**
1. `WUA-0` — read-only feasibility: inspect Web Alarm HTTP/UI, существующие GigaChat registry/transport, storage, permissions, пути интеграции; сопоставить 2–3 варианта и определить минимальный совместимый scope. **Нет runtime writes.** USER GO ещё нужен.
2. `WUA-1` — отдельный Connection Registry, profiles, состояния configured/authenticated/ready/error, безопасность credential references, первый mock GigaChat.
3. `WUA-2` — Ultra Tab и Chat: Workspace/Chat history, модель из готового профиля, composer, ответ/ошибка/отмена, persistence, server round-trip и UI smoke.
4. `WUA-3` — минимальный versioned Blueprint LLM Node: `Chat Input → LLM Node → Chat Output`, ссылки на connection/role/contexts, typed ports.
5. `WUA-4` — Codex как самостоятельный агент через отдельно подтверждённый agent lifecycle/transport (не выдавать LLM API или MCP tool за полноценный Codex session).
Этапы 1–5 — **кандидаты**; WUA-1–4 и полноценный visual editor **не назначены**. Круглый стол и сложные графы не нужны для первого GigaChat ответа.

## 3. Не смешивать архитектуры
1. **Старая Ultra / RT-002/B2**: самостоятельная Tkinter-система с `server.py`, `ultra_ui.py`, Project Context, Workspace/Chat, RAW history, Planner/Executor/Dredd, RUN/Audit; не ломать. `S0` offline independently accepted; `S1` не назначена; `S2` budget policy pure/offline source-reviewed bounded, **не live enforcement**; S3+/UI не объявлять готовыми. План RT-002 — 20 §5а. Эта ветка не равна новому Web Alarm Ultra MVP.
2. **Web Alarm Workspace / WA4-R**: владеет workflow TASK, lifecycle, authority, backup, approvals и физическими мутациями. Ultra Chat владеет только собственными Chat/Turn. Не создавать конкурирующий task/mutation authority.
3. **Web Alarm Ultra / новый MVP**: Connection Registry, Chat Runtime, Blueprint LLM Node — независимые слои. `connection_id`/credential-ref отдельно от UI и от node. `Chat ID` не равен `Web Alarm TASK ID`. Role, Input и разрешённые Context refs не дают сами по себе права читать весь диск или выполнять write.
4. **WUA Desktop MCP**: отдельный инструментальный bridge, а не необходимая предпосылка первого GigaChat чата. Для расширения через туннель нужен маршрут **только через V2Ray с fail-closed**, который пока не доказан; прямой обход V2Ray запрещён пользовательским требованием.

## 4. Claude 008 — свежий оперативный статус, только USER-REPORTED / LOCAL
`CLAUDE-WA4-R-AUD01T02B-REPAIR-001` закрыта исполнителем как `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, **не DONE/VERIFIED**. Ротация карточки Claude: новые постановка и результат в БЛОКАХ 2/3, БЛОК 1 свободен. Пользовательский отчёт:
- Исправлены глобальное transport JSONL framing/torn-tail/cross-process append/UTF-8 и CAS→event admission integrity микрозадач; разрешённая граница — 5 существующих файлов + 1 новый regression test.
- Full offline/local Windows: **849 всего = 848 PASS, 0 FAIL, 0 ERROR, 1 SKIP** (symlink). Новый регрессионный модуль 27/27; это **утверждение исполнителя**, пока не независимый rerun.
- Известное ограничение `AUD-02b-R`: crash между durable status CAS и event всё ещё оставляет status-only след; нужно решение о контракте recovery. `AUD-01T-R`: crash в середине transport append может оставить torn tail, ручное восстановление не спроектировано. `AUD-02c`: невалидный mid-journal в POST /microtasks/.../report; `AUD-03` и `AUD-04` OPEN.
- `WA4-R PARTIAL`; **WARN/GATEWAY REQUIRED/STRICT/Final Audit не разрешены**. Чистый CI W1 и отдельный read-only live-storage preflight W3 не выполнены.
- Локальный путь отчёта: `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-AUD01T02B-REPAIR-001/report.md` + evidence/manifest/probes/runs. **Эти изменения не были закоммичены на момент сдачи**. Не утверждать, что они уже в GitHub или приняты ChatGPT.

## 5. Codex 007 MCP — только фон, не блокировать MVP
По предыдущему локальному отчёту Codex, `WUA Desktop Read-only` через локальный Secure MCP Tunnel временно выполнял 4 теста: 3 OK, ожидаемый `TASK_ID_DENIED`. Это **не** обычный Desktop Chat; в обычном Chat по последней проверке **0/4**. Реальный hosted tunnel не создан, `tunnel_id`/OpenAI Platform key не предоставлены. Предложена V2Ray proxy `127.0.0.1:10808`, но маршрут, fail-closed и безопасный запуск **не доказаны**; запуск без отдельного GO блокирован. Ключи не вставлять в чат/репозиторий; не менять сеть, VPN/proxy/firewall самовольно. Это можно исследовать отдельно после разведения активных задач.

## 6. Роли, документы, публикация
- **ChatGPT** — основной Planner, координатор общей документации, независимый source/evidence reviewer, штатный читатель/писатель GitHub. **Пользователь** лично передаёт TASK Codex/Claude, обычно сам выполняет commit/push их локальной работы.
- **Claude/Codex/Astra** работают локально в своём конкретном write-scope. Нет прав Git/GitHub (даже read-only), commit/push и произвольной связи с ChatGPT **без отдельного явного user permission**. Все отчёты и безопасные evidence — внутри `ag_llm`, publishable и не спрятаны .gitignore. Не менять чужие активные БЛОКИ 1–3.
- При новой инженерной TASK: точный ARCH CLASS, pinned source SHA, read/write scope, негативные tests/CI, неизменность старой Ultra и Web Alarm WA4-R, документационное сопровождение, explicit user gate.
- Важные документы: `08_Старт.md`, `18_Регламент сопровождения документации.md`, `34_TACTICAL_CONTEXT.md`, `37_Старт перехода - Web Alarm Ultra.md`, `23/24/25` (Web Alarm), `19` (AI adapters), `11` (model registry), `Blueprint LLM.md` и его тактический контекст, `20 §5а` (отдельная старая Ultra), `36/36.1/36.2/36.3` (тестирование). Факты и статусы должны сверяться по свежему GitHub после пользовательского push.

## 7. Следующее действие для чата «Сервер LLM 12»
**Сначала принять этот handoff как контекст и не начинать изменения кода.** Затем с пользователем обсудить, как стартовать WUA-0: точный read-only feasibility scope, ресурсы и отсутствие пересечения с Claude/WA4-R; предоставить 2–3 архитектурные альтернативы с MVP trade-offs и подтверждёнными источниками. Только после отдельного USER GO выдать исполняемую TASK локальному агенту. Не объявлять этот документ разрешением на API-запросы, туннель, сеть, Git/GitHub или rollout.
