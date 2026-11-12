# WEB28 — H30 Windows Actions evidence-upload repair, isolated CI follow-up

**Дата:** 12.11.2026. Independent CI verifier infrastructure repair, **no new Codex task or HISTORY ID**. Source: H30 closeout commit №575 `597ccc434f293f55b2674f803fedde29dbf84a0f`; independent GitHub Actions [run 43287186090](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43287186090).

## Factual finding
Run 43287186090 on Windows runner at exact `GPT@597ccc434f293f55b2674f803fedde29dbf84a0f` passed all seven focused H30 OFFLINE tests (**7/7 PASS; 0 FAIL; 0 ERROR; 0 SKIP; network/isolation guard 0**). Checkout, Python and dependencies succeeded. The **overall job FAILED only at `actions/upload-artifact@v4`**, because it was asked to upload source files from `C:\h30` and `D:\a\_temp` in one call: `rootDirectory: D:\a\ag_llm\ag_llm is not a parent directory of file: C:\h30\evidence\results.json`. Not an H30 product failure.

## Narrow correction
Keep seven tests, guarded synthetic TEMP, SHA evidence, production and docs unchanged. Add `if: always()` stage: copy available JSON, isolation log and test output to one directory under `runner.temp` (single runner volume). Upload only from that directory. Preserve logs on FAIL. No provider/OAuth/network/paid calls added.

**Scope:** only GitHub Actions evidence packaging. This is a separate post-closeout CI-harness defect and its own atomic commit №576; **not** a second H30 product/source or documentation closeout. CI result of the repaired workflow is NOT RUN at the time of this report and must be inspected in the automatically triggered push run before recommending user merge. GitHub H30 test verdict from run 43287186090 remains 7 PASS; the historical run failure is never hidden. Original H30/H31 TEMP backup folders on source PC are not touched.

[Actions workflow](https://github.com/maxrus82gm-svg/ag_llm/actions/workflows/gpt-web28-h30-independent.yml)
