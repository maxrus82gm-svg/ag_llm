# WUA #666 — S1 / S2 / D8 closure and scoped CI

**Verdict: LOCAL OFFLINE PASS, hosted GitHub Actions NOT VERIFIED at authoring; MVP1 PARTIAL, LIVE NOT RUN.**
Owner GO 2026-11-24, accepted #665 baseline d1d44f07d10da8bf6a9f84904bd62454842a2fa0, isolated source candidate c13027b72082a3d0368dbbfbe10fc486fab78f5d. PLAN_READ 2026-11-24T00:42:36+05:00 SHA256 f37d7cc328bf1a5b3fde045a613b2882d076035a1978f93f0c493ec3bce3249b, archive SHA256 1071b531a3985ecb08d474651f73cedaf5aeb73cec1108b19daf764848fb4102. No actual HOME Manager or STANDARD touched, no paid cloud or real inference, no MVP2.

## Source changes and admission guards

- S1 failure came from outdated production network importer census and exact function/reference hashes after launcher/EVM changes. Reconciled the actual HTTPX Bridge import and reviewed launcher/EVM AST pins, keeping unknown network send detection, pinned RAW evidence and negative checks strict. FULL historic S1 69 is not replaced by its hosted static subset.
- S2 failure came from outdated exact policy/ledger/Turn AST admission digests and newly reviewed Windows ACL/Colibri schema external roots. Pinned current exact ASTs and only the known jsonschema/win32api/win32con/win32security imports; dynamic/unknown policy import and unknown external dependency remain rejected. Moved the S1 CI runner under this report to keep production graph and guard intact.
- D8 refusal came from direct root model_registry import by the read-only Ultra Chat history adapter for legacy TEST model choices. Its explicit TEST-only path now calls a pure test_model_selector with the same enabled non-local GigaChat choices. No transport import, second model registry, modified cloud path or hidden Colibri launch. D8 unmodified anti-import test now PASS.
- New Windows GitHub Actions workflow gpt-wua-666-safety-gates.yml runs S1 STATIC 16 only (not FULL 69 private RAW), S2 FULL, D8, mutation negatives and ordinary HTTP/UI/JS with no credentials/production. Dedicated CI source runner fails if no tests or security guard violations. Real GitHub workflow run remains NOT RUN/UNVERIFIED until observed.

## Verified isolated Windows evidence

| Gate | Result | Original log |
| --- | --- | --- |
| Historic FULL S1 with pinned private RAW | 69/69 PASS, exit 0 | S1_69_FINAL.txt |
| FULL S2 import/policy/ledger | 73/73 PASS, exit 0 | S2_AFTER_RUNNER_MOVE.txt |
| Hosted-equivalent source S1 only | 16/16 PASS, zero isolation violations | S1_HOSTED_RUNNER.txt |
| D8 | 1/1 PASS | D8_CANDIDATE3.txt |
| Negative mutation tests | 5/5 PASS | NEW_NEGATIVES_AFTER_MOVE.txt |
| Ordinary + model/EVM Python | 88/88 PASS on repeat | HTTP_88_RETRY.txt |
| JavaScript UI | 207/207 PASS | JS_207.txt |

One original 88-test local run reported WinError 10053 (connection aborted by Windows in existing EVM Http test); single test and full 88/88 repeated PASS. Initial failing log retained, root cause not proven fixed. Two candidate harness mistakes were corrected: an unknown outbound site was wrongly expected to be allowed, and default unittest initially discovered zero S1 tests. The new explicit S1 runner requires 16, and wrong root placement of its CI helper failed S2 correctly; helper moved out of production graph and S2 rechecked full 73 PASS. All original logs and SHA256/byte counts preserved in gates.json, outside Git in the approved local evidence vault.

## Remaining CI and LIVE HOLD

Full S1 requires private RAW not available in GitHub CI. The hosted workflow outcome MUST be verified after publishing, and a long-path/checkout failure or missing triggered job is NOT PASS. Historic full project CI, WUA package/install, physical HOME ACL/launch/identity, real Colibri status/stop, real usage/caching, long streaming and nonempty system/tool role handling still OPEN. MVP1 M1-10 real read-only needs separate owner permission; M1-11 local/cloud inference and any paid API require further GO. Colibri Ultra 14 independently configures multiple Managers; WUA has not connected to them. The above closes the HISTORIC SOURCE GATES within OFFLINE scope, not full MVP1 acceptance.

NEXT: inspect actual hosted workflow run and fix any real CI failures, coordinate Colibri launch/contract version in shared plan before requesting separately authorised read-only HOME preflight. Shared Colibri section and archive must not be edited by WUA.
