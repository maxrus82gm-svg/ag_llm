"""Scope, secret, size and retention policy for tracked mutation payloads (RC-1).

The policy follows RC-0 / invariant 33: payload bytes live only in machine-local
WEB-02 storage outside the repository/vault, are size-limited, are never deleted
automatically during the RC phases, and secret-like targets fail closed unless
the operation contract records an explicit per-target override.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

MAX_PAYLOAD_BYTES = 1024 * 1024
PAYLOAD_RETENTION = "KEEP_UNTIL_EXPLICIT_CLEANUP"

SECRET_NAME_PATTERNS = (
    ".env*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "*credential*",
    "*secret*",
    "*token*",
    "cookies*",
)


def secret_pattern_for(relative_posix: str) -> str | None:
    """Return the first deny-list pattern matched by any path component."""
    for component in relative_posix.split("/"):
        lowered = component.lower()
        for pattern in SECRET_NAME_PATTERNS:
            if fnmatch.fnmatchcase(lowered, pattern):
                return pattern
    return None


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, ValueError):
        return False
    return True
