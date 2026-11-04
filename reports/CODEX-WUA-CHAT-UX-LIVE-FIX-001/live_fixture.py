"""Disposable Windows GUI fixture. No launcher/config or production storage changes."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tempfile
import threading

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import context_storage as cs
from web_alarm import server as wa
from web_alarm.launcher import Launch, mark_page

parser = argparse.ArgumentParser()
parser.add_argument('--before', action='store_true')
args = parser.parse_args()
report = Path(__file__).resolve().parent
if args.before:
    namespace = {'__name__': 'web_alarm.before_ui', '__package__': 'web_alarm'}
    exec(compile((report / 'before/web_alarm/ui.py').read_text(encoding='utf-8'), 'before_ui.py', 'exec'), namespace)
    wa.INDEX_HTML = namespace['INDEX_HTML']

with tempfile.TemporaryDirectory(prefix='CODEX-WUA-CHAT-UX-LIVE-FIX-001-') as temp:
    base = Path(temp).resolve()
    api = wa.WebAlarmApi(base / 'registry')
    for name, titles in [('Alpha', ['Первый диалог', 'Второй диалог']), ('Beta', ['Единственный диалог'])]:
        root = base / name
        root.mkdir()
        cs.ensure_workspace_storage(root)
        for title in titles:
            chat = cs.create_chat(root, title)['chat_id']
            cs.append_raw_message(root, chat, 'user', 'Синтетическая история: ' + title)
        api.registry.register(name, root)
    empty = base / 'Empty'
    empty.mkdir()
    damaged = base / 'Damaged'
    damaged.mkdir()
    cs.ensure_workspace_storage(damaged)
    (damaged / '.ultra/workspace.json').write_text('{', encoding='utf-8')
    api.registry.register('Damaged', damaged)
    server = wa.create_server(api, port=0, enable_folder_picker=True)
    original = server.RequestHandlerClass
    class Handler(original):
        def _send_html(self, page):
            super()._send_html(mark_page(page, Launch(name='CODEX-WUA-CHAT-UX-LIVE-FIX-001 / ' + ('RED' if args.before else 'GREEN'), title='isolated GUI', standard=False)))
    server.RequestHandlerClass = Handler
    info = dict(url=f'http://127.0.0.1:{server.server_port}/', mode='before' if args.before else 'after',
                empty_folder=str(empty), base=str(base), user_storage_used=False,
                html_sha256=hashlib.sha256(wa.INDEX_HTML.encode()).hexdigest())
    (report / 'evidence' / ('gui_red_fixture.json' if args.before else 'gui_green_fixture.json')).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False), flush=True)
    stop = report / ('stop_red_fixture' if args.before else 'stop_green_fixture')
    def watch_stop():
        import time
        while not stop.exists():
            time.sleep(.2)
        server.shutdown()
    threading.Thread(target=watch_stop, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        rows = [dict(id=r.workspace_id, name=r.display_name) for r in api.registry.list()]
        (report / 'evidence' / ('gui_red_readback.json' if args.before else 'gui_green_readback.json')).write_text(json.dumps(dict(workspaces=rows, empty_history_created=(empty / '.ultra').exists()), ensure_ascii=False, indent=2), encoding='utf-8')
        print('OWNED FIXTURE STOPPED; temporary storage removed on exit', flush=True)
