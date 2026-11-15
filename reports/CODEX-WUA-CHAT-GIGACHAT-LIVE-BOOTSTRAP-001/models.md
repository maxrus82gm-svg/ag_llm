# Models — Stage A account catalog, 15.11.2026

| Internal ID | Provider ID | Catalog | Inference |
|---|---|---|---|
| `gigachat_2` | `GigaChat-2` | AVAILABLE | **BOUNDED REAL PASS 15.11** — `GigaChat-2:2.0.30.01`, `Готово` |
| `gigachat_2_max` | `GigaChat-2-Max` | AVAILABLE | NOT RUN |
| `gigachat_2_pro` | `GigaChat-2-Pro` | AVAILABLE | NOT RUN |
| `gigachat_3_lightning` | `GigaChat-3-Lightning` | AVAILABLE | NOT RUN |
| `gigachat_3_pro` | `GigaChat-3-Pro` | AVAILABLE | NOT RUN |
| `gigachat_ultra` | `GigaChat-3-Ultra` | AVAILABLE | NOT RUN |

The same catalog returned four embedding IDs: `Embeddings`, `Embeddings-2`, `EmbeddingsGigaR`, `GigaEmbeddings-3B-2025-09`. They are not Ordinary Chat text choices. All ten sanitized IDs are in `evidence/stage_a_result.json`.

Catalog presence is account-specific at probe time. The **initial** Stage B attempt stopped after OAuth/catalog and **before** inference (`stage-b-live-stop.md`). A **separately approved replacement** then returned one real `GigaChat-2` completion (`Готово`, version `GigaChat-2:2.0.30.01`, 100 prompt + 4 completion = 104 actual tokens; grant CLOSED). Details: `stage-b-user-retry-success.md`, `evidence/stage_b_user_retry_result.json`. This proves one model's bounded text completion, not the account's tariff/balance, other five models' inference, independent provider output cap or pricing. The bounded Lite `ModelContract` is specified in `contract-amendment.md`; no second inference is permitted under either spent grant.

The [official tariff for individuals](https://developers.sber.ru/docs/ru/gigachat/tariffs/individual-tariffs) (updated 7.10.2026) lists Freemium allowances over 12 months: `GigaChat-2` 250M, `GigaChat-2-Pro` 40M, `GigaChat-2-Max` 25M and `GigaChat-3-Ultra` 50M tokens. These are public plan limits, **not this account's verified remaining balance or assigned tariff**. That page does not list specific pricing for `GigaChat-3-Lightning` or `GigaChat-3-Pro`. The [official quotas page](https://developers.sber.ru/docs/ru/gigachat/limitations) allows one concurrent stream for individuals. Provider output caps and response versions for **other models** remain UNKNOWN. For `GigaChat-2`, only the **observed pinned** response version `GigaChat-2:2.0.30.01` is confirmed; future changes are not automatically approved.
