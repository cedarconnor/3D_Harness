"""Shared file helpers: hashing, link rejection, exclusive writes and verified copies.

Retained evidence is written once and never replaced, and a copy is trusted only after both
sides hash to the expected value. A failed write or copy is left in place for inspection.
"""
from __future__ import annotations

import hashlib
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import shutil
import stat


def _windows_io_path(path):
    """Spell an ordinary Windows path for I/O, never for retained identities.

    Extended syntax bypasses Win32 normalization as well as MAX_PATH. Refuse
    caller-provided namespaces and ambiguous/device components before adding it.
    Do not resolve links here: reject_links must inspect the components themselves.
    """
    text = os.fspath(path).replace('/', '\\')
    if text.startswith(('\\\\?\\', '\\\\.\\', '\\??\\')):
        raise ValueError('Device/extended namespaces are not logical filesystem paths')
    for component in PureWindowsPath(text).parts[1:] if PureWindowsPath(text).anchor else PureWindowsPath(text).parts:
        if component in ('.', '..'):
            continue
        if (component.endswith((' ', '.')) or ':' in component
                or PureWindowsPath(component).is_reserved()):
            raise ValueError('Ambiguous/device Windows path component: ' + component)
    absolute = ntpath.abspath(text)
    if absolute.startswith('\\\\'):
        return '\\\\?\\UNC\\' + absolute[2:]
    return '\\\\?\\' + absolute


def io_path(path):
    """Private filesystem spelling; keep the caller's logical Path in records/API results.

    Blender's Windows embedded Python can lack long-path process awareness even
    when host Python works. Apply this only at Python filesystem calls, not bpy
    APIs, environment variables, canonical comparisons, or fingerprint content.
    """
    return Path(_windows_io_path(path)) if os.name == 'nt' else Path(path)


def file_hash(path):
    h = hashlib.sha256()
    with io_path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reject_links(path, message="Links/reparse points are not supported"):
    """Reject redirecting files/directories before resolving a retained path.

    lstat() inspects each component itself: stat() would follow a Windows
    junction and report its target, letting the junction pass.
    """
    path = Path(path).absolute()
    for part in (path, *path.parents):
        try:
            info = io_path(part).lstat()
        except FileNotFoundError as exc:
            # Windows may classify path-too-long as FileNotFoundError (206).
            # Only actual missing components may be skipped, never bad/inaccessible paths.
            if getattr(exc, 'winerror', None) not in (None, 2, 3):
                raise
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"{message}: {part}")
    return path


def json_text(value, *, compact=False):
    """Canonical JSON text: sorted keys, no NaN or infinity, one trailing newline."""
    return json.dumps(value, indent=None if compact else 2, separators=(",", ":") if compact else None,
                      sort_keys=True, allow_nan=False) + "\n"


def json_bytes(value):
    return json_text(value).encode("utf-8")


def write_exclusive(path, data):
    """Create a new file with these bytes and flush it to disk; never replace an existing one."""
    with io_path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def copy_verified(source, target, expected, message):
    """Copy to a new file, then require both sides to hash to `expected`; else raise ValueError(message)."""
    source, target = Path(source), Path(target)
    io_path(target.parent).mkdir(parents=True, exist_ok=True)
    with io_path(source).open("rb") as incoming, io_path(target).open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if file_hash(target) != expected or file_hash(source) != expected:
        raise ValueError(message)
    return target
