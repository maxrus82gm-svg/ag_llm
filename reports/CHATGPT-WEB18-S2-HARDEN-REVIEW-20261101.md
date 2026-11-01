# WEB18 — независимая проверка Stage2 shared-storage replace hardening №479

**TASK:** `CLAUDE-WUA-CHAT-S2-REPLACE-HARDEN-001` — Claude 008; commit `main@508cba49c8f21b0e8a9c451b84f1c0f1a8fb6a19`, parent №478. **VERDICT: PASS / BOUNDED SOURCE+AUTHOR-EVIDENCE, DOC ITERATION CLOSED**. Не заявляется independently executed Python/CI/Windows runtime or FULL PRODUCT VERIFIED.

## Проверено
- Изменения разрешённого scope: `context_storage.py`, `test_ultra_chat_storage.py`, точная ротация карточки, отчёт/manifest/evidence; дополнительные `.obsidian/*` — пользовательские, не part of Claude code change.
- Source `rename_workspace` и `rename_chat` вызывает `_replace_verified`; `save_project_context` читает предыдущий текст через `_read_project_context_for_write`, публикует историю эксклюзивно `_publish_project_context_revision` и заменяет контекст через `_replace_verified`. F-01 writers не удалены. Contract: lock/ID, expected_title and byte-format unchanged per author evidence.
- Raw `gate_focused.json`: 166 = 161 PASS / 5 SKIP, exit 0, isolation 0. `gate_all_run1.json`: 1078 = 1075 PASS / 1 ERROR / 2 SKIP, exit 1; HTTP folder-picker WinError10053 — reported flake, root-cause not independently confirmed; 3 module reruns 16/16 per author. `gate_all.json`: 1078 = 1076 PASS / 2 SKIP, exit 0, isolation 0. Note: `all` runner doesn't discover root test_ultra_chat_storage: targeted set separate.
- Raw `mutants_run1.json`: 8 KILLED, 1 SURVIVED (H03, weak test oracle); final `mutants.json`: 9/9 KILLED. Earlier RED failure evidence kept, instead of being hidden.
- Author isolated synthetic environment/standard launcher reported; independent live/paid/real Workspace tests NOT RUN. No authorization for rollout or Stage3.

## Open
- Same-user adversarial folder swap after last handle-path check can affect outside folder before read-back detection; Stage0 §9 excluded this threat. No absolute TOCTOU guarantee.
- `create_chat` staging metadata card still goes through old `_atomic_write_json`; not an observed incident, candidate `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN/UNASSIGNED.
- Tk reader P1–P6, Run Store P9, clean Windows UNC/subst/POSIX/long-path, physical user GUI and independent regression gates unverified.

**Closeout:** №05 `FOLLOWUP-WUA-S2-REPLACE-HARDEN-001` CLOSED in bounded scope, `FOLLOWUP-WUA-S2-CHAT-STAGING-001` OPEN, №06 `EVT-WEB18-S2-HARDEN-PASS-20261101`, №34/40 updated; historical Stage2 №473 REVISE and F-01 №475 limited PASS unchanged. New task requires user approval.
