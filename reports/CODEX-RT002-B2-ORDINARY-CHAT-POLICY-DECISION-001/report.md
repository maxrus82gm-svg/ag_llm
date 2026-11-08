# Ordinary Chat policy — итог анализа и пакет решений

**TASK:** `CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001`  
**Исполнитель / дата:** Codex 007 / 2026-11-08.  
**Статус:** **RESULT READY / DECISION PACKET / WEB26 REVIEW PENDING**.  
**Режим:** STRICT OFFLINE / LOCAL ONLY / proposal, не действующая policy.  
**Assigned base:** main@90ecf12e76bb48ff7fe1e08cc94d4b764f8d8858, Git identity не проверялась.  
**Approval:** CHAT-A01 — USER согласовал общий Workspace envelope, равный выбранному session envelope. Числа A/B/C и U1–U6 не утверждены. Реализация не разрешена.

Подготовлены [полный decision packet](policy_decision_packet.md), отдельный
[route/scope contract](route_scope_contract.md), [A/B/C JSON proposal](policy_candidates.json)
и [OPEN/NEXT](followups.json). Реестры источников/хешей и арифметика находятся
в evidence. Только собственный report package изменён; код, tests, HTTP,
нормативные документы и параметры системы не менялись.

## Результат и рекомендация

Fresh evidence подтверждает bounded independent S1 69+23, S2 73 и S3a CI
35 ledger + 51 Run Store / negative 2/1/9 / guard6. Прежний S3a independent
OPEN закрыт последующим WEB26 review; старые snapshots не переписывались.

Ordinary route/profile/scope отсутствуют. В embedded S2 corpus 342 строки,
340 известных prompt usage, **0 Ordinary Chat samples**. Его числовые кандидаты
и profiles нельзя объявить Ordinary defaults. Подготовлены три ограниченных
proposal envelopes с происхождением **каждого** числового поля:

| Вариант | Bytes/request | Input estimate cap | Output reserve cap | Session L/N; Workspace W/N равны |
| --- | ---: | ---: | ---: | ---: |
| A | 65536 | 16000 | 1024 | 80000 / 12 |
| **B — рекомендация для обсуждения** | **131072** | **32000** | **2048** | **120000 / 16** |
| C | 262144 | 64000 | 4096 | 240000 / 24 |

Все три UNCALIBRATED/NOT ACTIVE. Recommended missing profile DENY, предложены
margin20%/min_samples20; bytes_per_token=null. Точные математические сценарии
не являются новым тестом policy runtime или измерением реальной стоимости.

Пользователь согласовал **Workspace anti-multiplication principle**, а не B:
создание Chat не выдаёт дополнительный бюджет. [CHAT-A01](chat_amendment_01.md)
сохранён дословно и будет передан штатному finish как chat amendment.
Повторного одобрения этого пункта пакет не требует. Остались шесть решений:
route/session, A/B/C/custom, calibration, lifetime/grants, RAW privacy и rollout
existing Workspace/single-owner.

## MANUAL ENGINEERING REVIEW

Рассмотрены маршруты/профили S2, ordinary injected sender, общий Web/Tk owner,
S3a engine/revision pins и replay binding, capacity и enrollment. Установлены
важные gaps для будущей TASK: simple new-scope append попадает в non-RUN MCP
fallback; schema/binding не имеют Ordinary; двууровневый atomic grant отсутствует;
изменение source engine несовместимо со старым marker без migration.

Отвергнуты role alias executor/mcp, per-Turn/F5 budgets, новое право из replay,
оптимистичный cancel/UNKNOWN release, borrowed legacy calibration и unlimited
new-Chat/model reset. Предложена versioned typed session с одним authority,
двойной atomic session/Workspace проверкой и carried obligations. Для future
guard описаны exact-wire/fresh-SENT/late usage и negative acceptance scenarios;
их исполнение не заявляется.

Разделены gates: утверждения/contract extensions и independent compatibility
до S3b; privacy/retention, историческая adoption, калибровка и rollout decisions
до real data/live; active-active/power-loss как открытые bounded limitations.
Inline wire_utf8, 4096 events и 64MiB не выданы за пригодный production data
contract. Прямой raw precached:null отличается от missing field: нынешний S2
считает явный null INVALID, а missing оставляет conservative estimate.

## Проверка пакета и NOT RUN

Выполнены адресное чтение 27 источников, сверка четырёх independent source pins,
AST-extraction dataset/CANDIDATES без imports тестов/production, проверка dataset
SHA, целочисленная арифметика и provenance чисел. Сохранены commands/exit receipts,
source registry, scope baseline, структура девяти разделов, links, согласованный
CHAT-A01 и manifest. Собственные helpers проверяются syntax/compile без bytecode.
Scope/readback подтверждаются package_check pre/post finish.

**NOT RUN:** полный runtime/test regression, новый benchmark/calibration,
API/HTTP/OAuth/LLM/paid, UI/launcher smoke, CI, новая независимая приёмка, реальная
миграция или изменения policy/schema. Для документационного анализа без
изменений кода regression не требовался. Existing independent results — ссылки
на сохранённые reviews, не повторные прогоны Codex. Credential values, реальная
история Chat и RAW prompts не читались для подготовки нового corpus.

## DOC IMPACT, OPEN/NEXT и сдача

DOC IMPACT — собственный пакет и штатная сдача текущей карточки с CHAT-A01.
Общие №05/20/21/34/37/40, tests/production/CMD и чужие отчёты не редактировались.
SHARED DOC DELTA для WEB26: Ordinary decisions подготовлены, Workspace/session
envelope equality approved by USER, остальные U1–U6 pending; S3a independent
predecessor уже bounded accepted; Stage6/7/live HOLD сохраняется.

NEXT: independent WEB26 review → решения USER → отдельные назначенные contract/
calibration/storage/S3b работы по gates пакета. Proposed NEXT IDs в followups
не являются созданными TASK. Никакой прямой отправки чужому чату не было;
пользователь получает локальный пакет для последующей независимой проверки.

После проверки выполняется официальный finish с exact TASK ID и
--chat-amendment chat_amendment_01.md, затем history readback. Его result/exit,
HISTORY ID, БЛОК1 WAITING и БЛОК1.1 SUBMITTED/REVIEW PENDING сохраняются в
finish_protocol.json/closeout.json. Report после HISTORY не меняется. Прежний
snapshot H25 и БЛОКИ2–4 сохраняются. Git/GitHub — NOT USED, реальные calls — 0.
