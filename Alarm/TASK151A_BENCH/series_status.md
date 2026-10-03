# TASK151A benchmark series status

## KT-1 statistical result
All four canonical comparison series now satisfy the doc20 initial minimum: five positive SUCCESS / Final Audit PASS samples per profile/configuration. Every positive has complete started/terminal provider-attempt identity, complete context-accounting fields, zero UNKNOWN usage and preserved fixed task/config/reset rules.

| Series | Positive | Median tokens | Range tokens |
|---|---:|---:|---:|
| B1-clean | 5/5 | 36,060 | 31,229–36,875 |
| B1-dirty | 5/5 | 30,647 | 25,158–41,175 |
| B2-bounded | 5/5 | 46,284 | 43,694–60,044 |
| B3 exact analytical | 5/5 | 33,019 | 31,596–38,668 |

B1-clean physical path is always exactly `write_file -> read_file -> verify_file_content(equals)`.
B1-dirty uses the byte-identical B1 RAW TASK and byte-identical unrelated dirty fixture; physical path is the same exact three tools.
B2-bounded uses fresh byte-identical copies of `B2_fixture_template`; every positive physical path is exactly `find_text -> replace_text -> python_compile -> verify_file_content -> ui_smoke_test`.
B3 exact uses the byte-identical repaired analytical RAW TASK and source files; every positive physically performs only `read_file -> read_file`, with no user-file mutation.

## Negative / outlier evidence retained
- B1-dirty `20261001_004215_145316`: FAILED on HTTP 429; Dredd usage remains UNKNOWN and is not converted to zero.
- B2 pilot `20261001_143717_a1fda6`: BLOCKED/PENDING, 19,473 tokens; task wording caused invalid separate find_text evidence stage and was corrected before canonical B2 was frozen.
- R-027 remains separate B2 stress/outlier evidence: BLOCKED after 1,736,351 known tokens and ~924.5k-char Executor context; it is not mixed into bounded B2 statistics.
- B3 semantic response-only and the original T-030/R-030 false-PASS history remain separate evidence and are not mixed into the exact analytical five-run series.

## Accounting conclusion
`benchmark_inventory.json/.md` currently inventories 24 isolated benchmark RUN. Started/terminal attempt identity and context schema validate across the inventory. The only expected incomplete usage is the retained HTTP 429 negative run. Statistical sampling required for KT-1 is complete.

NEXT: reconcile canonical docs and close TASK 151A / KT-1; TASK 151B Evidence Freshness is the next program stage.
