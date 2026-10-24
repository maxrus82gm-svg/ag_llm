"""Checkable source references for the static TOCTOU review (read-only; no repository writes besides refs.json).

Every reference is (id, file, line, anchor): the anchor text must occur on exactly that 1-based line of the file as
it is on disk now. The output records the file's SHA-256, the line and the stripped line text, so a verifier can
re-check each reference against the published blob. A reference whose anchor is not on its line is reported with
the lines where the anchor does occur and the script exits 1 (nothing is silently moved).
Usage: source_refs.py <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
REFS = [
    # mutation_executor.py - WA4-E write path
    ("E1", "web_alarm/mutation_executor.py", 110, "def _create_exclusive(path: Path, data: bytes)"),
    ("E2", "web_alarm/mutation_executor.py", 117, "temp = path.parent / f\".{path.name}."),
    ("E3", "web_alarm/mutation_executor.py", 124, "os.link(temp, path)"),
    ("E4", "web_alarm/mutation_executor.py", 130, "os.rename(temp, path)"),
    ("E5", "web_alarm/mutation_executor.py", 427, "claim = self.claims.acquire(task_id, op"),
    ("E6", "web_alarm/mutation_executor.py", 453, "with self.claims.mutation_boundary(task_id, op"),
    ("E7", "web_alarm/mutation_executor.py", 491, "canonical, _ = self.claims._target(current)"),
    ("E8", "web_alarm/mutation_executor.py", 495, "current = self.operations._transition_locked("),
    ("E9", "web_alarm/mutation_executor.py", 509, "kind = MutationKind.CREATE"),
    ("E10", "web_alarm/mutation_executor.py", 511, "self._apply(kind, path, data)"),
    ("E11", "web_alarm/mutation_executor.py", 515, "done = self.operations._transition_locked("),
    ("E12", "web_alarm/mutation_executor.py", 539, "_atomic_write_bytes(path, data)"),
    ("E13", "web_alarm/mutation_executor.py", 541, "_create_exclusive(path, data)"),
    ("E14", "web_alarm/mutation_executor.py", 543, "path.unlink()"),
    ("E15", "web_alarm/mutation_executor.py", 549, "observed = observe_path(path)"),
    ("E16", "web_alarm/mutation_executor.py", 613, "payload = src.path.read_bytes()"),
    ("E17", "web_alarm/mutation_executor.py", 623, "if not same_authority(observe_bytes(payload), source_pre):"),
    ("E18", "web_alarm/mutation_executor.py", 637, "owned = self.claims.acquire(task_id, delete_id"),
    ("E19", "web_alarm/mutation_executor.py", 317, "if record.status in (OperationStatus.STARTED, OperationStatus.UNKNOWN_AFTER_DISCONNECT):"),
    # target_identity.py - canonical target
    ("T1", "web_alarm/target_identity.py", 81, "root = Path(workspace_root).resolve(strict=True)"),
    ("T2", "web_alarm/target_identity.py", 98, "if is_link_or_reparse_point(candidate):"),
    ("T3", "web_alarm/target_identity.py", 101, "resolved = candidate.resolve(strict=False)"),
    ("T4", "web_alarm/target_identity.py", 102, "relative = resolved.relative_to(root)"),
    ("T5", "web_alarm/target_identity.py", 116, "path=resolved,"),
    # file_state.py - observation
    ("F1", "web_alarm/file_state.py", 130, "info = os.lstat(target)"),
    ("F2", "web_alarm/file_state.py", 135, "if is_link_or_reparse_point(target):"),
    ("F3", "web_alarm/file_state.py", 141, "with target.open(\"rb\") as handle:"),
    # target_claim_service.py - RC-3 boundary
    ("C1", "web_alarm/target_claim_service.py", 173, "canonical = canonical_target(root, record.target)"),
    ("C2", "web_alarm/target_claim_service.py", 178, "return canonical, physical_target_key(canonical.path)"),
    ("C3", "web_alarm/target_claim_service.py", 432, "observed = observe_path(canonical.path).authority()"),
    ("C4", "web_alarm/target_claim_service.py", 456, "with self.operations.task_lock(task_id):"),
    ("C5", "web_alarm/target_claim_service.py", 463, "canonical, physical_key = self._target(record)"),
    ("C6", "web_alarm/target_claim_service.py", 464, "with self._mutation_lock(task_id), self._target_lock(physical_key):"),
    # operation_store.py - INTENT pre-state and DONE post-proof
    ("O1", "web_alarm/operation_store.py", 504, "canonical = canonical_target(workspace_root, target)"),
    ("O2", "web_alarm/operation_store.py", 651, "observed_pre = observe_path(request.target.path)"),
    ("O3", "web_alarm/operation_store.py", 728, "canonical = canonical_target("),
    ("O4", "web_alarm/operation_store.py", 732, "if canonical.key != contract[\"target_key\"]:"),
    ("O5", "web_alarm/operation_store.py", 734, "observed = observe_path(canonical.path)"),
    # manifest_store.py - shared atomic write and the WA-1 explicit restore
    ("M1", "web_alarm/manifest_store.py", 81, "path.parent.mkdir(parents=True, exist_ok=True)"),
    ("M2", "web_alarm/manifest_store.py", 82, "temp = path.parent / f\".{path.name}."),
    ("M3", "web_alarm/manifest_store.py", 88, "os.replace(temp, path)"),
    ("M4", "web_alarm/manifest_store.py", 138, "if candidate.is_symlink():"),
    ("M5", "web_alarm/manifest_store.py", 140, "resolved = candidate.expanduser().resolve(strict=False)"),
    ("M6", "web_alarm/manifest_store.py", 751, "def restore_microtask(self, task_id: str, microtask_id: str)"),
    ("M7", "web_alarm/manifest_store.py", 799, "_atomic_write_bytes(target, data)"),
    ("M8", "web_alarm/manifest_store.py", 800, "restored = target.read_bytes()"),
    ("M9", "web_alarm/manifest_store.py", 806, "target.unlink()"),
    # rollback_service.py - RC-4 restore
    ("R1", "web_alarm/rollback_service.py", 200, "_atomic_write_bytes(path, data)"),
    ("R2", "web_alarm/rollback_service.py", 204, "path.unlink()"),
    ("R3", "web_alarm/rollback_service.py", 270, "if canonical.key != target[\"target_key\"] or target_hash("),
    ("R4", "web_alarm/rollback_service.py", 766, "observed = observe_path(self._canonical(root, target).path)"),
    ("R5", "web_alarm/rollback_service.py", 815, "canonical = self._canonical(root, target)"),
    ("R6", "web_alarm/rollback_service.py", 816, "observed = observe_path(canonical.path)"),
    ("R7", "web_alarm/rollback_service.py", 831, "if not same_authority(observed, target[\"preserved\"]):"),
    ("R8", "web_alarm/rollback_service.py", 837, "self._persist(record)"),
    ("R9", "web_alarm/rollback_service.py", 840, "_write_restored_bytes(canonical.path, snapshots"),
    ("R10", "web_alarm/rollback_service.py", 842, "_delete_created(canonical.path)"),
    ("R11", "web_alarm/rollback_service.py", 843, "post = observe_path(canonical.path)"),
    ("R12", "web_alarm/rollback_service.py", 854, "target[\"status\"] = T_RESTORED"),
    ("R13", "web_alarm/rollback_service.py", 888, "observed = observe_path(self._canonical(root, target).path)"),
    ("R14", "web_alarm/rollback_service.py", 921, "_, checked = self._prove_current(record, root)"),
    # identity of claims and locks
    ("K1", "web_alarm/target_claim_store.py", 91, "key = os.path.normcase(str(path))"),
    ("L1", "web_alarm/store_lock.py", 3, "This protects storage integrity (read-check-write of one store), not physical"),
    ("L2", "web_alarm/store_lock.py", 45, "msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)"),
    # entry point of the WA-1 restore
    ("CL1", "web_alarm/cli.py", 211, "manifests.restore_microtask(args.task_id, args.microtask_id)"),
    # contrast: identity-bound checks in the AUD-01T-R recovery tool
    ("X1", "web_alarm/transport_event_recovery.py", 148, "if before.st_nlink != 1:"),
    ("X2", "web_alarm/transport_event_recovery.py", 154, "if not (_identity(before) == _identity(opened) == _identity(after))"),
    ("X3", "web_alarm/transport_event_recovery.py", 481, "if current is None or current[1] != identity or current[0] != data:"),
]

out, problems, files = [], [], {}
for ref_id, rel, line, anchor in REFS:
    path = REPO / rel
    if rel not in files:
        data = path.read_bytes()
        files[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                      "lines": data.decode("utf-8").splitlines()}
    lines = files[rel]["lines"]
    text = lines[line - 1] if 0 < line <= len(lines) else ""
    if anchor in text:
        out.append({"id": ref_id, "file": rel, "line": line, "text": text.strip()[:200]})
    else:
        found = [i + 1 for i, x in enumerate(lines) if anchor in x]
        problems.append({"id": ref_id, "file": rel, "line": line, "anchor_found_on": found})
result = {"repository_root": "<REPO>", "files": {k: {"sha256": v["sha256"], "bytes": v["bytes"]} for k, v in files.items()},
          "refs": out, "problems": problems}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"refs_ok": len(out), "problems": problems}, ensure_ascii=True))
sys.exit(1 if problems else 0)
