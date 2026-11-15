# Stage B contract reconciliation — OFFLINE PASS, 15.11.2026

## REUSE CHECK

The existing H38 `ProviderSession`, `RealGigaChatTransport`, `OrdinaryProviderFactory`, `TurnService`, RAW store and `BudgetLedger` remain the only route for a real Web Alarm reply. `web_alarm.live_bootstrap.serve_one_inference` still composes them for a single reviewed grant. No OAuth, catalog or inference request was made for this amendment. Tkinter, STANDARD, TEST and historical Workspaces were not changed.

## Contract change

`ModelContract.context_tokens=128000` is the documented `GigaChat-2` context limit. Its existing `output_tokens` field now explicitly means the operator's per-attempt output bound, `32` for this proposed first call. New `provider_output_cap_tokens=None` records the separate provider maximum as **UNKNOWN**; it is not inferred from `32`. The existing wire and H38 admission checks still require `0 < max_tokens <= output_tokens`, `len(wire) <= 1024`, and `len(wire)+max_tokens <= 1056` under the proposed approval. No separate price or remaining balance is claimed.

`version_mode='DISCOVER_GIGACHAT_2'` is allowed only for one `gigachat_2` contract, one inference, a 32-token answer ceiling, a 1024-byte request ceiling and a 1056-token conservative liability ceiling. Its response must match the full ASCII pattern `GigaChat-2:2.0.[0-9]{1,3}.[0-9]{1,3}`. This is a bounded acceptance syntax, **not** a claim that any particular version exists. Pro, Max, another family, an absent version and extra suffixes fail. The actual observed full ID is written to the Turn and the account's durable confirmed-version marker before successful publication. A later grant for this model must use `version_mode='EXACT'` and exactly that observed ID. A pin write/readback failure becomes UNKNOWN. A model mismatch does not publish an assistant message, retains allowed usage evidence and never retries.

## H38 impact and checks

The source change is limited to `gigachat_runtime.py`, the durable Turn replay validator in `web_alarm/turn_service.py`, and corresponding AST policy pins in `rt002_multimodel_reconciliation.json`. No new endpoint, physical send path, OAuth path, ledger operation, TLS bypass, retry path or browser authority was introduced. The single physical inference route remains `RealGigaChatTransport.send_bytes`. Existing admission, reserve/SENT ordering, grant counters, account fencing, verified TLS and replay protection remain active.

MockTransport and loopback HTTP: 37/37 addressed tests PASS, including acceptance/pin, exact future grant, foreign family, malformed suffix, usage on rejection, request/provider-cap limits, pin failure UNKNOWN and F5-style GET/reopen without a second POST. Guarded S1: 69/69 PASS; guarded S2: 73/73 PASS; zero isolation violations. Logs: `evidence/amendment_offline_sealed.txt`, `evidence/amendment_s1.txt`, `evidence/amendment_s2_final.txt`. The prepared real Workspace ledger was read again after the OFFLINE run: 0 events.

Stage B physical calls under the old conditional GO and this amendment: OAuth **0**, catalog **0**, inference **0**. A new explicit user GO is required before any provider call under this revised contract.
