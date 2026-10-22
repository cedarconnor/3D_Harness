"""Owned, fresh background Blender processes for the package's private workers."""
from __future__ import annotations

import subprocess
import time
import os
from pathlib import Path

from .evidence import write_json


def run_process(command, log_path, *, timeout=3600, cancelled=None, env=None):
    """Bound and reap an owned child; a stopped process can still have written output."""
    from .evidence import finite_number
    finite_number(timeout)
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
            try:
                while process.poll() is None:
                    if interrupted():
                        raise RuntimeError('Native operation cancelled; inspect retained outputs')
                    remaining = timeout - (time.monotonic() - started)
                    if remaining <= 0:
                        raise TimeoutError('Native operation timed out; inspect retained outputs')
                    try:
                        process.wait(timeout=min(.1, remaining))
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
            if process.returncode:
                raise RuntimeError(f'Native process failed ({process.returncode}); inspect {log_path}')


def run_worker(blender, folder, worker, action, request, *, timeout=3600, cancelled=None, profile=None):
    """Run one worker action; its request and Blender log are retained in folder."""
    request_path = folder / (action + '-request.json')
    write_json(request_path, {**request, 'profile':profile} if profile is not None else request)
    command = [str(blender), '--background', '--offline-mode', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1']
    if profile is not None:
        command += ['--python', str(Path(__file__).with_name('_profile_blender.py'))]
    command += ['--python', str(worker), '--', action, str(request_path)]
    log_path = folder / (action + '.log')
    if profile is None:
        run_process(command, log_path, timeout=timeout, cancelled=cancelled)
    else:
        config = folder / (action + '-user-config'); config.mkdir()
        run_process(command, log_path, timeout=timeout, cancelled=cancelled,
                    env={**os.environ, 'BLENDER_USER_CONFIG':str(config.resolve()),
                         'BLENDER_USER_EXTENSIONS':str((folder / (action + '-user-extensions')).resolve())})
