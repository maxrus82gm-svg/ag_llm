import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / 'Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-WA4-R-EVIDENCE-SANITIZER-REPAIR-001'
PROBE = ORIGINAL.parent / 'TASK_GPT_CI_DUPLICATE_PROBE'

def main():
    if PROBE.exists():
        raise RuntimeError('CI probe path already exists; not overwriting it')
    try:
        shutil.copytree(ORIGINAL, PROBE)
        path = PROBE / 'runs/runs-map.json'
        mapping = json.loads(path.read_bytes())
        mapping['files'].append(dict(mapping['files'][0]))
        modified = (json.dumps(mapping, ensure_ascii=False, indent=1) + '\n').encode('utf-8')
        path.write_bytes(modified)
        manpath = PROBE / 'manifest.json'
        manifest = json.loads(manpath.read_bytes())
        manifest['files']['runs/runs-map.json'].update(
            sha256=hashlib.sha256(modified).hexdigest(), bytes=len(modified), eol='LF')
        manpath.write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + '\n').encode('utf-8'))
        p = subprocess.run([sys.executable, '-B', str(PROBE / 'tools/check_package.py')],
                           cwd=ROOT, capture_output=True, text=True)
        print('duplicate runs-map ID; manifest correctly rehashed; verifier exit=', p.returncode)
        print(p.stdout[-800:])
        if p.returncode == 0:
            print('FAIL-OPEN: duplicate ID accepted; independent REWORK REQUIRED')
            return 1
        print('PASS: duplicated ID refused')
        return 0
    finally:
        if PROBE.exists():
            shutil.rmtree(PROBE)

if __name__ == '__main__':
    sys.exit(main())
