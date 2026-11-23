# M1-09 GitHub Actions / packaging audit on WUA #670 (24.11.2026)

| Gate | Verified GitHub source/run | Outcome |
| --- | --- | --- |
| WUA focused Windows | [45253916385](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/45253916385), #669 e2b3a3d | SUCCESS: S1 static 16, S2 full 73, D8 1, five negatives, HTTP Python 36, JS 207; every job step success. **Scoped PASS only** |
| WUA STANDARD bounded OFFLINE | [45251979842](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/45251979842), #666 32330655 | guarded-offline job SUCCESS, no real provider. **Scoped PASS** |
| General Web Alarm smoke | [45251979686](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/45251979686), #666 | Four Windows jobs FAILED at Checkout project; test steps SKIPPED. WA4-A full job skipped for push. **BLOCKED/NOT RUN** |
| Full historical S1 private RAW | #666 local 69/69 original SHA-pinned RAW | GitHub only has S1 STATIC 16; full 69 hosted NOT RUN |
| Broad packaging/release | `.github/workflows/web-alarm-tests.yml` has conventional full checkout; full regression mainly PR/dispatch | No overall accepted new-hosted packaging/release matrix. **OPEN M1-09** |
| Colibri producer | [45016490605](https://github.com/maxrus82gm-svg/local_LLM/actions/runs/45016490605), #108 | Producer CI scoped PASS, not actual HOME bridge |
| New Colibri source #114/#115 | [45256596202](https://github.com/maxrus82gm-svg/local_LLM/actions/runs/45256596202) on #114 succeeded; #115 3385c29 docs | Restart-related Colibri source/CI, not WUA LIVE proof |

Broad WUA workflow may need a separate owner-approved engineering task: Windows long path / sparse checkout dependency closure, original guard+fixtures, real pinned SDK, exit codes, full/packaging selection, artifacts and evidence. Do not silently change broad workflow in this source-only prep. No new CI triggered by this docs-only task; author review != independent verdict.
