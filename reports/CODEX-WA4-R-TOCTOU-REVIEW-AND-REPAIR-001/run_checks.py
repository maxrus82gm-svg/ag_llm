"""Run only named offline unittest modules from a private source copy.

Usage: python -B run_checks.py --source <copy> --lab <lab> --run-id <id> module [...]
No discovery, package installation, Git, or network operations.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--lab', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('modules', nargs='+')
    args = parser.parse_args()
    lab, source = args.lab.resolve(), args.source.resolve()
    source.relative_to(lab)
    if not (lab / 'session.json').is_file():
        parser.error('lab must be initialized by this review')
    result_dir = Path(__file__).resolve().parent / 'test-results'
    env = dict(os.environ, TMP=str(lab / 'tmp'), TEMP=str(lab / 'tmp'),
               PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(source),
               WA4R_LAB=str(lab), WA4R_RUN_ID=args.run_id)
    command = [sys.executable, '-B', '-m', 'unittest', '-v', *args.modules]
    started = time.monotonic()
    completed = subprocess.run(command, cwd=source, env=env, capture_output=True,
                               encoding='utf-8', errors='replace', timeout=900)
    def clean(value):
        return value.replace(str(lab), '<LAB>').replace(str(Path.home()), '<USER>')
    text = clean(completed.stdout + completed.stderr)
    (result_dir / (args.run_id + '.txt')).write_text(text, encoding='utf-8')
    record = {'run_id': args.run_id, 'command': ['python', *command[1:]],
              'cwd': '<LAB>/' + source.name, 'exit_code': completed.returncode,
              'duration_seconds': round(time.monotonic() - started, 3),
              'environment': {'TEMP': '<LAB>/tmp', 'TMP': '<LAB>/tmp',
                              'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': '<LAB>/' + source.name},
              'summary': text.splitlines()[-5:]}
    (result_dir / (args.run_id + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
