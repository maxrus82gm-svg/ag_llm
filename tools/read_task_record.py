"""Read one documentation task record without returning the surrounding archive.

This is a local, read-only context helper, not an access-control boundary.
The caller must already be allowed to read the named registry and record.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


RECORD_ID = re.compile(r"[A-Z][A-Z0-9_-]{0,95}\Z")
MARKER = re.compile(r"<!-- TASK-RECORD ([A-Z][A-Z0-9_-]{0,95}) (BEGIN|END) -->\Z")
DEFAULT_MAX_CHARS = 20_000


@dataclass(frozen=True)
class TaskRecord:
    record_id: str
    start_line: int
    end_line: int
    text: str


def read_record(path: Path, record_id: str, max_chars: int = DEFAULT_MAX_CHARS) -> TaskRecord:
    """Scan marker lines locally; retain and return only the requested record.

    No partial record is printed on failure. Scanning continues after the match
    to detect duplicate IDs and malformed boundaries later in the registry.
    """
    if not RECORD_ID.fullmatch(record_id):
        raise ValueError("Invalid record ID; use the exact ID from the short index.")
    if not 1 <= max_chars <= 200_000:
        raise ValueError("max_chars must be between 1 and 200000.")
    seen: set[str] = set()
    active: str | None = None
    start = end = size = 0
    collected: list[str] = []
    # Text output uses consistent newlines; source bytes and snapshots stay untouched.
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            stripped = line.rstrip("\r\n")
            match = MARKER.fullmatch(stripped)
            if stripped.startswith("<!-- TASK-RECORD") and match is None:
                raise ValueError(f"Malformed record marker at line {line_no}.")
            if match:
                marker_id, kind = match.groups()
                if kind == "BEGIN":
                    if active is not None:
                        raise ValueError(f"Nested record at line {line_no}.")
                    if marker_id in seen:
                        raise ValueError(f"Duplicate record ID {marker_id} at line {line_no}.")
                    seen.add(marker_id)
                    active = marker_id
                    if marker_id == record_id:
                        start = line_no
                elif active != marker_id:
                    raise ValueError(f"Unmatched END marker at line {line_no}.")
            if active == record_id:
                size += len(line)
                if size > max_chars:
                    raise ValueError(
                        f"Record {record_id}, starting at line {start}, exceeds {max_chars} characters. "
                        "Request a deliberate larger --max-chars value for this ID only."
                    )
                collected.append(line)
            if match and match.group(2) == "END":
                if active == record_id:
                    end = line_no
                active = None
    if active is not None:
        raise ValueError(f"Missing END marker for {active}.")
    if not start:
        raise ValueError(f"Record {record_id} not found. Consult the short index; no archive fallback.")
    return TaskRecord(record_id, start, end, "".join(collected))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True, help="Registry file named in the short index")
    parser.add_argument("--id", dest="record_id", required=True, help="Exactly one record ID, e.g. BP-0001")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                        help="Maximum size of this one record (default: 20000; limit: 200000)")
    args = parser.parse_args(argv)
    try:
        record = read_record(args.registry, args.record_id, args.max_chars)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Task record not returned: {exc}", file=sys.stderr)
        return 2
    print(f"Record: {record.record_id} | Source: {args.registry} | Lines: {record.start_line}-{record.end_line}")
    sys.stdout.write(record.text)
    if not record.text.endswith("\n"):
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
