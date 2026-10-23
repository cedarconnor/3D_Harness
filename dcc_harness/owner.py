"""Owner approval: a record resting on the artist's authority needs the owner's own terminal.

This is a guard, not a wall (D18). It stops an agent from approving its own work through the
documented commands, payload files or a page export. An agent with an unrestricted shell can
still get around it.
"""
from __future__ import annotations

import getpass
import json
import os
import sys

from .evidence import digest
from .project import now


AGENT_MARKERS = ('CLAUDECODE', 'AI_AGENT', 'CODEX_SANDBOX', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID', 'GEMINI_CLI', 'DCC_HARNESS_AGENT')
# Where each kind names the actor whose authority it rests on. Notes and evidence producers are attributions only.
AUTHORITY = {'stage.complete': ('review', 'reviewer'), 'feedback.verify': ('reviewer',), 'feedback.decide': ('authority',),
             'stage.reopen': ('authority',), 'workflow.bind': ('binding', 'authority'), 'capability.bind': ('authority',)}
SHOWN = ('stage_id', 'note_id', 'action', 'verdict', 'finding', 'reason', 'answers', 'review_policies',
         'check_id', 'note', 'rationale', 'rule', 'stages', 'policy')


class OwnerRequired(RuntimeError):
    pass


class Approval:
    """Issued only by confirm(), for one request."""
    __slots__ = ('request_hash', 'provenance')

    def __init__(self, request_hash, provenance):
        self.request_hash, self.provenance = request_hash, provenance


class Terminal:
    def __init__(self):
        self.environ = os.environ

    def isatty(self):
        return sys.stdin is not None and sys.stdin.isatty()

    def ask(self, text):
        sys.stderr.write(text); sys.stderr.flush()
        return sys.stdin.readline()


def request_hash(kind, payload):
    return digest({'kind': kind, 'payload': payload})


def _actor(kind, payload):
    value = payload
    for key in AUTHORITY.get(kind, ()):
        value = value.get(key) if isinstance(value, dict) else None
    return value if kind in AUTHORITY and isinstance(value, dict) else None


def claims_artist(kind, payload):
    actor = _actor(kind, payload)
    return actor is not None and actor.get('role') == 'artist'


def describe(kind, payload):
    actor = _actor(kind, payload)
    lines = [f"Record {kind} as the artist's decision, by {actor.get('author', 'unnamed')}." if actor is not None
             else f'Approve {kind} as the owner.']
    for part in (payload, payload.get('review'), payload.get('binding')):
        if isinstance(part, dict):
            lines += [f'  {key}: ' + (part[key] if isinstance(part[key], str) else json.dumps(part[key])) for key in SHOWN if key in part]
    return '\n'.join(lines)


def confirm(kind, payload, console=None):
    """Ask the owner, at an interactive terminal outside any agent session, to confirm this exact request."""
    console = console or Terminal()
    found = [name for name in AGENT_MARKERS if console.environ.get(name)]
    if found:
        raise OwnerRequired(f'Owner approval is refused inside an agent session ({found[0]} is set). '
                            'The artist runs this command in their own terminal.')
    if not console.isatty():
        raise OwnerRequired('Owner approval needs an interactive terminal. The artist runs this command themselves, without piped input.')
    request = request_hash(kind, payload)
    code = request[:4].upper()
    answer = console.ask(describe(kind, payload) + f'\nType {code} to record this as your decision, or press Enter to cancel: ')
    if (answer or '').strip().upper() != code:
        raise OwnerRequired('Owner approval not confirmed; nothing was recorded.')
    try:
        user = getpass.getuser()
    except Exception:
        user = 'unknown'
    return Approval(request, {'channel': 'owner_terminal', 'confirmed_at': now(), 'user': user, 'code': code, 'strength': 'guard'})


def authorize(root, kind, payload, request_id, console=None):
    """Prompt only when the payload claims the artist and the request is not already committed."""
    if not claims_artist(kind, payload):
        return None
    from .coordination import read
    if any(event['request_id'] == request_id for event in read(root)):
        return None
    return confirm(kind, payload, console)


def require(kind, payload, request, approval):
    """Called by transact: the provenance to record, or a refusal when the artist is claimed without the owner."""
    if not claims_artist(kind, payload):
        return None
    if not isinstance(approval, Approval) or approval.request_hash != request:
        raise OwnerRequired("Owner approval required: this records the artist's decision. "
                            'The artist runs the command in their own terminal; an agent never does.')
    return approval.provenance
