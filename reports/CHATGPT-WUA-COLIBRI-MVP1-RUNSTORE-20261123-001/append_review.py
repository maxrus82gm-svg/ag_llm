"""Exact pinned Colibri #108, Windows child hard kills while writing append.pending."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-ORPHAN-20261123-001"))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-EVM-20261122-001"))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
import unittest,tempfile,subprocess,time,json,os,hashlib,threading
from recovery import Recovery
from web_alarm.turn_service import identities
from web_alarm.ultra_chat import UltraChatError
import context_storage as core
import run_store as runs

HERE=Path(__file__).resolve().parent

class AppendReview(Recovery):
    def child(self, root,wid,cid,body,mode):
        config=dict(root=str(root),workspace_id=wid,chat_id=cid,profile=str(self.folder),
                    bridge_id=self.bridge.bridge_id,target_id=self.local,body=body,mode=mode)
        fd,name=tempfile.mkstemp(prefix="wua664-kid-",suffix=".json")
        os.close(fd)
        tmp=Path(name)
        tmp.write_text(json.dumps(config),encoding='utf8')
        def dispose():
            tmp.unlink(missing_ok=True)
        self.addCleanup(dispose)
        proc=subprocess.Popen([sys.executable,'-B','-X','utf8',str(HERE/'append_child.py'),str(tmp)],
            cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def cleanup():
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=15)
        self.addCleanup(cleanup)
        return proc

    @staticmethod
    def signatures(root,runid):
        files=[runs.run_component_path(root,runid,'server.jsonl'),
               runs.run_component_path(root,runid,'records.idx.jsonl'),
               runs._pending_path(root,runid)]
        return {p.name:(hashlib.sha256(p.read_bytes()).hexdigest()
                        if p.exists() else None) for p in files}

    def setup_crash(self,mode,text):
        root,wid,cid,body,reader,server,base,read=self.prep(text)
        child=self.child(root,wid,cid,body,mode)
        self.assertEqual(child.wait(timeout=20),91 if mode=='after_stream' else 92)
        ids=identities(wid,cid,body['idempotency_key'])
        self.assertEqual(reader._load(root,wid,cid,ids['turn_id'])['state'],'ATTEMPTING')
        self.assertEqual(len(self.calls),1)
        self.assertTrue(runs._pending_path(root,ids['run_id']).exists())
        return root,wid,cid,body,reader,ids

    def test_hard_kill_after_stream_pending_requires_preview_and_explicit_rollback(self):
        root,wid,cid,body,reader,ids=self.setup_crash('after_stream','journal tail')
        preview=reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual(preview['decision'],'PENDING_APPEND_REVIEW')
        self.assertEqual(preview['journal_action'],'ROLLBACK_UNINDEXED')
        self.assertFalse(preview['remote_stop_proven'])
        self.assertTrue(preview['uncommitted_bytes'].get('server.jsonl',0)>0)
        before=self.signatures(root,ids['run_id'])
        self.assertEqual(reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id']),preview)
        self.assertEqual(self.signatures(root,ids['run_id']),before)
        with self.assertRaises(UltraChatError) as caught:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual(caught.exception.code,'local_append_repair_approval_required')
        self.assertEqual(self.signatures(root,ids['run_id']),before)
        terminal=reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'],
                                                     approve_pending_repair=True)
        self.assertEqual(terminal['state'],'UNKNOWN')
        self.assertEqual(terminal['diagnostic_code'],'owner_process_lost')
        self.assertIsNone(terminal['answer'])
        self.assertEqual(len(self.calls),1)
        self.assertFalse(runs._pending_path(root,ids['run_id']).exists())
        self.assertEqual(reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id'])['decision'],'ALREADY_TERMINAL')
        msg=core.read_chat_history_bounded(root,cid)
        self.assertEqual([m['role'] for m in msg['messages']],['user'])
        self.assertEqual(reader.lookup(root,wid,cid,body['idempotency_key'])['turn_id'],ids['turn_id'])

    def test_hard_kill_after_index_pending_keeps_durable_success_after_approval(self):
        root,wid,cid,body,reader,ids=self.setup_crash('after_index','journal committed')
        before=self.signatures(root,ids['run_id'])
        peek=reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual((peek['decision'],peek['journal_action']),
                         ('PENDING_APPEND_REVIEW','KEEP_COMMITTED'))
        self.assertEqual(before,self.signatures(root,ids['run_id']))
        with self.assertRaises(UltraChatError) as denied:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual(denied.exception.code,'local_append_repair_approval_required')
        result=reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'],
                                                   approve_pending_repair=True)
        self.assertEqual((result['state'],result['answer']),('SUCCEEDED','Ответ'))
        self.assertEqual(len(self.calls),1)
        page=core.read_chat_history_bounded(root,cid)
        self.assertEqual([(m['role'],m['text']) for m in page['messages']],
                         [('user','journal committed'),('assistant','Ответ')])
        self.assertEqual(reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id']),result)

    def test_partial_index_and_stream_tail_repair_is_opt_in_no_second_send(self):
        root,wid,cid,body,reader,ids=self.setup_crash('after_stream','partial index')
        pending=runs._read_json(runs._pending_path(root,ids['run_id']))
        to_append=runs._index_bytes(pending['record'])
        self.assertGreater(len(to_append),20)
        index=runs.run_component_path(root,ids['run_id'],'records.idx.jsonl')
        with index.open('ab') as stream:stream.write(to_append[:len(to_append)//2])
        preview=reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual(preview['journal_action'],'ROLLBACK_UNINDEXED')
        before=self.signatures(root,ids['run_id'])
        with self.assertRaises(UltraChatError) as denied:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual(denied.exception.code,'local_append_repair_approval_required')
        self.assertEqual(self.signatures(root,ids['run_id']),before)
        final=reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'],
                                                  approve_pending_repair=True)
        self.assertEqual(final['state'],'UNKNOWN')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(core.read_chat_history_bounded(root,cid)['messages'][-1]['role'],'user')

    def check_corrupt(self,kind):
        root,wid,cid,body,reader,ids=self.setup_crash('after_stream',kind)
        pending=runs._pending_path(root,ids['run_id'])
        if kind=='bad_intent':
            data=runs._read_json(pending)
            data['index_sha256']='f'*64
            pending.write_text(json.dumps(data),encoding='utf8')
        else:
            pending.unlink()
        before=self.signatures(root,ids['run_id'])
        peek=reader.inspect_orphaned_colibri(root,wid,cid,ids['turn_id'])
        self.assertEqual((peek['decision'],peek['reason']),('MANUAL_HOLD','unverified_run_store'))
        with self.assertRaises(UltraChatError) as denied:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids['turn_id'],
                                               approve_pending_repair=True)
        self.assertEqual(denied.exception.code,'local_recovery_manual_hold')
        self.assertEqual(self.signatures(root,ids['run_id']),before)
        self.assertEqual(len(self.calls),1)
        self.assertIsNone(reader._load(root,wid,cid,ids['turn_id']).get('answer'))

    def test_bad_intent_unchanged_manual_hold(self):
        self.check_corrupt('bad_intent')

    def test_orphan_tail_without_intent_unchanged_manual_hold(self):
        self.check_corrupt('missing_intent')

    def test_alive_owner_preview_read_only_before_hard_kill(self):
        root,wid,cid,body,reader,server,base,read=self.prep('owner active preview')
        ready,release=threading.Event(),threading.Event()
        def paused(profile,slot,model,messages,**kwargs):
            for packet in self.fake_stream(profile,slot,model,messages,**kwargs):
                if packet['type']=='delta':
                    ready.set()
                    if not release.wait(15):raise RuntimeError('test gate timeout')
                yield packet
        self.manager_stream=paused
        child=self.child(root,wid,cid,body,'after_stream')
        try:
            self.assertTrue(ready.wait(10))
            token=identities(wid,cid,body['idempotency_key'])['turn_id']
            preview=reader.inspect_orphaned_colibri(root,wid,cid,token)
            self.assertEqual(preview['decision'],'WAIT_ORIGINAL_OWNER')
            self.assertFalse(preview['remote_stop_proven'])
        finally:
            child.kill();child.wait(timeout=8);release.set()
        self.assertEqual(len(self.calls),1)

if __name__=='__main__':
    suite=unittest.TestSuite(AppendReview(name) for name in (
        'test_hard_kill_after_stream_pending_requires_preview_and_explicit_rollback',
        'test_hard_kill_after_index_pending_keeps_durable_success_after_approval',
        'test_partial_index_and_stream_tail_repair_is_opt_in_no_second_send',
        'test_bad_intent_unchanged_manual_hold',
        'test_orphan_tail_without_intent_unchanged_manual_hold',
        'test_alive_owner_preview_read_only_before_hard_kill'))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
