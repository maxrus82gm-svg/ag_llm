"""Disposable probe (TEMP only, synthetic bytes): which Windows file primitives the recovery design may rely on.

Prints one JSON object. Touches nothing outside its own TemporaryDirectory.
"""
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

facts = {"python": sys.version.split()[0], "platform": sys.platform}
with tempfile.TemporaryDirectory(prefix="wa_tailrec_probe_") as tmp:
    base = Path(tmp)
    f = base / "log.jsonl"
    f.write_bytes(b'{"a":1}\n{"b"')
    st_l = os.lstat(f)
    with f.open("rb") as h:
        st_f = os.fstat(h.fileno())
    facts["ino_nonzero"] = st_l.st_ino != 0
    facts["fstat_matches_lstat"] = (st_l.st_ino, st_l.st_dev) == (st_f.st_ino, st_f.st_dev)
    # os.replace onto a file a lock-free reader currently holds open
    new = base / "new.tmp"
    new.write_bytes(b'{"a":1}\n')
    reader = f.open("rb")
    try:
        os.replace(new, f)
        facts["replace_while_reader_open"] = "SUCCEEDED"
    except OSError as exc:
        facts["replace_while_reader_open"] = f"{type(exc).__name__}: winerror={getattr(exc, 'winerror', None)}"
    finally:
        reader.close()
    facts["after_failed_replace_original_intact"] = f.read_bytes() == b'{"a":1}\n{"b"' if new.exists() else None
    if new.exists():
        os.replace(new, f)
    facts["replace_after_reader_closed"] = f.read_bytes() == b'{"a":1}\n'
    # identity changes across replace (new file object)
    facts["ino_changes_on_replace"] = os.lstat(f).st_ino != st_l.st_ino
    # read-only target
    ro = base / "ro.jsonl"
    ro.write_bytes(b"x")
    os.chmod(ro, stat.S_IREAD)
    src = base / "src.tmp"
    src.write_bytes(b"y")
    try:
        os.replace(src, ro)
        facts["replace_onto_readonly"] = "SUCCEEDED"
    except OSError as exc:
        facts["replace_onto_readonly"] = f"{type(exc).__name__}: winerror={getattr(exc, 'winerror', None)}"
    os.chmod(ro, stat.S_IWRITE | stat.S_IREAD)
    # exclusive create
    ex = base / "ex.bin"
    fd = os.open(ex, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    os.close(fd)
    try:
        os.open(ex, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        facts["o_excl_second_create"] = "SUCCEEDED"
    except FileExistsError:
        facts["o_excl_second_create"] = "FileExistsError"
    # junctions and reparse detection
    target = base / "real"
    target.mkdir()
    junction = base / "junc"
    try:
        import _winapi
        _winapi.CreateJunction(str(target), str(junction))
        attrs = os.lstat(junction).st_file_attributes
        facts["junction_created"] = True
        facts["junction_reparse_attr"] = bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        facts["path_is_junction"] = Path(junction).is_junction()
        facts["path_is_symlink_for_junction"] = Path(junction).is_symlink()
        facts["resolve_follows_junction"] = Path(junction).resolve() != junction
        os.rmdir(junction)
    except Exception as exc:  # noqa: BLE001 - probe records what happened
        facts["junction_created"] = f"{type(exc).__name__}: {exc}"
    try:
        os.symlink(target, base / "sym", target_is_directory=True)
        facts["symlink_created"] = True
    except OSError as exc:
        facts["symlink_created"] = f"{type(exc).__name__}: winerror={getattr(exc, 'winerror', None)}"
    # directory fsync
    try:
        dfd = os.open(base, os.O_RDONLY)
        try:
            os.fsync(dfd)
            facts["directory_fsync"] = "SUCCEEDED"
        finally:
            os.close(dfd)
    except OSError as exc:
        facts["directory_fsync"] = f"{type(exc).__name__}: errno={exc.errno}"
print(json.dumps(facts, indent=1))
