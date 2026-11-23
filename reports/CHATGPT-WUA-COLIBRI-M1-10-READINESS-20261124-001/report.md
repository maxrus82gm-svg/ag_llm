# WUA #671 — M1-10 read-only preparation, LIVE HOLD

**TASK:** CHATGPT-WUA-COLIBRI-M1-10-READINESS-20261124-001; **history:** H-CHATGPT-000025; **author:** ChatGPT WEB35; **status:** SUBMITTED / DOC-SOURCE READY / REVIEW PENDING. Independent acceptance of own work NOT VERIFIED. MVP1 PARTIAL / NOT OWNER ACCEPTED.

GitHub WUA main=GPT #670 `88728ed3d1a249351626c13c8f4627d791fc1698`. Colibri main=GPT_2_local #115 `3385c29a1c1104e75fed1467fd1c1ff5bb596802`. Pinned Colibri #107 contract v1.0.0 `2d9e7f6fb860fdd53747f4ba75350d15bab27877`, #108 producer `883d91d4ad2e47fc260bfd7b1e61d230f8fb99ea`. Canonical openapi Git blob `e578c496aee64ccd0dba1279000e7e0ab12a764a`, SSE Git blob `e39b255f539ce69d21e263f0e7943bd7d9fa112a`, equal at #107 and #115. WUA `web_alarm/colibri_bridge_transport.py` pins version+SHAs; checks protected profile/descriptor/Windows DACL, loopback auth, health, catalog, no redirects. Actual HOME installed build, token ownership and slot occupancy NOT INSPECTED.

**Important source finding:** Bridge v1 GET /health and /models are scoped `read`, but neither reports active/queued request counts, and READY alone cannot prove available idle target. GET /requests/{id} is `chat` permission, not initial read-only. Need Colibri 14 independent safe occupancy evidence and separate owner exact-scoped M1-10 GO.

**CI:** focused WUA run 45253916385 success; STANDARD offline 45251979842 success. Broad `Web Alarm smoke` 45251979686 fails Checkout before tests; M1-09 remains PARTIAL, packaging OPEN. Details `ci_inventory.md`. Colibri #115 source update is no deployed HOME proof.

**Deliverables:** assignment.md; read_only_preflight.md; handoff_colibri14.md; ci_inventory.md; this report; task_record/history and №05/06/34/40 in one atomic #671 GPT commit. LOCAL-PLAN-01 re-read before TASK: `PLAN_SHA256=9e269f901164b7328229f37d6e58ee24dee04439c5d912eb819a7d39ca8b2cef`. Local WUA-only №34.1 update separately after GitHub publication, Colibri row/archive not touched.

**NOT RUN:** new independent Windows CI on this documentation-only task; physical browser, real Colibri GET, proof idle/queue, actual engine streaming/usage/cancel, paid cloud M1-11, user acceptance M1-12. Live calls=0, scans=0, tokens read=0, engine/process changes=0. Historical full S1 69 local only. No STANDARD restart; no change to unrelated `Документация/AI_Info.pur`.

**NEXT:** forward handoff to Colibri Ultra 14, receive installed/idle/ACL evidence; then request explicit bounded read-only M1-10 OWNER GO. Further actual inference/paid require separate grants. Broad CI repair separate TASK. No MVP2 or archive.
