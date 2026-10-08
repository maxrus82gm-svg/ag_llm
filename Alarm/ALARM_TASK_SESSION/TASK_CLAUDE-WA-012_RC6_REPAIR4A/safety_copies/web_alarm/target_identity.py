"""Canonical Windows-safe target identity for Web Alarm operation contracts (RC-1).

One function decides what physical file an operation target names:
- the target is resolved against the registered workspace root; parent
  junctions/symlinks are followed, and the result must stay inside the root;
- the target itself must not be a link or reparse point;
- alternate data streams, device names, trailing dots/spaces and characters
  invalid on Windows are rejected instead of being silently aliased;
- ``relative`` keeps a POSIX display spelling (on-disk case for existing
  components), ``key`` is the case-insensitive comparison identity.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .file_state import is_link_or_reparse_point

_RESERVED_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_INVALID_CHARACTERS = frozenset('<>:"|?*')


class TargetIdentityError(RuntimeError):
    """Raised when a target cannot be given a safe canonical identity."""


@dataclass(frozen=True, slots=True)
class CanonicalTarget:
    workspace_root: Path
    path: Path
    relative: str
    key: str


def target_key(relative: str) -> str:
    """Comparison key for an already workspace-relative path of any spelling."""
    if not isinstance(relative, str) or not relative.strip():
        raise TargetIdentityError("target must be a non-empty string")
    key = os.path.normcase(os.path.normpath(relative.strip()))
    if os.sep != "/":
        key = key.replace(os.sep, "/")
    return key


def _check_component(component: str, raw_target: str, *, allow_dots: bool = False) -> None:
    if allow_dots and component in {".", ".."}:
        return
    if not component or component in {".", ".."}:
        raise TargetIdentityError(f"target has an empty or relative component: {raw_target}")
    if any(ord(char) < 32 for char in component):
        raise TargetIdentityError(f"target contains control characters: {raw_target}")
    if _INVALID_CHARACTERS.intersection(component):
        raise TargetIdentityError(
            f"target contains characters invalid on Windows (incl. ADS ':'): {raw_target}"
        )
    if component.endswith((".", " ")):
        raise TargetIdentityError(
            f"target component ends with a dot or space: {raw_target}"
        )
    stem = component.split(".", 1)[0].rstrip(" ").upper()
    if stem in _RESERVED_DEVICE_NAMES:
        raise TargetIdentityError(f"target names a reserved device: {raw_target}")


def canonical_target(
    workspace_root: str | os.PathLike[str],
    raw_target: str,
) -> CanonicalTarget:
    if not isinstance(raw_target, str) or not raw_target.strip():
        raise TargetIdentityError("target must be a non-empty string")
    raw_target = raw_target.strip()
    if "\x00" in raw_target:
        raise TargetIdentityError("target contains a NUL character")
    try:
        root = Path(workspace_root).resolve(strict=True)
    except OSError as exc:
        raise TargetIdentityError(
            f"registered workspace_root is unavailable: {workspace_root}"
        ) from exc
    if not root.is_dir():
        raise TargetIdentityError(f"workspace_root is not a directory: {root}")

    supplied = Path(raw_target)
    if supplied.drive and not supplied.is_absolute():
        raise TargetIdentityError(f"drive-relative target is ambiguous: {raw_target}")
    # Windows resolution may silently drop ADS suffixes, trailing dots/spaces or
    # map device names, so the supplied spelling is checked before resolving.
    lexical_parts = supplied.parts[1:] if supplied.anchor else supplied.parts
    for component in lexical_parts:
        _check_component(component, raw_target, allow_dots=True)
    candidate = supplied if supplied.is_absolute() else root / supplied
    if is_link_or_reparse_point(candidate):
        raise TargetIdentityError(f"target is a link or reparse point: {raw_target}")
    try:
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise TargetIdentityError(
            f"target escapes registered workspace: {raw_target}"
        ) from exc
    if not relative.parts:
        raise TargetIdentityError("target must name a file inside the workspace")
    for component in relative.parts:
        _check_component(component, raw_target)
    if resolved.exists() and not resolved.is_file():
        raise TargetIdentityError(f"target is not a regular file: {raw_target}")
    display = relative.as_posix()
    return CanonicalTarget(
        workspace_root=root,
        path=resolved,
        relative=display,
        key=target_key(display),
    )
