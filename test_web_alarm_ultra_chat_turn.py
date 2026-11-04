"""Stage3 prerequisite oracles. Known Run Store defects remain RED; no XFAIL or substitute store.

All mutations are in a uniquely allocated TEMP tree, including the synthetic 'outside' target.
No provider imports/calls. Run directly with unittest; evidence is optional via S3_EVIDENCE_DIR.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import context_storage as cs
import run_store as rs

ROOT = Path(__file__).resolve().parent
CHILD = r'''
import json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
def guard(event,args):
    if event=='socket.connect': raise AssertionError('External/provider sockets forbidden in this probe')
sys.addaudithook(guard)
import context_storage as cs,run_store as rs
root,control,mode=Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4]
if mode=='first':
    original=rs._next_sequence
    def pause(path):
        value=original(path)
        (control/'first_read').write_text(str(value))
        deadline=time.monotonic()+15
        while not (control/'release').exists():
            if time.monotonic()>deadline: raise RuntimeError('bounded barrier timeout')
            time.sleep(.01)
        return value
    rs._next_sequence=pause
try:
    value=rs.append_run_record(root,'run_s3',source='SERVER',event='s3_test',payload={'writer':mode},timestamp=1.0)
    print(json.dumps({'outcome':'recorded','sequence':value['sequence'],'provider_calls':0}),flush=True)
except cs.WorkspaceBusyError:
    print(json.dumps({'outcome':'workspace_busy','provider_calls':0}),flush=True)
'''


class TurnPrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='CODEX-WUA-CHAT-S3-')
        self.base = Path(self.temp.name).resolve()
        self.assertEqual(self.base.parent, Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = self.base / 'workspace'
        self.root.mkdir()
        self.identity = cs.ensure_workspace_storage(self.root)['workspace_id']
        self.chat = cs.create_chat(self.root, 'Synthetic only')['chat_id']
        self.children = []
        self.addCleanup(self.reap)
        self.connect = patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')).start()
        self.addCleanup(patch.stopall)

    def reap(self):
        for child in self.children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=20)

    def evidence(self, name, value):
        directory = os.environ.get('S3_EVIDENCE_DIR')
        if directory:
            target = Path(directory).resolve()
            allowed = [ROOT / 'reports' / name for name in
                       ['CODEX-WUA-CHAT-S3-TURN-RECOVERY-001', 'CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001']]
            self.assertTrue(any(target.is_relative_to(path) for path in allowed))
            target.mkdir(parents=True, exist_ok=True)
            (target / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    def summary(self):
        return rs.create_run_summary(self.root, self.identity, self.chat, 'tb_s3', 'run_s3')

    def test_normal_run_roundtrip_uses_existing_store(self):
        self.summary()
        receipt = rs.append_run_record(self.root, 'run_s3', source='SERVER', event='s3_test',
                                       payload={'synthetic': True}, timestamp=1.0)
        persisted = rs.load_run_record(self.root, 'run_s3', receipt['record_id'], expected_sha256=receipt['sha256'])
        self.assertEqual(persisted['payload'], {'synthetic': True})
        self.assertEqual(rs.load_run_summary(self.root, 'run_s3')['workspace_id'], self.identity)
        self.assertEqual(cs.list_existing_chats(self.root)[0]['chat_id'], self.chat)
        self.connect.assert_not_called()
        self.evidence('normal_run', dict(sequence=receipt['sequence'], hash_verified=True, provider_calls=0))

    @unittest.skipUnless(os.name == 'nt', 'Windows junction oracle requires Windows')
    def test_audit_junction_must_not_write_outside_workspace(self):
        import _winapi
        outside = self.base / 'outside'
        outside.mkdir()
        marker = outside / 'untouched.txt'
        marker.write_bytes(b'unchanged')
        link = self.root / '.ultra/audit'
        _winapi.CreateJunction(str(outside), str(link))
        self.addCleanup(lambda: os.rmdir(link))  # remove only the owned junction before TEMP cleanup
        refused = False
        try:
            self.summary()
        except (cs.StorageWriteError, OSError, ValueError):
            refused = True
        files = sorted(p.relative_to(outside).as_posix() for p in outside.rglob('*') if p.is_file())
        self.evidence('audit_path', dict(refused=refused, outside_files=files,
                                       marker_unchanged=marker.read_bytes()==b'unchanged', provider_calls=0))
        self.connect.assert_not_called()
        self.assertEqual(files, ['untouched.txt'], 'Run Store followed .ultra/audit junction and wrote outside the Workspace')

    def test_same_run_two_processes_have_unique_sequences_or_visible_refusal(self):
        self.summary()
        control = self.base / 'control'
        control.mkdir()
        def spawn(mode):
            p = subprocess.Popen([sys.executable, '-B', '-c', CHILD, str(ROOT), str(self.root), str(control), mode],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            self.children.append(p)
            return p
        first = spawn('first')
        deadline = time.monotonic()+8
        while not (control/'first_read').exists():
            self.assertIsNone(first.poll(), 'first writer exited before the phase marker')
            self.assertLess(time.monotonic(), deadline, 'first writer did not reach the controlled phase')
            time.sleep(.01)
        second = spawn('second')
        try:
            try:
                out2, err2 = second.communicate(timeout=3)
                second_finished_before_release = True
            except subprocess.TimeoutExpired:
                second_finished_before_release = False
        finally:
            (control/'release').write_bytes(b'go')
        out1, err1 = first.communicate(timeout=15)
        if not second_finished_before_release:
            out2, err2 = second.communicate(timeout=15)
        self.assertEqual((first.returncode, second.returncode), (0, 0), err1+err2)
        results = [json.loads(out1), json.loads(out2)]
        index_path = self.root / '.ultra/audit' / self.chat / 'run_s3/records.idx.jsonl'
        raw = index_path.read_bytes()
        records = [json.loads(line) for line in raw.splitlines()]
        sequences = [r['sequence'] for r in records]
        self.evidence('same_run_writers', dict(controlled_phase_reached=True, second_finished_before_release=second_finished_before_release,
                                             writers=results, sequences=sequences, record_count=len(records),
                                             raw_index=records, raw_index_sha256=hashlib.sha256(raw).hexdigest(), provider_calls=0))
        self.connect.assert_not_called()
        recorded = sum(r['outcome']=='recorded' for r in results)
        self.assertEqual(len(records), recorded)
        self.assertEqual(sorted(sequences), list(range(1, recorded+1)), 'Two processes acknowledged the same RUN sequence')


if __name__ == '__main__':
    unittest.main(verbosity=2)
