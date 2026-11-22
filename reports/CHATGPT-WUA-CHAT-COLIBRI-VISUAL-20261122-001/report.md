# Ultra Chat visual alignment with Colibri — author submission

TASK ID: CHATGPT-WUA-CHAT-COLIBRI-VISUAL-20261122-001
Baseline: WUA GPT #650 945d44097329bc681da534d5e6e5ae6f29289617; main #649 2d63d11681ae8d9cf64e0d4a34c4cac06410393b.
Colibri visual reference: GPT_2_local #108 883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea, Client_Ultra_LLM/web_assets/client.css (read-only).
PLAN_READ: 2026-11-22T16:30:42+05:00 SHA 8ee1bbebe505e98467dd8d5595eaa07ea2f73175aa01fa19910c6e2a169df506; no shared plan modification.

## Implemented
- Exact Colibri palette for chat (background #0c1017, panel #151b25, cards #1c2634, selected #282640 / #8f8aff, assistant #222d3d, user #373565), desktop navigation rail with Web Alarm Ultra branding; narrow view uses existing navigation. Existing Workspace and personal groups retained. No right inspector.
- Existing model picker and disabled voice placeholder above composer; send icon inside input, retry/recovery keeps explicit text. Drag handle and keyboard resizing, clamped height, localStorage stores layout height only.
- Per-message copy of existing text; accessible feedback; oversize omitted messages are not copied. Dates already provided by the history projection remain visible.
- Read-only metrics attached only to matching SUCCEEDED assistant RAW message IDs in the existing bounded durable usage read. Known token fields preserved, absent values not zero. Request elapsed seconds from durable SERVER turn_started/turn_result timestamps, not measured generation latency. TEST explicitly labelled. Legacy messages lacking records receive no invented metrics. No accounting or request changes.
- Existing true streaming/reasoning text is not available in ordinary GigaChat (stream=false), so no fake controls/metrics or extra transport. Status invalidation, all-model check and profile sync remain separate requirements.

## Author tests (isolated TEMP snapshot, no live storage)
- node --test test_web_alarm_ultra_chat_ui.js: 78/78 PASS (new copy/resize/metrics test).
- node --test test_web_alarm_evm_ui.js: 50/50 PASS (E19 updated only for intentionally changed DOM position; admission checks retained).
- node --test test_web_alarm_operator_ui.js: 77/77 PASS.
- Python unittest test_web_alarm_perchat_usage_settings.PerChatTests test_web_alarm_ordinary_application: 22/22 PASS; new durable per-message metrics correlation/paging/chat isolation test included.
- py_compile for three changed Python modules: PASS.
- Broader Python run (46 tests): 42 PASS, 1 skip, 1 D8 FAIL, 2 fixture errors on missing context_defaults.json. D8 reproduced identically on exact base #650 (pre-existing model_registry import); unchanged candidate failure, not closed. Both Tk errors rechecked individually after restoring tracked config from baseline: PASS 2/2. Broad suite not rerun as a complete batch.
- Headless Chrome offline fixture: exit 0; 1584x805 viewport, nav x=0 width=174, main x=422, input x=455 y=563 width=1096 h=220, send x=1513 y=746 w=30 h=29, sendInside=true, navSeparate=true, history height=314.5. Synthetic layout snapshot only, not a live server GUI acceptance.
- Independent Windows CI, owner GUI acceptance, real/paid API requests, STD restart: NOT RUN. No claim of independent PASS.

## Handoff
Author SUBMITTED / REVIEW PENDING. Candidate changes are source-only and do not touch runtime files or reset local Git. One atomic publication to GPT only; owner merges main after safe synchronization preserving local shared plan and pending documentation. No direct changes to Colibri.
