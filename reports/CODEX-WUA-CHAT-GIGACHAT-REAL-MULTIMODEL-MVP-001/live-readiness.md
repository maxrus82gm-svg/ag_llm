# LIVE readiness — HOLD, код готов к независимому review

Реальный transport/factory реализован; новая vertical slice проверена OFFLINE через те же production методы. Независимый S13a/Windows review, реальные account/caps/trust и owner GO ещё отсутствуют. **Сейчас нельзя запускать OAuth, catalog, balance, token-count или completion.** Ни одного такого запроса в задаче не было.

Перед GO независимому verifier:

1. Проверить manifest/source fingerprints и Windows suites по test-results.md; отдельно прочитать новый LiveApproval/session transport и census/policy pins. Публичные источники — transport-contract.md; code admission не является доказательством реальных caps.
2. Установить применимость S3b/S3c/S4/S5/S9/C1/C2 и независимый S13a ordinary release, не закрывая остальной B2. Выбрать один свежий Workspace без historical audit; проверить existing ledger enrollment через штатный BudgetLedger.initialize, не мигрировать старую базу автоматически.
3. Подтвердить владельца credentials/project, scope, one-process/one-Workspace account topology, доверенные CA, endpoint и exact provider/version caps. Пока этих фактов нет, real ModelContract не заполняется synthetic числами.
4. Account catalog/тариф могут требовать отдельного probe GO. Предлагаемый probe envelope: OAuth ≤1, GET models ≤1, inference=0; отдельный probe-only LiveApproval допускает пустые contracts и физически запрещает inference. Нет auto refresh/retry/balance/token-count. Generic serialized UI grant не поддерживается.

Проект **следующего**, ещё не разрешённого inference GO:

- Account/project/scope и выбранная по подтверждённому тарифу самая экономичная **доступная** текстовая модель: TBD. Не считать Lightning самой дешёвой без фактов.
- Exact allowed response_model versions, context cap, whole-generation output cap: TBD по официальным/аккаунтным evidence и independent review.
- Единственное сообщение: `Ответь одним словом: готово` без private context, files, tools; allowlisted свежий Chat.
- Max inference physical POST: 1; max OAuth 1 (0 при подходящем cache), max catalog 1; максимум реальных control+inference=3. Auto retries=0, redirects=0, proxy/env transport=0.
- Предлагаемый output 32 tokens, wire ≤1024 B, conservative liability ≤1056 tokens. Это **предложение**, не доказанный provider cap и не рублёвая цена. Финансовый предел/валюта/тариф TBD; без доказанной верхней границы всей генерации HOLD.
- Период ≤15 минут; один grant_id, один процесс/Workspace/account. Экономию от cache при резервировании не предполагать.
- Stop: любой non-200/401/429, TLS/scope/model/version/usage anomaly, timeout/cancel, неполный reserve/SENT/terminal/RAW, неожиданный вызов/attempt. Повтор UNKNOWN запрещён.

После конкретного GO доверенный bootstrap переиспользует **существующий** server composition (не новый permanent launcher): создать проверенный SSLContext и LiveApproval с точными фактами → ProviderSession(existing root/wid/ledger) → явно discover_models() в разрешённом envelope → OrdinaryProviderFactory.for_session(api.registry, session) → web_alarm.server.create_server(api, ordinary_factory=factory). Session object не принимается от браузера/JSON/env. Две постоянные CMD/config не меняются; обычный STANDARD остаётся HOLD, TEST fake.

Сверка после ответа: physical call count exactly1; request hash в ledger соответствует Request; accepted response version; billed prompt+completion=total; cached/full input и reasoning subset/UNKNOWN; один user RAW/assistant RAW и terminal; F5/reopen/read-only latest не отправляют повтор. Close session (после завершения inflight), stop server, вернуть стандартный HOLD; проверить immutable ledger/историю. При crash ACTIVE marker/UNKNOWN не очищать, сохранить evidence и запросить адресную reviewed reconciliation.

Полный неизменённый historical Workspace и cross-process/cross-Workspace rollout не входят в первый smoke. После публикации/проверки пользователю нужен окончательный самодостаточный GO с заполненными TBD — текущее задание такого GO не даёт.
