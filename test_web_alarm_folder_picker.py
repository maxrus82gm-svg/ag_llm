"""Native picker boundary: loopback HTTP, no real dialog, disposable bytes."""
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

from web_alarm.folder_picker import FolderPicker, FolderPickerError, native_selection
from web_alarm.server import WebAlarmApi, create_server
from test_web_alarm_operator_ui import tree


def completed(value):
    return subprocess.CompletedProcess([], 0, json.dumps(value), '')


class PickerHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wa4ux002_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.selected = self.root/'Выбор папки with spaces'
        self.selected.mkdir()
        (self.selected/'untouched.txt').write_bytes(b'original')
        self.api = WebAlarmApi(self.root/'storage')
        self.server = create_server(self.api, port=0, enable_folder_picker=True)
        self.picker = self.server.web_alarm_folder_picker
        self.cap = patch.object(self.picker, 'capabilities', return_value={'available': True, 'reason': None}).start()
        self.addCleanup(patch.stopall)
        self.run = patch('web_alarm.folder_picker.subprocess.run', return_value=completed({'status': 'SELECTED', 'workspace_root': str(self.selected)})).start()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.origin = 'http://127.0.0.1:'+str(self.server.server_port)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        self.assertFalse(self.thread.is_alive())

    def request(self, method='POST', path='/ui/pick-workspace-folder', body=b'{}', changes=None, omit=(), extra=()):
        headers = {'Host': self.origin.removeprefix('http://')}
        if method == 'POST':
            headers.update({'Origin': self.origin, 'Content-Type': 'application/json',
                            'Content-Length': str(len(body)), 'X-WebAlarm-Folder-Token': self.picker.token})
        headers.update(changes or {})
        for key in omit:
            headers.pop(key, None)
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for k, v in [*headers.items(), *extra]:
                conn.putheader(k, v)
            conn.endheaders(body if method == 'POST' else None)
            response = conn.getresponse()
            raw = response.read()
            return response.status, json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw
        finally:
            conn.close()

    def test_capability_get_is_pure_and_does_not_open_dialog(self):
        before = tree(self.root)
        code, value = self.request('GET', '/ui/capabilities')
        self.assertEqual(code, 200)
        self.assertTrue(value['folder_picker']['available'])
        self.assertEqual(value['folder_picker']['token'], self.picker.token)
        self.run.assert_not_called()
        self.assertEqual(tree(self.root), before)

    def test_selected_path_and_cancel_do_not_register_or_mutate(self):
        before = tree(self.root)
        with patch.object(self.api.registry, 'register', side_effect=AssertionError('unexpected registration')), patch.object(self.api.tasks, 'create_task', side_effect=AssertionError('unexpected task')):
            code, value = self.request()
            self.assertEqual((code, value), (200, {'status': 'SELECTED', 'workspace_root': str(self.selected.resolve())}))
            self.run.return_value = completed({'status': 'CANCELLED'})
            self.assertEqual(self.request(), (200, {'status': 'CANCELLED'}))
        self.assertEqual(tree(self.root), before)

    def test_wrong_origin_host_token_and_fetch_metadata_never_reach_helper(self):
        cases = [({'Origin': 'https://foreign.example'}, (), ()), ({'Origin': 'null'}, (), ()),
                 ({}, ('Origin',), ()), ({'Origin': self.origin+'/'}, (), ()),
                 ({'Host': 'foreign.example:'+str(self.server.server_port)}, (), ()),
                 ({'Host': '127.0.0.1:1'}, (), ()), ({}, ('Host',), ()),
                 ({'X-WebAlarm-Folder-Token': 'wrong'}, (), ()), ({}, ('X-WebAlarm-Folder-Token',), ()),
                 ({'Sec-Fetch-Site': 'cross-site'}, (), ()), ({'Sec-Fetch-Site': 'same-site'}, (), ()),
                 ({}, (), (('Host', 'foreign.example'),)), ({}, (), (('Origin', self.origin),)),
                 ({'Sec-Fetch-Site': 'same-origin'}, (), (('Sec-Fetch-Site', 'cross-site'),)),
                 ({}, (), (('X-WebAlarm-Folder-Token', self.picker.token),))]
        before = tree(self.root)
        for changes, omit, extra in cases:
            with self.subTest(changes=changes, omit=omit, duplicate=[k for k, _ in extra]):
                code, _ = self.request(changes=changes, omit=omit, extra=extra)
                self.assertEqual(code, 403)
        self.run.assert_not_called()
        self.assertEqual(tree(self.root), before)

    def test_foreign_capability_get_does_not_disclose_token(self):
        code, value = self.request('GET', '/ui/capabilities', changes={'Origin': 'https://foreign.example'})
        self.assertEqual(code, 403)
        self.assertNotIn(self.picker.token, json.dumps(value))
        self.run.assert_not_called()

    def test_non_ascii_capability_is_rejected_before_native_helper(self):
        self.assertEqual(self.request(changes={'X-WebAlarm-Folder-Token': 'invalid-é'})[0], 403)
        self.run.assert_not_called()

    def test_native_route_rejects_other_methods(self):
        for method in ('GET', 'PUT', 'PATCH', 'DELETE'):
            with self.subTest(method=method):
                self.assertEqual(self.request(method)[0], 405)
        self.assertEqual(self.request('POST', '/ui/capabilities')[0], 405)
        self.run.assert_not_called()

    def test_body_and_media_type_are_strict(self):
        for raw in (b'[]', b'null', b'{broken', b'{"workspace_root":"C:/untrusted"}', b' '*65):
            with self.subTest(raw=raw):
                self.assertEqual(self.request(body=raw)[0], 400)
        self.assertEqual(self.request(changes={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request(omit=('Content-Length',))[0], 400)
        self.assertEqual(self.request(extra=(('Content-Length', '2'),))[0], 400)
        self.assertEqual(self.request(changes={'Content-Length': '9'*100})[0], 400)
        self.assertEqual(self.request(path='/ui/pick-workspace-folder?path=bad')[0], 400)
        self.run.assert_not_called()

    def test_disabled_mode_is_unavailable_without_side_effects(self):
        self.cap.return_value = {'available': False, 'reason': 'disabled'}
        self.assertEqual(self.request()[0], 503)
        value = self.request('GET', '/ui/capabilities')[1]['folder_picker']
        self.assertFalse(value['available'])
        self.assertIsNone(value['token'])
        self.run.assert_not_called()

    def test_remote_bind_metadata_is_rejected_even_for_loopback_client(self):
        address = self.server.server_address
        try:
            self.server.server_address = ('0.0.0.0', address[1])
            self.assertEqual(self.request()[0], 403)
        finally:
            self.server.server_address = address
        self.run.assert_not_called()

    def test_single_flight_and_release_after_completion(self):
        entered, release = threading.Event(), threading.Event()
        def native(*args, **kwargs):
            entered.set()
            if not release.wait(4):
                raise AssertionError('test barrier timed out')
            return completed({'status': 'CANCELLED'})
        self.run.side_effect = native
        first = []
        worker = threading.Thread(target=lambda: first.append(self.request()))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.assertEqual(self.request()[0], 409)
            self.assertEqual(self.run.call_count, 1)
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(first, [(200, {'status': 'CANCELLED'})])
        self.assertEqual(self.request()[0], 200)

    def test_timeout_and_startup_failure_are_honest_and_release_lock(self):
        self.run.side_effect = subprocess.TimeoutExpired('owned helper', 0.05)
        self.assertEqual(self.request()[0], 504)
        self.run.side_effect = OSError('unavailable')
        self.assertEqual(self.request()[0], 503)
        self.run.side_effect = None
        self.assertEqual(self.request()[0], 200)

    def test_ui_cannot_be_framed_by_external_site(self):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request('GET', '/')
            response = conn.getresponse()
            self.assertEqual(response.getheader('X-Frame-Options'), 'DENY')
            response.read()
        finally:
            conn.close()


class PickerWorkerTests(unittest.TestCase):
    def test_default_server_and_broker_are_disabled(self):
        self.assertFalse(FolderPicker().capabilities()['available'])
        with tempfile.TemporaryDirectory(prefix='wa4ux002_default_') as directory:
            server = create_server(WebAlarmApi(Path(directory)/'storage'), port=0)
            try:
                self.assertFalse(server.web_alarm_folder_picker.enabled)
            finally:
                server.server_close()

    def test_invalid_native_outputs_fail_closed_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='wa4ux002_invalid_') as directory:
            root = Path(directory)
            file = root/'file.txt'
            file.write_bytes(b'untouched')
            before = tree(root)
            picker = FolderPicker(enabled=True)
            values = [[], {'status': 'SELECTED', 'workspace_root': 'relative'},
                      {'status': 'SELECTED', 'workspace_root': str(file)},
                      {'status': 'SELECTED', 'workspace_root': str(root/'missing')},
                      {'status': 'CANCELLED', 'workspace_root': str(root)}, {'status': 'UNKNOWN'}]
            with patch.object(picker, 'capabilities', return_value={'available': True}), patch('web_alarm.folder_picker.subprocess.run') as run:
                for value in values:
                    with self.subTest(value=value):
                        run.return_value = completed(value)
                        with self.assertRaises(FolderPickerError):
                            picker.pick()
                run.return_value = subprocess.CompletedProcess([], 0, '{broken', '')
                with self.assertRaises(FolderPickerError):
                    picker.pick()
                run.return_value = subprocess.CompletedProcess([], 1, '', 'private error')
                with self.assertRaisesRegex(FolderPickerError, 'valid result'):
                    picker.pick()
            self.assertEqual(tree(root), before)

    def test_real_bounded_subprocess_is_killed_and_reaped(self):
        picker = FolderPicker(enabled=True, timeout=0.1)
        real_popen, children = subprocess.Popen, []
        def capture(_args, **kwargs):
            child = real_popen([sys.executable, '-B', '-c', 'import time;time.sleep(10)'], **kwargs)
            children.append(child)
            return child
        try:
            with patch.object(picker, 'capabilities', return_value={'available': True}), patch('web_alarm.folder_picker.subprocess.Popen', side_effect=capture):
                with self.assertRaises(FolderPickerError) as caught:
                    picker.pick()
            self.assertEqual(caught.exception.code, 'folder_picker_timeout')
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(children[0].wait(timeout=1), children[0].returncode)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=2)

    def test_native_selection_uses_existing_directory_dialog_and_destroys_owner(self):
        owner, dialog = Mock(), Mock()
        tk = types.ModuleType('tkinter')
        tk.Tk = Mock(return_value=owner)
        tk.filedialog = types.SimpleNamespace(askdirectory=dialog)
        for selected in ('M:/TEMP/Выбор', ''):
            with self.subTest(selected=selected), patch.dict(sys.modules, {'tkinter': tk}), patch('web_alarm.folder_picker.sys.platform', 'win32'):
                owner.reset_mock()
                dialog.return_value = selected
                result = native_selection()
                self.assertEqual(result['status'], 'SELECTED' if selected else 'CANCELLED')
                self.assertTrue(dialog.call_args.kwargs['mustexist'])
                owner.destroy.assert_called_once()
        with patch.dict(sys.modules, {'tkinter': tk}), patch('web_alarm.folder_picker.sys.platform', 'win32'):
            owner.reset_mock()
            dialog.side_effect = RuntimeError('GUI unavailable')
            self.assertEqual(native_selection(), {'status': 'UNAVAILABLE'})
            owner.destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
