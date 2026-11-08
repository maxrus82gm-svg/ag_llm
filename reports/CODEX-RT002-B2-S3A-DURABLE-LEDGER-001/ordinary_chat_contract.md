# Ordinary Chat → RT-002/B2: предложение, НЕ включённый маршрут

TASK `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`, 2026-11-08.
Основания: №20 §5а/§14; №37 Stage6/§2.4/§4; S1/S2 и новый OFFLINE S3a.

## Что требует USER GO

Предлагаемые имена: route `ordinary_chat`, role `ordinary_chat`, отдельный
scope `ORDINARY_CHAT_SESSION`. Они сейчас не добавлены ни в ROUTES, ни в
политику. Нельзя направлять Ordinary Chat через executor/mcp_chat, чтобы
обойти отсутствие профиля. Текущий S3a на таком route отвечает DENY.

Предлагаемый budget owner — стабильная Chat budget session, общая для двух UI,
а не новый бюджет на каждый Turn/F5/reopen. Длительность session, rollover,
workspace-wide предел поверх Chat, output reserve, unknown profile, отдельный
token calibration profile и числовые пределы требуют утверждения. Никакие
числа synthetic tests не становятся пользовательскими defaults. Final Audit
для существующих агентских маршрутов не отключается; отдельная Ordinary Chat
семантика должна быть согласована в S2/S5, не маскироваться чужой ролью.

## Идентичность и immutable snapshot

Workspace ID → Chat ID → Turn ID → logical_call_id → provider_attempt_id.
Один физический retry = новый provider_attempt_id, даже при том же logical call;
повтор delivery того же события использует старый ID и не является новой попыткой.

В S3a reserve замораживаются raw validated policy (revision hash), S2 engine
source identity, route, точные S2 serialized UTF-8 wire bytes (model/max_tokens,
messages/tools входят в body), RunContext и binding run/chat/turn/logical-call.
Запись не хранит абсолютный workspace path. Перенос возможен с той же identity
и всеми ledger/marker/index-generation файлами, после остановки старого владельца.
Копирование одного Workspace ID в два одновременно активных независимых root
не даёт глобальной межмашинной блокировки и требует отдельного fencing contract.

Текущие зарегистрированные S2 RUN routes привязываются `binding.run_id ==
RunContext.scope_id`. Будущая Ordinary Chat scope-схема должна быть добавлена
в S2 явным amendment. До него новый ledger остаётся OFFLINE библиотекой для
существующих зарегистрированных synthetic routes.

## Предлагаемый порядок S3b, не реализован здесь

1. Trusted adapter выбирает утверждённый route и scope; UI/LLM не подменяет их.
2. S1 inventory должен охватывать физические sites и aliases всех LLM routes;
   OAuth отдельно. Текущий S1 selector имеет 2 FAIL — сначала отдельная сверка.
3. Собрать final wire body один раз через общий S2 serializer, включая tools,
   max_tokens, request blocks/source refs/schema version. Измерение и отправка
   должны относиться к тем же неизменяемым bytes/hash, без пересериализации.
4. Общий S3a reserve под Workspace writer lock: validate policy, проверить
   остаток, durable commit, проверенный receipt. Никакого HTTP на ошибке записи.
5. Durable mark_sent непосредственно перед физическим I/O. Только свежий
   допустимый переход может быть использован guard; replayed receipt НЕ
   разрешает повторную отправку. Gap между SENT и HTTP консервативно расходует
   резерв после crash, пока S9 не получит достаточные доказательства.
6. Proven not-sent допустим до SENT и только от доверенного pre-HTTP owner,
   с locator факта. Строка proof API не доказывает сеть сама по себе. После
   SENT/timeout/cancel нельзя освобождать резерв как нулевой.
7. Terminal/usage поступают по исходному provider_attempt_id: duplicate
   идемпотентен; противоречие даёт S2 ANOMALY, позднее уточнение UNKNOWN —
   существующий S2 RECONCILED. Provider units не равны деньгам/биллингу.
8. Web/Tk читают одну authority и показывают projections; usage summaries
   не дают право на следующую попытку. Reopen/F5 не создаёт budget session.

## Узлы и gates

| Узел | Текущее состояние / требуемое включение |
| --- | --- |
| S1 | Guarded 69: 67 PASS, 2 FAIL текущей инвентаризации; отдельный amendment на разбор inventory, не blanket allowlist |
| S2 | 73/73 core PASS, политика не менялась; новый route/profile/scope и numeric choices ждут USER GO |
| S3a | Новый общий durable OFFLINE API; fresh enrollment, replay, crash/concurrency/UNKNOWN; независимая приёмка ожидается |
| S3b | Не реализован: обязательный physical pre-HTTP guard всех routes/aliases, 0 physical sends на DENY, immutable bytes |
| S3c | Не реализован: резерв обязательной проверки до mutation; к обычному read/write agent не добавлять обход |
| S9 | Не реализован в новом чате: trusted late usage ingestion/reconciliation, origin/authenticity и orphan outcomes |

## Отмена, данные и восстановление

До SENT доказанная отмена освобождает reserve через NOT_SENT. После SENT
UNKNOWN/SENT сохраняет liability; отмена UI/разрыв браузера не доказывает
отсутствие paid attempt. Сохранность user/assistant RAW и включение в будущий
контекст — отдельные слои и не меняют budget journal.

recover здесь проверяет сохранённые facts под тем же lock; не исполняет
provider, не освобождает orphan SENT и не сбрасывает missing/corrupt ledger.
Fresh enrollment разрешён только на пустом audit store. Для исторических
Run Store accounting, полной истории/переустановки и S2 engine upgrade нужен
явный approved adoption/migration protocol; автоматический ноль запрещён.

Ни один пункт этого предложения не включает новый route, HTTP guard, реальный
GigaChat/OAuth, paid defaults или Stage6B. Эти действия вне текущего scope.
