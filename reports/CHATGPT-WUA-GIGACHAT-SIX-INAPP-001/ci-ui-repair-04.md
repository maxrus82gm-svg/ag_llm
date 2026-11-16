# CI correction 04 — browser Russian label compatibility

Source #636 Windows [43922959294](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43922959294): **57 Python tests all PASS, 0 error/fail**. Strict reconciled physical send-site inventory passed after reviewed exact AST pin update. Node DOM **75 PASS / 1 FAIL** of 76: the existing blocked-model test expects substring `пока не разрешена`, while new UI message omitted `пока`. Restoring those two words preserves the accurate model-specific warning and makes the existing regression stable; no condition or authorization changed. No credentials/API traffic, history reset or launcher modification.

The #637 authoring change adds the source-locator status to №34/40 and an OPEN followup №05, without overstating six-model live acceptance. Windows rerun pending at publication. General full-checkout long-path smoke remains a separate historical CI failure.
