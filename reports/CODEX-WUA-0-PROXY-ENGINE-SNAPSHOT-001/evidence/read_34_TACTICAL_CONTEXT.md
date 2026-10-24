## WEB_11 / CURRENT 2026-10-24 — проверены offline MCP NPFS и broker

**Codex CODEX-WUA-0-MCP-NOTCP-NPFS-001:** PARTIAL / bounded source-evidence review (`main@1147d283674f60ad94dd0be4b26f49e751523669`): independently **1404/1404** listed paths and **10/10** SHA-256; Codex saved 24/24 NPFS, 63/63 MCP, 24/24 security, independent Windows rerun NOT RUN. C# STDIO ↔ Named Pipe ↔ server-owned U synthetic MCP API candidate exists. **Codex CODEX-WUA-0-V2RAY-BROKER-OFFLINE-001:** PARTIAL / bounded offline source-evidence accepted (`main@1324f544c7d3fef6c0a80bf71f7460f372f6950d`): independently **617/617** paths and **12/12** selected SHA-256; Codex 33/33 broker + 63/63 MCP + 24/24 security; DIRECT and synthetic owner negative controls reviewed, independent Windows rerun NOT RUN.

**Незакрытые:** historical v2rayN launched sing-box, not proven V2Ray Core; exact engine version/source/schema/HTTP CONNECT BLOCKED. Real B/C technical accounts, actual V2Ray egress owner, WFP containment, hosted tunnel and ordinary ChatGPT E2E NOT VERIFIED. `can_apply=false`, `can_start_tunnel=false`, `HOSTED_TUNNEL_ON_HOLD_BY_USER`. Next bounded TASK — read-only exact engine fingerprint and compatibility analysis; engine change and native run need separate decision/GO. Full verifier entries in 06, Codex B4 (on GPT), architecture 19 §7.4. GPT publication does not mean merged main/local.

---

**ПРИОРИТЕТНОЕ РЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ / 2026-10-24 / DOC-GPT-BRANCH-01@1:** в репозитории `maxrus82gm-svg/ag_llm` собственная ветка ChatGPT — **GPT**; одобренные изменения и независимые диагностические CI ChatGPT публикует в GPT. PR `GPT → main` допускается; **merge в main делает только пользователь**, без нового отдельного разрешения ChatGPT не пишет main. Сверять актуальные HEAD и run ID. Claude/Codex не получают Git/GitHub прав. Полная норма — 18, DOC-GPT-BRANCH-01@1.

**РЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ 2026-10-22 / ПРИОРИТЕТ НАД СТАРЫМИ ЗАПРЕТАМИ:** ChatGPT по умолчанию координатор и независимый проверяющий, но может **сам писать и запускать безопасные временные диагностические тесты** и доступные независимые CI. **По прямому поручению пользователя в текущем чате** вправе лично изменить tracked код, постоянные тесты или CI в согласованном scope и передать изменения через GitHub. По умолчанию без поручения инженерные файлы не изменяются. Самопроверка своего исправления не является независимой приёмкой. Роли Claude/Codex и их ограничения Git, scope, live/production неизменны. См. `Решение пользователя - ChatGPT тесты и правки кода - 2026-10-22.md`.



## ARCH DECISION / 2026-10-20 / WEB_11 — универсальная ChatGPT MCP-интеграция и независимые сетевые профили

**Решение пользователя / FUTURE, НЕ РЕАЛИЗОВАНО:** Web Alarm Ultra проектируется как переносимая мультимодельная система с каталогом подключений собственных LLM/API, локальных моделей, CLI/агентов и MCP-инструментов. Внешний ChatGPT → Ultra MCP/plugin tools **не равен** Ultra → LLM model provider. «Проводник» в будущем показывает официальные способы авторизации, доступные возможности, выбранный сетевой профиль, необходимые изменения/scopes и запрашивает отдельное согласие; секреты не попадают агенту.

**Сеть:** `DIRECT_ALLOWED` (только явный выбор), `APPROVED_PROXY` (поддерживаемый прокси), `STRICT_V2RAY_BROKER` (наша текущая обязательная цель Codex: технические SID/WFP, две учётные записи и выделенный V2Ray-брокер без DIRECT). V2Ray не обязателен для MCP вообще; **для выбранной локальной строгой политики он обязателен, отказ должен быть fail-closed без fallback**. Два Windows SID — кандидат именно строгого режима, не защита всей Windows/ChatGPT Desktop.

**STATUS / NEXT:** детали зафиксированы в 11 и 19. Codex Install/Uninstall BLOCKED; WFP/V2Ray/network isolation/ChatGPT E2E NOT VERIFIED; `HOSTED_TUNNEL_ON_HOLD_BY_USER` остаётся. Нет новой TASK или разрешения на установку, рабочий firewall/V2Ray/систему не меняем. Следующий обсуждаемый этап — проверяемый security backend и доказательство в изолированной Windows-лаборатории.

**Повторная архитектурная сверка / 2026-10-20 / WEB_11:** подтверждено разделение двух независимых направлений (Ultra → model provider и ChatGPT → Ultra tools). Уточнены ещё две независимые оси: *мультимодельность ≠ мультимодальность* (документ 11, ASR из 12 пока FUTURE) и *MCP transport / reachability ≠ OS-level egress/V2Ray* (документ 19, §7.2). Нужны три разные группы доказательств: официальный ChatGPT→MCP read-only E2E, достижимость/auth и изолированные сетевые negative tests. Этот аудит — только документационная корректировка; capability, install, tunnel и production gates **не изменены**, Blueprint LLM не утверждался и не редактировался.

---

