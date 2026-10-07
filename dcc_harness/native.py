"""Owned, fresh background Blender processes for the package's private workers."""
from __future__ import annotations

import subprocess

from .evidence import write_json


def run_worker(blender, folder, worker, action, request):
    """Run one worker action; its request and Blender log are retained in folder."""
    request_path = folder / (action + '-request.json')
    write_json(request_path, request)
    command = [str(blender), '--background', '--factory-startup', '--disable-autoexec',
               '--python-exit-code', '1', '--python', str(worker), '--', action, str(request_path)]
    log_path = folder / (action + '.log')
    with log_path.open('x', encoding='utf-8') as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise RuntimeError(f'Blender {action} failed; inspect {log_path} and retained outputs before retrying')
