"""Task-local early guard. No production imports; inherited by Python children."""
import ipaddress
import json
import os
import socket
import sys
import threading
import time

_log = os.environ["ORDINARY_GUARD_LOG"]
_loopback = os.environ.get("ORDINARY_GUARD_NETWORK") == "loopback"
_root = os.path.normcase(os.path.abspath(os.environ["ORDINARY_GUARD_ROOT"]))
_environment_getitem = os._Environ.__getitem__
_internal = threading.local()
_socketpair = socket.socketpair


def _deny(event, boundary):
    with open(_log, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": event, "boundary": boundary,
                                 "pid": os.getpid(), "monotonic": time.monotonic()}) + "\n")
    raise PermissionError("OFFLINE guard: " + boundary)


def _env_getitem(self, key):
    if str(key).upper() in {"GIGACHAT_CREDENTIALS", "GIGACHAT_SCOPE", "GIGACHAT_ACCESS_TOKEN"}:
        _deny("credential_read", "credentials")
    return _environment_getitem(self, key)


os._Environ.__getitem__ = _env_getitem


def _env_contains(self, key):
    # Model cards may ask presence, without reading the value.
    return key in iter(self)


os._Environ.__contains__ = _env_contains


def _local(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def _self_pipe(*args, **kwargs):
    # CPython on Windows implements socketpair via loopback for asyncio's
    # wake-up pipe. This synchronous stdlib call is the sole strict-mode
    # exception; ordinary loopback connects remain denied.
    _internal.self_pipe = True
    try:
        return _socketpair(*args, **kwargs)
    finally:
        _internal.self_pipe = False


socket.socketpair = _self_pipe


def _audit(event, args):
    if event in {"socket.connect", "socket.connect_ex", "socket.bind"}:
        address = args[1]
        internal = getattr(_internal, "self_pipe", False)
        if not ((_loopback or internal) and isinstance(address, tuple) and _local(address[0])):
            _deny(event, "physical_network")
    elif event == "socket.getaddrinfo":
        if not ((_loopback or getattr(_internal, "self_pipe", False)) and _local(args[0])):
            _deny(event, "dns")
    elif event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}:
        executable = args[0]
        if executable is None and event == "subprocess.Popen":
            command = args[1]
            if isinstance(command, (list, tuple)):
                executable = command[0]
            elif isinstance(command, str):
                command = command.lstrip()
                executable = command.split('"', 2)[1] if command.startswith('"') else command.split(None, 1)[0]
        if os.path.normcase(os.path.abspath(str(executable))) != os.path.normcase(os.path.abspath(sys.executable)):
            _deny(event, "non_python_process")
    elif event in {"open", "os.scandir", "os.listdir"} and args:
        if isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
            if ".git" in path.split(os.sep):
                _deny(event, "git_metadata")
            if event == "open" and (os.path.basename(path) == ".env" or os.path.basename(path).startswith(".env.")):
                _deny(event, "credential_file")
            if path.startswith(_root + os.sep) and ".ultra" in path.split(os.sep):
                _deny(event, "repository_live_storage")
            if event == "open":
                mode = args[1]
                flags = args[2] or 0
                writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                if writing and any(path == os.path.join(_root, folder) or path.startswith(os.path.join(_root, folder) + os.sep)
                                   for folder in (".ultra", "чат_pro", "чат_pro_01", ".obsidian")):
                    _deny(event, "live_data_write")


sys.addaudithook(_audit)
