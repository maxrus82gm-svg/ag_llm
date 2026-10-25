"""Produce an unapplied patch and a private candidate; never edit repo sources."""
import argparse
import difflib
import json
from pathlib import Path
import shutil


def revise(path, old, new):
    raw = path.read_bytes()
    text = raw.decode('utf-8').replace('\r\n', '\n')
    if text.count(old) != 1:
        raise RuntimeError('patch anchor is not unique: ' + path.name)
    result = text.replace(old, new)
    if b'\r\n' in raw:
        result = result.replace('\n', '\r\n')
    path.write_bytes(result.encode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lab', type=Path, required=True)
    args = parser.parse_args()
    lab = args.lab.resolve()
    if not (lab / 'session.json').is_file():
        parser.error('expected review lab')
    baseline, candidate = lab / 'baseline', lab / 'candidate'
    shutil.copytree(baseline, candidate)  # Existing candidate is an error, never overwrite.
    path = candidate / 'web_alarm/file_state.py'
    revise(path, 'def observe_path(path: str | os.PathLike[str]) -> FileState:\n', '''def _observation_signature(info: os.stat_result) -> tuple:
    """Bind an observation to one regular file and detect visible concurrent writes."""
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_size,
        info.st_mtime_ns,
        getattr(info, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT,
    )


def observe_path(path: str | os.PathLike[str]) -> FileState:
''')
    revise(path, '''        with target.open("rb") as handle:
            while True:
                chunk = handle.read(_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
''', '''        with target.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _observation_signature(info) != _observation_signature(opened):
                raise FileStateError(f"target changed before observation: {target}")
            while True:
                chunk = handle.read(_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
            finished = os.fstat(handle.fileno())
            if (_observation_signature(opened) != _observation_signature(finished)
                    or digest.size != finished.st_size):
                raise FileStateError(f"target changed during observation: {target}")
            current = os.lstat(target)
            if _observation_signature(current) != _observation_signature(finished):
                raise FileStateError(f"target identity changed during observation: {target}")
''')
    path = candidate / 'web_alarm/manifest_store.py'
    revise(path, '''                    data = binary_path.read_bytes()
                    actions.append((target, snapshot, data))
''', '''                    data = binary_path.read_bytes()
                    # Verify the exact retained buffer consumed by the restore, not
                    # only an earlier read of this mutable snapshot path.
                    if (len(data) != snapshot.size_before
                            or _sha256(data) != snapshot.sha256_before):
                        raise ManifestStoreError(
                            f"snapshot integrity failure before restore: {entry.source_path}"
                        )
                    actions.append((target, snapshot, data))
''')
    patch = []
    for relative in ('web_alarm/file_state.py', 'web_alarm/manifest_store.py'):
        before = (baseline / relative).read_text(encoding='utf-8').splitlines(keepends=True)
        after = (candidate / relative).read_text(encoding='utf-8').splitlines(keepends=True)
        patch.extend(difflib.unified_diff(before, after, fromfile='a/' + relative, tofile='b/' + relative))
    report = Path(__file__).resolve().parent
    (report / 'proposed-fix.patch').write_text(''.join(patch), encoding='utf-8', newline='\n')
    print(json.dumps({'candidate': '<LAB>/candidate', 'production_sources_modified': False,
                      'patch_paths': ['web_alarm/file_state.py', 'web_alarm/manifest_store.py']}))


if __name__ == '__main__':
    main()
