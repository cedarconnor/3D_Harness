"""Bound Python socket connections during explicit managed provider calls only.

This is a local execution guard, not an operating-system sandbox. Native libraries,
subprocesses or deferred work outside the call need separate provider qualification.
"""
from contextlib import contextmanager
import sys

ACTIVE = []
INSTALLED = False


def audit(event, args):
    if ACTIVE and event == 'socket.connect':
        ACTIVE[-1].append(str(args[1]))
        raise RuntimeError('Offline provider call refused a network connection')


@contextmanager
def scope(attempts):
    global INSTALLED
    if not INSTALLED:
        sys.addaudithook(audit); INSTALLED = True
    ACTIVE.append(attempts)
    try:
        yield
    finally:
        ACTIVE.pop()
