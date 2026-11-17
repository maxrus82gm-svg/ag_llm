"""Local shutdown admission and socket lifecycle; never uses provider credentials."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from web_alarm.server import WebAlarmApi, create_server


class GracefulExitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='wa-exit-test-')
        self.addCleanup(self.tmp.cleanup)
        self.server = create_server(WebAlarmApi(Path(self.tmp.name)), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop)
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def _stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def _call(self, path, *, body=None, token=None, origin=None):
        headers = {'Host':'127.0.0.1:'+str(self.server.server_port)}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if token is not None:
                headers['X-WebAlarm-Ultra-Chat-Write-Token'] = token
            if origin is not None:
                headers['Origin'] = origin
        req = Request(self.base+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_shutdown_requires_local_origin_token_and_confirmation(self):
        _, capability = self._call('/ui/ultra-chat/write-capability')
        token = capability['ultra_chat_write']['token']
        self.assertEqual(self._call('/ui/shutdown',body={'confirmation':'SHUTDOWN WEB ALARM'},token=token,origin='http://evil.invalid')[0],403)
        self.assertEqual(self._call('/ui/shutdown',body={'confirmation':'SHUTDOWN WEB ALARM'},origin=self.base)[0],403)
        self.assertEqual(self._call('/ui/shutdown',body={},token=token,origin=self.base)[0],400)
        self.assertFalse(self.server.web_alarm_shutdown_tracker['stopping'])
        status, result = self._call('/ui/shutdown',body={'confirmation':'SHUTDOWN WEB ALARM'},token=token,origin=self.base)
        self.assertEqual((status,result['state'],result['scope']),(202,'STOPPING','THIS_INSTANCE'))
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.server.web_alarm_shutdown_tracker['active'],0)

    def test_stopping_rejects_new_work_and_port_can_restart(self):
        tracker=self.server.web_alarm_shutdown_tracker
        with tracker['condition']:
            tracker['stopping']=True
        status, result=self._call('/status')
        self.assertEqual((status,result['error']['code']),(503,'application_stopping'))
        with tracker['condition']:
            tracker['stopping']=False
        port=self.server.server_port
        self._stop()
        restarted=create_server(WebAlarmApi(Path(self.tmp.name)),port=port)
        try:
            self.assertEqual(restarted.server_port,port)
        finally:
            restarted.server_close()

    def test_duplicate_shutdown_while_server_stopping_is_idempotent(self):
        _, capability=self._call('/ui/ultra-chat/write-capability')
        token=capability['ultra_chat_write']['token']
        real_shutdown=self.server.shutdown
        release=threading.Event()
        self.server.shutdown=lambda: release.wait(3)
        try:
            for _ in range(2):
                status, result=self._call('/ui/shutdown',body={'confirmation':'SHUTDOWN WEB ALARM'},token=token,origin=self.base)
                self.assertEqual((status,result['state']),(202,'STOPPING'))
        finally:
            release.set()
            self.server.shutdown=real_shutdown


if __name__ == '__main__':
    unittest.main()
