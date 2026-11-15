# Proposed fresh USER GO — Stage B, one real response

This is a proposal for separate approval, not an executed grant. The earlier conditional Stage B GO does not authorize the revised contract.

Authorize this task only, existing `GIGACHAT_API_PERS` account and the prepared isolated Workspace/chat named in `bootstrap.md`. One `GigaChat-2` (`gigachat_2`) request with the exact text `Ответь одним словом: готово`. Maximum one OAuth POST, one GET `/v1/models`, one POST `/v1/chat/completions`; zero automatic retries; grant expires within 15 minutes. No other model, tool, attachment or historical user message. Bound the UTF-8 wire to 1024 bytes, `max_tokens=32`, and conservative request-plus-output liability to 1056 tokens.

Use verified TLS and the existing H38 admission, ledger, account fencing and replay protection. Set `context_tokens=128000` from official model documentation; `output_tokens=32` is the operator limit; `provider_output_cap_tokens=None` explicitly remains UNKNOWN. Permit one first response-version observation only if its full ID matches `GigaChat-2:2.0.[0-9]{1,3}.[0-9]{1,3}`. Save the exact returned ID and require it exactly for any later grant. Stop on error, mismatch, UNKNOWN or ambiguous usage; do not repeat or substitute another model. Public Freemium terms do not establish this account's balance, tariff or zero cost. Token spend is limited by the approved liability, subject to actual account terms.

Before spending a control call, recheck fresh Workspace identity and ledger, process/account ownership, credential scope, certificate verification and bind the loopback server. After a success, verify the real answer in Web Alarm, RAW/Turn/ledger and usage, then read/reopen after F5 without another POST. Record safe diagnostics and physical call counts only; do not publish secrets, tokens or raw OAuth responses.

**Approval requested:** a new explicit Stage B GO for precisely this envelope. No provider request is permitted until it is given.
