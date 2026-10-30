"""Durable cooperative provider lifecycle, independent of Blender's event loop.

Only the instance which creates an operation can dispatch callbacks. Reopening an
unfinished journal is read-only reconciliation: provider work is never replayed.
A successful result is provider output, not independent permission to publish it.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import threading
import time
import uuid

from .files import io_path, json_bytes, reject_links, write_exclusive


MAX_JSON_BYTES = 65536
TERMINAL = frozenset({'SUCCEEDED', 'FAILED', 'CANCELLED', 'NEEDS_RECONCILIATION'})


def _json(value, *, limit=MAX_JSON_BYTES):
    """Freeze callback data and reject non-finite, oversized or non-JSON output."""
    data = json_bytes(value)
    if len(data) > limit:
        raise ValueError('JSON exceeds bounded output limit')
    return json.loads(data)


class AsyncOperation:
    """One operation journal; call step on timer ticks, drive only in owned workers.

    Status has state, phase, operation_id, progress and poll_interval (the next
    safe scheduling delay, bounded by deadline and cancellation grace). Only
    SUCCEEDED includes result. Each immutable event includes the invocation,
    provider handle (once known), timing and status. Events are fsynced before
    atomic publication. Incomplete writes remain inspectable and block recovery.
    """

    def __init__(self, folder, invocation, callbacks, *, clock=time.monotonic,
                 cancelled=lambda: False, operation_id=None):
        if operation_id is not None:
            if not isinstance(operation_id, str):
                raise ValueError("operation_id must be a canonical UUID")
            try:
                if str(uuid.UUID(operation_id)) != operation_id:
                    raise ValueError("operation_id must be a canonical UUID")
            except (ValueError, AttributeError) as exc:
                raise ValueError("operation_id must be a canonical UUID") from exc
        self._expected_operation_id = operation_id
        self.folder = reject_links(folder).absolute()
        self.invocation = _json(invocation)
        for name in ('poll_interval', 'timeout', 'cancel_grace'):
            value = self.invocation.get(name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(name + ' must be a finite positive number')
        for name in ('submit', 'poll', 'cancel', 'collect'):
            if not callable(callbacks.get(name)):
                raise ValueError('Missing lifecycle callback: ' + name)
        self.callbacks = dict(callbacks)
        self.clock, self.cancelled = clock, cancelled
        self._lock = threading.RLock()
        self._running = False
        self._sequence = -1
        self._readonly = False
        self._record = {'version': 1, 'operation_id': operation_id or str(uuid.uuid4()),
                        'invocation': self.invocation, 'state': 'PENDING',
                        'phase': 'READY', 'progress': None, 'handle': None,
                        'started': clock(), 'next_poll': 0, 'cancel_started': None}
        try:
            # Atomic directory creation elects the only dispatching instance.
            io_path(self.folder).mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            self._readonly = True
            self._restore()
        else:
            try:
                self._persist()
            except Exception as exc:
                self._uncertain('Initial persistence failed: ' + str(exc), persist=False)

    def _restore(self):
        try:
            entries = sorted(self.folder / p.name for p in io_path(self.folder).iterdir())
            if not entries or any(not p.name.startswith('event-') or p.suffix != '.json' for p in entries):
                raise ValueError('Incomplete operation journal')
            previous = None
            for index, path in enumerate(entries):
                reject_links(path)
                if path.name != f'event-{index:08d}.json' or path.stat().st_size > MAX_JSON_BYTES * 4:
                    raise ValueError('Invalid journal sequence or size')
                record = json.loads(path.read_text(encoding='utf-8'))
                if (record['version'] != 1 or record['invocation'] != self.invocation
                        or record['state'] not in TERMINAL | {'PENDING'}
                        or (previous and record['operation_id'] != previous['operation_id'])):
                    raise ValueError('Invalid operation identity or invocation')
                if (str(uuid.UUID(record['operation_id'])) != record['operation_id']
                        or (self._expected_operation_id is not None
                            and record['operation_id'] != self._expected_operation_id)):
                    raise ValueError('Managed operation identity differs')
                if record['state'] == 'SUCCEEDED' and ('result' not in record or record.get('phase') != 'DONE'):
                    raise ValueError('Incomplete success record')
                for key in ('progress', 'handle', 'result'):
                    if key in record:
                        _json(record[key])
                previous = record
            self._record = previous
            self._sequence = len(entries) - 1
            if previous['state'] not in TERMINAL:
                self._uncertain('Restored unfinished operation requires reconciliation', persist=False)
        except Exception as exc:
            self._uncertain('Unreadable operation journal: ' + str(exc), persist=False)

    def _persist(self):
        reject_links(self.folder)
        target = reject_links(self.folder / f'event-{self._sequence + 1:08d}.json')
        staged = reject_links(self.folder / ('staging-' + str(uuid.uuid4())))
        write_exclusive(staged, json_bytes(self._record))
        # rename, unlike replace, refuses an existing destination on Windows.
        # Exclusive event ownership also prevents concurrent dispatch on POSIX.
        if io_path(target).exists():
            raise ValueError('Operation journal already advanced')
        os.rename(io_path(staged), io_path(target))
        if os.name != 'nt':
            fd = os.open(io_path(self.folder), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        self._sequence += 1

    def _transition(self, **changes):
        self._record.update(changes)
        self._persist()

    def _uncertain(self, reason, *, persist=True):
        self._record.update(state='NEEDS_RECONCILIATION', phase='RECONCILIATION', error=str(reason)[:2000])
        self._record.pop('result', None)
        if persist and not self._readonly:
            try:
                self._persist()
            except Exception:
                # The previously durable intent still blocks replay on restore.
                self._readonly = True

    def _status(self):
        names = ('state', 'phase', 'operation_id', 'progress', 'error', 'reason')
        status = {key: self._record[key] for key in names if key in self._record}
        status['poll_interval'] = self.invocation['poll_interval']
        if self._record['state'] == 'PENDING':
            now = self.clock()
            cancelling = self._record['cancel_started'] is not None
            if cancelling:
                bound = self._record['cancel_started'] + self.invocation['cancel_grace']
                interval = min(self.invocation['poll_interval'], 0.1, self.invocation['cancel_grace'] / 4)
            else:
                bound = self._record['started'] + self.invocation['timeout']
                interval = self.invocation['poll_interval']
            # A due deadline yields an immediate tick. Never sleep through a
            # deadline or cancellation grace because the provider polls slowly.
            remaining = max(0.0, bound - now)
            status['poll_interval'] = min(interval, remaining / 2 if cancelling else remaining)
            if self._record['next_poll'] > now:
                status['poll_interval'] = min(status['poll_interval'], self._record['next_poll'] - now)
        if self._record['state'] == 'SUCCEEDED':
            status['result'] = self._record['result']
        return _json(status, limit=MAX_JSON_BYTES * 3)

    def step(self):
        """Advance without sleeping; callback exceptions imply unknown termination."""
        with self._lock:
            if self._running:
                raise RuntimeError('Reentrant lifecycle step')
            if self._readonly or self._record['state'] in TERMINAL:
                return self._status()
            self._running = True
            try:
                self._step()
            except Exception as exc:
                self._uncertain(type(exc).__name__ + ': ' + str(exc))
            finally:
                self._running = False
            return self._status()

    def _step(self):
        now = self.clock()
        record = self._record
        if record['phase'] == 'READY':
            if self.cancelled():
                self._transition(state='CANCELLED', phase='DONE', reason='Cancelled before submission')
                return
            self._transition(phase='SUBMIT_INTENT', started=now)
            handle = _json(self.callbacks['submit']())
            self._transition(phase='POLL', handle=handle, next_poll=now)
            return
        if record['phase'] not in ('POLL', 'CANCELLING'):
            self._uncertain('Interrupted lifecycle dispatch requires reconciliation')
            return
        cancelling = record['cancel_started'] is not None
        if not cancelling and (self.cancelled() or now - record['started'] >= self.invocation['timeout']):
            reason = 'Cancelled by caller' if self.cancelled() else 'Deadline expired'
            self._transition(phase='CANCEL_INTENT', cancel_started=now, reason=reason)
            response = _json(self.callbacks['cancel'](_json(record['handle'])))
            if isinstance(response, dict) and response.get('state') in ('FAILED', 'UNKNOWN', 'NEEDS_RECONCILIATION'):
                raise ValueError('Provider cancellation failed or termination is uncertain')
            if self.clock() - record['cancel_started'] >= self.invocation['cancel_grace']:
                self._uncertain('Cancellation callback exceeded termination grace')
                return
            self._transition(phase='CANCELLING', next_poll=now)
            return
        if cancelling and now - record['cancel_started'] >= self.invocation['cancel_grace']:
            self._uncertain('Provider did not confirm termination within cancellation grace')
            return
        if now < record['next_poll']:
            return
        response = _json(self.callbacks['poll'](_json(record['handle'])))
        if not isinstance(response, dict) or response.get('state') not in ('PENDING', 'SUCCEEDED', 'FAILED', 'CANCELLED'):
            raise ValueError('Invalid provider poll state')
        state = response['state']
        if state == 'PENDING':
            interval = self.invocation['poll_interval']
            if cancelling:
                remaining = record['cancel_started'] + self.invocation['cancel_grace'] - self.clock()
                interval = min(interval, 0.1, self.invocation['cancel_grace'] / 4, max(0.0, remaining / 2))
            self._transition(progress=response.get('progress'), next_poll=now + interval)
        elif state in ('FAILED', 'CANCELLED'):
            self._transition(state=state, phase='DONE', error=str(response.get('error', ''))[:2000])
        elif cancelling or self.cancelled() or self.clock() - record['started'] >= self.invocation['timeout']:
            self._transition(state='CANCELLED', phase='DONE', reason='Provider terminated after cancellation')
        else:
            self._transition(phase='COLLECT_INTENT', progress=response.get('progress'))
            result = _json(self.callbacks['collect'](_json(record['handle'])))
            # A cancellation delivered during collect prevents publication too.
            if self.cancelled() or self.clock() - record['started'] >= self.invocation['timeout']:
                self._transition(state='CANCELLED', phase='DONE', reason='Cancellation or deadline during collection')
            else:
                self._transition(state='SUCCEEDED', phase='DONE', result=result)

    def drive(self, *, sleep=time.sleep):
        """Drive independent background jobs; never use on Blender's UI thread."""
        while True:
            status = self.step()
            if status['state'] in TERMINAL:
                return status
            sleep(min(float(status['poll_interval']), 1.0))


def drive(operation, *, sleep=time.sleep):
    """Background worker convenience wrapper for an existing owned operation."""
    return operation.drive(sleep=sleep)
