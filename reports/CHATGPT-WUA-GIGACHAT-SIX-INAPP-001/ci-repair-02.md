# CI correction 02 — audited source fingerprint reconciliation

**Task:** `CHATGPT-WUA-GIGACHAT-SIX-INAPP-001`; implementation #633, offline-error correction #634. GitHub Windows [run 43922363800](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43922363800) executed 57 Python tests: **56 PASS, 1 expected FAIL due to exact AST safety inventory**. The unavailable-model regression is repaired and passing; no other Python error. JavaScript suite was skipped because strict guard stopped first.

The fingerprint diagnostic in the Windows workflow printed four exact CPython 3.12 `ast.dump(node, include_attributes=False)` SHA256 values; only these four changes in `gigachat_runtime.py` are reconciled:

| Pinned node | Newly measured AST SHA256 |
| --- | --- |
| `ProviderSession` | `2b6bc1bdeb41701a535ce5bdf8422b5b3896f5abf423ffd3250880336dcb75cb` |
| `RealGigaChatTransport` | `b9f712745ec69ba51d8712917bd6dc93bcbeeae9fd4e7343bb79f6235e3f4cdb` |
| `ModelContract` | `9fe852a4e700b678da190f2a53ba4be1892ac3d20b3e8006c92385775ee707fe` |
| `response_model_allowed` | `67d170f7a9bdfdb919cc053bc4c4d96971b406d1bac866f2a93a6c9f60800c5d` |

**Source review:** The scoped diff extends model-family response validation and durable per-family version pinning, and bounds six-model grant sessions; it does NOT add a third physical send site, OAuth backend, redirect/proxy path, unsanctioned retry or URL input. Runtime still exposes exactly existing `ProviderSession.request` (one OAuth/catalog stream) and `RealGigaChatTransport.send_bytes` (one physical send) with shared admission/ledger; `test_exact_census_rejects_new_runtime_send_or_changed_authority` requires exact two-site inventory and a negative mutation. Fingerprints are not a broad bypass; unexpected modifications remain fail-closed. This manifest update is a reviewable scoped micro-correction, not proof of release.

**Next:** independent GitHub Windows full bounded profile against the exact #635 SHA, JS DOM and H31; owner must not merge until green and later perform manual real API acceptance. No credentials / real GigaChat API were used in diagnostics. General Web Alarm smoke historical long-path checkout issue remains separate.
