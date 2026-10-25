"""Offline deterministic schedules. All fixture paths are below WA4R_LAB/tmp.

Assertions in RepairOracles express safety invariants and are expected RED on
the baseline. Other tests record observed behavior, including confirmed risks;
their PASS is not a claim that the behavior is safe.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import web_alarm.file_state as fs
import web_alarm.manifest_store as ms
import web_alarm.mutation_executor as mx
import web_alarm.rollback_service as rb
from web_alarm.models import OperationStatus
from test_web_alarm_mutation_executor import Fixture as MutationFixture, TASK, AFTER, BEFORE
from test_web_alarm_manifest_store import ManifestSnapshotStoreTests as ManifestFixture
from test_web_alarm_rollback import RollbackFixture, TASK as RBTASK, AFTER as RBAFTER, BEFORE as RBBEFORE


def evidence(case, **facts):
    lab = Path(os.environ['WA4R_LAB']).resolve()
    target = lab / 'runs' / (os.environ['WA4R_RUN_ID'] + '-observations.jsonl')
    with target.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'case': case, **facts}, sort_keys=True) + '\n')


def outcome_facts(result):
    return {key: result.get(key) for key in ('result', 'result_code', 'operation_status', 'receipt')}


class MutationResearch(MutationFixture):
    def test_drift_before_final_cas_is_refused(self):
        self.activate()
        real = self.executor.claims._cas
        def drift(*args, **kwargs):
            self.write('a.txt', b'foreign-before-cas')
            return real(*args, **kwargs)
        with mock.patch.object(self.executor.claims, '_cas', side_effect=drift), \
                mock.patch.object(mx.MutationExecutor, '_apply') as apply:
            result = self.run_write()
        self.assertEqual(result['result_code'], 'PRECONDITION_FAILED')
        apply.assert_not_called()
        self.assertEqual(self.read('a.txt'), b'foreign-before-cas')
        evidence(self._testMethodName, **outcome_facts(result), apply_calls=0)

    def test_create_collision_after_cas_never_overwrites(self):
        self.activate()
        real = mx.MutationExecutor._apply
        def competing_create(kind, path, data):
            path.write_bytes(b'foreign-created')
            return real(kind, path, data)
        with mock.patch.object(mx.MutationExecutor, '_apply', side_effect=competing_create) as apply:
            result = self.executor.execute(TASK, 'm1', 'op_create', 'create', 'new.txt', payload=AFTER)
        self.assertEqual(result['result'], 'RECONCILIATION_REQUIRED')
        self.assertEqual(self.read('new.txt'), b'foreign-created')
        with mock.patch.object(mx.MutationExecutor, '_apply') as replay_apply:
            replay = self.executor.execute(TASK, 'm1', 'op_create', 'create', 'new.txt', payload=AFTER)
        replay_apply.assert_not_called()
        evidence(self._testMethodName, **outcome_facts(result), apply_calls=apply.call_count,
                 replay_code=replay['result_code'], replay_apply_calls=0)

    def test_existing_write_loses_uncooperative_update_after_cas(self):
        self.activate()
        real = mx.MutationExecutor._apply
        def competing_write(kind, path, data):
            path.write_bytes(b'foreign-after-cas')
            return real(kind, path, data)
        with mock.patch.object(mx.MutationExecutor, '_apply', side_effect=competing_write) as apply:
            result = self.run_write()
        self.assertEqual(result['result'], 'EXECUTED')
        self.assertEqual(self.read('a.txt'), AFTER)
        with mock.patch.object(mx.MutationExecutor, '_apply') as replay_apply:
            replay = self.run_write()
        replay_apply.assert_not_called()
        evidence(self._testMethodName, **outcome_facts(result), foreign_bytes_lost=True,
                 apply_calls=apply.call_count, replay_result=replay['result'], replay_apply_calls=0)

    def test_existing_delete_removes_uncooperative_update_after_cas(self):
        self.activate()
        real = mx.MutationExecutor._apply
        def competing_write(kind, path, data):
            path.write_bytes(b'foreign-after-cas')
            return real(kind, path, data)
        with mock.patch.object(mx.MutationExecutor, '_apply', side_effect=competing_write):
            result = self.executor.execute(TASK, 'm1', 'op_delete', 'delete', 'gone.txt')
        self.assertEqual(result['result'], 'EXECUTED')
        self.assertIsNone(self.read('gone.txt'))
        evidence(self._testMethodName, **outcome_facts(result), foreign_bytes_lost=True)

    def test_post_action_drift_has_no_done_receipt_or_blind_replay(self):
        self.activate()
        real = mx.MutationExecutor._apply
        def post_drift(kind, path, data):
            real(kind, path, data)
            path.write_bytes(b'post-action-drift')
        with mock.patch.object(mx.MutationExecutor, '_apply', side_effect=post_drift):
            result = self.run_write()
        self.assertEqual(result['result_code'], 'POST_PROOF_FAILED')
        self.assertEqual(self.op().status, OperationStatus.STARTED)
        self.assertIsNone(self.op().receipt)
        with mock.patch.object(mx.MutationExecutor, '_apply') as apply:
            replay = self.run_write()
        apply.assert_not_called()
        evidence(self._testMethodName, **outcome_facts(result), replay_code=replay['result_code'], replay_apply_calls=0)

    def _parent_swap(self, action, target):
        if os.name != 'nt':
            self.skipTest('native Windows junction schedule')
        import _winapi
        self.activate()
        parent = self.project / 'sub'
        parked = self.project / 'sub_parked'
        alternative = Path(self.tempdir.name) / 'alternative'
        alternative.mkdir()
        (alternative / 'r_src.txt').write_bytes(b'foreign-target')
        real = mx.MutationExecutor._apply
        def swap(kind, path, data):
            parent.rename(parked)
            _winapi.CreateJunction(str(alternative), str(parent))
            try:
                return real(kind, path, data)
            finally:
                parent.rmdir()
                parked.rename(parent)
        kwargs = {} if action == 'delete' else {'payload': AFTER}
        with mock.patch.object(mx.MutationExecutor, '_apply', side_effect=swap) as apply:
            result = self.executor.execute(TASK, 'm1', 'op_swap', action, target, **kwargs)
        leaf = Path(target).name
        alt = alternative / leaf
        actual = alt.read_bytes() if alt.exists() else None
        self.assertEqual(actual, None if action == 'delete' else AFTER)
        self.assertEqual(result['result'], 'RECONCILIATION_REQUIRED')
        self.assertEqual(result['result_code'], 'POST_PROOF_FAILED')
        self.assertIsNone(self.ops.get(TASK, 'op_swap').receipt)
        with mock.patch.object(mx.MutationExecutor, '_apply') as replay_apply:
            replay = self.executor.execute(TASK, 'm1', 'op_swap', action, target, **kwargs)
        replay_apply.assert_not_called()
        evidence(self._testMethodName, **outcome_facts(result), action=action,
                 alternate_target_modified=True, original_target_unchanged=True,
                 apply_calls=apply.call_count, replay_code=replay['result_code'], replay_apply_calls=0)

    def test_junction_swap_redirects_write_before_post_proof(self):
        self._parent_swap('write', 'sub/r_src.txt')

    def test_junction_swap_redirects_create_before_post_proof(self):
        self._parent_swap('create', 'sub/r_dst.txt')

    def test_junction_swap_redirects_delete_before_post_proof(self):
        self._parent_swap('delete', 'sub/r_src.txt')


class RollbackResearch(RollbackFixture):
    def test_uncooperative_write_after_rollback_cas_is_lost(self):
        resolution = self.scenario()
        record = self.prepare(resolution)['rollback']
        real = rb._write_restored_bytes
        def competing_write(path, data):
            path.write_bytes(b'foreign-after-rollback-cas')
            return real(path, data)
        with mock.patch.object(rb, '_write_restored_bytes', side_effect=competing_write) as write:
            result = self.rollbacks.apply(RBTASK, record['rollback_id'])
        self.assertEqual(result['result'], 'VERIFIED')
        self.assertEqual(self.path('target.txt').read_bytes(), RBBEFORE)
        with mock.patch.object(rb, '_write_restored_bytes') as replay_write:
            replay = rb.RollbackService(self.storage).apply(RBTASK, record['rollback_id'])
        replay_write.assert_not_called()
        evidence(self._testMethodName, result=result['result'], result_code=result['result_code'],
                 foreign_bytes_lost=True, write_calls=write.call_count,
                 replay_result=replay['result'], replay_write_calls=0)

    def test_snapshot_change_after_plan_is_blocked_by_freshness(self):
        resolution = self.scenario()
        record = self.prepare(resolution)['rollback']
        real = self.rollbacks.manifests.restore_plan
        def change_after_plan(*args):
            plan = real(*args)
            snapshots = list((self.storage / 'tasks').rglob('*.bin'))
            self.assertTrue(snapshots)
            for path in snapshots:
                if 'restore_point' in path.parts:
                    path.write_bytes(b'changed-after-read')
            return plan
        with mock.patch.object(self.rollbacks.manifests, 'restore_plan', side_effect=change_after_plan), \
                mock.patch.object(rb, '_write_restored_bytes') as write:
            result = self.rollbacks.apply(RBTASK, record['rollback_id'])
        evidence(self._testMethodName, result=result['result'], result_code=result['result_code'], write_calls=write.call_count)
        self.assertEqual(result['result'], 'BLOCKED')
        write.assert_not_called()
        self.assertEqual(self.path('target.txt').read_bytes(), RBAFTER)

    def test_snapshot_change_after_final_basis_uses_retained_verified_bytes(self):
        resolution = self.scenario()
        record = self.prepare(resolution)['rollback']
        real = self.rollbacks._session_basis
        def change_after_basis(*args):
            refusal = real(*args)
            self.assertIsNone(refusal)
            snapshots = [p for p in self.storage.rglob('*.bin') if 'restore_point' in p.parts]
            self.assertTrue(snapshots)
            for path in snapshots:
                path.write_bytes(b'changed-after-final-basis')
            return refusal
        with mock.patch.object(self.rollbacks, '_session_basis', side_effect=change_after_basis):
            result = self.rollbacks.apply(RBTASK, record['rollback_id'])
        self.assertEqual(result['result'], 'VERIFIED')
        self.assertEqual(self.path('target.txt').read_bytes(), RBBEFORE)
        evidence(self._testMethodName, result=result['result'], retained_verified_bytes=True)


class SnapshotRepairOracles(ManifestFixture):
    # Do not inherit the existing tests into this extra suite.
    def _arrange(self):
        self.store.prepare_microtask(self.task.task_id, 'm1', [('existing.bin', 'edit')])
        self.existing.write_bytes(b'current-to-preserve')
        snapshot = self.store.list_snapshots(self.task.task_id, 'm1')[0]
        restore = self.store._restore_dir(self.task.task_id, 'm1', active_only=True)
        return snapshot, self.store._snapshot_binary_path(restore, snapshot.snapshot_id)

    def test_consumed_snapshot_must_be_revalidated_before_restore(self):
        snapshot, binary = self._arrange()
        original_verify = self.store.verify_restore_point
        def change_after_verify(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            binary.write_bytes(b'X' * snapshot.size_before)
            return result
        error = None
        with mock.patch.object(self.store, 'verify_restore_point', side_effect=change_after_verify):
            try:
                self.store.restore_microtask(self.task.task_id, 'm1')
            except ms.ManifestStoreError as exc:
                error = str(exc)
        actual = self.existing.read_bytes()
        evidence(self._testMethodName, refused=error is not None,
                 error=error, current_bytes_preserved=actual == b'current-to-preserve',
                 bad_bytes_written=actual == b'X' * snapshot.size_before)
        self.assertIsNotNone(error)
        self.assertEqual(actual, b'current-to-preserve', 'unverified snapshot bytes must never be written')

    def test_consumed_snapshot_size_drift_is_refused_before_restore(self):
        snapshot, binary = self._arrange()
        original_verify = self.store.verify_restore_point
        def change_after_verify(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            binary.write_bytes(b'larger-unverified-snapshot')
            return result
        with mock.patch.object(self.store, 'verify_restore_point', side_effect=change_after_verify):
            with self.assertRaises(ms.ManifestStoreError):
                self.store.restore_microtask(self.task.task_id, 'm1')
        self.assertEqual(self.existing.read_bytes(), b'current-to-preserve')

    def test_repeated_corrupt_restore_performs_no_write(self):
        snapshot, binary = self._arrange()
        original_verify = self.store.verify_restore_point
        def change_after_verify(*args, **kwargs):
            result = original_verify(*args, **kwargs)
            binary.write_bytes(b'X' * snapshot.size_before)
            return result
        real_write = ms._atomic_write_bytes
        with mock.patch.object(self.store, 'verify_restore_point', side_effect=change_after_verify), \
                mock.patch.object(ms, '_atomic_write_bytes', wraps=real_write) as write:
            for _ in range(2):
                with self.assertRaises(ms.ManifestStoreError):
                    self.store.restore_microtask(self.task.task_id, 'm1')
        evidence(self._testMethodName, apply_calls=write.call_count,
                 current_bytes_preserved=self.existing.read_bytes() == b'current-to-preserve')
        self.assertEqual(write.call_count, 0)
        self.assertEqual(self.existing.read_bytes(), b'current-to-preserve')


class ObservationRepairOracles(unittest.TestCase):
    def test_replacement_between_lstat_and_open_must_be_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.bin'
            replacement = Path(directory) / 'replacement.bin'
            target.write_bytes(b'checked-by-lstat')
            replacement.write_bytes(b'other-file')
            real = fs.is_link_or_reparse_point
            def replace_after_check(path):
                result = real(path)
                os.replace(replacement, target)
                return result
            error, observed = None, None
            with mock.patch.object(fs, 'is_link_or_reparse_point', side_effect=replace_after_check):
                try:
                    observed = fs.observe_path(target)
                except fs.FileStateError as exc:
                    error = str(exc)
            evidence(self._testMethodName, refused=error is not None,
                     returned_replacement_digest=bool(observed and observed.sha256 == hashlib.sha256(b'other-file').hexdigest()))
            self.assertIsNotNone(error, 'opened file identity must match the checked file identity')

    def test_in_place_write_during_stream_must_not_return_mixed_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.bin'
            length = fs._CHUNK_SIZE
            target.write_bytes(b'A' * (2 * length))
            original_open = Path.open
            changed = []
            class Reader:
                def __init__(self, handle):
                    self.handle = handle
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    self.handle.close()
                def fileno(self):
                    return self.handle.fileno()
                def read(self, count):
                    chunk = self.handle.read(count)
                    if chunk and not changed:
                        changed.append(True)
                        with original_open(target, 'r+b', buffering=0) as writer:
                            writer.write(b'B' * (2 * length))
                            writer.flush()
                            os.fsync(writer.fileno())
                        # Ensure this controlled schedule changes metadata even on coarse clocks.
                        info = target.stat()
                        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns + 10_000_000))
                    return chunk
            def hooked_open(path, *args, **kwargs):
                handle = original_open(path, *args, **kwargs)
                return Reader(handle) if path == target and args and args[0] == 'rb' else handle
            error, observed = None, None
            with mock.patch.object(Path, 'open', hooked_open):
                try:
                    observed = fs.observe_path(target)
                except fs.FileStateError as exc:
                    error = str(exc)
            evidence(self._testMethodName, refused=error is not None,
                     returned_mixed_digest=bool(observed and observed.sha256 == hashlib.sha256(b'A' * length + b'B' * length).hexdigest()),
                     final_bytes_are_b=target.read_bytes() == b'B' * (2 * length))
            self.assertIsNotNone(error, 'a concurrent in-place write must invalidate streaming observation')

    def test_stable_observation_and_absence_still_work(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target.bin'
            self.assertFalse(fs.observe_path(target).exists)
            target.write_bytes(b'stable')
            self.assertEqual(fs.observe_path(target).authority(), fs.observe_bytes(b'stable').authority())


def load_tests(loader, tests, pattern):
    # Explicit selection prevents re-running inherited ManifestFixture tests here.
    suite = unittest.TestSuite()
    for cls in (MutationResearch, RollbackResearch, ObservationRepairOracles):
        suite.addTests(loader.loadTestsFromTestCase(cls))
    for name in ('test_consumed_snapshot_must_be_revalidated_before_restore',
                 'test_consumed_snapshot_size_drift_is_refused_before_restore',
                 'test_repeated_corrupt_restore_performs_no_write'):
        suite.addTest(SnapshotRepairOracles(name))
    return suite
