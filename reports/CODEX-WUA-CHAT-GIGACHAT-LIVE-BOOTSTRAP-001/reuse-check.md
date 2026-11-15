# REUSE CHECK

Tkinter `ultra_ui.py` calls the existing `server.py`; the Web path and Tk path share `gigachat_transport.py` endpoints and credential environment names. The Windows **user** environment contains nonempty `GIGACHAT_CREDENTIALS` and `GIGACHAT_SCOPE`; both exactly match this process's inherited values. Credential shape passes H38's printable ASCII/length checks. Scope is `GIGACHAT_API_PERS`. Values of credentials and token were never printed, copied, hashed into evidence, or written to the repository. Account entitlement and token validity remain unverified until approved OAuth/catalog calls.

H38 `ProviderSession` already owns bounded OAuth/catalog/inference calls, TLS, per-grant counters and credential access. `OrdinaryProviderFactory.for_session()` and `create_server()` already connect the real provider to existing Ordinary Chat, Turn, RAW, history, and `BudgetLedger`. `model_registry.py` already contains all six model records. This task adds only `web_alarm/live_bootstrap.py`, which composes those objects for an operator and separates probe-only from single-inference grants. No Tkinter, permanent launcher, transport, OAuth or ledger implementation was changed.

System SSL context has CERT_REQUIRED, hostname checks and 99 loaded CAs. A live provider TLS handshake and any provider-specific trust chain remain unverified. No trust bypass was added.
