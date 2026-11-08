# Ordinary Chat — отдельный route/scope contract

**Тип:** PROPOSAL / NOT IMPLEMENTED / NOT ACTIVE.  
Связь: [основной пакет §4–5](policy_decision_packet.md), TASK
`CODEX-RT002-B2-ORDINARY-CHAT-POLICY-DECISION-001`.

**Согласовано только CHAT-A01:** Workspace Ordinary envelope равен выбранному
session envelope и не увеличивается при создании Chat. Абсолютные A/B/C,
остальной contract и реализация ожидают отдельных решений/назначений.

| Поле | Предлагаемый контракт |
| --- | --- |
| route / role / profile key | ordinary_chat / ordinary_chat / ordinary_chat |
| scope | ORDINARY_CHAT_SESSION, отдельная typed ветвь S2, не RUN/MCP/Compressor |
| owner | Один Workspace Run Store/ledger, общий для Web и Tk; существующий writer lock |
| identity | Workspace → Ordinary grant/epoch → Chat → session → Turn → logical_call → physical attempt |
| scope ID | `oc:` + 64 hex SHA-256 канонического Workspace/Chat/session tuple; не display name/path |
| session lifetime | Предложение: сохранять до контролируемого закрытия, без automatic TTL/reset |
| grant lifetime | Предложение: явное изменение абсолютного ceiling с carry всех обязательств/attempts |
| admission | Session L/N и Workspace W/N проверяются вместе одним commit; W=L, workspace N=session N |
| concurrency | Предложение: inflight≤1/Chat; разные Chat делят общий остаток атомарно |
| snapshot | Policy/engine/route/scope/binding, model/profile/serializer identity, exact wire bytes/hash/output reserve неизменны для attempt |
| output | Резерв exact positive body.max_tokens, ограниченного утверждённым cap |
| missing profile / unsupported backend | DENY; zero Ordinary samples сейчас, никаких borrowed executor/mcp profiles |
| retries | Каждому новому physical call новый attempt ID/reserve; старый UNKNOWN не освобождается |
| receipt | Replay — факт, не permit; fresh one-use transition контролируется trusted S3b owner |
| model switch | Та же session/Workspace quota; только профиль для нового effective model; старые долги неизменны |
| tools / agents | Text-only; agent work требует отдельного RUN и обязательных verification/mutation gates |
| namespace isolation | Chat связывается с проверенным Workspace; другой Workspace отдельный, клон того же ID не новый кошелёк |

Пример **будущего** binding, не принимаемый текущей схемой:

```json
{
  "document_type": "PROPOSED_BINDING_VNEXT_NOT_CURRENT_SCHEMA",
  "binding_type": "ORDINARY_CHAT",
  "workspace_id": "SYNTHETIC_WORKSPACE",
  "budget_epoch_id": "SYNTHETIC_EXPLICIT_GRANT",
  "chat_id": "SYNTHETIC_CHAT",
  "session_id": "SYNTHETIC_STABLE_SESSION",
  "turn_id": "SYNTHETIC_TURN",
  "logical_call_id": "SYNTHETIC_LOGICAL_CALL",
  "provider_attempt_id": "SYNTHETIC_PHYSICAL_ATTEMPT",
  "policy_revision": "PROPOSAL_ONLY",
  "effective_provider_model_id": "REQUIRES_CALIBRATION",
  "profile_key": "ordinary_chat",
  "wire_sha256": "COMPUTED_FROM_IMMUTABLE_FINAL_BYTES"
}
```

Нельзя подставлять session ID в обязательный нынешний run_id ради обхода
валидации. Нужны versioned binding и backward-compatible reader/migration.
Текущий ledger фиксирует policy revision на scope и policy-engine source SHA;
новая версия требует явной совместимости и повторной приёмки.

Переходы для будущего guard:

1. Проверить trusted route/binding/grant/model и обе quota; получить durable
   reserve на тех же immutable bytes, которые будут отправлены.
2. Свежий durable SENT перед одним physical LLM I/O. Повтор receipt/потеря ACK/
   crash не дают ещё один I/O. До разрешения новой попытки обе quota учитывают
   временный RESERVED и все pending/known obligations.
3. Proven pre-send NOT_SENT освобождает liability/attempt quota **только из
   RESERVED до durable SENT**; событие всё равно остаётся в storage. После
   SENT release не допускается нынешним контрактом даже в crash gap до HTTP.
   Cancel UI, timeout и закрытие браузера — не proof.
4. SENT без результата/usage остаётся conservatively held. Trusted late usage
   уточняет исходный ID; duplicate идемпотентен, conflict даёт ANOMALY/DENY.
5. F5/reopen/новый Chat/model не создаёт grant. Controlled new epoch/session
   получает проверенный carry; старые facts не переписываются и не исчезают.

Сохранение user/assistant RAW, включение в следующий context и budget journal
отдельны: ни удаление видимого сообщения, ни отсутствие его в context не
доказывает отсутствия provider spend. Workspace aggregate не зависит от UI.

**Приёмка этого contract ещё не выполнена.** Требуются пользовательские U1–U4,
новые S2/S3a contract tests, cross-Chat/cross-UI atomicity, replay/cancellation/
late usage/migration failures и independent review. S3b физический guard и
реальные provider calls данным документом не разрешаются.
