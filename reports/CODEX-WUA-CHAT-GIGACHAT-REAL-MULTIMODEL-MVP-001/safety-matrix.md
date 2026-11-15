# Safety / ordinary applicability

| Gate | Авторское evidence | Статус / граница |
|---|---|---|
| S1 | 69/69 standalone, historical local RAW verified by unchanged runner | AUTHOR PASS; GitHub RAW availability NOT RUN. Census new sinks explicitly pinned; independent pin review pending. |
| S2 | 73/73 standalone, exact existing policy; dependency graph retains all entrypoints | AUTHOR PASS; new authority modules pinned, no policy formula change. |
| S3a | Existing 35-test ledger suite inside broad regression; ledger source unchanged | AUTHOR regression pass; existing durable facts reused, no historical adoption. |
| S3b ordinary | Exact final Request bytes; reserve/SENT before mock physical dispatch; no authority/proxy/retry/redirect bypass | AUTHOR bounded PASS; actual TLS/network semantics not externally tested. Legacy routes stay HOLD. |
| S3c | Ordinary has no tools or filesystem mutation requested by a model; user/assistant RAW is server storage, not model tools | Tool-verification reserve N/A to this route; full agent S3c remains OPEN, not closed by N/A. |
| S4 | Bounded context_storage readers + 32-message/2048 B message/8192 B aggregate; long/unreadable context denied | AUTHOR ordinary bound; model-controlled file-read tools absent. Full S4 not claimed. |
| S5 | Separate metadata/settings and snapshot; model choice restored HTTP/DOM; requested answer clamped to session/model bound and reported effective | AUTHOR bounded; physical owner UX pending. Planner/Final Audit factors untouched/HOLD. |
| S9 | One attempt, cached full-input, nested reasoning, missing usage UNKNOWN, model change/reopen/replay | AUTHOR ordinary PASS; no monetary estimation, no full-route independent S9. |
| C1 | Text-only common parser rejects function/tool calls; HTML rendered as text; no agent final protocol | Ordinary protocol covered by existing parser tests. Agent final protocol scope unchanged/HOLD. |
| C2 | Existing Workspace/Chat no-follow/writer identity, exact session root and registry | AUTHOR ordinary scope; no model path predicates/tools. Full agent C2 OPEN. |
| S13a | Separate independent verifier required | NOT RUN / HOLD. No author substitution. |
| TEST → REAL | TEST constructs exact fixture types/TEMP; no launcher/env authority option | Author regression/negative controls PASS. Native permanent CMD blocked by parent process guard, NOT RUN. |
| Recovery | RAW assistant write failure→explicit same-key recovery without second POST; UNKNOWN timeout/replay; grant reuse/account owner denied | AUTHOR bounded; physical power loss/cross-machine owner untested. |
| Secrets | early env/.env/DNS/socket guard; synthetic-only credentials; static diagnostic allowlist; no provider error text in UI | AUTHOR PASS in tests; real credential/client machine configuration NOT RUN. |

Limits do not silently relax when missing: no calibrated or approved model context/output evidence → do not issue a real LiveApproval. ModelContract is explicit server evidence, not proof that its numbers are true. HARD_BOUND policy does not make fictional caps true. New per-session call records are conservative (even denied/uncertain pre-send can consume approval); never refund them automatically.

Authorization scope is one server process, one enrolled Workspace/account. Durable marker blocks overlapping grants in that Workspace and restart; cross-Workspace/account distributed fencing needs a separate operational decision. No global budget, EVM permission, env flag or UI selection may create a session.
