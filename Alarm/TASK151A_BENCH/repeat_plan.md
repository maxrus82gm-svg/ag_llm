# TASK151A — fixed repeat plan

Purpose: close KT-1 statistically without changing runtime semantics.
No provider call is made by preparing this file.

## Global comparison rules
- Keep Main / Planner / Verifier model assignment identical to the canonical sample: `gigachat_ultra`.
- Keep Planner ON, Final Audit ON, READ ON, DELETE OFF, VERIFY ON and Guard P1 ON.
- Preserve failed/BLOCKED runs in the final table; UNKNOWN provider usage stays UNKNOWN.
- A positive sample requires SUCCESS + Final Audit PASS + complete started/terminal provider-attempt identity.
- Never mix different RAW TASK texts into one statistical series.
- Restore an equivalent initial workspace state before every repeat.
- Do not use Git operations inside benchmark tasks.

## B1-clean
Canonical positive: `20261001_004029_1585f3` = 33,142 tokens.
Positive count: 1/5; remaining: 4.
Permissions from canonical run: READ `.`, WRITE `.`, DELETE OFF, VERIFY ON, tool limit 6.
Initial state: fresh isolated workspace; `b1_probe.txt` absent; no unrelated dirty fixture.
RAW TASK: byte-identical to the canonical `B1_clean/.../task.json`.
Expected physical path: exactly `write_file -> read_file -> verify_file_content(equals)`.
Reset: create a new isolated workspace from empty benchmark root; never reuse the created probe.

## B1-dirty
Canonical positive: `20261001_005308_03a909` = 39,551 tokens.
Positive count: 1/5; remaining: 4.
Keep failed HTTP 429 run `20261001_004215_145316` as negative evidence.
Permissions/task text: identical to B1-clean.
Initial state: fresh isolated workspace with the same unrelated dirty fixture as canonical B1-dirty and `b1_probe.txt` absent.
The unrelated dirty file must be recreated byte-identically before each sample.
Expected physical path remains exactly three tools; extra blocked executed=false attempts are reported, not hidden.

## B2-bounded canonical fixture
Status: DEFINED / NOT YET PROVIDER-RUN.
Fixture template: `Alarm/TASK151A_BENCH/B2_fixture_template/`.
Files:
- `b2_logic.py` — the only file allowed to change.
- `b2_contract_test.py` — deterministic post-change contract check.
- `ultra_ui.py` — tiny UltraApp smoke harness that executes the contract check during construction.

Initial byte SHA256:
- b2_logic.py: `B4DF2ECAAFBBCF37706ACA1D4EBEB583341A8CEFEF4B03AFFFACFC3965796EE0`
- b2_contract_test.py: `2B30986F65925728543BA3475F3F4C2F31FA80B2DA281ABE90E4160AD7F2DD71`
- ultra_ui.py: `59AC8438A5E6497DB3D61EEB15862ECA361C5337AD7C9367CDA99FBC824C478A`

B2 fixed permissions:
READ ON scope `.`; WRITE ON scope `.`; DELETE OFF; VERIFY ON; Guard P1 ON;
Planner ON; Final Audit ON; tool limit 8; Main/Planner/Verifier = `gigachat_ultra`.

B2 intended bounded physical path:
1. Existing-code mutation stage exposes READ+WRITE; Executor may use at most one `find_text` on b2_logic.py only to obtain the current SHA required by precise edit.
2. `replace_text` changes only the constant using that SHA.
3. `python_compile` exactly [b2_logic.py, b2_contract_test.py, ultra_ui.py].
4. `verify_file_content(kind=equals)` for the exact post-change b2_logic.py.
5. `ui_smoke_test` — constructs UltraApp and therefore executes `assert_contract()`.
No separate server_evidence stage is required for `find_text`; it is mutation preparation inside the same persistence stage. No whole-file read, no Git, no unrelated file inspection or repeated exploration.

## B2 fixed RAW TASK
```text
Benchmark B2-bounded.
In the existing code file b2_logic.py change exactly:
STATUS_PREFIX = "PENDING"
to:
STATUS_PREFIX = "READY"
Do not change any other line or any other file.

Use one existing-code mutation stage with READ+WRITE. Inside that stage, use at most one find_text on b2_logic.py only if needed to obtain the current content SHA for precise edit; do not model that lookup as a separate completion/evidence requirement.
Then perform exactly one replace_text for that line and do not modify any other file.
After the change, run exactly one python_compile with paths:
["b2_logic.py", "b2_contract_test.py", "ultra_ui.py"]
Then run exactly one verify_file_content on b2_logic.py with kind=equals and this full exact expected content:
STATUS_PREFIX = "READY"

def status_label(name: str) -> str:
    return f"{STATUS_PREFIX}: {name.strip().upper()}"

Finally run exactly one ui_smoke_test. The smoke imports b2_contract_test and must fail unless status_label("bench") returns exactly "READY: BENCH".
Do not inspect or modify any other user file. Do not use git. Do not add extra READ/VERIFY calls.
Return SUCCESS only if the existing-code mutation, compile, exact source verification, contract check and UI smoke all succeed.
```

B2 reset rule: for every sample create a fresh isolated run workspace by copying the three template files byte-identically.
Do not run the benchmark directly in the template. After a sample, retain its Run Store evidence but do not promote the mutated sample as the next initial state.
R-027 remains a separate stress/outlier baseline for TASK151G and is never counted in this bounded B2 series.

## B3 exact analytical
Canonical positive: `20261001_121011_24b22d` = 34,595 tokens.
Positive count: 1/5; remaining: 4.
RAW TASK must stay byte-identical to `B3_analytical_repair_01/.../task.json`.
Initial state: fresh isolated workspace with byte-identical `provider_accounting.py`, `task.txt`, and empty `Документация/`.
Canonical permissions: READ `.`, WRITE `Документация`, DELETE OFF, VERIFY ON, tool limit 20.
No file mutation is permitted by RAW TASK; positive sample must contain zero physical mutation tools.
Do not mix the 15,071-token semantic response-only B3 into this series.

## Remaining positive samples
| Series | Positive now | Required | Remaining |
|---|---:|---:|---:|
| B1-clean | 1 | 5 | 4 |
| B1-dirty | 1 | 5 | 4 |
| B2-bounded | 0 | 5 | 5 |
| B3 exact analytical | 1 | 5 | 4 |

Total new positive samples required for the current four-series plan: 17.
Provider-heavy sampling is a separate execution step; do not launch it blindly or in parallel.

## Per-run acceptance capture
For every repeat record: run_id, SUCCESS/BLOCKED/FAILED, Final Audit, provider started/terminal counts,
UNKNOWN usage count, total known/complete tokens, role calls/tokens, physical tools in order,
blocked executed=false attempts, repair/replan count, max context chars by role, and initial-state proof.
After five positive samples per series, report every run plus median and min-max range; failed/BLOCKED rows remain visible.
