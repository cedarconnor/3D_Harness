"""Shared file helpers: hashing, link rejection, exclusive writes and verified copies.

Retained evidence is written once and never replaced, and a copy is trusted only after both
sides hash to the expected value. A failed write or copy is left in place for inspection.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
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
            info = part.lstat()
        except (FileNotFoundError, NotADirectoryError):
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
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def copy_verified(source, target, expected, message):
    """Copy to a new file, then require both sides to hash to `expected`; else raise ValueError(message)."""
    source, target = Path(source), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if file_hash(target) != expected or file_hash(source) != expected:
        raise ValueError(message)
    return target
