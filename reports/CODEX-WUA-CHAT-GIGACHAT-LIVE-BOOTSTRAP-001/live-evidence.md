# LIVE evidence

Current status: **NOT RUN / GO PENDING**.

Actual OAuth POST: 0. Actual `GET /v1/models`: 0. Actual inference POST: 0. Actual provider response: none. Thus `PROBE PASS` and `LIVE PASS` are not claimed. The existing credential was checked only for presence, source equality and H38-compatible shape, without displaying its value.

Exact Stage A GO requested: one GigaChat account already configured in Windows user environment, scope `GIGACHAT_API_PERS`, one new enrolled Workspace and empty chat identified in `bootstrap.md`; at most **1 OAuth POST** to `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`, **1 GET** to `https://api.giga.chat/v1/models`, **0 inference**, **0 retries**, no redirect/proxy use, system verified TLS, 10-minute grant. Output is sanitized model IDs, observed scope/result and call counts. Stop on TLS, authorization, scope, malformed response or any uncertain event. This GO does not authorize first reply or other account endpoints.
