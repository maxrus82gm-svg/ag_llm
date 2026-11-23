"""Real Windows child process hard-kill tests of WUA durable Turn owner/reconcile."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-EVM-20261122-001"))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
import unittest,tempfile,subprocess,time,json,os,threading,uuid
from unittest.mock import patch
import joint_evm
import context_storage as core
from web_alarm.turn_service import TurnService,identities
from web_alarm.ultra_chat import UltraChatError
from web_alarm.colibri_owner_lease import claim,OwnerLeaseBusy
import run_store as runs

HERE=Path(__file__).resolve().parent
PY=sys.executable

class Recovery(joint_evm.JointEVM):
    def spawn(self, root,wid,cid,body,mode):
        config=dict(root=str(root),workspace_id=wid,chat_id=cid,profile=str(self.folder),
                    bridge_id=self.bridge.bridge_id,target_id=self.local,body=body,mode=mode)
        fd,name=tempfile.mkstemp(prefix="wua663-kid-",suffix=".json");os.close(fd)
        temp=Path(name)
        temp.write_text(json.dumps(config),encoding="utf8")
        self.addCleanup(temp.unlink,missing_ok=True)
        proc=subprocess.Popen([PY,"-B","-X","utf8",str(HERE/"child.py"),str(temp)],
            cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda:proc.kill() if proc.poll() is None else None)
        self.addCleanup(lambda:proc.wait(timeout=10))
        return proc

    def prep(self,text):
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")
        body=self.body(text,self.local)
        body=dict(body,config_ref="colibri-offline:v1",context_ref="stage5:"+cid)
        reader=TurnService(test_roots=[root])
        return root,wid,cid,body,reader,server,base,read

    @staticmethod
    def until(predicate,timeout=10):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return True
            time.sleep(.05)
        return False

    def test_alive_owner_refused_then_actual_kill_durable_UNKNOWN(self):
        root,wid,cid,body,reader,server,base,read=self.prep("kill midstream")
        # The WUA worker really runs in a separate Python process; the pinned
        # Colibri producer fixture stays in the parent.
        ready,release=threading.Event(),threading.Event()
        def blocked(profile,slot,model,messages,**kw):
            for e in self.fake_stream(profile,slot,model,messages,**kw):
                if e["type"]=="delta":
                    ready.set()
                    if not release.wait(15):
                        raise RuntimeError("producer test timeout")
                yield e
        self.manager_stream=blocked
        ids=identities(wid,cid,body["idempotency_key"])
        kid=self.spawn(root,wid,cid,body,"ordinary")
        try:
            self.assertTrue(ready.wait(10),"Physical fake Manager never reached stream")
            self.assertIsNone(kid.poll())
            view=reader.lookup(root,wid,cid,body["idempotency_key"])
            self.assertEqual(view["state"],"UNKNOWN")
            self.assertTrue(view["owner_unverified"])
            records=runs.load_stream_records(root,ids["run_id"],"SERVER")
            self.assertIn("turn_bridge_dispatch",{r["event"] for r in records})
            with self.assertRaises(UltraChatError) as e:
                reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"])
            self.assertEqual(e.exception.code,"local_owner_still_running")
            self.assertEqual(len(self.calls),1)
            kid.kill();self.assertIsNotNone(kid.wait(timeout=5))
        finally:
            release.set()
        # Windows kernel has released the worker's locked file handle.
        result=reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"])
        self.assertEqual(result["state"],"UNKNOWN")
        self.assertEqual(result["diagnostic_code"],"owner_process_lost")
        self.assertFalse(result["owner_unverified"])
        self.assertIsNone(result["answer"])
        self.assertEqual(len(self.calls),1)
        r2=reader.lookup(root,wid,cid,body["idempotency_key"])
        self.assertEqual(r2["turn_id"],result["turn_id"])
        self.assertEqual(r2["state"],"UNKNOWN")
        self.assertEqual(len(self.calls),1)
        page=core.read_chat_history_bounded(root,cid)
        self.assertEqual([m["role"] for m in page["messages"]],["user"])
        self.assertEqual(len(core.list_chats(root)),1)

    def test_actual_child_crashes_after_durable_terminal_then_RECOVER_SUCCESS(self):
        root,wid,cid,body,reader,server,base,read=self.prep("crash after terminal")
        kid=self.spawn(root,wid,cid,body,"after_terminal")
        self.assertEqual(kid.wait(timeout=15),87)
        ids=identities(wid,cid,body["idempotency_key"])
        saved=reader._load(root,wid,cid,ids["turn_id"])
        self.assertEqual(saved["state"],"ATTEMPTING")
        records=runs.load_stream_records(root,ids["run_id"],"SERVER")
        self.assertIn("turn_bridge_terminal",{r["event"] for r in records})
        self.assertEqual(len(self.calls),1)
        result=reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"])
        self.assertEqual(result["state"],"SUCCEEDED")
        self.assertEqual(result["answer"],"Ответ")
        self.assertFalse(result["owner_unverified"])
        self.assertEqual(len(self.calls),1)
        self.assertEqual(reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"]),result)
        self.assertEqual(len(self.calls),1)
        page=core.read_chat_history_bounded(root,cid)
        self.assertEqual([(m["role"],m["text"]) for m in page["messages"]],
                         [("user","crash after terminal"),("assistant","Ответ")])

    def test_child_dies_before_START_evidence_remains_manual_HOLD(self):
        root,wid,cid,body,reader,server,base,read=self.prep("no start proof")
        kid=self.spawn(root,wid,cid,body,"before_start")
        self.assertEqual(kid.wait(timeout=15),86)
        ids=identities(wid,cid,body["idempotency_key"])
        self.assertEqual(len(self.calls),0)
        self.assertEqual(reader._load(root,wid,cid,ids["turn_id"])["state"],"ATTEMPTING")
        self.assertEqual(runs.load_stream_records(root,ids["run_id"],"SERVER"),[])
        with self.assertRaises(UltraChatError) as exc:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"])
        self.assertEqual(exc.exception.code,"local_recovery_incomplete")
        # The OS lease only guards ownership; it cannot translate failures
        # raised inside the protected Turn into a fake "lock unavailable".
        with self.assertRaisesRegex(ValueError,"Turn body sentinel"):
            with claim(root,ids["run_id"]):
                raise ValueError("Turn body sentinel")
        # A pre-#663 Turn would have no lock file at all. A modern reader
        # cannot safely infer that the older sender is dead.
        lease=runs.run_component_path(root,ids["run_id"],"colibri-owner.lock")
        self.assertTrue(lease.is_file())
        lease.unlink()
        with self.assertRaises(UltraChatError) as old:
            reader.reconcile_orphaned_colibri(root,wid,cid,ids["turn_id"])
        self.assertEqual(old.exception.code,"local_owner_lease_unrecorded")
        self.assertEqual(reader.lookup(root,wid,cid,body["idempotency_key"])["state"],"UNKNOWN")
        self.assertEqual(len(self.calls),0)
        self.assertEqual([m["role"] for m in core.read_chat_history_bounded(root,cid)["messages"]],["user"])

if __name__=="__main__":
    suite=unittest.TestSuite(Recovery(n) for n in (
        "test_alive_owner_refused_then_actual_kill_durable_UNKNOWN",
        "test_actual_child_crashes_after_durable_terminal_then_RECOVER_SUCCESS",
        "test_child_dies_before_START_evidence_remains_manual_HOLD"))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
