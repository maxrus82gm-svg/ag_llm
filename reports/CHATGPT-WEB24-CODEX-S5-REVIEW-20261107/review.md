# WEB24 independent review — H-CODEX-000020 / Stage5 OFFLINE TEST

**Date:** 2026-11-07. TASK `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001`; HISTORY `H-CODEX-000020`. Published author source **commit №523**, `main@4f155ca2e60224a77f943e813ec0992834f6b97c`. B1 WAITING and B1.1 exactly H-CODEX-000020; native finish `ROTATED`, exit 0.

## Verdict

**PASS / BOUNDED INDEPENDENT WINDOWS Stage5 OFFLINE core, Web HTTP, Tkinter and JS UI. READY FOR №37 Stage6 OFFLINE B2 preparation.** This does **not** mean complete cross-host portability, current final-code visual browser acceptance, whole Ultra regression, production live GigaChat, paid policy or Colibri approval.

The implementation reuses `OfflineUltraChatService`, existing Workspace Registry, `TurnService`, S4A/4B fake provider, RAW and Run Store. In synthetic Workspace tests: two isolated Chat and two Workspace paths, model affinity, selected context, 2-message history, external cancellation to UNKNOWN with usage, no assistant false SUCCESS, conflict and same-key identity after process restart without second transport, final HTTP lost-reply recovery, legitimate Tk controls and Web+Tk shared history.

**Source and evidence integrity:** independent Windows CI checks **83/83 published manifest files** by exact SHA-256+UTF-8 byte size, 62 raw exact and 21 matching only after Windows Git LF/CRLF normalization. 0 unmatched; no arbitrary content repair. Author originally reported 209 Python PASS, 165 JS PASS, final Windows smoke PASS, early RED for lost HTTP reply and START/runner issues preserved. Author-only 595 user files and editor baseline, launcher STANDARD; independent personal-workspace audit NOT RUN.

## Independent Windows evidence

Pinned Windows `windows-latest`, Python 3.12.10, Node 22, mcp 2.2.0, temp fixtures, strict guards, no provider/OAuth/credentials or paid network use by tests. Completed [GitHub Actions run 42286738432](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42286738432), job `128129391441`, **SUCCESS**:
- H20 Stage5 real Tk widgets + HTTP **13 PASS**
- Web history/storage **43 PASS**
- Stage4A and Stage4B **58 PASS**
- Stage3 Turn/HTTP **30 PASS**
- RAW crash/idempotency/path **14 PASS**
- Run Store v2 **51 PASS**
- **Main Python 209 PASS**; independent reviewer custom boundary **3 PASS** (cross-Workspace same key, bad model reject, fresh-service same-key no replay); HTTP client disconnect scenario **10/10 PASS** against final source; JavaScript UI/Operator/EVM **165 PASS**
- **Total 387 checks PASS, 0 FAIL/ERROR/SKIP**. Strict network, DNS and credential negative tests emitted expected denials. No real external LLM requests.

**Negative verifier CI evidence preserved:** [42284763742](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42284763742) and [42285072025](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42285072025) were verifier manifest-checker failures due Windows checkout line endings and misencoded literal backslashes; [42285502197](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42285502197) caught reviewer fixture missing `Path.resolve()`; [42285819723](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42285819723) failed on missing `mcp` dependency when importing Tk; [42286331719](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/42286331719) failed because sparse checkout omitted existing `context_defaults.json`. These are independent harness preparation errors, not validated product defects. They are **not** counted PASS and are not erased by the final success. The final runner used exact pinned published H20 product SHA, not changed implementation. Distinct corrective commits numbered №524–529 were required for one review CI harness: **PROCESS NONCONFORMITY** with strict one logical result→one atomic commit rule. No history rewriting; next verifier must validate harness in scratch before the one numbered publication. Documentary acceptance is one atomic commit №530.

## Limits and open records

1. **KEEP OPEN / new FUP:** actual end-user Chromium/GUI visual smoke after the author's *last* HTTP disconnect fix and shared model-list update was NOT RUN on final SHA. Author browser smoke happened on preceding revision; current pinned independent HTTP/Tk/Node test PASS does not replace a final visual browser session. Test visible two dialogs, model menu, send, F5, cancel, no mixing, retry; no external calls.
2. **KEEP OPEN / new FUP:** clean independent Windows installation/move to different path §2.4 not run; CI Windows runner with sparse checkout is not a deployment portability acceptance.
3. **KEEP OPEN** historical `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001`; original WinError writer-lock cause not proven by Stage5 regression. Other UI access, full Ultra suite, budget B2 and production gates remain their own tasks.
4. **CLOSE BOUNDED:** `FOLLOWUP-WUA-S4B-STAGE5-UI-001` for validated offline Web/Tk integration. Scope is precisely test fixtures and bounded independent Windows CI.

**NEXT according to approved №37:** Stage6 **RT-002/B2** policy/attempt ledger/budget fail-closed work, coordinated with approved №20 §5а rather than second budget core; independent QA and no real provider calls. Stage7 genuine GigaChat requires separate USER GO and accepted 5–6. **Colibri only after full №37 completed/accepted.** No Stage5 claims for production live/portability or future Blueprint implementation.
