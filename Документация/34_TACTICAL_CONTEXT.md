# Оперативная память проекта — №34

## CURRENT WEB26 / 08.11.2026 — USER H26 approval: 3-layer pre-send and continuation budget protection (design only)

**Owner decision / explicit «Конечно» + «Да, фиксиру» after spoken discussion:** Adopt the **principle** of three complementary safety gates for Ultra LLM execution; this is an architectural H26 policy decision, **not yet code, S3b acceptance, numeric budget approval, paid/live authorization or a new Codex TASK**.

1. **Before every physical LLM/API request**, trusted Ultra Server identifies the actual route (Ordinary Chat versus agent RUN/Planner/Executor/Dredd/MCP), approved model/provider profile, final immutable input bytes and their conservatively accounted token cost, existing durable usage/liability plus all RESERVED/SENT/UNKNOWN obligations, intended maximal generation including reasoning if billable, and suitable attempt/retry ceiling. It makes a **durable pre-send reservation / DENY** under both session and shared Workspace ceilings and applicable global controls. No bypass for repeated calls or next chat; no automatic grant/reset. Estimated counts without a trustworthy upper bound are insufficient for hard guarantee.
2. **Provider/engine-side bounded generation**, to the extent positively supported by the **actual selected model, endpoint, API version and serializer**: set and record effective output-token cap and, where available, explicit reasoning-token/thinking budget and request time/attempt controls; validate whether these settings jointly bound **all charged generated tokens** rather than only visible final text. For GigaChat Ultra, claimed `reasoning_max_tokens` (API v1), `model_options.reasoning.max_tokens` (v2) and `max_tokens` must be independently checked against the exact supported interface and billing semantics; a merely documented field is not proof of compatibility, enforcement, or interruption mid-request. Do not promise an absolute hard ceiling where no verified enforceable total-cost bound exists.
3. **Before every actual tool invocation and before each subsequent LLM call**, the trusted Server verifies permission, current RUN/Turn state and remaining authorized budget; on denied continuation, no tool action or next request is executed. Denial of next action is reliable within Ultra's authority; killing already-running remote inference, stopping billing instantly on closed HTTP, or resuming without possible charged UNKNOWN are **not** guaranteed. Tool checks never substitute for pre-provider-send checks. Agent RUN may require mandatory audits/verification unaffected by these gates.

**User idea: two thresholds.** Distinguish configurable *soft alert/nominal allowance* (e.g. 300,000 cumulative tokens in a session) and *absolute hard admission ceiling* (e.g. 350,000 with a discretionary 50,000 emergency headroom). These numbers are **illustrative only / not U2 approved defaults**. Reaching soft threshold triggers warning / explicit owner policy for headroom, while the pre-send ceiling only permits a new attempt if existing accounted/pending charges + conservative upper-bound **input + all output/reasoning + retries as relevant** fit inside the hard ceiling. If 250,000 already spent and an attempt's maximum cost is 99,000 then at most 349,000, but 101,000 must be rejected; the guard is evaluated **before** the attempt and atomically shared where required. Unknown outcome stays held; incomplete provider usage cannot prove a free call. If the backend cannot supply a reliable total-token cap, the server must use a separately validated conservative bound or refuse the unsafe request; a timer/cancellation is at best a secondary mitigation.

**Route-specific implications:** Paid remote API needs strict pre-send monetary/token protection. Local models still need max context, generation, memory/CPU/GPU resource and timeout protections: free tokens do not mean unbounded safe resource use. Keep separate (a) current next-request context size, (b) cumulative charged tokens, and (c) persisted Workspace history and compact memory; these are not interchangeable. Reuse Ultra's existing post-run Planner/Executor/Dredd metering after auditing actual code; reported usage alone does not constitute enforcement.

**Status:** H26 U2 A/B/C remains DEFERRED pending matched calibration, U3 precise profile corpus/rules still OPEN, U4–U6 OPEN. The three-layer safety **principle** is USER-APPROVED; concrete GigaChat Ultra capabilities, bound arithmetic, telemetry and implementation require separate proof and independent tests. S3b/Stage6, paid/live and real provider requests **HOLD**.

## CURRENT WEB26 / 08.11.2026 — owner decision H26 U2: numeric A/B/C deferred pending model-specific rule and calibration

**Confirmed owner choice, H26 U2 (reply «Ну да» to explicit A/B/C deferral question):** **Do not approve or activate A/B/C nominal Ordinary Chat budgets (A L80k, B L120k, C L240k) yet**. First define separate, configurable and safely enforced policy dimensions for (a) model-specific actual next-request context fit (including Workspace selected memory, system/template overhead and output reserve), (b) request/attempt output/input and repeat bounds, and (c) durable session and aggregate Workspace spending liability; then calibrate numerical thresholds against matched model/provider/ordinary-chat observations and owner approval. A large supported model context must not be silently conflated with a small arbitrary input estimate ceiling; no data storage/token budget conflation. The historical proposal A/B/C stays as unapproved comparison only. CHAT-A01 (shared workspace spending ceiling, not chat-history storage ceiling) remains agreed as previously scoped; owner has not selected new absolute values or reset rules. **U3–U6 still unresolved.** Ordinary sample count remains zero; S3b/Stage6/paid/live HOLD. This is a documented decision, not a new Codex TASK or engineering GO.

## CURRENT WEB26 / 08.11.2026 — OWNER-APPROVED FUTURE DIRECTION: LLM STATIST / empirical context-capability telemetry

**User decision (08.11.2026):** Mandatory future development direction, **not merely a suggestion**: build a reusable *LLM Statist* capability in the existing Ultra core, available to future Web Alarm Ultra and Blueprint LLM blocks. Its purpose is to measure how a specific LLM/provider/configuration actually performs as active context increases, distinguish the manufacturer's advertised context window from the observed practically usable window, and support informed user-adjustable working limits. Owner's motivating example: advertised 250k context, but response/work initiation becomes unacceptably slow around 150k; these are illustrative values, **not verified measurements or a default policy**.

**Required future observability contract (design pending):** Record per model ID + provider/endpoint + tokenizer/template/profile + model build/quantization + hardware/resources + relevant runtime settings: estimated/actual request-context tokens, input/output token usage, time queued, request start, time to first token/first meaningful response or work start, total completion latency, generation rate, timeout/error/abort, concurrency/load, context composition and effective output reserve. Distinguish server-side response time from app-side queue and orchestration. Reuse existing Ultra accounting/Run Store/events where technically confirmed, without second accounting core or dependence on legacy UI. Persistent versioned samples with stable identifiers allow per-model/context-size trends, percentiles, distributions and uncertainty labels; avoid falsely attributing slowness to context when hardware load or network/provider service differs.

**LLM Statist design choice remains OPEN:** First establish passive, minimally invasive deterministic telemetry and analysis; a later optional dedicated LLM 'statistician' or Blueprint block may interpret aggregated data, identify bottlenecks and suggest changes, but is not the authoritative source of token counts, timings or safety enforcement. No automatic paid experimentation, no unsanctioned real-model calls, no synthetic inference presented as empirical observation. Protect privacy: collect performance metadata without RAW message bodies by default; storage, consent, retention/access and tests must be specified before implementation. Model working cap should remain visible and user-configurable, subject to documented provider/runtime hard bounds and the independent budget guard.

**Separate concerns / order:** (1) Model context-window hard/working fit for the *next* request; (2) Ordinary Chat durable per-session and aggregate Workspace token-spend budget; (3) global/execution route limits; (4) empirical responsiveness/statist per LLM. Asking an LLM to be concise is advisory only, never a spending safety boundary. Enforce hard quotas pre-physical-send via separately accepted S2/S3a/S3b gates. Future Blueprint Statist and context-compression blocks follow stable provider connectivity and the approved implementation roadmap. H26 U2–U6 numeric choices, S3b and live/paid remain unapproved/HOLD. **This entry records a firm future requirement, not permission to start implementation or change the existing code.**

## CURRENT WEB26 / 08.11.2026 — existing Ultra token accounting shown in owner GUI screenshots

**OWNER DEMONSTRATION / UI OBSERVATION:** The existing Ultra legacy interface already shows per-role token statistics in its execution-inspection panel: `PLANNER`, `EXECUTOR`, `DREDD`, `TOTAL`, with detailed execution events/logging and context/answer views. In one screenshot the displayed example is Planner **7,367**, Executor **23,671**, Dredd **8,511**, Total **39,549** tokens (role sum matches total). These are example observed spent-token counters for a past agent run, **not** Ordinary Chat real consumption data, model context-window size, a provider quota, or proof of pre-send budget denial. The visible `tools limit 20` is a tool-count setting, not a token quota.

**DECISION / NEXT:** Reuse the existing Ultra core accounting/event evidence where compatible, rather than rebuild a separate role-token telemetry engine. Map future Ordinary Chat UI accounting and model/profile context-window reporting separately; source-code audit must establish exact reusable APIs and persistence semantics. H26 U1 concerns a typed Ordinary budget route and attribution, while S2/S3a/S3b will additionally need reliable *pre-physical-send admission and durable quota enforcement*, not merely end-of-run statistics. CHAT-A01 aggregate Workspace envelope and U2–U6 remain OPEN; S3b/paid/live HOLD. Legacy GUI shown solely as historical evidence; do not reopen its development. No runtime/code/GUI changes authorized by this note.

## CURRENT WEB26 / 08.11.2026 — owner clarification: web-only UI; Ordinary budget vs model context

**USER UI DECISION:** Legacy desktop GUI is frozen/untouched, remains as-is, and is excluded from future planning/discussion unless the owner explicitly reopens it. All new UI development targets Web Alarm Ultra. Preserve the existing Ultra core; no second engine. This does not authorize removal/refactoring of legacy code.

**ORDINARY CHAT U1 — conceptual agreement, contract details still open:** A chat owns its own conversation history/context accounting. The *content sent to a model* is not the same as *cumulative token spending/liability*. U1 concerns distinct trusted `ordinary_chat` route/scope/accounting in the same Ultra core, segregated from RUN/MCP/Compressor execution budgets. Agent requests that read chat material are charged to the actual executing route, not silently to Ordinary Chat; cross-route authorization and attribution require an explicit future contract. Existing CHAT-A01 remains: Ordinary Workspace aggregate session-equivalent ceiling shared by all its chats, not a fresh token-wallet on each chat creation. Owner expressed conceptual agreement with a separate ordinary-chat budget but asked what U1 means; don't falsely mark the full technical U1 route/scope/owner contract formally approved. A/B/C absolute limits, calibration, U2–U6 and implementation remain OPEN.

**CONTEXT DESIGN NOTE / FUTURE, not H26 budget policy:** Model profile should expose supported context-window and configurable working cap; before model switch compare estimated actual next-request context + system/tool/template overhead + output reserve against effective model window. Prefer optional, explicit, reviewed compression using existing Ultra core facilities where confirmed. Preserve original messages/ID-linked archive and offer recovery; do not silently irreversibly compress, nor equate historical spend with current prompt size. Blueprint compression/context blocks are later work. Prioritize provider integrations (GigaChat and local models) after required safety gates; S3b/live/paid remain HOLD. No code/GUI changes authorized by this note.

## CURRENT WEB26 / 08.11.2026 — H26 POLICY PACKET INDEPENDENT BOUNDED PASS; U1–U6 WAIT USER; S3b HOLD

**User #551 `7eea28e24a51` / Codex H26 `CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001`:** packet for Ordinary Chat route/scope/session and A/B/C provisional budget envelopes published; Codex finish ROTATED/readback, B1 WAITING, B1.1 H26. WEB26 independently checked authored document and direct S2 code, arithmetic: A 64KiB/16k+1024/L80k/N12 (max full UNKNOWN 4), B 128KiB/32k+2048/L120k/N16 (3), C 256KiB/64k+4096/L240k/N24 (3); **PASS / DOCUMENT-AND-SOURCE ONLY**, no code or test changes. **All A/B/C UNCALIBRATED / NOT ACTIVE; Ordinary samples 0.** CHAT-A01 equality of Workspace/session quota is recorded by Codex as author-saved user amendment (original other-chat turn not independently fetched); numerical approval is absent. **OPEN U1–U6** (distinct route and owner, A/B/C choice, calibrate+DENY, immutable carry/no reset, RAW data limits, fresh single-owner synthetic rollout). **S3b/S3c/S9/Stage6/paid/live HOLD**. S1/S2/S3a previous bounded PASS remain. Review `reports/CHATGPT-WEB26-CODEX-RT002-ORDINARY-POLICY-REVIEW-20261108/review.md`. Next: ask user policy decisions before next assigned code TASK; separate versioned S2/S3a hierarchical-budget contract before S3b. No manual script or Desktop Commander changes.

## HISTORICAL WEB26 / 08.11.2026 — S3a independent GitHub BOUNDED PASS, NEXT policy decisions

WEB26 independently accepted S3a in BOUNDED OFFLINE EXECUTION scope on [GitHub Actions run 42498405794](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42498405794), HEAD `3635c79a1378`: **35/35 S3a PASS, 51/51 Run Store PASS, 3 mutant oracles expected RED (2/1/9 FAIL), 6/6 guard probes PASS**, no FAIL/ERROR/SKIP in positive suites, no actual provider calls, no live Workspace writes. Exact H23 LF source pins matched after CRLF-only normalization for GitHub Windows checkout. **S3a test predecessor CLOSED**; S3b/paid/live remains HOLD. OPEN: Ordinary Chat policy choices (scope/routes, numeric limits, calibration), RAW wire retention/privacy, historical audit adoption, storage durability/fencing/clone ownership, dynamic physical-send inventory. Report `reports/CHATGPT-WEB26-RT002-S3A-REVIEW-20261108/review.md`; CI artifact 13623893337 expires 2026-11-22. GitHub-first verification, Desktop Commander exceptional only.

**PROCESS NOTE:** CI setup commits №546–549 were intermediate patch commits for one deliverable, contrary to DOC-COMMIT-01; do not rewrite history. One atomic commit for this review. Codex B1 WAITING/B1.1 H25. No new S3b, paid, Colibri or Blueprint task authorized.

## HISTORICAL WEB26 / 08.11.2026 — H25 S2 bounded independent PASS, S3a OPEN, S3b HOLD

H25 user main №544 `f52363a1bd15`, Codex `CODEX-RT002-B2-S2-ISOLATION-ORACLE-REPAIR-001` / `H-CODEX-000025` finished ROTATED, БЛОК 1 WAITING, 1.1 H25. WEB26 независимо на Windows Python 3.12.10 проверил S2 **73/73 PASS**, quality **47/47 PASS**, weakening expected RED **43/1/1 FAIL**, S1 **69/69 PASS**, 0 isolation; source SHA matched publication. **H25 S2 BOUNDED INDEPENDENT OFFLINE PASS; DOC ITERATION CLOSED.** Авторские S1-extra23 и S3a35 не повторялись; independent S3a NOT RUN; full CI/live NOT RUN. **OPEN:** S3a independent, Ordinary Chat policy/numeric user decisions, ledger adoption/fencing/RAW and S3b dynamic physical sends. **Stage6/7/paid/live HOLD**. Review `reports/CHATGPT-WEB26-CODEX-RT002-S2-REVIEW-20261108/review.md`; runs `reports/CHATGPT-WEB26-CODEX-RT002-S2-REVIEW-20261108/independent_runs.json`. Codex 007 WAITING, №001/05/06/20/21/37/40 updated only after review; STANDARD/TEST, Blueprint, Ultra LLM and external MCP rights unchanged. Future S3a acceptance and new S3b implementation require separate USER GO; no paid/live.

## HISTORICAL WEB25 / 08.11.2026 — H24 S1 INDEPENDENT OFFLINE PASS, S2 1 FAIL, S3b HOLD

**CURRENT WEB25 / 08.11.2026 / H-CODEX-000024 S1:** main №542 `a455d97f`. Independent Windows guarded S1 **69/69 PASS** and extra reconciliation **23/23 PASS** (18 mutations), exit0/guard0; author 3 weakening RED (reviewer did not rerun). Independent guarded S2 **72/73 FAIL** on isolation oracle treating standalone S3a ledger importing pure policy as production import; separate narrow scope required. S3a independent runtime 35 NOT RUN (author 35 PASS). **S1 bounded accepted; H24 overall PARTIAL; Stage6 S3b/Stage7/paid/live HOLD**. Review `reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/review.md`; OPEN S2-OFFLINE-LEDGER-ISOLATION-ORACLE, S3A-INDEPENDENT-EXECUTION, Ordinary Chat policy/adoption/privacy, dynamic S3b coverage.

 **Execution proof:** authorized Windows Desktop Commander, Python 3.12.10, source SHA `35426388`, exact S1 guard 69 PASS exit0, extra 23 PASS exit0, exact S2 guard 72 PASS/1 FAIL exit1. Independent runs JSON `reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/independent_runs.json`; no live provider or paid calls. **Codex:** H-CODEX-000024 `CODEX-RT002-B2-S1-INVENTORY-RECON-001`, finish ROTATED, B1 WAITING, B1.1 H24; task documentally partial closeout. User #542 `.obsidian/workspace.json` incidental and not touched. **NEXT (needs separate USER GO):** narrow S2 isolation-oracle test repair with positive/negative proof; independent S3a 35-test runtime; Ordinary Chat route/profile decisions before S3b. Older H23 snapshot below is historical. Stage5 remaining browser risks unchanged.

## HISTORICAL WEB25 / 08.11.2026 — H23 S3a OFFLINE PARTIAL (superseded by H24)

**CURRENT / WEB25 / 08.11.2026 / S3a H-CODEX-000023:** №539 `53d7ce91` опубликовал отдельный OFFLINE durable ledger (`ultra_budget_ledger.py`) и 35 tests. Author S3a 35 PASS, Run Store 51 PASS, S2 73 PASS, mutation negative 3/3 expected red; S1 **67 PASS / 2 FAIL** (source inventory for Web Alarm launcher, ordinary transport, model cards). WEB25 `PARTIAL / BOUNDED SOURCE+AUTHOR EVIDENCE`, exact 16 focused SHA checks, independent Python/CI **NOT RUN**. Это не обязательная `independently ACCEPTED S3a` для S3b и не Stage6 DONE. S1 reconcile, user Ordinary Chat policy decision, historical ledger adoption, RAW wire retention, durability/fencing и full runtime OPEN. Подробнее №21/№05, review `reports/CHATGPT-WEB25-CODEX-RT002-S3A-REVIEW-20261108/review.md`. S3b/paid/live запрещены до отдельных gates.

 **Слот Codex:** БЛОК 1 WAITING, БЛОК 1.1 H-CODEX-000023 (finish ROTATED exit0). SOURCE: две новые рабочие Python files, `.obsidian/workspace.json` динамический пользовательский tracking file в №539 — не инженерное изменение, не править. Непроверенное: hardware power-loss, cross-host cloned Workspace, full independent S3a Windows/runtime, migration старого audit, ещё нет production S3b/S9. **NEXT SAFE:** пользователь отдельно разрешает адресный S1 inventory AMENDMENT либо отдельную проверку S3a; не запускать их автоматически. Stage5 остатки сохраняются, настоящий GigaChat, paid/Colibri/MCP HOLD.

## CURRENT WEB25 / 08.11.2026 — Stage5 OFFLINE BOUNDED USER SMOKE CLOSED

**WEB25 / USER GUI 08.11.2026 — Stage5 OFFLINE завершён документально, BOUNDED ACCEPTED.** H21 диагностика PARTIAL; H22 (№536) PARTIAL / bounded source+author evidence, author 52 JS/63 web Python/2 отдельные Tk PASS; WEB25 проверил опубликованные исходники/hash, независимый повтор runtime NOT RUN. Пользователь: fake response «Ответ на: привет тест», Turn check с явным результатом, Enter, два изолированных Chat «01» и «02», F5 сохранил выбор и историю. Не проверены целиком cancel/retry/models, 480px/a11y, clean Windows, Tcl combined; историческая отмена/RAW причина OPEN. Review `reports/CHATGPT-WEB25-S5-CLOSEOUT-20261108/review.md`. NEXT №37 Stage6 RT-002/B2 отдельная TASK; Stage7 OAuth/live только отдельно.

**OPEN:** `FOLLOWUP-WUA-S5-FINAL-BROWSER-001` PARTIAL (cancel/retry/models/a11y); историческая RAW loss после F5, 480px, Tcl combined process, clean Windows §2.4 и writer-busy остаются. FUTURE per-message Turn check `FOLLOWUP-WUA-S5-TURN-PER-MESSAGE-UX-001` NON-BLOCKING; Turn check проверяет исход запроса, а не membership RAW в контексте LLM. Obsidian `.obsidian/workspace.json` не изменять. Codex БЛОК 1 WAITING, 1.1 H22. Два фиксированных CMD `Start_WebAlarm_Standard.cmd` и `Start_WebAlarm_Test.cmd`; TEST — disposable fixture, не реальный Workspace picker. Stage6 new assignment USER GO, Stage7/live/paid HOLD.

## CROSS-PROJECT HANDOFF 08.11.2026 — Ultra LLM Manager для будущего Blueprint (INTEGRATION DESIGN ONLY)

**Источник:** владелец в чате Colibri Ultra 4 (08.11.2026) требует, чтобы будущая Web Alarm Ultra могла выбирать локальные/серверные LLM, видеть не просто наличие endpoint, а реальную способность запуска с учётом RAM/VRAM, пользователей, игр DayZ/Valheim и контроля доступа. **Это документирование границы двух проектов, НЕ разрешение на Web Alarm provider calls, Stage7/GigaChat/Colibri, сетевые изменения, paid/live или новую TASK.** Текущие Web Alarm Stage6 B2/S3a HOLD и чужие OPEN остаются без изменений.

**Ответственность:** Ultra LLM Manager / Core владеет machine/model/instance registry, adapter к Colibri (позже другие), модельными RAM min/max и evidence, host policy, atomic capacity reservation, живым server-side process ownership, health/status, machine reason codes и audit событий. Web Alarm Ultra владеет Blueprint orchestrator, Turn/RUN, контекстом, промптами, memory, MCP tools, разрешениями бизнес-действий и checkpoint. MCP может дать инструменты поиска/резерва, но inference идёт отдельным OpenAI-совместимым API. Web Alarm не получает автоматическое право STOP чужой LLM.

**Ресурсы:** по прямой оценке владельца начальный provisional бюджет 10 GiB на MoE LLM; для KAT и Qwen3.6 исходный диапазон owner hypothesis 5–10 GiB, measured peak UNKNOWN. Не считать это физически измеренным RAM cap. Для сервера ~48 GiB условно резервируем 20 GiB под игровые/системные службы и ещё ≥10 GiB свободной RAM после нового размещения; таким образом консервативный модельный конверт 18 GiB (один, а не два 10GiB claims). Разделение policy и actual telemetry обязательно. Если запуска четырёх Blueprint LLM невозможно обеспечить, Core отказывает до side effects с кодом INSUFFICIENT_RESOURCES, дефицитом и допустимыми вариантами; чужие LLM без подтверждения не останавливать. Нужны атомарные групповые заявки для Blueprint и отказ при stale telemetry.

**Факт по Ultra LLM:** в SMB \\192.168.0.77\Server\Ultra_LLM\Colibri\manager_dev/ у ChatGPT создан offline/mock prototype UL-MGR-0A+0B (resource_catalog, dynamic registry, Colibri fake-adapter/owner isolation, RU default/EN UI); 78/78 Python unit PASS на домашнем агенте DESKTOP-SC96D3U. Это NOT VERIFIED на сервере: real START/STOP, 2×CPU, 3×CUDA, LAN, measured RAM/VRAM и integration Web Alarm API NOT RUN. Истина Ultra LLM: Documents/13_Тактический_контекст.md → «ТЕКУЩИЙ РЕЗУЛЬТАТ», №06 → DEC-UL-MGR-RAM-RANGE-20261108-001, №09 → CHATGPT-UL-MGR-0B-20261108-001. Локальная Colibri на пользовательском ПК DEFERRED. После безопасной серверной приёмки и собственного Web Alarm USER GO согласовать только версионированный Core/API contract, auth/capabilities/lease/error semantics и test harness с fake response, не создавать второй engine runtime.

**Сохранение:** эта запись добавлена в локальную рабочую копию №34 на M:\GitHub\ag_llm, не доказывает публикацию в GitHub/GPT/main; Web Alarm commit-gate №08/DOC-COMMIT-01 остаётся отдельным OPEN и не обходится.

## OWNER DIRECTION 08.11.2026 — Web Alarm Ultra, локальные LLM и агентная перспектива (NO NEW TASK)

**Окончательная роль, исправленная владельцем:** **Web Alarm Ultra** управляет агентами и Blueprint-процессами: формирует промпты/контексты, выбирает исполнителей и разрешённые MCP-инструменты, сохраняет память и промежуточные checkpoint, контролирует Turn/RUN, проверяет результаты и отвечает за восстановление. **Colibrì** — движок локального инференса/API, не главный координатор и не постоянная память агента. **Ultra LLM** — отдельная серверная инфраструктура моделей/профилей/запуска/диагностики; не создавать в нём второе агентное ядро.

**Наблюдаемая работа моделей:** KAT-Coder V2.5 Dev и Qwen3.6 действительно запускались и отвечали в Colibrì на домашней машине. KAT показала хорошее понимание русского и короткие ответы (~22–25 tok/s по интерфейсу), но при длительном C++-запросе перестала отвечать; Colibrì вручную перезапустили, корневая причина неизвестна. Qwen3.6 завершила синтетический C++17 LRUCache; итоговый код проверен отдельно, ~15 tok/s по предварительному сообщению владельца. Сообщения о пиках KAT ~120 tok/s в reasoning и большом количестве символов рассуждений Qwen — предварительные наблюдения, не измеренный sustained throughput. Реальные tool calls, длинные агентные циклы, устойчивость и одновременная работа моделей ещё НЕ ПРОВЕРЕНЫ. Качество важнее мгновенной скорости, пока виден прогресс.

**Проект будущего исполнения:** Web Alarm Ultra выдаёт небольшие проверяемые этапы, сохраняет результат/checkpoint и внешний контекст между вызовами, проверяет разрешения на инструмент и side effects. Монитор различает долгий prefill/reasoning с новыми токенами, ожидание инструмента, сетевой/UI-обрыв, API health и фактическое отсутствие прогресса; не убивать здоровую модель только по таймеру. При отказе — ограниченный recovery и безопасное продолжение с последней подтверждённой точки, без слепого повтора действий. Это использует опыт сохранения этапов при прежних обрывах Remote/Desktop, НО внешний ChatGPT Desktop ↔ MCP/Tunnel/V2Ray из №39/44 остаётся FROZEN. Внутренние будущие MCP-tools Web Alarm Ultra — другой контур.

**Несколько моделей:** сервер 48 ГБ RAM / RTX 3070 8 ГБ VRAM, возможны одновременно DayZ/Valheim. Исследовать отдельно доступность двух моделей (например, KAT CPU/RAM и Qwen CUDA/RAM), независимые порты, лимиты RAM/VRAM/KV-cache, CPU/GPU очередь, маленькие специализированные LLM; одновременная работа пока НЕ ДОКАЗАНА. DDR4/DDR5 и XMP не считать подтверждённой причиной различий скорости без сопоставимого эксперимента.

**Порядок владельца:** сначала завершить текущую Web Alarm Ultra и интеграцию исходной Ultra / UI по принятому №37; затем по отдельным разрешениям реальные и локальные LLM; после этого подключить Codex как ещё одного агента/adapter; только затем — практические мультиагентные опыты и развитие Blueprint по №43. Текущий Codex как разработчик Web Alarm не равен будущему Codex-provider. Сохранить Stage5/Stage6, B2, TEST/Standard, платные/live и MCP gates. **Сегодня лишь документирован замысел: NO ENGINEERING GO / NO NEW TASK / NO LIVE OR SERVER CHANGES.** NEXT — существующие OPEN №05 и актуальный №37, а не немедленные эксперименты с LLM.

## CURRENT WEB25 / USER GO 07.11.2026 — постоянный STANDARD/TEST и TEST smoke

Решение пользователя: две постоянные пользовательские точки Web Alarm Ultra — `Start_WebAlarm_Standard.cmd` и `Start_WebAlarm_Test.cmd`; на будущих этапах изменяется внутренний TEST-профиль, не CMD/ярлыки. USER Windows GUI smoke: STANDARD открыл историю Workspace на localhost:8765, одновременно TEST Stage5 OFFLINE показал пустой тестовый профиль на localhost:51238. Это не доказательство полного разъединения storage/cleanup и не финальный браузерный PASS. `Start_WebAlarm.bat` пуст в опубликованном №531 (`main@740ec44`); локальное обнуление предшествовало новым CMD, автор/причина UNKNOWN, новые CMD его не используют, восстанавливать третью точку не требуется. `Start_WebAlarm_Demo.cmd` — прежний отдельный синтетический WA4-O fixture, удаление только после проверки зависимостей; `Start_Ultra.cmd` — сохранённый отдельный Tkinter, freeze. В №531 в main также попали восемь посторонних отслеживаемых файлов (пять непустых `Test_Chat_02/.ultra` данных, два writer.lock и `dir`); **OPEN REPOSITORY HYGIENE / PRIVACY**, ничего не удалять и не читать переписки ради изменения правил.

**Исторический NEXT 07.11:** начатый браузерный TEST частично принят 08.11; актуальные результаты и остаточные OPEN — в CURRENT WEB25 выше. Standard не трогать. Stage6 RT-002/B2 по №37 — следующая отдельная инженерная TASK; paid/live/Colibri/MCP не разрешены. Нормы №08, `DOC-WUA-LAUNCH-01`; USER smoke не закрывает `FOLLOWUP-WUA-S5-CLEAN-WINDOWS-001` или writer-busy.

## USER GO 04.11.2026 — история по ID и автоматическая сдача

**CURRENT WEB24 / 07.11.2026 — H-CODEX-000020 Stage5 FULL OFFLINE Web+Tk BOUNDED PASS → №37 Stage6 B2 NEXT:** author numbered №523 `main@4f155ca`, manifest 83/83 SHA+UTF8 bytes (62 exact/21 LF normalized), finish ROTATED/exit0, Codex B1 WAITING/B1.1 H20. Independent Windows [42286738432](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42286738432) **SUCCESS 387 PASS**, 209 core Python (S5 Tk+HTTP13, history43, S4A/B58, Stage3 30, RAW14, RunStore51), 3 reviewer boundary, 10 final HTTP-disconnect repeats, 165 JS. S5 synthetic UI→Turn→S4 fake→RAW/Run Store works in Web and Tk; 0 provider/OAuth calls; credentials/network negative guard passed. Prior failed reviewer CI runs 42284763742/42285072025/42285502197/42285819723/42286331719 were harness-only and retained; multiple correction commits №524–529 are **PROCESS NONCONFORMITY** with one task/commit user rule; no history rewrite, validate harness before any next publication. **Stage5 accepted BOUNDED only**; actual Chromium final-source visual smoke after last HTTP/model-picker change NOT RUN; clean Windows portability §2.4 NOT RUN; `FOLLOWUP-WUA-S5-FINAL-BROWSER-001` and `FOLLOWUP-WUA-S5-CLEAN-WINDOWS-001` OPEN; historical `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001` OPEN. `FOLLOWUP-WUA-S4B-STAGE5-UI-001` CLOSED bounded. User personal 595 files + launcher STANDARD author-only checks. Report `reports/CHATGPT-WEB24-CODEX-S5-REVIEW-20261107/review.md`, event `EVT-WEB24-CODEX-S5-REVIEW-20261107`. **NEXT:** strictly №37 Stage6 RT-002/B2 agreed policy+durable ledger and real-send fail-closed gate coordinated with №20 §5а; no paid/live/Colibri or Blueprint work. Stage7 genuine GigaChat requires new USER GO and accepted 5–6; Colibri only after entire №37 completed and accepted.

**Обязательный вход и сопровождение:** новый обычный координатор читает текущую часть этого №34 целиком, короткие №001 Codex/Claude/Ultra Desktop (до десяти строк в каждом) и все OPEN/FOLLOWUP №05. Цель — восстановить, что строим и зачем, достигнутую точку, последние результаты и NEXT без повторного объяснения пользователем. Координатор обновляет №34 после значимого решения/результата/изменения OPEN или NEXT и перед передачей чата; сохраняет цели, участников, решения и ограничения, ID результатов и конкретный следующий шаг. Полные постановки и отчёты остаются по ID. Исполнитель до `finish` сохраняет известное незавершённое в отчёте; веб после независимой проверки актуализирует FOLLOWUP, не меняя освобождённый слот. Изолированный INDEPENDENT_PLAN сохраняет прежнее исключение.

Веб-планировщик ведёт документацию по общему №000 и новой редакции №18. `finish` сохраняет дословную постановку, создаёт/переиспользует HISTORY ID и `reports/<TASK-ID>/task_record.json`, проверяет сохранность, затем освобождает БЛОК 1. Новая строка БЛОКА 1.1 и протокол содержат ID/адрес. Запускает исполнитель после итогового пакета либо пользователь через программу; веб без Python поручает запуск, не имитирует его. Авторская сдача не означает independent PASS. Проверяющий читает запись по ID, добавляет свой verdict, обновляет короткие №001/05, событие №06 и текущие OPEN/NEXT здесь. №001 показывает последние десять названий, полные источники сохранены отдельно. Все FOLLOWUP остаются до доказанного закрытия; старые архивы не являются стартовым контекстом. Пакет внедрения: `reports/CODEX-TASK-HISTORY-ID-001/`; локальная проверка не доказывает публикацию/независимую приёмку.

**Срез 04.11.2026 / WEB23 — актуальный результат:** Run Store prerequisite repair `CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001` / `H-CODEX-000012`, опубликован `main@e3253b41502ac2d76c61c0faf7a5b660e2cc7eb9`. WEB23: **PASS / BOUNDED SOURCE+AUTHOR-EVIDENCE** для path-safety, same-RUN writer и explicit recovery; independently executed Windows/CI **NOT RUN**. Автор 389 PASS/5 SKIP, начальный WinError 10053 на picker сохранён, затем targeted/full repeat зелёный. Git опубликовал один test file с одиночным CRLF→LF, строгий SHA этого файла отличается от author manifest, содержимое теста эквивалентно. Author finish ROTATED/exit0, БЛОК 1 Codex WAITING, 1.1 H-CODEX-000012; Claude SLOT HOLD из-за NO_TASK_ID не трогали. `FOLLOWUP-WUA-P9-AUDIT-PATH-001` и `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001` закрыты только в bounded evidence scope; independent P9 runtime, UX picker, Stage3 Turn, Tk/staging/portability сохраняются OPEN. **NEXT:** независимо перепроверить критические Run Store оракулы на pinned Windows/CI, затем отдельно согласовать с пользователем новую Stage3 TASK; до этого Stage3 и paid/live/Colibri/Blueprint/MCP HOLD. Документальный closeout готовится только в ветке GPT, USER MERGE PENDING; review `reports/CHATGPT-WEB23-CODEX-RUNSTORE-S3-GATE-REVIEW-20261104/review.md`.

**Исторический срез 04.11.2026 / WEB22:** Codex Stage3 diagnostic, published main@5088d307defdf3b6b92d4f119c45fc29863a6bb5: 2 unsafe Run Store prerequisites, audit junction external write and concurrent same-RUN sequence [1,1]. Stage3 Turn/HTTP/mock/TEST UI NOT IMPLEMENTED; author 1 PASS/2 intentional RED FAIL, JS 158 PASS, Python 166 PASS/5 SKIP, P9 21 PASS; verifier independently inspected GitHub source, test and raw author evidence; independently executed Windows/CI NOT RUN. Script receipt ROTATED exit0; B1 WAITING, B1.1 exact 383-line Stage3 TASK, earlier UX snapshot archived. Stage3 remains BLOCKED; next separately USER GO for Run Store repair. Stage4+, Colibri, Blueprint execution, paid/live and Desktop MCP remain not authorised. №05 REG-WEB22-CODEX-S3-PREREQ-20261104, №06 EVT-WEB22-CODEX-S3-PREREQ-20261104, review reports/CHATGPT-WEB22-CODEX-S3-PREREQ-REVIEW-20261104/review.md. Документационная итерация закрыта в GPT, user merge pending; legacy OPEN других направлений не снимались.

**Предыдущий срез:** 04.11.2026 / WEB22: `CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01, source main@2e57cf2d2e59e225ab7c0d5aa7fd7097d15039ef (№501; проверенная публикация; технический пакет до документационного коммита): WEB22 **PASS / BOUNDED SOURCE + AUTHOR EVIDENCE**, пользователь подтвердил в Windows создание первого и следующих чатов (`USER GUI ACCEPTED` для happy path). Author 158 JS PASS, Python 166 PASS / 5 SKIP; verifier independent runtime/CI/negative Windows NOT RUN. First Chat из безопасного `missing_history` только после подтверждения через общее ядро; чтение/регистрация не инициализируют storage. Codex штатно сдал `finish --chat-amendment` ROTATED/exit0, БЛОК1 WAITING, 1.1 точная TASK + 1 amendment. OPEN `FOLLOWUP-WUA-CHAT-UX-INDEP-RUNTIME-001`, `FOLLOWUP-WUA-CHAT-UX-CRASH-001`, `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001`, прежние UI GUI/independent, P9/audit/Tk/staging. Stage3/LLM send/paid/live/MCP HOLD. №05 `REG-WEB22-CODEX-UX-LIVE-FIX-20261104`, №06 `EVT-WEB22-CODEX-UX-LIVE-FIX-20261104`. Документальная дельта ожидает пользовательского GPT→main.

**Предыдущий срез:** 04.11.2026 / WEB21: пользователь опубликовал №499 `main@5ca3ed1b`, UI task `CODEX-WUA-CHAT-UI-INTEGRATION-001` независимо принята **BOUNDED SOURCE+AUTHOR EVIDENCE PASS**, verifier 13/13 SHA+bytes, author 66 JS/57 Python; verifier runtime/Windows/Tk/viewport/CI NOT RUN. Существующая форма регистрации Workspace теперь доступна из Ultra Chat; сохранение общего Chat/RAW проверено только на синтетических данных; sending disabled. Старая исследовательская TASK Codex штатно ROTATED (проверены отчёт и snapshot), последняя UI TASK штатно перенесена в БЛОК 1.1, БЛОК 1 ожидает новую задачу. №37 Stage3, Blueprint runtime и paid/live HOLD; Colibri/adapter по-прежнему OPEN. №05 `REG-WEB21-CODEX-UI-INTEGRATION-20261104`.

## WEB22 / 04.11.2026 — завершение UX-итерации Workspace/Chat

Последовательность: прямая CHAT TASK WEB21 `CODEX-WUA-CHAT-UX-LIVE-FIX-001` устранила неверный failure регистрации, `nullnullnullnull` и сбои переименования; AMENDMENT 01 добавил создание первого диалога в безопасном пустом зарегистрированном Workspace только по явному подтверждению. Пользователь после STANDARD Windows проверки подтвердил создание Workspace/первого и следующих чатов; раннее подтверждение rename/save отражено в авторском AMENDMENT. Технические источники в main №501, report `reports/CODEX-WUA-CHAT-UX-LIVE-FIX-001/amendment_01/report.md`, review `reports/CHATGPT-WEB22-CODEX-UX-LIVE-FIX-REVIEW-20261104/review.md`. Verifier ограничен source+evidence, авторские 158 JS, 166 Python PASS/5 SKIP; независимое full runtime и негативный GUI matrix NOT RUN. DOC iteration closed только в GPT до merge.

OPEN/NEXT: `FOLLOWUP-WUA-CHAT-UX-INDEP-RUNTIME-001`, `FOLLOWUP-WUA-CHAT-UX-CRASH-001`, `FOLLOWUP-WUA-CHAT-UX-PICKER-10053-001`, `FOLLOWUP-WUA-CHAT-UI-GUI-001` (частичная user GUI проверка), `FOLLOWUP-WUA-CHAT-UI-INDEP-RUNTIME-001`, прочие P9/staging/Tk/portability. Colibri/Ollama и Blueprint П1 без новой TASK, Stage3/send/live/paid HOLD. БЛОК 1 Codex WAITING; БЛОК 1.1 трогать нельзя, новые назначения только USER GO.

## Дополнение 02.11.2026 — Астра / Blueprint LLM

**Исторический срез 02.11.2026:** актуальный на тот момент отчёт Астры — `42_Астра_Архитектура блока LLM.md.md` (развёрнутый архитектурный анализ). В GitHub появился начальный редактор «Блюпринт LLM» с универсальными блоками, настройками, связями, сохранением и синтетическим предпросмотром; работа над прототипом продолжается, **независимая приёмка и реальные вызовы LLM не подтверждены**. Сегодня никаких новых задач не назначаем и архитектуру не меняем. После завершения текущей работы Астры — запросить план дальнейшей реализации по её отчёту и фактическому коду, затем согласовать исполнителей. Подробности: `Blueprint LLM - тактический контекст.md` → срез 02.11.2026.

**Актуализация Blueprint / 03.11.2026:** редактор сдан автором, пакет `CODEX-WUA-BLUEPRINT-MVP-001`, запись `BP-0001`; независимая приёмка и реальные вызовы ещё не подтверждены. По прямому поручению пользователя созданы `43_План работ по Blueprint LLM.md`, краткий индекс №43.1 и полный реестр №43.2. Порядок: план → индекс → одна нужная запись по ID; правило закреплено в №18 и общем №000. Ближайшие шаги — приёмка П0 и контракт П1, затем два блока через общий RUN на имитаторах. Инженерные задачи здесь не назначаются. Отмеченные пользователем две Wiki-связи из №34 заменены текстовыми адресами; остальные направления этой сводки не переоценивались.

## Постоянные ориентиры

- Проект `ag_llm / Web Alarm Ultra`. Локальный корень этого снимка `M:/GitHub/ag_llm`; идентификатор репозитория `maxrus82gm-svg/ag_llm`. Переносимый продукт не должен жёстко зависеть от этого пути.
- Пользователь назначает/расширяет задачи, разрешает отдельные этапы и принимает публикации. ChatGPT-координатор планирует, проверяет чужую работу и ведёт closeout. Claude 008/Codex 007 — самостоятельные инженеры в своём scope; Ultra Desktop — отдельный исполнитель, не Ultra runtime.
- Общий рабочий порядок: №18 → DOC-CONTEXT-OPS-01. Формы — №07. Полное назначение в персональной карточке либо прямом адресном поручении пользователя; ни строка NEXT, ни этот снимок не запускают работу автоматически.
- Локальным агентам Git/GitHub запрещены без явного адресного разрешения. ChatGPT использует только свои подтверждённые права; публикация/принятие GPT → main по действующему порядку. Техническая возможность не означает разрешение.
- Два постоянных CMD для Web Alarm Ultra: `Start_WebAlarm_Standard.cmd` / `Start_WebAlarm_Test.cmd`; USER GUI smoke параллельных окон подтверждён 07.11, полноценная изоляция и cleanup ещё OPEN. Старый BAT не восстанавливать автоматически; применим №08 → DOC-WUA-LAUNCH-01.

## Что сейчас делаем

| Направление | Назначение и состояние среза | Ближайший разрешённый шаг |
| --- | --- | --- |
| А — Ultra Chat / EVM, WEB21 / Claude 008 (лимиты, временно недоступен) | №479 Stage2 bounded PASS; P9 `CLAUDE-WUA-CHAT-RUNSTORE-P9-001` опубликован в main и независимо принят WEB21 **PASS / BOUNDED SOURCE+EVIDENCE**, author full 1076 PASS/2 SKIP, verifier runtime NOT RUN. БЛОК 1 P9 удержан из-за `NO_TASK_ID`; БЛОК 1.1 №479 сохранён. | DOC closeout P9 — `REG-WEB21-P9-REVIEW-20261103`; ротация только штатным скриптом после исправления TASK ID и архивного readback; `FOLLOWUP-WUA-P9-AUDIT-PATH-001` / Run writer / independent runtime / staging / Tk P1–P6 OPEN. Stage3 только после отдельного GO и gates |
| Б — исследования локальных LLM / Codex 007 | `CODEX-WUA-LOCAL-LLM-DISCOVERY-001` документально закрыта 02.11 с BOUNDED PASS / TASK PARTIAL; Colibri .77 UNKNOWN, адаптер NOT IMPLEMENTED. Проверенный архив исследования находится в `reports/CODEX-WUA-LOCAL-LLM-DISCOVERY-001/`; текущий БЛОК 1 ожидает новую TASK. | Исследовательские `FOLLOWUP-WUA-LOCAL-LLM-COLIBRI-001` и `FOLLOWUP-WUA-LOCAL-LLM-DISCOVERY-ADAPTER-001` OPEN/UNASSIGNED; не считать их выполненными новой UI-задачей. Новых реальных provider/go запросов нет |
| Ultra Chat UI / Codex 007 | `CODEX-WUA-CHAT-UI-INTEGRATION-001`: new registration shortcut and catalog reload in source №499, WEB21 bounded PASS, author 66 JS/57 Python, verifier 13/13 manifest, independent runtime/Tk/viewport NOT RUN. UI TASK штатно перенесена в БЛОК 1.1; БЛОК 1 ожидает нового назначения, прежние полные TASK сохранены в snapshots. №43 П0/П1 не перераспределены автоматом. | №05 `FOLLOWUP-WUA-CHAT-UI-GUI-001` и `FOLLOWUP-WUA-CHAT-UI-INDEP-RUNTIME-001` OPEN; Stage3 gate, audit path, RUN writer, Tk P1–P6 отдельные. Следующая TASK только после user GO |

Направление исследования локальных LLM завершило итерацию 02.11 (№05 `REG-LLM15-LOCAL-LLM-DISCOVERY-20261102`), но не внедрение. USER GO 04.11 меняет приоритет Codex на WEB21/Ultra Chat после освобождения слота. UI-задача опубликована в №499 и принята WEB21 в bounded scope; №37 Stage3 и №43 П1 этим не запускаются. №482/483 сохраняются в истории; пересечения — №40.

## Действующие пользовательские решения и границы

| Решение / граница | Что сохраняется | Адрес подробностей |
| --- | --- | --- |
| №37 утверждён 27.10.2026 | Кандидат 2 от 26.10 и portability §2.4/H24 приняты как программа; фактический перенос на чистую Windows NOT VERIFIED | `37_Старт перехода - Web Alarm Ultra.md` → статус, 2.4, 4, 6, 9 |
| Этапы Ultra Chat | Stage1 **DOC CLOSED / TERMINAL PARTIAL** по явному решению пользователя 2026-10-28; технические Stage1 gates остаются OPEN. Stage2–7 не назначаются из факта одобрения №37 | №05 → `REG-WEB16-S1-20261028`; №06 → `EVT-WEB16-S1-CLOSE-20261028`; №001 Claude → 2026-10-28 / Stage1 |
| B2 / RT-002 | Утверждённая история B2 и safety остаются; Ordinary Chat V-13 DEFERRED, paid/live и снятие Tkinter требуют своих решений | №20 → §5а; №37 → 4. Совместная работа с WA4-R и B2; RT-история адресно |
| Web Alarm authority / WA4-R | Bounded PASS отдельных проверок не закрывает всю WA4-R; WARN/GATEWAY REQUIRED/STRICT/Final Audit и опасные native/live операции без отдельного GO не разрешены | №23/24 и профильная история №25 по TASK |
| Desktop MCP / tunnel / V2Ray / WFP | FROZEN / USER HOLD; source-исследование не даёт запуск/установку/смену сетевых прав | `39_Архив ChatGPT Desktop MCP - Web Alarm Ultra - заморозка 2026-10-25.md`; архитектура №19 |
| Переносимость | Стабильные идентичности и безопасная перепривязка roots; внешние credentials и OS prerequisites подключаются заново | №37 → 2.4; №03/19/23/24 по конкретному аспекту |
| Закрытие TASK | Исполнитель сохраняет OPEN в отчёте, затем `finish` записывает HISTORY ID и переносит БЛОК 1 до независимой проверки; координатор после опубликованного review обновляет task_record/№001/05/06/34 и не меняет освобождённые слоты | №18 → DOC-TASK-CLOSEOUT-OWNER-01, DOC-CONTEXT-OPS-01 |
| История и граф | Ничего уникального не вытеснять без проверенного владельца/снимка; текстовые указатели без новых графовых связей | №18 → DOC-HISTORY-ACCESS-01, DOC-CHANGE-01; OPS-LOCATOR/OPS-BUDGET |
| EVM / карточки моделей (решение пользователя 27–31.10) | №464 inline/Ctrl-preview/reorder/Favorites и №467 независимые закреплённые окна с сохранением/восстановлением приняты пользователем. Мышь и сенсорный ввод подтверждены на Windows; авторские проверки полные в отчётах, independent full-run NOT RUN. №457 сохраняет исторический REVISE. Платный live-check и новые этапы требуют USER GO; идея FUTURE реализована в №467. | №05 → `REG-WEB17-EVM-PINS-20261031`, `REG-WEB17-EVM-DND-20261030`, `FUTURE-EVM-PINNED-COMPARE-001` (IMPLEMENTED); №06 `EVT-WEB17-EVM-PINS-ACCEPT-20261031`; №001 Claude 2026-10-31; №467 `f4597868` |

## Открытые проверки и риски

**EVM №457 FOLLOWUP:** №05 `FOLLOWUP-EVM-457-HOVER-001` и `FOLLOWUP-EVM-457-DND-001` — ACCEPTED_BY_USER 2026-10-30 через №464. Мышь и сенсорный ввод пользователь подтвердил 2026-10-31 в №467; `FOLLOWUP-EVM-457-GUI-001` и `FOLLOWUP-EVM-457-REGRESSION-001` остаются VERIFICATION_GAP OPEN только для независимых/альтернативных платформенных проверок. Идея `FUTURE-EVM-PINNED-COMPARE-001` реализована и принята через №467, не дефект №464.

| Пункт | Тип / влияние | Владелец и следующий шаг |
| --- | --- | --- |
| `FOLLOWUP-CODEX-DISCOVERY-SLOT-001` | **CLOSED / source+script evidence**: №499 опубликовал `task_slot_rotate.py` ROTATED с previous №483 guarded, B1.1 содержит точную discovery TASK, пользователь затем вставил UI TASK в B1 | Слот UI уже сдан скриптом; повторные ручные операции запрещены; UI task review №05 `REG-WEB21-CODEX-UI-INTEGRATION-20261104` |
| Stage2 / F-01 и replace hardening | F-01 №473 исправлен №475: `FOLLOWUP-WUA-S2-CONTEXT-PATH-001` CLOSED в bounded scope; `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` CLOSED по №479. Исторический REVISE №473 сохранён | WEB19 независимо выполнил focused Windows-проверки №479; full independent regression/CI NOT RUN. `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED; Run Store P9 bounded PASS по source/evidence, независимый runtime и audit-path OPEN; Tk readers P1–P6 OPEN, Stage3/live/paid HOLD |
| Stage1/EVM независимые Windows/visual/regression | VERIFICATION_GAP остаётся **OPEN**, хотя обе завершённые инженерные задачи архивированы как terminal PARTIAL; это не доказательство дефекта UI и не полный runtime PASS | ChatGPT/verifier: на отдельном разрешённом scope проверить Windows N1–N30, EVM check-window, independent regression; новые этапы/live/paid требуют USER GO. №05 REG-WEB16-S1/EVM-20261028 |
| WA4-R остаточные native/live/PWR/TOCTOU gates и P1/P2/P3 | OPEN в документах; не разрешены автоматически. Исторические gates сверять адресно с новым evidence, не считать все навечно открытыми по старому снимку | LLM15: перед действием сверить профиль №24/25, TASK и последнюю независимую запись |
| Перенос на другую Windows-машину | PORTABILITY TARGET / NOT VERIFIED; архитектурное требование отдельно от испытания | Назначить адресные portability-проверки при соответствующем этапе по решению пользователя |
| `RISK-DOC-CURRENT-001` | Риск принять старый CURRENT за нынешнее разрешение. Мера: отделены текущая картина и архивные адреса; независимая оценка остатка OPEN | ChatGPT-координатор, verifier UNASSIGNED до назначения; №05 → Оперативные риск-карточки → risk_id. Закрытие после проверки cold-start сценариев и отсутствия ложных разрешений |
| Приёмка опубликованной документационной дельты | Опубликовано; независимая полная семантическая приёмка PARTIAL/OPEN. Адресно сверены №06 S001/S004/S005/S006/S216 и соответствующие №001 для четырёх задач; **Stage1 архивирована с терминальным PARTIAL в №001 Claude 2026-10-28 (ветка GPT, до merge)**. Это не 13/13 семантический PASS | ChatGPT: проверять только оставшиеся locators и сквозные сценарии; слот Astra освобождён по USER GO 01.11, однако независимые semantic/graph/cold-start gaps OPEN; архивирование Astra по №482 не закрыло эти проверки |

Открытые запреты и проверки не исчезают из-за возраста. Полную риск-карточку хранить у №05, evidence — в отчёте/профильном журнале. Если нового риска ещё нет в нормализованном реестре, это не означает отсутствия рисков. Поля/статусы — №18 → OPS-RISK; форма — №07.

## Последние существенные результаты

**WEB21 / 03.11 / P9:** source+published evidence 26/26 verified (25 exact+один CR reconstructed), author 5/5 RED→0/5 defects, 21 focused PASS, full 1076 PASS/2 SKIP; независимый runtime NOT RUN. `FOLLOWUP-WUA-P9-AUDIT-PATH-001`, `FOLLOWUP-WUA-P9-SINGLE-RUN-WRITER-001`, `FOLLOWUP-WUA-P9-INDEPENDENT-RUNTIME-001`, `FOLLOWUP-CLAUDE-P9-SLOT-001` OPEN. №05 `REG-WEB21-P9-REVIEW-20261103`, №06 `EVT-WEB21-P9-REVIEW-20261103`, reviewer `reports/CHATGPT-WEB21-P9-REVIEW-20261103/review.md`. Stage3 HOLD.

**LLM15 / 02.11:** `CODEX-WUA-LOCAL-LLM-DISCOVERY-001` — 28/28 опубликованных артефактов согласованы с манифестом (12 CRLF реконструированы); .9 Ollama GET observed, .77 Colibri NOT VERIFIED; `FOLLOWUP-WUA-LOCAL-LLM-COLIBRI-001` и `FOLLOWUP-WUA-LOCAL-LLM-DISCOVERY-ADAPTER-001` OPEN. Нет реализованного провайдерного adapter, E2E или изменения серверов.

**WEB19 / independent Stage2 storage check:** №479 source SHA pinned, two Windows Python versions `68 run/4 SKIP` each, additional reviewer probes 4/4 PASS; only focused execution. `reports/CHATGPT-WEB19-S2-INDEPENDENT-WINDOWS-20261101.md`. Run Store P9 NEXT, Stage3 HOLD.


Это короткая рабочая выборка по локальным документным свидетельствам; числа не являются новым исполнением тестов этой TASK. Полные отчёты и исходные FAIL остаются у владельцев.

| Направление / TASK | Краткий результат и границы | Текстовый адрес |
| --- | --- | --- |
| А / CLAUDE-WUA-CHAT-S2-SHARED-STORAGE-001, 31.10 | №473; общий writer + Web create/rename; автор 1076 PASS/2 SKIP full, 140 JS, 39 mutants; независимые 8/8 SHA и JSON counts; **REVISE**: F-01 вложенная junction при записи context state/variants; independent runtime NOT RUN. | №05 `REG-WEB18-S2-REVISE-20261031`, `FOLLOWUP-WUA-S2-CONTEXT-PATH-001`; №06 `EVT-WEB18-S2-REVISE-20261031`; `reports/CHATGPT-WEB18-S2-REVIEW-20261031.md` |
| А / CLAUDE-WUA-EVM-PINNED-MULTIWINDOW-001, 31.10 | №467 `f4597868`; multiwindow и layout persistence, автор Python 1065 PASS/2 SKIP, JS 133/133, browser 198/198, mutants 38/38. Пользователь принял mouse+touch UX; verifier GitHub source/evidence reviewed, independent runtime NOT RUN. | №05 `REG-WEB17-EVM-PINS-20261031`; №06 `EVT-WEB17-EVM-PINS-ACCEPT-20261031`; №001 Claude 2026-10-31 |

| А / CLAUDE-WUA-EVM-INTERACTION-DND-001, 30.10 | №464; source/evidence inspected, author Python 1061 PASS/2 SKIP, JS 126/126, real-input browser 125/125, mutants 35/35. User accepted Windows UX. Independent full runtime NOT RUN; platform gaps tracked. | №05 `REG-WEB17-EVM-DND-20261030`; №06 `EVT-WEB17-EVM-DND-ACCEPT-20261030`; №001 Claude 2026-10-30 |
| А / CLAUDE-WUA-CHAT-S1-READONLY-UI-001, 27–28.10 | WEB15: bounded source/evidence 33/33, author 1024 PASS/2 SKIP и 36 mutants; WEB16: пользовательский terminal PARTIAL, документационно закрыто в `GPT`, но Windows/visual/regression OPEN. | №05 → `REG-WEB16-S1-20261028`; №06 → `EVT-WEB16-S1-CLOSE-20261028`; №001 Claude → `2026-10-28 — CLAUDE-WUA-CHAT-S1-READONLY-UI-001` |
| А / CLAUDE-WUA-EVM-MODEL-CARD-UI-001, 27–28.10 | Опубликованная EVM #455; WEB16 independently reviewed source/6 SHA256 (UI CRLF), evidence авторских 1057 PASS/2 SKIP, JS 109/109, mutants 30/30, но independently tests/CI NOT RUN. Пользователь подтвердил основной экран и настройки; DOC CLOSED / TERMINAL PARTIAL в `GPT`; детали проверки OPEN. | №05 → `REG-WEB16-EVM-20261028`; №06 → `EVT-WEB16-EVM-CLOSE-20261028`; №001 Claude → `2026-10-28 — CLAUDE-WUA-EVM-MODEL-CARD-UI-001` |
| А / CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001, 26.10 | Bounded architecture/evidence integrity PASS; 17/17 hashes по прежней приёмке. Не разрешение на последующие стадии само по себе | №05 → WEB_14 / 2026-10-26 — результат подготовительного этапа Ultra Chat; `reports/CLAUDE-WUA-CHAT-S0-BASELINE-CONTRACT-001/report.md` |
| А / ASTRA-WUA-37-ROADMAP-REVISION-001, 26.10; решение 27.10 | Независимый documentary/bounded architecture review принят; затем пользователь отдельно утвердил №37. Runtime/portability/paid gates остаются отдельными | №05 → WEB_14 / 2026-10-26 — независимая приёмка кандидатной программы №37; `reports/ASTRA-WUA-37-ROADMAP-REVISION-001/report.md`; №37 |
| А / ASTRA-WUA-2-MIGRATION-ARCH-REVIEW-001 rev2, 26.10 | Bounded architectural source review: 30/30 source pins, 8/8 коррекций по прежнему verdict; не runtime PASS | №05 → WEB_14 / 2026-10-26 — независимая архитектурная приёмка Ultra; `Дополнительная аналитика Астры.md` |
| Б / CLAUDE-WA4-R-FT1-CI-REPAIR-001, 24.10 | Bounded gate PASS; по документам focused 45 PASS/1 SKIP, full 988 PASS/1 SKIP, isolation=0. Общий WA4-R PARTIAL; не снятие rollout gates | №25/06 по TASK адресно; точный report locator требует сверки координатором. Источник этого handoff сохранён в исходном снимке №34 → WEB_15 / CURRENT 2026-10-24 |
| Б / CLAUDE-WA4-R-TRANSPORT-TAIL-RECOVERY-001, AUD-01T-R, 20.10 | Независимый Windows test gate PASS, 909/909 в прежнем evidence; публикационные/операционные ограничения не исчезают. Поздний FT1 результат не подменяет остальные gates | №05 → LLM13 / 2026-10-20 — независимый Windows-прогон восстановления журнала завершён, остаточные риски открыты; №24/25 адресно |
| Б / CODEX-WA4-O-001, 11.10 | Implementation + automated verification PASS, человеческая визуальная оценка INTERIM; full visual suite не подтверждён. UX A/B/C не реализован этим результатом | №05 → Ветка WA: Web Alarm Workspace → CODEX-WA4-O-001; `reports/CODEX-WA4-O-001/report.md` |

Не добавлять новую строку для каждой доставки одного отчёта. Для новой принятой задачи заменить вытесненную из окна после loss-check. Отдельные важные исторические ориентиры, включая WA4-A и accepted S0, доступны через №05/профиль, а не через бесконечный prepend.

## Следующие действия и восстановление после смены чата

1. Определить конкретное поручение пользователя и роль; отличить документационную работу от технических направлений А/Б. Дату этого снимка не выдавать за свежую проверку внешнего состояния.
2. Сверить актуальный №40 и личную карточку исполнителя в относящемся scope. При конфликте источников сохранить обе версии и запросить/получить точный первоисточник доступным разрешённым способом.
3. №467 USER ACCEPTED сохраняется. F-01 закрыт №475 в bounded scope; REPLACE-HARDEN закрыт №479. WEB19 добавил focused Windows PASS; full independent regression/CI, Tk readers P1–P6 и Stage3 prerequisites OPEN. №05/06 дают точные record/event ID.
4. UI task `CODEX-WUA-CHAT-UI-INTEGRATION-001` source/evidence PASS по №499, независимый runtime NOT RUN; следующая задача не назначена автоматически. P9 принят в bounded source+evidence scope 03.11, №496 уже в main; Stage3 prerequisites (audit-path, Tk P1–P6, независимый runtime, RUN writer, Claude SLOT HOLD) остаются OPEN. Текущий приоритет по USER GO 04.11: освободить слот Codex штатным механизмом и назначить узкую UI-задачу по общему Workspace/истории, не запускать Turn/Stage3/paid/live. `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED; №37 и №43 не переписывать.
5. При передаче новому чату назвать: цель, TASK/источник разрешения, read/write-scope, достигнутое состояние, OPEN/риски, следующий шаг и точные locators. Не переносить полную переписку и все архивы.

## Как сопровождать эту память

Канон №18 → DOC-CONTEXT-OPS-01 → OPS-CLOSE/OPS-BUDGET. При закрытии задачи координатор сначала сохраняет полный результат у владельца, проверяет readback, затем обновляет соответствующие поля здесь. Условия безопасности и открытые риски сохраняются до явного resolution. Никакой самостоятельной фоновой синхронизации нет.

**WEB22 / temporary budget note:** 04.11.2026 после UX closeout №34 временно составляет около 31 тыс. символов (выше целевых 15–25 тыс., ниже предела 50 тыс.). При следующем плановом сопровождении выполнить адресный loss-check владельцев/локаторов и уплотнить только безопасно сохранённые фрагменты, без удаления уникальных OPEN и графовых связей. Это не разрешение на немедленное вытеснение данных.

Цель 15–25 тысяч символов, абсолютный максимум 50 тысяч, считая весь файл. Выше 25 тысяч — объяснить временное расширение и назначить возврат; выше 50 тысяч — не принимать документационную дельту, пока сохранность и адреса не позволяют безопасно уплотнить её. №05 и историю не урезать ради бюджета. Ниже начинается область прежних адресов; она не входит в обычное стартовое чтение.

## Сохранённые адреса прежней редакции

Эта область сохраняет прежние заголовки и графовые конструкции для адресной совместимости. Старые CURRENT/NEXT здесь являются историческими названиями, а не действующими инструкциями. На обычном старте область пропускается. Полный исходный текст: `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027/preservation/34_TACTICAL_CONTEXT.md.source.txt`. Границы записей Snnn и SHA-256: `reports/ASTRA-DOC-CONTEXT-OPTIMIZATION-001/implementation-20261027/evidence/preservation_index.json`. Исторический текст читать только по нужному Snnn/TASK, не целиком.

## CURRENT / WEB15 / 2026-10-27 — единый BAT и возврат после любого TEST

История `S001`; текущий вход — начало файла.

## HANDOFF / WEB15 — 2026-10-27 / Stage1 source/evidence bounded review

История `S002`; текущий вход — начало файла.

## HANDOFF / WEB15 — 2026-10-27 / финальное утверждение №37 и опубликованный Stage1

История `S003`; текущий вход — начало файла.

## HANDOFF / WEB_14 — 2026-10-26 / USER portability requirement, №37 revised for final approval

История `S004`; текущий вход — начало файла.

## HANDOFF / WEB_14 — 2026-10-26 / Ultra Chat Stage0 accepted as bounded architecture, Stage1 approval next

История `S005`; текущий вход — начало файла.

## HANDOFF / WEB_14 — 2026-10-26 / Astra №37 DOCUMENT PASS, roadmap still awaits user

История `S006`; текущий вход — начало файла.

## HANDOFF / WEB_14 — 2026-10-26 / Astra rev2 bounded PASS, user decision next

История `S007`; текущий вход — начало файла.

## HANDOFF / WEB_14 — 2026-10-26 / WEB_13 → Astra rev2 review, Ultra Chat migration

История `S008`; текущий вход — начало файла.

## HANDOFF / WEB_13 — 2026-10-25 / WEB_12 → Web Alarm Ultra API & Chat

История `S009`; текущий вход — начало файла.

## USER PRIORITY / 2026-10-25 — FREEZE CHATGPT DESKTOP MCP / RESUME WEB ALARM ULTRA API

История `S010`; текущий вход — начало файла.

## WEB_12 / CURRENT — 2026-10-25 / Codex strict admission independent offline PASS

История `S011`; текущий вход — начало файла.

## WEB_12 / CURRENT — 2026-10-25 / accepted bounded source review, user-approved terminal closeout

История `S012`; текущий вход — начало файла.

## WEB_11 → NEXT MCP CHAT / 2026-10-25 — краткий handoff

История `S013`; текущий вход — начало файла.

## CURRENT GOVERNANCE / 2026-10-24 — координация персональных TASK и архивов

История `S014`; текущий вход — начало файла.

## WEB_15 / CURRENT 2026-10-24 — независимый FT1-CI-REPAIR PASS; WA4-R PARTIAL

История `S015`; текущий вход — начало файла.

## WEB_11 / CURRENT 2026-10-24 — sing-box source review и dependency closure

История `S016`; текущий вход — начало файла.

## CURRENT HANDOFF / 2026-10-24 — Claude FT1/Archive Retry, НЕЗАВЕРШЁННАЯ независимая приёмка (следующий ChatGPT)

История `S017`; текущий вход — начало файла.

## CURRENT COORDINATION / 2026-10-24 — выдача TASK, общий контекст и Claude 409

История `S018`; текущий вход — начало файла.

## WEB_11 / CURRENT 2026-10-24 — проверены offline MCP NPFS и broker

История `S019`; текущий вход — начало файла.

## CROSS-CHAT CURRENT / 2026-10-21 — БЛОК 4, утверждённый общий регламент

История `S020`; текущий вход — начало файла.

## CROSS-CHAT CURRENT / 2026-10-21 — GitHub-права, роли и лаборатории (решение пользователя)

История `S021`; текущий вход — начало файла.

## WEB_11 / CURRENT 2026-10-21 — MCP Windows Lab Gate, независимая ограниченная OFFLINE-приёмка

История `S022`; текущий вход — начало файла.

## CURRENT / 2026-10-20 / LLM13 — AUD-01T-R independent Windows execution PASS; publication/operational gates OPEN (supersedes LLM12 RUNNING snapshot)

История `S023`; текущий вход — начало файла.

## CURRENT / 2026-10-20 / LLM12 — HANDOFF TO NEXT CHAT: complete AUD-01T-R independent verification (source, CI, evidence, safety)

История `S024`; текущий вход — начало файла.

## CURRENT / 2026-10-20 / LLM12 — Claude AUD-01T-R опубликован; независимая проверка ещё продолжается

История `S025`; текущий вход — начало файла.

## ARCH DECISION / 2026-10-20 / WEB_11 — универсальная ChatGPT MCP-интеграция и независимые сетевые профили

История `S026`; текущий вход — начало файла.

## CURRENT / 2026-10-20 / WEB_10 — portable MCP toolkit published and bounded independently reviewed

История `S027`; текущий вход — начало файла.

## CURRENT / 2026-10-20 / LLM12 — Web Alarm: W1 Windows CI выполнена, окончательная приёмка ограничена

История `S028`; текущий вход — начало файла.

## CURRENT / 2026-10-19 / WEB_10 — Codex SID/WFP no-VM architecture independently reviewed

История `S029`; текущий вход — начало файла.

## CURRENT / 2026-10-18 / WEB_10 — Claude no-VM identity-scoped egress analysis, bounded verifier review

История `S030`; текущий вход — начало файла.

## CURRENT / 2026-10-18 / LLM12 — Web Alarm WA4-R R-MT/R-OP published repair independent bounded review

История `S031`; текущий вход — начало файла.

## CURRENT / 2026-10-18 / WEB_10 — CODEX-WUA-0-OFFLINE-VM-PREFLIGHT-001 independent bounded review

История `S032`; текущий вход — начало файла.

## CURRENT / 2026-10-18 / WEB_10 — CODEX-WUA-0-NATIVE-EGRESS-GATE-001 independent bounded review

История `S033`; текущий вход — начало файла.

## CURRENT / 2026-10-18 / WEB_10 — AMENDMENT 07 bounded independent source/evidence review

История `S034`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / LLM12 independent crash-consistency design review — AUD-02b-R and AUD-03

История `S035`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / LLM12 — WA4-R AUD-01T/02b independent bounded review (GitHub-first)

История `S036`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / WEB_10 — official tunnel-client v0.0.16 exact-tag source-only preflight (COORDINATOR RESEARCH)

История `S037`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / WEB_10 — WUA MCP AMENDMENT 06, bounded independent review

История `S038`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / WEB_10 — WUA MCP AMENDMENT 05, bounded independent GitHub review

История `S039`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / HANDOFF WEB_09 → «Сервер WEB_10» — MCP, V2Ray, Secure Tunnel

История `S040`; текущий вход — начало файла.

## CURRENT / 2026-10-17 / USER WORKSTREAM CORRECTION — LLM12=WEB ALARM; WEB_09=MCP

История `S041`; текущий вход — начало файла.

## LLM12 / 2026-10-17 / CONTEXT TRANSFER — WEB ALARM ULTRA MVP (READ ONLY, NO GO)

История `S042`; текущий вход — начало файла.

## WEB_09 / 2026-10-17 / USER WORKFLOW OVERRIDE — LOCAL REPORTS, USER PUSH, GITHUB-FIRST COORDINATION

История `S043`; текущий вход — начало файла.

## WEB_09 / 2026-10-16 / CURRENT — Claude bounded repair review + two independent streams

История `S044`; текущий вход — начало файла.

## WEB_09 / 2026-10-16 / CONTEXT TRANSFER — WA4-R + MCP (coordination only)

История `S045`; текущий вход — начало файла.

## WEB ALARM ULTRA / 2026-10-15 / USER PRIORITY DECISION — WEB_08 FIRST, THEN TRANSITION

История `S046`; текущий вход — начало файла.

## WEB_08 / 2026-10-16 / USER DIRECTION — MCP FIRST FEASIBILITY + CODEX CHAT RELAY

История `S047`; текущий вход — начало файла.

## WEB_08 / 2026-10-15 / ChatGPT Desktop ↔ MCP ↔ Ultra — FUTURE FEASIBILITY CONCEPT

История `S048`; текущий вход — начало файла.

### WEB_08 / 2026-10-16 / AG LLM → WEB_08 — INITIAL MESSAGE RELAY SMOKE

История `S049`; текущий вход — начало файла.

### WEB_08 / 2026-10-15 / GitHub-only evidence handoff decision — PREPARED, NOT ASSIGNED

История `S050`; текущий вход — начало файла.

## WEB_08 HANDOFF / 2026-10-14 / WEB_07 — READ THIS FIRST (supersedes older CURRENT labels only where specified)

История `S051`; текущий вход — начало файла.

### WEB_07 R-004 INDEPENDENT SOURCE CHECKPOINT / 2026-10-14 — NOT RUNTIME ACCEPTED

История `S052`; текущий вход — начало файла.

## CURRENT WEB_07 HANDOFF — 2026-10-13

История `S053`; текущий вход — начало файла.

# 34 — TACTICAL CONTEXT / Живой тактический контекст

История `S054`; текущий вход — начало файла.

[[05_Реестр задач]]

## ULTRA-ONLY CONTINUITY / 2026-10-13 — курс после Web Alarm, S1 research и автоматизация

История `S055`; текущий вход — начало файла.

## 0. Переход в новый Chat — короткий и самостоятельный

История `S056`; текущий вход — начало файла.

### CURRENT WEB-02 / 2026-10-11 — WA4-O technical PASS, WA4-R next candidate

История `S057`; текущий вход — начало файла.

### GitHub Actions — первоначальный smoke CI №256 (исторический обзор)

История `S058`; текущий вход — начало файла.

## 1. Что сейчас происходит

История `S059`; текущий вход — начало файла.

## 2. Ограничения и открытые вопросы

История `S060`; текущий вход — начало файла.

## 3. Git и среда — снимок, перепроверять

История `S061`; текущий вход — начало файла.

## 4. Карта чтения — брать только по потребности

История `S062`; текущий вход — начало файла.

[[05_Реестр задач]]

## 5. NEXT SAFE ACTION

История `S063`; текущий вход — начало файла.

## 5а. RT-002 — завершённое планирование, актуальный инженерный маршрут

История `S064`; текущий вход — начало файла.

## 6. Обязательное сопровождение — DELTA, а не переписывание истории

История `S065`; текущий вход — начало файла.

## 7. Последний тактический handoff

История `S066`; текущий вход — начало файла.

