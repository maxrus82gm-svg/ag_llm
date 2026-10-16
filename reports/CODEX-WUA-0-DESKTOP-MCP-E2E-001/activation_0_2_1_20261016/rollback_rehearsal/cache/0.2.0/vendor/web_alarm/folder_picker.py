"""Opt-in local folder selection. No registry, task, or project writes."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading


class FolderPickerError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class FolderPicker:
    def __init__(self, *, enabled: bool = False, timeout: float = 120):
        if not 0 < timeout <= 120:
            raise ValueError('folder picker timeout must be in (0, 120] seconds')
        self.enabled = enabled
        self.timeout = timeout
        self.token = secrets.token_urlsafe(32)
        self._lock = threading.Lock()

    def capabilities(self) -> dict:
        reason = ('disabled' if not self.enabled else 'windows_required' if sys.platform != 'win32'
                  else 'tk_unavailable' if importlib.util.find_spec('tkinter') is None else None)
        return {'available': reason is None, 'reason': reason}

    def pick(self) -> dict:
        if not self.capabilities()['available']:
            raise FolderPickerError('folder_picker_unavailable', 'Native folder selection is unavailable; enter the path manually')
        if not self._lock.acquire(blocking=False):
            raise FolderPickerError('folder_picker_busy', 'Another folder selection is in progress')
        try:
            try:
                result = subprocess.run(
                    [sys.executable, '-B', str(Path(__file__).resolve()), '--native-worker'],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding='utf-8', errors='strict', timeout=self.timeout, check=False,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
            except subprocess.TimeoutExpired as exc:
                # run() kills and reaps its own child before raising TimeoutExpired.
                raise FolderPickerError('folder_picker_timeout', 'Folder selection timed out; the dialog was closed') from exc
            except (OSError, UnicodeError) as exc:
                raise FolderPickerError('folder_picker_unavailable', 'Cannot start native folder selection') from exc
            if result.returncode != 0 or len(result.stdout) > 65536:
                raise FolderPickerError('folder_picker_unavailable', 'Native folder selection did not return a valid result')
            try:
                payload = json.loads(result.stdout)
                if not isinstance(payload, dict):
                    raise ValueError('not an object')
                if payload.get('status') == 'CANCELLED' and set(payload) == {'status'}:
                    return {'status': 'CANCELLED'}
                if payload.get('status') != 'SELECTED' or set(payload) != {'status', 'workspace_root'}:
                    raise ValueError('unexpected result')
                raw = payload['workspace_root']
                if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
                    raise ValueError('not an absolute path')
                directory = Path(raw).resolve(strict=True)
                if not directory.is_dir():
                    raise ValueError('not a directory')
            except (ValueError, OSError, TypeError) as exc:
                raise FolderPickerError('folder_picker_invalid_result', 'The selected directory could not be validated') from exc
            return {'status': 'SELECTED', 'workspace_root': str(directory)}
        finally:
            self._lock.release()


def native_selection() -> dict:
    """Runs only in the bounded helper's main thread, after authorized POST."""
    if sys.platform != 'win32':
        return {'status': 'UNAVAILABLE'}
    owner = None
    try:
        import tkinter
        from tkinter import filedialog
        owner = tkinter.Tk()
        owner.withdraw()
        owner.attributes('-topmost', True)
        selected = filedialog.askdirectory(parent=owner, title='Выберите папку Workspace', mustexist=True)
        return {'status': 'SELECTED', 'workspace_root': selected} if selected else {'status': 'CANCELLED'}
    except Exception:
        return {'status': 'UNAVAILABLE'}
    finally:
        if owner is not None:
            try:
                owner.destroy()
            except Exception:
                pass


if __name__ == '__main__':
    if sys.argv[1:] != ['--native-worker']:
        raise SystemExit(2)
    # Bound the native UI even if the server itself disappears before its timeout.
    watchdog = threading.Timer(125, lambda: os._exit(3))
    watchdog.daemon = True
    watchdog.start()
    try:
        value = native_selection()
    finally:
        watchdog.cancel()
    print(json.dumps(value, ensure_ascii=True), flush=True)
    raise SystemExit(1 if value['status'] == 'UNAVAILABLE' else 0)
