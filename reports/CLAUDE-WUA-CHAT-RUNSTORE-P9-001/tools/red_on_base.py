"""RED evidence: the final test_run_store_v2.py run against the ORIGINAL run_store.py in a disposable TEMP mirror.

Mirror = top-level *.py / *.json and web_alarm/*.py / *.json of the working tree (no Git metadata, no data); then
run_store.py is replaced by the pre-edit copy given as an argument (a private TEMP file, never published). The tests
run through tools/run_pytest.py with P9_CODE_ROOT pointing at the mirror.
Usage: red_on_base.py <pre-edit run_store.py> <out.json>
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[2]


def main():
    original, target = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    mirror = Path(tempfile.mkdtemp(prefix="p9-red-mirror-"))
    try:
        for pattern in ("*.py", "*.json"):
            for path in REPO.glob(pattern):
                shutil.copy2(path, mirror / path.name)
        (mirror / "web_alarm").mkdir()
        for pattern in ("*.py", "*.json"):
            for path in (REPO / "web_alarm").glob(pattern):
                shutil.copy2(path, mirror / "web_alarm" / path.name)
        shutil.copy2(original, mirror / "run_store.py")
        env = dict(os.environ, P9_CODE_ROOT=str(mirror), PYTHONIOENCODING="utf-8")
        done = subprocess.run([sys.executable, "-B", str(TOOLS / "run_pytest.py"),
                               "RED: the final test_run_store_v2.py on the ORIGINAL run_store.py (TEMP mirror)",
                               str(target), "test_run_store_v2.py"], env=env, capture_output=True, text=True, encoding="utf-8")
        print(done.stdout.strip())
    finally:
        shutil.rmtree(mirror, ignore_errors=True)


if __name__ == "__main__":
    main()
