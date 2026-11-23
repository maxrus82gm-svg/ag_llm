"""MVP1 independent, isolated WUA PRE-LIVE safety gate (#662).

Exact pinned Colibri #108 producer, actual temporary HTTP Bridge handler,
same WUA HTTP/API and primary Turn service; no real Home Manager access.
"""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-EVM-20261122-001"))
sys.path.insert(0,str(ROOT/"reports"/"CHATGPT-WUA-COLIBRI-MVP1-REVIEW-20261122-001"))
import unittest
import threading
import time
import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from web_alarm.colibri_bridge_transport import BridgeFault
from web_alarm.turn_service import TurnService
from web_alarm.ultra_chat import UltraChatError
import context_storage as core
import joint_evm

class Preflight(joint_evm.JointEVM):
    def test_default_project_context_marker_only_is_no_instruction(self):
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        untouched=core.load_project_context(root)
        self.assertEqual(untouched,core.PROJECT_CONTEXT_TEMPLATE)
        self.assertEqual(self.http(server,"POST",base+"/model",{"model_ref":self.local},write)[0],200)
        body=self.body("No PROJECT CONTEXT instructions",self.local)
        status,result=self.http(server,"POST",base+"/turns",body,write)
        self.assertEqual(status,200,result)
        self.assertEqual(result["state"],"SUCCEEDED")
        self.assertEqual(self.calls,[[{"role":"user","content":"No PROJECT CONTEXT instructions"}]])
        # The file itself is unchanged; cloud gets its original system context.
        self.assertEqual(core.load_project_context(root),untouched)
        core.save_project_context(root,untouched+"\n# Important extra user directive\n")
        status,refused=self.http(server,"POST",base+"/turns",self.body("Require system",self.local),write)
        self.assertEqual(status,409,refused)
        self.assertEqual(refused["error"]["code"],"unsupported_capability")
        self.assertEqual(len(self.calls),1)
        core.save_project_context(root,"# PROJECT CONTEXT\n\nПока не заполнен.\n")  # near match is NOT the actual template
        status,refused=self.http(server,"POST",base+"/turns",self.body("Near marker",self.local),write)
        self.assertEqual(status,409,refused)
        self.assertEqual(refused["error"]["code"],"unsupported_capability")
        self.assertEqual(len(self.calls),1)
        self.assertEqual([m["text"] for m in
            self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]["messages"]],
            ["No PROJECT CONTEXT instructions","Ответ"])

    @unittest.skipUnless(os.name == "nt", "Windows-specific ACL admission")
    def test_windows_acl_broad_read_denied_without_network(self):
        import win32security as sec
        import ntsecuritycon as rights

        everyone=sec.CreateWellKnownSid(sec.WinBuiltinUsersSid,None)
        for name in ("bridge-discovery.json","bridge-wua.token","."):
            with self.subTest(name=name):
                file=self.folder/name
                sd=sec.GetNamedSecurityInfo(str(file),sec.SE_FILE_OBJECT,
                                              sec.DACL_SECURITY_INFORMATION)
                old=sd.GetSecurityDescriptorDacl()
                self.assertIsNotNone(old)
                weak=sec.ACL()
                for i in range(old.GetAceCount()):
                    ace=old.GetAce(i)
                    self.assertEqual(ace[0][0],sec.ACCESS_ALLOWED_ACE_TYPE)
                    weak.AddAccessAllowedAceEx(sec.ACL_REVISION,ace[0][1],ace[1],ace[2])
                weak.AddAccessAllowedAceEx(sec.ACL_REVISION,0,rights.FILE_GENERIC_READ,everyone)
                # Only disposable fixture files. Restore exact prior ACL before continuing.
                try:
                    sec.SetNamedSecurityInfo(str(file),sec.SE_FILE_OBJECT,
                                             sec.DACL_SECURITY_INFORMATION,None,None,weak,None)
                    with self.assertRaises(BridgeFault) as error:
                        self.transport.catalog()
                    self.assertEqual(error.exception.code,"unsafe_discovery")
                    self.assertEqual(self.calls,[])
                finally:
                    sec.SetNamedSecurityInfo(str(file),sec.SE_FILE_OBJECT,
                                             sec.DACL_SECURITY_INFORMATION,None,None,old,None)
                self.assertEqual(self.transport.catalog()["bridge_id"],self.bridge.bridge_id)
        # Also fail closed if a normal process cannot inspect the Windows DACL.
        with patch("win32security.GetNamedSecurityInfo", side_effect=OSError("access denied")):
            with self.assertRaises(BridgeFault) as error:
                self.transport.catalog()
            self.assertEqual(error.exception.code,"unsafe_discovery")
        self.assertEqual(self.calls,[])

    def test_owner_uncertain_cross_service_read_only_no_retry(self):
        """Reader in another WUA service has no local proof of physical owner."""
        ws,cid,server,cap,read,write,base,root,wid=self.application()
        core.save_project_context(root,"")
        self.assertEqual(self.http(server,"POST",base+"/model",{"model_ref":self.local},write)[0],200)
        ready=threading.Event()
        release=threading.Event()
        def blocked(*args,**kwargs):
            for event in self.fake_stream(*args,**kwargs):
                if event["type"]=="delta":
                    ready.set()
                    if not release.wait(15):
                        raise RuntimeError("test barrier")
                yield event
        self.manager_stream=blocked
        body=self.body("Owner over another process",self.local)
        with ThreadPoolExecutor() as executor:
            pending=executor.submit(server.web_alarm_ultra_chat.submit_turn,ws,cid,body)
            try:
                self.assertTrue(ready.wait(10))
                reader=TurnService(test_roots=[root])
                from web_alarm.turn_service import identities
                turn_id=identities(wid,cid,body["idempotency_key"])["turn_id"]
                view=reader.get(root,wid,cid,turn_id)
                self.assertEqual(view["state"],"UNKNOWN")
                self.assertTrue(view["owner_unverified"])
                # The upstream HTTP stream may buffer its first reasoning
                # frame while the producer is paused; no durable frame is
                # promised before the physical packet reaches the WUA reader.
                self.assertIsInstance(view["reasoning"],str)
                self.assertIsNone(view["answer"])
                self.assertFalse(any(e["type"]=="delta" for e in self.cancels))
                # New same-chat turn cannot silently jump over unfinished Turn.
                with self.assertRaises(UltraChatError) as err:
                    server.web_alarm_ultra_chat.submit_turn(ws,cid,self.body("No hidden duplicate",self.local))
                self.assertEqual(err.exception.code,"test_chat_busy")
                self.assertEqual(len(self.calls),1)
            finally:
                release.set()
            result=pending.result(timeout=25)
        self.assertEqual(result["state"],"SUCCEEDED")
        self.assertFalse(reader.get(root,wid,cid,turn_id)["owner_unverified"])
        replay=server.web_alarm_ultra_chat.submit_turn(ws,cid,body)
        self.assertEqual(replay["turn_id"],turn_id)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(core.list_chats(root)),1)

if __name__ == "__main__":
    suite=unittest.TestSuite(Preflight(name) for name in (
        "test_default_project_context_marker_only_is_no_instruction",
        "test_windows_acl_broad_read_denied_without_network",
        "test_owner_uncertain_cross_service_read_only_no_retry"))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
