"""Compact sidebar: actual local HTTP, no provider or production storage."""
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import context_storage as core
from web_alarm.ultra_chat import OrdinaryCoreChatService
from web_alarm.server import WebAlarmApi
from web_alarm.ordinary_provider import OrdinaryProviderFactory
import test_web_alarm_ultra_chat_s5 as s5

BASE = "/ultra/chat/sidebar"

def fresh(prefix):
    return prefix + "_" + uuid4().hex

class CompactSidebarTests(s5.Fixture):
    serve = s5.HttpAndTkTests.serve
    http = s5.HttpAndTkTests.http
    tokens = s5.HttpAndTkTests.tokens

    def setUp(self):
        super().setUp()
        self.api = WebAlarmApi(self.root / "registry")
        self.service = OrdinaryCoreChatService(self.api.registry, self.root)

    def compact_flow(self, offline):
        server = self.serve(offline_chat=self.service) if offline else self.serve()
        cap, read, write = self.tokens(server)
        self.assertTrue(cap["compact_sidebar"])
        self.assertIsNone(cap["personal_workspace_id"])
        post = lambda endpoint, body: self.http(server, "POST", BASE + endpoint, body, write)
        get = lambda: self.http(server, "GET", BASE, headers=read)[1]
        self.assertEqual(get()["workspaces"], [])
        cid = fresh("chat")
        self.assertEqual(self.http(server,"POST",BASE+"/personal", {"chat_id":cid})[0],403)
        self.assertEqual(get()["workspaces"], [])
        status, personal = post("/personal", {"chat_id":cid})
        self.assertIn(status, (200,201))
        self.assertEqual(personal["chat"]["title"], "Новый чат")
        pid = personal["wa_workspace_id"]
        self.assertEqual(get()["personal_workspace_id"],pid)
        self.assertEqual(len(get()["workspaces"][0]["chats"]),1)
        self.assertIn(post("/personal", {"chat_id":cid})[0], (200,201))
        self.assertEqual(len(get()["workspaces"][0]["chats"]),1)
        ws = fresh("ws")
        self.assertEqual(post("/workspace", {"workspace_id":ws})[0],201)
        snapshot = next(w for w in get()["workspaces"] if w["wa_workspace_id"] == ws)
        self.assertIsNone(snapshot["folder"])
        self.assertEqual(snapshot["chats"],[])
        root = Path(self.api.registry.get(ws).workspace_root)
        self.assertTrue(root.is_dir())
        chat = fresh("chat")
        self.assertEqual(post("/chat", {"workspace_id":ws,"chat_id":chat})[0],201)
        wid = core.read_workspace_identity_bounded(root)["workspace_id"]
        text = "Один два 3 четыре пять"
        core.commit_raw_message(root,chat,fresh("msg"),"user",text,expected_workspace_id=wid)
        self.assertEqual(core.list_chats_bounded(root)["chats"][0]["title"], "Один два 3 четыре")
        core.commit_raw_message(root,chat,fresh("msg"),"user","Не меняй название",expected_workspace_id=wid)
        self.assertEqual(core.list_chats_bounded(root)["chats"][0]["title"], "Один два 3 четыре")
        self.assertEqual(post("/chat", {"workspace_id":ws,"chat_id":chat})[0],200)
        chat2 = fresh("chat")
        self.assertEqual(post("/chat", {"workspace_id":ws,"chat_id":chat2})[0],201)
        core.rename_chat(root,chat2,"Новый чат",expected_workspace_id=wid)
        core.commit_raw_message(root,chat2,fresh("msg"),"user","Manual must remain",expected_workspace_id=wid)
        self.assertEqual(next(c for c in core.list_chats_bounded(root)["chats"] if c["chat_id"]==chat2)["title"],"Новый чат")
        folder = self.root / "selected-project"
        folder.mkdir()
        sentinel = folder / "keep.txt"
        sentinel.write_text("do not change")
        expected = None if offline else str(folder)
        self.assertEqual(post("/folder", {"workspace_id":ws,"folder":expected})[0],200)
        self.assertEqual(Path(self.api.registry.get(ws).workspace_root),root)
        self.assertEqual(sentinel.read_text(),"do not change")
        self.assertEqual(list(folder.iterdir()),[sentinel])
        raw = core.read_chat_history_bounded(root,chat)
        self.assertEqual(post("/archive", {"workspace_id":ws,"chat_id":chat})[0],200)
        self.assertEqual(core.read_chat_history_bounded(root,chat),raw)
        self.assertNotIn(chat,[c["chat_id"] for w in get()["workspaces"] for c in w["chats"]])
        self.assertEqual(post("/archive", {"workspace_id":ws})[0],200)
        self.assertNotIn(ws,[w["wa_workspace_id"] for w in get()["workspaces"]])
        self.assertTrue(root.is_dir())
        self.assertEqual(core.read_chat_history_bounded(root,chat),raw)
        self.assertEqual(post("/archive", {"workspace_id":pid})[0],409)
        second = self.serve(offline_chat=self.service) if offline else self.serve()
        _,r2,_ = self.tokens(second)
        self.assertNotIn(ws,[w["wa_workspace_id"] for w in self.http(second,"GET",BASE,headers=r2)[1]["workspaces"]])
        self.assertTrue(sentinel.exists())

    def test_test_offline(self):
        self.compact_flow(True)

    def test_standard_hold(self):
        self.compact_flow(False)

    def test_title_cap_and_manual_override(self):
        _, w = self.service.create_workspace({"title":"fixture"})
        ws=w["wa_workspace_id"]
        cid=fresh("chat")
        self.service.create_chat(ws,{"chat_id":cid,"title":"Новый чат","auto_title":True,"initialize_workspace":True})
        root=Path(self.api.registry.get(ws).workspace_root)
        core.commit_raw_message(root,cid,fresh("msg"),"user","x"*100+" second")
        self.assertEqual(core.list_chats_bounded(root)["chats"][0]["title"],"x"*40)

    def test_real_http_offline_turn_and_title(self):
        server = self.serve(offline_chat=self.service)
        cap, read, write = self.tokens(server)
        cid = fresh("chat")
        status, personal = self.http(server, "POST", BASE+"/personal", {"chat_id":cid},write)
        self.assertIn(status,(200,201))
        ws = personal["wa_workspace_id"]
        base = f"/ultra/chat/workspaces/{ws}/chats/{cid}"
        msg = "Первое сообщение с 42 цифрами"
        body = {"idempotency_key": str(uuid4()),"model_ref":"gigachat_2_pro","text":msg}
        status, turn = self.http(server,"POST",base+"/turns",body,write)
        self.assertEqual((status,turn["state"]),(200,"SUCCEEDED"),turn)
        page = self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]
        self.assertEqual(page["chat"]["title"],"Первое сообщение с 42")
        self.assertEqual(page["messages"][0]["text"],msg)
        self.assertEqual(self.http(server,"POST",base+"/turns",body,write)[1],turn)
        self.assertEqual(self.http(server,"POST",BASE+"/archive",{"workspace_id":ws,"chat_id":cid},write)[0],200)
        self.assertEqual(self.http(server,"GET",base+"/messages?limit=50",headers=read)[1]["messages"],page["messages"])
        visible=self.http(server,"GET",BASE,headers=read)[1]
        self.assertEqual(visible["workspaces"][0]["chats"],[])
