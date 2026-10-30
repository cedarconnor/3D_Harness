"""Owned, fresh background Blender processes for the package's private workers."""
from __future__ import annotations

import subprocess
import time
import os
from pathlib import Path

from .evidence import write_json


def run_process(command, log_path, *, timeout=3600, cancelled=None, env=None, cancel_grace=0):
    """Bound and reap an owned child; a stopped process can still have written output."""
    from .evidence import finite_number
    finite_number(timeout)
    finite_number(cancel_grace)
    if not 0 <= cancel_grace <= 120:
        raise ValueError('Native cancellation grace must be between zero and 120 seconds')
    if timeout <= 0:
        raise TimeoutError('Native time budget exhausted before dispatch')
    cancel_file = os.environ.get('DCC_HARNESS_CANCEL_FILE')
    def interrupted():
        return (cancelled is not None and cancelled()) or (cancel_file is not None and Path(cancel_file).exists())
    if interrupted():
        raise RuntimeError('Native operation cancelled before dispatch')
    started = time.monotonic()
    with log_path.open('x', encoding='utf-8') as log:
        with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as process:
            def grace():
                # The worker independently observes its managed marker/deadline.
                # Waiting here permits provider cleanup; it never makes the result publishable.
                until = time.monotonic() + cancel_grace
                while process.poll() is None:
                    remaining_grace = until - time.monotonic()
                    if remaining_grace <= 0:
                        break
                    try:
                        process.wait(timeout=min(.1, remaining_grace))
                    except subprocess.TimeoutExpired:
                        pass
            try:
                while process.poll() is None:
                    if interrupted():
                        if cancel_grace:
                            grace()
                        raise RuntimeError('Native operation cancelled; inspect retained outputs')
                    remaining = timeout - (time.monotonic() - started)
                    if remaining <= 0:
                        if cancel_grace:
                            grace()
                        raise TimeoutError('Native operation timed out; inspect retained outputs')
                    try:
                        process.wait(timeout=min(.1, remaining))
                    except subprocess.TimeoutExpired:
                        pass
                # Refuse candidates when termination raced cancellation/deadline.
                if interrupted():
                    raise RuntimeError('Native operation cancelled; inspect retained outputs')
                if time.monotonic() - started >= timeout:
                    raise TimeoutError('Native operation timed out; inspect retained outputs')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
            if process.returncode:
                raise RuntimeError(f'Native process failed ({process.returncode}); inspect {log_path}')


def run_worker(blender, folder, worker, action, request, *, timeout=3600, cancelled=None, profile=None, gui=False, cancel_grace=0):
    """Run one worker action; its request and Blender log are retained in folder."""
    from .evidence import finite_number
    finite_number(cancel_grace)
    if not 0 <= cancel_grace <= 120:
        raise ValueError('Native cancellation grace must be between zero and 120 seconds')
    capability = request.get('capability')
    if action == 'execute' and capability is not None:
        from .recipe_store import load
        selected = capability['resolution']['selected']
        bundle = load(capability['root'], selected['recipe_id'], selected['recipe_digest'])
        invocation = bundle['recipe']['invocation']
        if invocation['completion'] == 'asynchronous':
            allowance = min(12., 2 * invocation['poll_interval'] + 1.)
            cancel_grace = max(cancel_grace, invocation['cancel_grace'] + allowance)
    request_path = folder / (action + '-request.json')
    if gui:
        if action not in ('recipe_apply','recipe_verify') or profile is None:
            raise ValueError('Owned GUI workers are limited to explicit recipe qualification')
        request = {**request, 'owned_gui':True}
    write_json(request_path, {**request, 'profile':profile} if profile is not None else request)
    command = [str(blender), *([] if gui else ['--background']), '--offline-mode', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1']
    if profile is not None:
        command += ['--python', str(Path(__file__).with_name('_profile_blender.py'))]
        command += ['--', action, str(request_path), str(worker)]
    else:
        command += ['--python', str(worker), '--', action, str(request_path)]
    log_path = folder / (action + '.log')
    if profile is None:
        run_process(command, log_path, timeout=timeout, cancelled=cancelled, cancel_grace=cancel_grace)
    else:
        config = folder / (action + '-user-config'); config.mkdir()
        temporary = folder / (action + '-temporary'); temporary.mkdir()
        run_process(command, log_path, timeout=timeout, cancelled=cancelled, cancel_grace=cancel_grace,
                    env={**os.environ, 'BLENDER_USER_CONFIG':str(config.resolve()),
                         'TEMP':str(temporary.resolve()), 'TMP':str(temporary.resolve()),
                         'BLENDER_USER_EXTENSIONS':str((folder / (action + '-user-extensions')).resolve())})
