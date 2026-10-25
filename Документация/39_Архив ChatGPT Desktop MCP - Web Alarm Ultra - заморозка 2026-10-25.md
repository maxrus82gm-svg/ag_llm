---
graph_cluster: web-alarm
aliases:
  - ChatGPT Desktop MCP — архив заморозки
  - WUA Desktop Read-only — архив
  - Secure MCP Tunnel / V2Ray — точка восстановления
---

# 39. Архив направления ChatGPT Desktop ↔ MCP ↔ Web Alarm Ultra

**Статус:** `FROZEN / USER-DIRECTED HOLD / HISTORICAL & RECOVERY ARCHIVE`  
**Решение пользователя:** 2026-10-25. **Источник для подготовки:** `main@e6aa16cc0a8fd18bf7e8cb71ead648008b83f098` (`ag_llm`), прежние опубликованные technical reports и независимые записи WEB_09–WEB_12.  
**Владелец архитектуры:** [[19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP]]; **оперативный указатель:** [[34_TACTICAL_CONTEXT]].  
**Ни одна пометка «PASS» в этом документе не повышает чужие результаты до полного E2E/production PASS.**

> **ПРИОРИТЕТНОЕ USER DIRECTION 2026-10-25.** Пользователь **ставит на паузу всю исследовательскую/исполнительную ветку подключения именно обычного ChatGPT Desktop к локальному Web Alarm / будущей Web Alarm Ultra через MCP, плагины, Secure MCP Tunnel и выбранный для этой ветки строгий V2Ray-маршрут**. Перестать назначать новые задачи, тратить ресурсы на этот канал, запускать туннель, меня́ть Windows/WFP/прокси/движок или предлагать обходные способы до **нового отдельного решения пользователя**. Сохраняем наработки, документы, отчёты, тесты и незакрытые статусы **без удаления и без ложного закрытия**.

**ПРИОРИТЕТ ДАЛЬШЕ:** реализация самой **Web Alarm Ultra**, подключение LLM-провайдеров через официальные API, Connection Registry, обычный веб-чат/история чатов/Workspace, затем дальнейший перенос подходящих компонентов старой Ultra и агентские интеграции по отдельным задачам. Эта приоритетная смена **не включает автоматический engineering GO** на конкретный код, API-платежи или production. Историческое ограничение документа №38 «пока не начинать Ultra Tab» относится к решению от 2026-10-17; по **новому** решению пользователя от 2026-10-25 приоритет Ultra/API/Chat возобновлён. Текущая работа над исходным Web Alarm / WA4-R не объявляется автоматически закрытой и продолжает иметь отдельные gates.

---

## 1. Что именно заморожено, а что — нет

| Контур | Решение |
| --- | --- |
| **Обычный ChatGPT Desktop → WUA Desktop Read-only / local STDIO MCP** | **FROZEN**, никакой новой локальной активации/переустановки/повтора smoke |
| **Обычный ChatGPT Desktop/Web → Secure MCP Tunnel → локальный MCP/Web Alarm** | **FROZEN**, hosted tunnel не создавать и не запускать, `HOSTED_TUNNEL_ON_HOLD_BY_USER` |
| **Для этого канала строгая защита `STRICT_V2RAY_BROKER`** — C/B identities, NPFS, broker, WFP, sing/sing-box, default deny, no DIRECT | **FROZEN**, включая native-lab readiness/работы и дальнейшие source studies; принятый offline-код сохраняется |
| **Проверка Plus/Pro / availability локальных Desktop tools, Secure MCP Tunnel, Platform tunnel_id/key** | **FROZEN / UNRESOLVED**, не заявлять, что Plus разрешён или запрещён без подтверждения конкретного официального способа/аккаунта |
| **Web Alarm / WA4-R / server-owned TASK authority** | **НЕ ЗАМОРОЖЕНО этой записью**, собственный план и отдельная приёмка |
| **Web Alarm Ultra: свой веб-чат, providers/API, connection profiles, GigaChat, затем другие модели/агенты** | **АКТИВНЫЙ ПРИОРИТЕТ ПОЛЬЗОВАТЕЛЯ**, архитектурные документы №37/№11/№23–24 по применимости |
| **Универсальный MCP как протокол, Codex CLI/App Server, агенты внутри Ultra, сторонние адаптеры** | Не запрещены вообще; именно **путь ChatGPT Desktop к Web Alarm** заморожен. Любая новая работа отдельно назначается пользователем |

Не переносить локальные ограничения V2Ray/двух SID на все будущие провайдеры/API: это **только выбранный строгий профиль** конкретного канала. Другие описанные профили `DIRECT_ALLOWED`, `APPROVED_PROXY` существуют как **FUTURE / USER-CHOICE**, не как разрешённые fallback.

## 2. Исходный замысел и точки интеграции — важно не перепутать

**Первоначальная цель:** штатный **обычный ChatGPT Desktop Chat** должен стать главным внешним Planner/независимым проверяющим для Web Alarm Ultra, вызывать server-owned ограниченные инструменты, читать TASK/RUN/status/report/context/evidence и по отдельным полномочиям управлять задачами. **Web Alarm остаётся authority**: права, состояние, backup, audit, STOP, recovery и подтверждение опасных действий находятся у сервера. Codex и Claude — отдельные Worker/Reviewer, а **Codex Relay** — возможный транспорт уведомлений в конкретный чат, не второй Planner и не MCP-tool-call.

Никогда не смешивать три независимые границы:

1. **Входящий доступ ChatGPT к инструментам:** официальный Desktop MCP plugin/local executor либо официальный hosted/remote MCP transport. Наличие плагина и регистрация в конфиге не доказывают реальный вызов из **обычного** ChatGPT.
2. **Reachability:** локальный STDIO/bridge, IPC/NPFS, Streamable HTTP или Secure MCP Tunnel; V2Ray сам по себе **не создаёт** входного соединения от облачного ChatGPT.
3. **Egress security:** `STRICT_V2RAY_BROKER` — `wua-client` (C) → разрешённый локальный C→B путь → отдельный `wua-broker` (B) → разрешённый V2Ray/upstream. Никакого DIRECT/fallback и недоказанных DNS/UDP/IPv6 путей, при сбое `BLOCKED`.

**Не путать направления:** ChatGPT → Ultra tools по MCP ≠ Ultra → OpenAI/GigaChat/Claude API как LLM provider ≠ Codex CLI/App Server agent lifecycle ≠ отправка Codex сообщения в существующий веб-чат. Возможность Codex отправить сообщение в конкретный чат в Desktop-контуре обсуждалась и имела bounded smoke, но **не доказывает обычный Desktop MCP E2E** или unattended двухстороннюю автоматику.

## 3. Историческая шкала: что реально сделали

### 2026-10-15—16 — старт и первые настоящие локальные проверки

- В №37 зафиксирована исходная идея локального read-only MCP, в №19 — разделение внешнего ChatGPT/adapter от внутренних AI API. Codex провёл feasibility: реальная цепочка **локальный MCP SDK → синтетический WebAlarmApi** работала; полноценный обычный Desktop E2E — нет.
- Подготовлен `WUA Desktop Read-only`, прямой STDIO MCP-кандидат, регистрация и последовательные правки `0.2.0 → 0.2.1`; plugin в конфигурации Desktop установлен/включён. Read-only tools и receipt проверялись **локальным SDK**, включая успешные вызовы и ожидаемый отказ `TASK_ID_DENIED`.
- В отдельном официальном локальном bridge/SDK тесте было **четыре настоящих MCP-вызова: три успешных и один намеренно запрещённый**; обычный ChatGPT Desktop Chat после установки/перезапусков **не выдал доступные MCP-инструменты — 0 реальных вызовов**. Часть источников обозначает gate «0/4», но это **не четыре доказанных server-side отказа**: инструменты в обычном чате не экспонировались.
- Диагностика показала ограниченность local executor исследованной версии Desktop режимами Work/TPP. После неудачного обычного Chat теста исследован **официальный Secure MCP Tunnel**, а не произвольная автоматизация браузера как эквивалент MCP. Tunnel-client был локально подготовлен/изучен, но hosted tunnel не создан.

**Корневой источник:** `reports/CODEX-WUA-0-MCP-FEASIBILITY-001/report.md`, `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/report.md`, `post_restart_diagnostics_20261016/`, `secure_tunnel_preparation/`, `STDIO_REGISTRATION.md`, `NEXT_MANUAL_GATE.md`. Не делать повторных Desktop-install/restart только ради повторения уже сохранённой диагностики.

### 2026-10-16—18 — Secure MCP Tunnel, proxy и источник клиента

- Подтверждалось локальное наличие v2rayN/proxy endpoint `127.0.0.1:10808` и работоспособность HTTP CONNECT **в той тогдашней среде**; это не доказательство полноценного удалённого маршрута либо текущей доступности proxy.
- Пользователь утвердил для этого канала **только V2Ray**, запрет DIRECT и fallback. Runtime `tunnel-client`, remote V2Ray route, полный fail-closed и hosted E2E не запускались/не подтверждались. Для hosted пути требовались подтверждение прав Platform/ChatGPT, нужный `tunnel_id` и возможный отдельный Platform runtime key — это не то же самое, что платный model API.
- Сохранены исследование `v2ray_proxy_constraints_20261016/`, source/adapter `native_client_offline_20261017/`, synthetic `http_socks_adapter_20261018/` и `v2ray_preflight_20261017/`. Python/synthetic PASS != работа реального Go tunnel-client через защищённый маршрут.
- Исходники официального `tunnel-client v0.0.16` и подготовка source-only изучались отдельно. Ни их чтение, ни совместимость HTTP CONNECT ↔ SOCKS5 не разрешали включать hosted tunnel.

### 2026-10-18—21 — Windows security architecture и переносимый toolkit

- Разобраны варианты без VM / с отдельно изолированной лабораторией, `wua-client`/ `wua-broker` (C/B), SID-scoped egress, WFP IPv4/IPv6, непроверенные loopback/IPC/DNS, token owner, port ownership, default-deny и восстановление.
- Выполнены offline WFP backend/ABI/source review, Windows Lab Gate `I01–I12`, план portable deployment; реальное WFP enforcement, устанавливаемая/удаляемая защита, реальные accounts и нативная лаборатория **не доказаны**. `Install`/`Uninstall` в toolkit — deliberate BLOCKED scaffold.
- Отдельно утвердили универсальную концепцию Ultra с профилями `DIRECT_ALLOWED`, `APPROVED_PROXY`, `STRICT_V2RAY_BROKER`. **V2Ray — не требование протокола MCP**, а выбор пользователя для строгого режима этого соединения.
- В №19 §7б сохранена роль единственного ChatGPT Planner, серверный durable outbox и **bounded smoke** передачи сообщения Codex в существующий чат; не доказаны автоматический wake-up, session restore, штатные двусторонние вызовы и ChatGPT MCP readback.

### 2026-10-21—24 — MCP ↔ Web Alarm integration, Named Pipe, broker

- `CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001`: сделан ограниченный локальный MCP/API adapter с синтетическими Web Alarm операциями; отделены tools и service owner. Отмечено, что простой STDIO/Python может сам открывать сетевые сокеты, а формальная localhost/proxy-конфигурация не даёт строгой гарантии против обходов.
- `CODEX-WUA-0-MCP-NOTCP-NPFS-001`: C# STDIO→NPFS relay и server-owned gateway, настоящие локальные SDK-прогоны; **cross-SID/real C/B account access** не проверен. Это **C→U gateway**, не автоматически готовый C→B proxy через pipe.
- `CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001`: broker preflight/negative tests реализованы и приняты в **bounded offline** объёме, но реальная ownership B-owned process, engines, WFP, physical route — **BLOCKED**.
- Фактический proxy runtime v2rayN на исследованном хосте использовал embedded **sing-box.exe v1.13.4**. Метка `engine.family=V2Ray` является целевой конфигурацией, **не доказательством установленного V2Ray Core**. Не переключать движок/настройки без нового решения.

### 2026-10-24—25 — исходники sing, строгий admission, точка заморозки

- `CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001`: исходники sing-box v1.13.4, независимая ограниченная приёмка WEB_11 (публикационный/selected-source объём), не native pass; выявлены default DIRECT, DNS, UoT и условные egress.
- `CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001`: exact source `github.com/sagernet/sing@v0.8.3-0.20260315153529-ed51f65fbfde`; WEB_12 независимо **87/87** manifest SHA, **6/6** официальных исходников и **33/33** locators, reconstructed module h1 **из опубликованных** 322 hashes. Закрыто **TERMINAL PARTIAL / BOUNDED SOURCE & EVIDENCE ACCEPTED**; raw ZIP/physical route/native НЕ независимо верифицированы. Выявлено: `users=[]` отключает auth; ошибки способны включать `Proxy-Authorization` или password; CONNECT 200 выдаётся до downstream dial; JSON duplicate/default/merge/secondary paths не являются строгим отказом.
- `CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001`: WEB_12 независимо принял **PASS / INDEPENDENT BOUNDED OFFLINE SOURCE & EVIDENCE ACCEPTED**, опубликованные 53/53 SHA; Codex logs 52/52 admission, 51/51 compatible regression с **19 пересекающимися** тестами, 7/7 mutants caught, сохранён первый 19 PASS/21 FAIL. Python strict admission проверяет declared auth/canonical JSON/controller pins/CONNECT destination/deny-other; **`STRICT_ADMISSION_BLOCKED` сохраняется**, а риск утечки credentials upstream остаётся SECURITY BLOCKER.
- `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001`: **в `main@e6aa16cc0a8fd18bf7e8cb71ead648008b83f098` отчёт уже присутствует**, Codex указал `PASS / BOUNDED READINESS`, 14/14 ограниченных read-only групп, 28/28 offline tests, 3 mutants, no native. **Это SELF-REPORTED / RESULT READY / AWAITING INDEPENDENT VERIFICATION WEB_12**. WEB_12 эту последнюю TASK **не принимал независимо** на момент заморозки. Карточка Codex **БЛОК 1 остаётся назначенной**; не очищать и не объявлять итог Verified по факту архивирования. В отчёте уточнено: accounts C/B в ограниченной проверке не обнаружены; IPC C→B не реализован, WFP/native 0 tests; готов лишь blueprint/readiness package.

**Положение последней TASK:** `RESULT READY / AWAITING INDEPENDENT VERIFICATION`, затем **USER-DIRECTED HOLD** на дальнейшие действия. Если Codex ещё исполняет активный сеанс, пользователь должен передать ему STOP/HOLD и попросить сохранить текущие артефакты, без локальной ротации карточки. Сам факт нового архива **не является** terminal PARTIAL/PASS и не отменяет `DOC-TASK-CLOSEOUT-OWNER-01@1`.

## 4. Сводная матрица доказанности на дату заморозки

| Критерий | Фактическое состояние |
| --- | --- |
| Локальный MCP server / SDK initialize, tools, synthetic read и отрицательный чужой TASK | **BOUNDED TESTED**, верифицировано не через обычный ChatGPT |
| Plugin registration / visibility в исследованном Desktop | **OBSERVED**, v0.2.0/0.2.1; не равна доступности tools |
| Вызовы MCP из **обычного** ChatGPT Desktop Chat | **NOT VERIFIED — 0 реальных calls** |
| Codex → конкретный существующий чат ChatGPT: message smoke | **BOUNDED SUCCESS**, **не** MCP, не unattended workflow |
| Локальный bridge / NPFS / server-owned synthetic gateway | **BOUNDED SDK / offline**; real cross-SID/IPC ownership NOT VERIFIED |
| HTTP CONNECT к локальному proxy endpoint | **Исторически OBSERVED**; полный V2Ray remote route/fail-closed NOT VERIFIED |
| sing-box/sing source-review и точные SHA | **BOUNDED SOURCE VERIFIED**, не live binary attestation |
| Broker strict config / admission/secret refs | **BOUNDED OFFLINE PASS**, эксплуатационный запуск заблокирован |
| `wua-client`/`wua-broker` accounts, host ACL и B-owned socket | **NOT PROVISIONED / NOT VERIFIED** |
| Windows WFP default-deny IPv4/IPv6/DNS/UDP/child/loopback/IPC | **NOT VERIFIED / NOT RUN** |
| Secret-safe upstream HTTP auth/error logs | **OPEN SECURITY BLOCKER** |
| Hosted Secure MCP Tunnel, `tunnel_id`, runtime API credentials, access of user's Plus | **NOT VERIFIED / ON HOLD**; не утверждать tariff entitlement без официального фактического gate |
| Normal ChatGPT ↔ Web Alarm Ultra production E2E | **NOT VERIFIED** |
| `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001` по последнему опубликованному отчёту | **AWAITING INDEPENDENT VERIFICATION / HOLD**, не заменять статус на PASS |

**Инварианты без изменений:** `engine.family=V2Ray`; `can_apply=false`; `can_start_tunnel=false`; `install_uninstall=BLOCKED`; `STRICT_ADMISSION_BLOCKED`; `HOSTED_TUNNEL_ON_HOLD_BY_USER`. Полная система, SDK, облачные сервисы, ChatGPT workspace/территориальные и тарифные разрешения оцениваются отдельно, при возвращении к направлению.

## 5. Реестр исходников, отчётов и подтверждений — НЕ УДАЛЯТЬ

**Канонический репозиторий:** `maxrus82gm-svg/ag_llm`. Все пути ниже относительно корня Git; сохранённые task reports/readme/manifest/runs не перемещать и не переписывать, даже если внутри остались исторические `LOCAL ONLY` или `AWAITING` — пояснять отдельным current verdict.

| Слой / период | Канонический источник |
| --- | --- |
| Исходная архитектура ChatGPT→Ultra, транспорт, profiles, ChatGPT Planner/Codex Relay | `Документация/19_Архитектура внешних AI-интеграций - Codex CLI и ChatGPT MCP.md` §§3–7, §7б |
| Изначальное пожелание пользователя о Desktop, Ultra/API/chat | `Документация/37_Старт перехода - Web Alarm Ultra.md` §§1, 9 |
| Историческое разделение Web Alarm и MCP (2026-10-17) | `Документация/38_Контекст передачи в Сервер LLM12 - Web Alarm Ultra MVP.md` |
| Первичная feasibility и local SDK | `reports/CODEX-WUA-0-MCP-FEASIBILITY-001/report.md` и `smoke_attempt_*.json` |
| Desktop plugin 0.2.0/0.2.1, STDIO, диагностика, ordinary 0 calls, hosted HOLD | `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/report.md`, `STDIO_REGISTRATION.md`, `post_restart_diagnostics_20261016/`, `secure_tunnel_preparation/`, `NEXT_MANUAL_GATE.md` |
| Proxy adapter and tunnel native source investigations | `reports/CODEX-WUA-0-DESKTOP-MCP-E2E-001/{v2ray_preflight_20261017,native_client_offline_20261017,http_socks_adapter_20261018}/` |
| Claude WFP/egress architecture, Codex 2-identity review | `reports/CLAUDE-WUA-0-EGRESS-ARCH-REVIEW-001/`, `reports/CODEX-WUA-0-IDENTITY-EGRESS-REVIEW-001/report.md` |
| Offline WFP/backend, lab conditions, VM preflight, portable install planner | `reports/CODEX-WUA-0-WFP-OFFLINE-BACKEND-001/`, `reports/CODEX-WUA-0-WINDOWS-LAB-GATE-001/`, `reports/CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001/`, `reports/CODEX-WUA-0-PORTABLE-DEPLOY-KIT-001/` |
| MCP WebAlarmApi/strict V2Ray integration | `reports/CODEX-WUA-0-MCP-CHATGPT-V2RAY-INTEGRATION-001/`, `integrations/wua_chatgpt_mcp/` |
| STDIO→NPFS local IPC, synthetic read-only SDK gateway | `reports/CODEX-WUA-0-MCP-NOTCP-NPFS-001/` |
| Broker offline preflight | `reports/CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001/` |
| sing-box v1.13.4 native source snapshot | `reports/CODEX-WUA-0-PROXY-ENGINE-SNAPSHOT-001/`, `reports/CODEX-WUA-0-SINGBOX-SOURCE-REVIEW-001/` |
| Exact sing module dependency, full source graph/strict gaps, WEB_12 terminal PARTIAL | `reports/CODEX-WUA-0-SING-DEPENDENCY-REVIEW-001/`, `Документация/06_Журнал выполнения и отчёты.md` |
| Independently accepted strict admission/policy and mutants | `reports/CODEX-WUA-0-STRICT-ADMISSION-CONTRACT-001/`, Codex БЛОК 4 и `001_История выполненных задач Codex.md`, журнал №06 |
| **Последняя опубликованная, но не принятая independently readiness сдача** | `reports/CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001/`; Codex БЛОК 1; не трогать до отдельного решения |
| Хронология фактических user GO/вердиктов и сохранённая карточка | `Документация/000_Задачи Codex.md`, `Документация/001_История выполненных задач Codex.md`, `Документация/05_Реестр задач.md`, `Документация/06_Журнал выполнения и отчёты.md`, `Документация/34_TACTICAL_CONTEXT.md` |

**Исторические верификаторы и фактические доказательства не пересчитывать:** `WEB_09 / WEB_10 / WEB_11 / WEB_12`, Codex 007, Claude 008 — каждый результат читать с указанием exact report/manifest, `SOURCE REVIEW` vs `OFFLINE TEST` vs `NATIVE` vs `ORDINARY DESKTOP E2E`. Упоминание строки `PASS` в runner не даёт более широкого статуса.

## 6. Что было ОТКРЫТО и почему мы остановились — точка возврата

Это **решение о приоритетах**, не технический провал и не утверждение, что MCP запрещён/невозможен.

**Вопросы, которые придётся решить при возвращении:**

1. **Официальная доступность именно нужного канала на аккаунте:** локальный ChatGPT Desktop MCP versus hosted Secure MCP Tunnel; Plus/Pro/workspace capabilities, read-only или write tools; требование Platform token/tunnel resource, availability UI. Доступность **не доказана**: старые Desktop-перезапуски не активировали tools в обычном чате, а новая возможность могла измениться. Нельзя без проверки обещать Plus поддержку или объявлять запрет. Доступ из территорий/через сети должен соответствовать действующим условиям сервиса; никакого вывода по одному IP/proxy.
2. **Endpoint transport и inbound reachability:** официальный поддерживаемый local plugin/STDIO/HTTP или hosted bridge, проверка auth и прав; `ping`/tools-list/read_context **из обычного ChatGPT Desktop**, client identity и серверный receipt. Не подменять Codex/SDK calls реальным Desktop Chat.
3. **Секреты/безопасность:** исключить upstream leakage `Proxy-Authorization`/password, обеспечить защищённые credential store/ACL и недопустимость конфигурационного обхода.
4. **Native Windows:** C/B SIDs/tokens, NPFS/IPC, B socket owner, WFP default-deny IPv4+IPv6/DNS/UDP/loopback/child, independent observer, fail-closed при отключении proxy, guaranteed rollback **в отдельно разрешённой изолированной среде**.
5. **Exact runtime route:** v2rayN/sing-box versus V2Ray Core; source/installed EXE/config compatibility, физический upstream и отсутствие DIRECT/fallback. Не предполагать, что `CONNECT 200` означает route success.
6. **E2E и переносимость:** синтетический MCP SDK → реальный WebAlarmApi → обычный ChatGPT Chat → TASK/RUN readback с nonce/hash/audit; затем отдельно утверждённые write tools, durable notification и возможная portable installer release.

**Условия снятия заморозки:** только новое явное решение пользователя `UNFREEZE CHATGPT DESKTOP MCP`; перед действием проверить актуальную официальную ChatGPT Desktop/MCP/Tunnel поддержку, GitHub HEAD, статусы активной Codex TASK, сохранённые reports, живую машину и разрешения. Сначала **минимальный безвредный read-only eligibility test**, без реального туннеля и без side effects, затем отдельные GO на lab, native security, hosted routing, production. Старые инструкции из отчётов/прошлых чатов **не становятся автоматически разрешением**.

## 7. Регламент хранения и передачи в новые чаты/агентам

- **Этот №39 — текущий authoritative freeze-index для данного интеграционного направления**; документ №19 остаётся владельцем детальной архитектуры; №34 — оперативный контекст, №08/000/00 — навигационные ссылки. Старые §§19/37/38 и все `reports/` сохраняются как исторические документы, не редактируются задним числом.
- **Никаких повторных исследовательских TASK, автоустановки, «пробного» туннеля, default proxy DIRECT, WFP, provisioning, downloading или OS configuration** до нового USER GO. Остановить любые агентские работы этой ветки через пользовательское сообщение STOP/HOLD; **не очищать активную Codex TASK и не записывать новую** в её БЛОК 1 автоматически.
- Для уже опубликованной `CODEX-WUA-0-WINDOWS-ISOLATION-READINESS-001` сохранить `REPORT READY / AWAITING INDEPENDENT VERIFICATION`. Дальнейшая независимая приёмка и terminal closeout только по последующему пользовательскому разрешению и действующим правилам `DOC-TASK-CLOSEOUT-OWNER-01@1`.
- **Смена приоритета на Web Alarm Ultra/API/chat — разрешение на планирование следующей отдельной задачи, но не на автоматический запуск исполнителей или платных запросов**.
- При возобновлении начать чтение с №39 → №19 §§3, 7.1, 7.2, 7.3–7.8, 7б → №34 → только указанные здесь report/evidence/manifest и действующая карточка Codex. Нет необходимости повторять локальные SDK smoke/source archive/hash verification без противоречащих новых данных.

## 8. Быстрый handoff будущему WEB-чату

**Контур:** внешний ChatGPT Desktop Chat как единственный будущий Planner Web Alarm Ultra, MCP tool access через официальный local/hosted transport, профиль `STRICT_V2RAY_BROKER` со строгим no-DIRECT и двумя Windows identities. **На 2026-10-25: FROZEN BY USER.** Локальные MCP/NPFS/SDK и strict admission подтверждены **в ограниченных offline-сферах**, обычный ChatGPT Desktop calls **0**, Secure MCP Tunnel не запускался, Plus eligibility не доказана, real route/WFP/C/B E2E блокированы. Последняя readiness TASK опубликована, **ещё не проверена WEB_12**. Код/отчёты/архитектуру не удалять. Пока делать Web Alarm Ultra с provider API, соединениями и веб-чатом. Возобновление — только отдельным явным решением пользователя и свежей проверкой платформы.
