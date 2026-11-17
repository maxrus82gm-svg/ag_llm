"""Disposable loopback tests for cooperative instance inventory and cleanup."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from web_alarm.instance_control import cleanup, inventory, register, unregister
from web_alarm.server import WebAlarmApi, create_server
from web_alarm.ui import UI_VERSION, INDEX_HTML


class InstanceControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='wa-instance-test-')
        self.addCleanup(self.tmp.cleanup)
        self.servers=[]
        self.addCleanup(self._stop)

    def _server(self, label, storage):
        root=Path(self.tmp.name)/str(len(self.servers))
        server=create_server(WebAlarmApi(root), port=0)
        register(server,profile=label,storage=storage,ui_version=UI_VERSION)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.servers.append((server,thread))
        return server

    def _stop(self):
        for server,thread in self.servers:
            unregister(server)
            server.shutdown()
            server.server_close()
            thread.join(3)

    def test_identity_inventory_cleanup_preserves_current_and_test(self):
        current=self._server('standard','same-storage')
        extra=self._server('standard','same-storage')
        test=self._server('test','test-storage')
        states={r['instance_id']:r['state'] for r in inventory(current)}
        self.assertEqual(states[current.web_alarm_instance['instance_id']],'CURRENT')
        self.assertEqual(states[extra.web_alarm_instance['instance_id']],'EXTRA_CONFIRMED')
        self.assertEqual(states[test.web_alarm_instance['instance_id']],'OTHER_CONFIRMED')
        result=cleanup(current,[current.web_alarm_instance['instance_id'],test.web_alarm_instance['instance_id'],extra.web_alarm_instance['instance_id']])
        self.assertEqual([r['state'] for r in result],['REFUSED_UNVERIFIED','REFUSED_UNVERIFIED','STOPPING'])
        self.servers[1][1].join(3)
        self.assertFalse(self.servers[1][1].is_alive())
        self.assertTrue(self.servers[0][1].is_alive())
        self.assertTrue(self.servers[2][1].is_alive())

    def test_instance_endpoint_and_cache_marker(self):
        current=self._server('standard','same-storage')
        base=f'http://127.0.0.1:{current.server_port}'
        with urlopen(base+'/ui/instance',timeout=3) as response:
            found=json.load(response)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(found['instance_id'],current.web_alarm_instance['instance_id'])
        self.assertEqual(found['port'],current.server_port)
        self.assertIn(f'content="{UI_VERSION}"',INDEX_HTML)
        with urlopen(base+'/',timeout=3) as response:
            self.assertEqual(response.headers['Cache-Control'],'no-store')

    def test_cleanup_requires_existing_write_token_and_exact_origin(self):
        current=self._server('standard','same-storage')
        base=f'http://127.0.0.1:{current.server_port}'
        body=json.dumps({'confirmation':'CLEAN EXTRA WEB ALARM','instance_ids':[]}).encode()
        for headers in ({'Content-Type':'application/json'},
                        {'Content-Type':'application/json','Origin':'http://evil.invalid'}):
            with self.subTest(headers=headers):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(base+'/ui/instances/cleanup',data=body,headers=headers,method='POST'),timeout=3)
                self.assertEqual(caught.exception.code,403)
        self.assertTrue(self.servers[0][1].is_alive())


if __name__=='__main__':
    unittest.main()
