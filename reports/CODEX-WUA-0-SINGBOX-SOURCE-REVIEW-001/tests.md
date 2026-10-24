# Current reproducibility — amendment01

Source-only runner from `M:/GitHub/ag_llm` with existing Python3.12.10/jsonschema4.26.0, no dependency install:

```powershell
& './.venv/Scripts/python.exe' -I -X utf8 -B integrations/wua_chatgpt_mcp/tests/singbox_source_review_suite.py
```

It reads the already authorized external source/ZIP at paths recorded in provenance. **It never downloads anything**. If the source is unavailable on the verifier host, tests are NOT RUN until exact pinned bytes are supplied. Do not run the historical blocked-phase report helpers as current final report generators.

Final source attempt `amendment_01/runs/source-20261024-213332-1493e644`:30/30 PASS,0 FAIL/ERROR/SKIP =11 source checks+19 existing pure broker contracts. Earlier source attempt213226 also30/30, retained; clean unused imports justified repeat. Initial no-bundle phase19/19 remains historical, not added to final counts. Full IDs and source hashes in result/pins; source-specific checks inspect21 files and54 anchor loci, full source-tree ledger pins1013 files.

Negative oracles: wrong archive hash/revision, missing source/module files, critical go.mod/go.sum mismatch, inserted unknown top-level option field, changed config default/merge and hidden-source branch, selected outbound changed to literal unapproved. Known native empty/default already DIRECT; separate default-DIRECT mutant targets existing strict review intent and is rejected by prior validator. Neither mutant runs Go. These are bounded lexical/hash tripwires on reviewed source, not native behavior or whole-program proof.

Current engine/downloader executed counts: one approved ZIP GET artifact (GitHub→codeload redirect), core0, Go/build/test0, dependency download0, native network tests0. Runtime SDK/NPFS/network suites NOT RUN. Pure test runner rejects socket/child process creation; this is instrumentation, not OS isolation.

`amendment_01/seal.py` verifies manifest,107 old project file hashes, external ZIP hash and1013 source files. `amendment_01/rotate_card.py` is single-use; do not repeat. Download script is also single-attempt and must not be rerun without new USER GO.

Source excerpts and `other_outbound_mutant.go` originate from SagerNet/sing-box exact revision; the latter is an intentionally modified review artifact, not operational code. Upstream license retained as `amendment_01/evidence/upstream_LICENSE.txt`.
