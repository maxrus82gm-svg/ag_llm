"""Prove browser startup, no Tk imports and disposable cleanup through the existing Stage 5 fixture."""
import builtins
import contextlib
import http.client
import io
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch
import webbrowser

fixture = Path(sys.argv[1]).resolve()
opened = []
original_import = builtins.__import__


def no_tk(name, *args, **kwargs):
    if name == "ultra_ui" or name == "tkinter" or name.startswith("tkinter."):
        raise AssertionError("Web entry must never import Tk: " + name)
    return original_import(name, *args, **kwargs)


def open_local(url):
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    assert parts.scheme == "http" and parts.hostname == "127.0.0.1"
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)
    try:
        connection.request("GET", "/")
        reply = connection.getresponse()
        assert reply.status == 200 and b'data-stage5-offline="true"' in reply.read()
    finally:
        connection.close()
    opened.append(url)
    return True


before = set(Path(tempfile.gettempdir()).glob("stage5_тест_*"))
module = runpy.run_path(str(fixture))
output = io.StringIO()
with patch.object(sys, "argv", [str(fixture), "--web"]), patch.object(sys, "stdin", io.StringIO("\n")), \
        patch.object(webbrowser, "open", side_effect=open_local), patch.object(builtins, "__import__", no_tk), \
        contextlib.redirect_stdout(output):
    module["main"]()
print(output.getvalue(), end="")
assert len(opened) == 1, "TEST must open its Web page automatically; browser opens=" + str(len(opened))
assert set(Path(tempfile.gettempdir()).glob("stage5_тест_*")) == before, "TEST storage must be removed"
print("PASS: browser opens once; HTTP 200/OFFLINE; no Tk import; Enter stops server; TEST storage removed")
