"""Verify publication hashes and that source files still match the reviewed bytes.

Run from any directory: python -B verify_package.py --repo <repo>
This verifier reads files only; it does not use Git or execute project code.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    snapshot = json.loads((package / 'source-snapshot.json').read_text(encoding='utf-8'))
    problems, counts = [], {}
    for kind, root, rows in [('package', package, manifest['files']), ('sources', args.repo.resolve(), snapshot['files'])]:
        checked = 0
        for row in rows:
            relative = Path(row['path'])
            if relative.is_absolute() or '..' in relative.parts:
                problems.append(kind + ': unsafe manifest path')
                continue
            path = root / relative
            if not path.is_file():
                problems.append(kind + ': missing ' + row['path'])
                continue
            data = path.read_bytes()
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                problems.append(kind + ': mismatch ' + row['path'])
            checked += 1
        counts[kind] = checked
    print(json.dumps({'checked': counts, 'problems': problems}, indent=2))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
