# Models — Stage A account catalog, 15.11.2026

| Internal ID | Provider ID | Catalog | Inference |
|---|---|---|---|
| `gigachat_2` | `GigaChat-2` | AVAILABLE | NOT RUN |
| `gigachat_2_max` | `GigaChat-2-Max` | AVAILABLE | NOT RUN |
| `gigachat_2_pro` | `GigaChat-2-Pro` | AVAILABLE | NOT RUN |
| `gigachat_3_lightning` | `GigaChat-3-Lightning` | AVAILABLE | NOT RUN |
| `gigachat_3_pro` | `GigaChat-3-Pro` | AVAILABLE | NOT RUN |
| `gigachat_ultra` | `GigaChat-3-Ultra` | AVAILABLE | NOT RUN |

The same catalog returned four embedding IDs: `Embeddings`, `Embeddings-2`, `EmbeddingsGigaR`, `GigaEmbeddings-3B-2025-09`. They are not Ordinary Chat text choices. All ten sanitized IDs are in `evidence/stage_a_result.json`.

Catalog presence is account-specific at probe time. It does not prove remaining balance, successful completion, exact response version, output cap or price. No real `ModelContract` has been created.

The [official tariff for individuals](https://developers.sber.ru/docs/ru/gigachat/tariffs/individual-tariffs) (updated 7.10.2026) lists Freemium allowances over 12 months: `GigaChat-2` 250M, `GigaChat-2-Pro` 40M, `GigaChat-2-Max` 25M and `GigaChat-3-Ultra` 50M tokens. These are public plan limits, **not this account's verified remaining balance or assigned tariff**. That page does not list specific pricing for `GigaChat-3-Lightning` or `GigaChat-3-Pro`. The [official quotas page](https://developers.sber.ru/docs/ru/gigachat/limitations) allows one concurrent stream for individuals. Exact output caps and accepted response versions remain UNKNOWN.
