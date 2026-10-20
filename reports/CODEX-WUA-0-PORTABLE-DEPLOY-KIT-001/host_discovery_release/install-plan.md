# WUA deployment plan (PUBLIC REDACTED / NOT EXECUTABLE)

Approval SHA-256: aa8eed5bedb576871f1c8f76cb8e268bda93da211a7bd39639b9d4b86c9aedf9
State: BLOCKED; backend NOT_IMPLEMENTED; activation NOT STARTED.
Digest binds input content only, not authenticated approval or host identity.
Private paths/remote endpoint are referenced through operator input; use a local private review before any future Apply.

## 1. reserve_owner_ledger
WHY: Reserve exclusive ownership before any mutation
TARGET: owner:new_root
BEFORE: absent
AFTER: owned empty ledger
REQUIRED PRIVILEGES: administrator
VERIFICATION: exact local path and no prior objects
ROLLBACK: retain diagnostics only

## 2. create_disabled_client
WHY: Create NEW local standard account; do not reuse foreign SID
TARGET: role:client
BEFORE: absent
AFTER: disabled new identity
REQUIRED PRIVILEGES: administrator
VERIFICATION: read back local SID and disabled state
ROLLBACK: remove only after deny/quiescence

## 3. create_disabled_broker
WHY: Separate broker identity from client and current user
TARGET: role:broker
BEFORE: absent
AFTER: disabled new identity
REQUIRED PRIVILEGES: administrator
VERIFICATION: read back distinct new local SID
ROLLBACK: remove only after deny/quiescence

## 4. bind_new_sids
WHY: Resolve actual freshly created account SIDs locally
TARGET: roles:client,broker
BEFORE: symbolic
AFTER: local SID bindings in protected ledger
REQUIRED PRIVILEGES: administrator
VERIFICATION: distinct local SIDs, no imported SID
ROLLBACK: keep principals disabled

## 5. set_logon_rights
WHY: Least rights; batch/service only, no interactive/elevation grant
TARGET: roles:client,broker
BEFORE: captured before
AFTER: least privilege
REQUIRED PRIVILEGES: administrator
VERIFICATION: rights diff exact owner entries
ROLLBACK: restore exact prior owned assignments

## 6. set_owned_acls
WHY: Separate immutable binaries and role private profiles/resources
TARGET: path_refs:owned_resources
BEFORE: captured before
AFTER: minimal role ACLs
REQUIRED PRIVILEGES: administrator
VERIFICATION: DACL readback, no workspace-wide grant
ROLLBACK: restore exact before descriptor

## 7. install_sid_policy
WHY: Install reviewed disjoint denies before enabling any identity
TARGET: policy:owner_guid
BEFORE: absent
AFTER: effective deny partition
REQUIRED PRIVILEGES: administrator
VERIFICATION: independent SID/loopback/arbitration/lifecycle proof
ROLLBACK: KEEP deny until all SID work absent

## 8. configure_private_broker
WHY: No DIRECT; authenticated approved remote endpoint
TARGET: role:broker/config
BEFORE: absent
AFTER: version-pinned config plus local secret refs
REQUIRED PRIVILEGES: administrator
VERIFICATION: loaded graph and remote pin; no DNS bypass
ROLLBACK: remove only owned config after stop

## 9. register_disabled_startup
WHY: Stage noninteractive least-privilege startup; no activation
TARGET: startup:owner_guid
BEFORE: absent
AFTER: disabled task/service definitions
REQUIRED PRIVILEGES: administrator
VERIFICATION: principal SID and dependencies; no start
ROLLBACK: remove exact ledger task/service only

## 10. verify_staged_install
WHY: Independently compare installed objects and protected ledger
TARGET: ledger:owner_guid
BEFORE: staged
AFTER: verified or BLOCKED
REQUIRED PRIVILEGES: reviewed verifier
VERIFICATION: effective filters, ACL, identities; no mock proof
ROLLBACK: retain deny and disabled resources

## 11. activation_separate_go
WHY: Native/live activation is a separate future authorization
TARGET: activation:separate_gate
BEFORE: not started
AFTER: NOT STARTED
REQUIRED PRIVILEGES: separate USER GO
VERIFICATION: native containment/live/E2E gates
ROLLBACK: no activation in this toolkit version
