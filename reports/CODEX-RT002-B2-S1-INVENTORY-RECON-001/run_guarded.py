"""Task-local wrapper: retain the exact S1 runner; add secret-read denial before imports."""
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(tempfile.mkdtemp(prefix="codex-s1-recon-"))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
for key in ("LOCALAPPDATA", "APPDATA", "TEMP", "TMP"):
    location = BASE / key.lower()
    location.mkdir()
    os.environ[key] = str(location)
tempfile.tempdir = str(BASE / "temp")
SECRET_KEYS = {"GIGACHAT_CREDENTIALS", "GIGACHAT_SCOPE", "GIGACHAT_ACCESS_TOKEN"}
for key in SECRET_KEYS:
    try:
        del os.environ[key]  # erase inherited values without reading them
    except KeyError:
        pass
secret_denials = []
synthetic_reads = []
synthetic_values = {}
original_getitem, original_pop, original_setitem, original_delitem = (
    os._Environ.__getitem__, os._Environ.pop, os._Environ.__setitem__, os._Environ.__delitem__)


def secret_getitem(self, key):
    if str(key).upper() in SECRET_KEYS:
        if key in synthetic_values:
            synthetic_reads.append(key)
            return synthetic_values[key]
        if key == "GIGACHAT_SCOPE":
            raise KeyError(key)  # public default; inherited value was erased, not read
        secret_denials.append("environment secret read")
        raise PermissionError("OFFLINE: credential read forbidden")
    return original_getitem(self, key)


def synthetic_setitem(self, key, value):
    if str(key).upper() in SECRET_KEYS:
        if key != "GIGACHAT_CREDENTIALS" or value != "s1-dummy-credentials":
            secret_denials.append("non-synthetic credential assignment")
            raise PermissionError("OFFLINE: only the exact S1 dummy credential fixture is allowed")
        synthetic_values[key] = value
    return original_setitem(self, key, value)


def synthetic_delitem(self, key):
    synthetic_values.pop(key, None)
    return original_delitem(self, key)


def safe_pop(self, key, *default):
    if str(key).upper() in SECRET_KEYS:
        try:
            del self[key]  # erase without retrieving a credential value
        except KeyError:
            if not default:
                raise
        return default[0] if default else None
    return original_pop(self, key, *default)


def secret_file_guard(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        name = Path(os.fsdecode(args[0])).name.lower()
        if name in {".env", "credentials.json", "access_token.json"}:
            secret_denials.append("credential file read")
            raise PermissionError("OFFLINE: credential file access forbidden")


os._Environ.__getitem__, os._Environ.pop, os._Environ.__setitem__ = secret_getitem, safe_pop, synthetic_setitem
os._Environ.__delitem__ = synthetic_delitem
sys.addaudithook(secret_file_guard)
mode = sys.argv[1]
sys.argv = [str(ROOT / "test_rt002_s1_routes.py")]
try:
    if mode == "s1":
        runpy.run_path(sys.argv[0], run_name="__main__")
    else:
        import test_rt002_s1_routes as s1
        s1._install_guards(BASE)  # same network/process/filesystem guard, BEFORE production imports
        s1._ISOLATED = True
        if mode == "controls":
            import socket
            controls = []
            for label, probe in [
                ("socket", lambda: socket.socket().connect(("192.0.2.1", 443))),
                ("dns", lambda: socket.getaddrinfo("offline.invalid", 443)),
                ("credentials", lambda: os.environ["GIGACHAT_ACCESS_TOKEN"]),
                ("credential_file", lambda: open(BASE / ".env")),
            ]:
                try:
                    probe()
                except PermissionError:
                    controls.append(label)
            assert controls == ["socket", "dns", "credentials", "credential_file"]
            print(json.dumps({"expected_blocked_before_io": controls, "physical_calls": 0}))
        else:
            sys.argv = [str(Path(__file__).with_name("recon_checks.py")), mode]
            runpy.run_path(sys.argv[0], run_name="__main__", init_globals={"SANDBOX": BASE})
finally:
    print(json.dumps({"secret_guard": {"denials": secret_denials, "synthetic_reads": len(synthetic_reads),
                                     "sandbox": str(BASE)}}, ensure_ascii=False))
