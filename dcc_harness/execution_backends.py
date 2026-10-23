"""Native dispatch boundaries; policy and checkpoint publication stay in execution."""
from pathlib import Path
from typing import Protocol

from .evidence import file_hash, read_json, write_json


class ExecutionBackend(Protocol):
    def prepare(self, request: dict) -> dict: ...
    def submit(self, request: dict, prepared: dict) -> str: ...
    def status(self, operation_id: str) -> dict: ...
    def cancel(self, operation_id: str) -> dict: ...
    def verify(self, receipt: dict) -> None: ...
    def before_publish(self, receipt: dict) -> None: ...
    def published(self, result: dict, receipt: dict) -> dict: ...
    # Optional implementations may close an exact durable pre-mutation refusal.
    # The controller never calls submit again to recover an existing operation.
    def recover_failure(self) -> dict | None: ...


class BackgroundBackend:
    def __init__(self, folder, run):
        self.folder = Path(folder)
        self.run = run

    def prepare(self, request: dict) -> dict:
        self.request = request
        return {'operation_id': request['operation_id'], 'source': request['source']}

    def submit(self, request: dict, prepared: dict) -> str:
        if prepared['operation_id'] != request['operation_id'] or prepared['source'] != request['source']:
            raise ValueError('Prepared background operation changed')
        if 'capability' in request:
            self.run(Path(__file__).with_name('_capability_blender.py'),'execute',request)
        else:
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

    def verify(self, receipt: dict) -> None:
        self.run(Path(__file__).with_name('_observe_blender.py'), 'observe',
                 {'source': {'path': receipt['candidate'], 'sha256': receipt['sha256']},
                  'out': str(self.folder), 'compact': True})
        if 'capability' in self.request:
            self.run(Path(__file__).with_name('_capability_blender.py'),'capability-verify',
                     {**self.request,'source':{'path':receipt['candidate'],'sha256':receipt['sha256']}})

    def before_publish(self, receipt: dict) -> None:
        pass

    def published(self, result: dict, receipt: dict) -> dict:
        return {}


def make_backend(kind, *, root, folder, run):
    if kind == 'background':
        return BackgroundBackend(folder, run)
    if kind == 'live':
        from .live import LiveBackend
        return LiveBackend(root, folder, run)
    raise ValueError('Unknown execution backend')
