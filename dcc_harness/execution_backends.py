"""Native dispatch boundaries; policy and checkpoint publication stay in execution."""
from pathlib import Path
from typing import Protocol

from .evidence import file_hash, read_json, write_json


class ExecutionBackend(Protocol):
    def prepare(self, request: dict) -> dict: ...
    def submit(self, request: dict, prepared: dict) -> str: ...
    def status(self, operation_id: str) -> dict: ...
    def cancel(self, operation_id: str) -> dict: ...


class BackgroundBackend:
    def __init__(self, folder, run):
        self.folder = Path(folder)
        self.run = run

    def prepare(self, request: dict) -> dict:
        return {'operation_id': request['operation_id'], 'source': request['source']}

    def submit(self, request: dict, prepared: dict) -> str:
        if prepared['operation_id'] != request['operation_id'] or prepared['source'] != request['source']:
            raise ValueError('Prepared background operation changed')
        self.run(Path(__file__).with_name('_execution_blender.py'), 'execute',
                 {'source': request['source'], 'script': request['script'],
                  'script_sha256': request['script_sha256'], 'output': request['output']})
        write_json(self.folder / 'backend-saved.json',
                   {'operation_id': request['operation_id'], 'state': 'SAVED',
                    'candidate': request['output'], 'sha256': file_hash(request['output'])})
        return request['operation_id']

    def status(self, operation_id: str) -> dict:
        path = self.folder / 'backend-saved.json'
        if not path.exists():
            return {'operation_id': operation_id, 'state': 'NEEDS_RECONCILIATION'}
        result = read_json(path)
        if result['operation_id'] != operation_id or file_hash(result['candidate']) != result['sha256']:
            raise ValueError('Saved background result changed')
        return result

    def cancel(self, operation_id: str) -> dict:
        # run_worker owns its child and polls the service cancellation marker.
        return {'operation_id': operation_id, 'state': 'CANCEL_REQUESTED'}


def make_backend(kind, *, root, folder, run):
    if kind == 'background':
        return BackgroundBackend(folder, run)
    if kind == 'live':
        from .live import LiveBackend
        return LiveBackend(root, folder)
    raise ValueError('Unknown execution backend')
