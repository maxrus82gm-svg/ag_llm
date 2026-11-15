# Transport contract

Документальные источники прочитаны 15.11.2026, исключительно публичные страницы, без provider/account API:

- [OAuth](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-token): token endpoint, access token 30 минут. Epoch-ms expires_at проверен по ранее сохранённому H37 OpenAPI/provider-contract.
- [Authorization/API](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api): Basic credentials, scope, RqUID; completion base api.giga.chat.
- [Chat completions](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat): text messages и non-streaming, documented HTTP errors.
- [Models](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/get-models): account-specific list; Ultra Freemium физлиц.
- [Usage](https://developers.sber.ru/docs/ru/gigachat/guides/counting-tokens): billed prompt исключает precached; total=prompt+completion. H37 accounting clarification сохранена совместимой.

Запросы: OAuth POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth; catalog GET https://api.giga.chat/v1/models; inference POST https://api.giga.chat/v1/chat/completions. URLs не берутся из браузера/env. Никакие endpoints в этой TASK не вызывались физически.

Порядок: reviewed single-use approval → existing enrolled ledger/account owner → explicit bounded catalog → Chat snapshot → Turn/RAW → final immutable S2 bytes → reserve/readback → SENT/readback → existing shared OAuth/cache → deadline/cancel/model/owner recheck → durable control-call limit → exact Request bytes/method/url check → one physical dispatch → bounded response → exact model version → common parser → existing terminal ledger → durable event → assistant RAW. OAuth/catalog тоже имеют durable call counter до I/O. Резерв после неясного сбоя не снимается.

SSLContext CERT_REQUIRED/check_hostname, system trust либо явно переданный проверяемый trust context; нет verify=False. AsyncHTTPTransport retries=0/trust_env=False; AsyncClient trust_env=False/follow_redirects=False. Проверка реального trust chain/установки необходимых CA NOT RUN. Cache key включает доверие, scope, account и SHA credentials; token storage только в старом модуле, не в файлах/HTTP/evidence. refresh после 401 не запускается автоматически.

Ошибки не содержат provider body/header/token/exception string. 301/307/401/403/404/429/500 остаются failed, timeout/transport/cancel после SENT — UNKNOWN. Transport-level mismatched model сохраняет допустимый numeric usage, но не публикует ответ. Reasoning берётся только из numeric completion_tokens_details.reasoning_tokens ≤ completion; отсутствие UNKNOWN. Availability/caps не выводятся из MODEL_REGISTRY.enabled.

LiveApproval — доверенный Python server API, не криптографическая система согласований. Он должен быть создан оператором только после независимого review и явного USER GO; strings user_go/review — provenance, а не автоматическая проверка текста разрешения. Untrusted browser/env/config не имеют доступа к этому factory. Distributed authorization в scope не заявлена.
