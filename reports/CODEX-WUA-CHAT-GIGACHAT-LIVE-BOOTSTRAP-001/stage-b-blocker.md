# Stage B preflight — BLOCKED BEFORE INFERENCE

The USER GO authorizes at most one OAuth, catalog GET and inference POST, but explicitly requires verified model bounds and exact admissible response-version identifiers before sending. No Stage B grant was created and no Stage B provider request was made. Prior Stage A remains the only real account API activity (OAuth 1, catalog 1, inference 0).

## Confirmed

- The prepared Workspace, Ultra identity, empty Chat and existing ledger match the Stage A record; ledger still has 0 events. `GIGACHAT_CREDENTIALS` is present, scope matches `GIGACHAT_API_PERS`; no credential value was read into evidence.
- Local server port 8765 was bindable; after the read-only preflight there was no matching active Tk Ultra/Web Alarm process. System SSL context requires certificate and hostname verification, with 99 loaded CAs. Stage A had already completed verified HTTPS OAuth/catalog.
- The account-specific Stage A catalog included `GigaChat-2`. The [official GigaChat 2 Lite model page](https://developers.sber.ru/docs/ru/gigachat/models/gigachat-2-lite) documents a 128,000-token context and text input/output. The [model selection guide](https://developers.sber.ru/docs/ru/gigachat/guides/selecting-a-model) identifies `GigaChat-2` as the fast, lower-cost Lite choice. The user approved `max_tokens=32`, 1024 request bytes and 1056 conservative liability; these are session bounds, not evidence of a provider output cap.

## Blocking facts

1. H38 `ModelContract.response_models` is an **exact allowlist** of the response's model/version string. The Stage A catalog returned the request model ID but `ProviderSession.discover_models()` exposed only IDs. The searched [official model update page](https://developers.sber.ru/docs/ru/gigachat/models/updates) labels the current GigaChat 2 release “30.1” without an exact `GigaChat-2:<version>` response ID; an [official response example](https://developers.sber.ru/docs/ru/gigachat/guides/structured-output) shows a suffix for **GigaChat-2-Max**, not for the approved Lite model. Neither establishes a safe exact Lite response allowlist. Constructing `GigaChat-2:2.0.30.01` by analogy would be a guess.
2. The official Lite page documents context size, but no separate maximum output-token cap. The API's positive `max_tokens` parameter and the user's 32-token request cap do not prove that model's published provider cap. `ModelContract.output_tokens=32` would be an operator bound presented as a provider contract without the evidence required by the TASK.

Accordingly the mandatory `ModelContract` cannot be formed on the evidence available. Do not widen H38's exact-version check, invent a cap, issue a provisional POST, or consume the GO's OAuth/catalog allowance just to discover the same base IDs. The user explicitly ordered a pre-inference stop on this condition. A future reviewed path needs authoritative exact Lite response-version and output-cap evidence, or an explicit change to the contract/review policy before a new inference decision. No amount was charged by Stage B.
