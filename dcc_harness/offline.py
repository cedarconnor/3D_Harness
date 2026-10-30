"""Bound Python socket connections during explicit managed provider calls only.

This is a local execution guard, not an operating-system sandbox. Native libraries,
subprocesses or deferred work outside the call need separate provider qualification.
"""
from contextlib import contextmanager
import sys

ACTIVE = []
LEASES = {}
INSTALLED = False


def audit(event, args):
    if (ACTIVE or LEASES) and event == 'socket.connect':
        targets = list(LEASES.values()) + (ACTIVE[-1:] if ACTIVE else [])
        recorded = set()
        for attempts in targets:
            if id(attempts) not in recorded:
                attempts.append(str(args[1]))
                recorded.add(id(attempts))
        raise RuntimeError('Offline provider call refused a network connection')


def _install():
    global INSTALLED
    if not INSTALLED:
        sys.addaudithook(audit)
        INSTALLED = True


def begin_lease(attempts, owner):
    """Keep auditing across callbacks, independently of synchronous scope stacks."""
    if not isinstance(owner, str) or not owner or not isinstance(attempts, list):
        raise ValueError('Offline lease requires an owner and attempts list')
    if owner in LEASES:
        raise ValueError('Offline lease owner is already active')
    _install()
    LEASES[owner] = attempts


def end_lease(owner):
    """Release the named guard; repeated terminal cleanup is harmless."""
    LEASES.pop(owner, None)


@contextmanager
def scope(attempts):
    _install()
    ACTIVE.append(attempts)
    try:
        yield
    finally:
        ACTIVE.pop()
