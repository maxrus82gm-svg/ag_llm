# One model provider contract — PARTIAL, RELEASE HOLD

Checked 2026-11-14, solely the four B1 URLs explicitly authorized by OWNER. This is a factual reading record, not a saved provider schema or account probe.

Candidate from existing model_registry.py: `gigachat_2_pro` → `GigaChat-2-Pro`. Text-only v1 endpoint: `https://api.giga.chat/v1/chat/completions`. Model identity and this endpoint appear in the [model selection guide](https://developers.sber.ru/docs/ru/gigachat/guides/selecting-a-model), updated 2026-09-28. No context-window or maximum-output figures were exposed in the accessible text; linked pages outside the four-page authorization were not followed. The guide's certificate-verification-disabled example is unsuitable for this task.

The [authorization reference](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/gigachat-api), updated 2026-07-17, documents Basic OAuth at `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`, UUID4 RqUID, form scope and Bearer API access. Scope variants are PERS (individual), B2B (prepaid business) and CORP (business pay-as-you-go), with the `GIGACHAT_API_` prefix. Documented token lifetime is 30 minutes and OAuth limit is 10 requests/second. No credentials or example tokens were copied.

The [available-models reference](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/get-models), updated 2026-10-07, makes availability account dependent. No authenticated models request was made. ACCOUNT TYPE / SCOPE / MODEL AVAILABILITY UNVERIFIED.

The [chat reference](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat), updated 2026-10-07, specifies UTF-8 messages and failure statuses including authorization, model, context/parameters, rate and server errors. Its detailed request/response schema was dynamically unavailable in the accessible text. Linked OpenAPI was not downloaded. Usage/cache/reasoning semantics, model caps, prices and chat frequency limits are therefore UNKNOWN, not inferred from the fixture parser.

Local safety policy: TLS verification must remain enabled, redirects/proxy environment must not become authority, no implicit retries, and one first LIVE attempt requires an independently accepted bounded policy. A provider-specific CA/proxy contract is UNVERIFIED; the cold existing OAuth implementation has not been admitted for REAL by H35.

Before OWNER GO: verify the account's model/scope, authoritative caps and usage semantics, applicable prices and approved request/output/cost/attempt bounds, TLS trust/proxy policy, and close the mandatory predecessor gates. UI preferences 250000/10000/20000 and H34 synthetic caps are excluded as evidence. Separate independent Windows acceptance and physical owner UX remain required.
