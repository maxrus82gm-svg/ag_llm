# CHATGPT-WUA-PERSONAL-CHAT-UX-001 — personal direct chat + blocked-model recovery

**Status:** BOUNDED INDEPENDENT WINDOWS **OFFLINE PASS** on candidate SHA `4425a86e295e24c46831958abd9f3413a1d70c20`; GPT numbered publication/own CI readback and physical GUI **PENDING**. Distinct user-directed implementation after GPT №623–624; no Codex B1 task rotation or main merge.

**Owner request 15.11.2026:** выяснить необходимость `GigaChat LIVE` Workspace/числового выбора и починить ситуацию, когда заблокированная модель оставляет кнопку отправки заблокированной после выбора разрешённой. Desk Commander не использовать.

## Cause and reuse
`web_alarm/standard_live.py` previously enumerated **only already-enrolled registered Workspace** and forced a numeric selection because `ProviderSession` and `BudgetLedger` require a verified Ultra workspace identity; GigaChat API does not require such a project. The original probe `GigaChat LIVE` was a deliberately isolated physical evaluation root, not a special LLM mode. Existing Web UI exposed persistent per-chat model selection independently of availability and contained asynchronous preference readback races. No second core or new OAuth client is needed.

## Changes
- `web_alarm/standard_live.py`: following *fresh exact console* `LIVE 12` only, provision managed private `registry.storage_root/personal_chats`, Ultra identity, S3a ledger and first dialogue; register `Личные чаты` once. Reopen preserves existing identity/history. Refuse unrelated pre-existing directory, file, link or broken/unregistered/corrupt ledger instead of adopting/clearing it. No writes on decline, GET, F5 or noninteractive launch.
- `web_alarm/ordinary_provider.py`: capability reports read-only `personal_workspace_id` and active `live_workspace_id`; existing scope restriction and contract/Turn/RAW persist unchanged.
- `web_alarm/ui.py`: `+ Новый чат` in the personal section creates using existing safe POST, no folder picker or required Workspace creation. Prioritise the approved personal chat on first LIVE open; preserve other project history. Explicitly block Send outside approved LIVE root and when selected/pending model is not approved. Disable unavailable/unapproved model choices and ignore stale GET/readback after a newer confirmed model save; return to approved GigaChat-2 resets the former blocked Send state.
- `test_web_alarm_standard_live.py`, `test_web_alarm_ultra_chat_ui.js`: exact-consent/decline/no-credentials/no-enrollment/unknown-or-foreign root/reopen/no duplicate chat/catalog scope, plus JS model block/return/race/F5/default personal chat/direct new chat; retain existing negative and historical synthetic regressions.
- `.github/workflows/wua-standard-live-offline.yml`: Github-hosted Windows 3.12 sparse checkout for the pinned legacy reconciliation file, Python and Node frontend suite; no provider credentials, real OAuth or inference.

**Safety ceiling unchanged:** 1 OAuth, 1 catalog, up to 12 real `GigaChat-2` sends if and only if the user approves at runtime; 128 max output tokens and 8192 max request wire bytes per send, liability bound 99,840; 30 min. No auto paid retry. Five unverified GigaChat model contracts remain forbidden for physical sends. No migration of historical project chats, no new launcher, no permissions outside the local personal root.

## Independent evidence
- Initial candidate [Windows run 43749501341](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43749501341): Python 38 PASS, JS 72 PASS / 2 FAIL, exact diagnostics stored.
- Corrected model text and GET race test [run 43749746730](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43749746730): Python **38/38**, JS **74/74**, PASS.
- Additional personal-first opening/F5 targeting [run 43750081610](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43750081610) on `4425a86e295e24c46831958abd9f3413a1d70c20`: Python **38/38**, JS **75/75**, 0 failures, 0 errors. Includes existing GigaChat model protocol and H38 bootstrap regression. GitHub Actions artifacts retain the complete logs.

**NOT RUN / HOLD:** no actual physical new STANDARD session, no Chrome/F5 owner confirmation, no real LLM call using the personal root, no account tariff/balance verification, no live inference for five other models, no broad independent full S3b/S3c/S9/S13a or release gate. `main` unchanged until owner merges final `GPT`. Current Codex `CODEX-WUA-CHAT-GIGACHAT-LIVE-BOOTSTRAP-001` remains independent and active.

**NEXT:** after successful final GPT readback/CI, owner merges and performs manual STANDARD personal chat UX smoke. Do not ask the user to choose a Workspace number. Separate user GO for first paid personal-chat generation if needed; expand other five models via separately verified provider contracts.
