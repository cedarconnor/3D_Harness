"""Local pairing and document lifetime; contains no Blender API calls."""
import hmac
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
import uuid

try:  # Standalone export includes this shared module beside the bridge.
    from .files import json_bytes, reject_links, write_exclusive
except ModuleNotFoundError:
    from dcc_harness.files import json_bytes, reject_links, write_exclusive


class StaleGenerationError(ValueError):
    """Authenticated caller refers to a document that has since been replaced."""


class Session:
    def __init__(self, workspace, port):
        self.workspace = reject_links(workspace).resolve(strict=True)
        self.port = port
        self.session_id = str(uuid.uuid4())
        self.generation = str(uuid.uuid4())
        self._token = secrets.token_hex(32)
        self._prepared = {}
        self._lock = threading.RLock()
        self.project = self.scene = self.active = None
        self.reason = None
        folder = reject_links(self.workspace / '.harness-mcp/bridge')
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.descriptor_path = folder / (self.session_id + '.json')
        self._write_descriptor()

    def _write_descriptor(self):
        value = {**self.describe(), 'token': self._token, 'workspace': str(self.workspace), 'pid': os.getpid()}
        temporary = reject_links(self.descriptor_path.with_suffix('.' + uuid.uuid4().hex + '.tmp'))
        write_exclusive(temporary, json_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, reject_links(self.descriptor_path))

    def retain_outcome(self, command, payload, result, *, generation=None):
        """Freeze an exact request result before replying; absence proves nothing."""
        identity = {'command': command, 'payload': payload, 'session_id': self.session_id,
                    'generation': self.generation if generation is None else generation}
        name = hashlib.sha256(json_bytes(identity)).hexdigest() + '.json'
        folder = reject_links(self.workspace / '.harness-mcp/outcomes' / self.session_id)
        folder.mkdir(parents=True, exist_ok=True)
        record = {**identity, 'result': result}
        path = reject_links(folder / name)
        if path.exists():
            if json.loads(path.read_text()) != record:
                raise ValueError('Retained bridge outcome changed')
        else:
            write_exclusive(path, json_bytes(record))
        return result

    def describe(self):
        with self._lock:
            return {'schema': 'dcc.blender.session.v1', 'session_id': self.session_id,
                    'generation': self.generation, 'port': self.port,
                    'project': str(self.project) if self.project else None,
                    'scene': self.scene, 'active_operation': self.active, 'reason': self.reason}

    def authorize(self, token, session_id, generation):
        with self._lock:
            if (not isinstance(token, str) or not hmac.compare_digest(token, self._token)
                    or session_id != self.session_id):
                raise ValueError('Unauthorized session or stale document generation')
            if generation != self.generation:
                raise StaleGenerationError('Unauthorized session or stale document generation')

    def invalidate(self, reason):
        with self._lock:
            self.generation = str(uuid.uuid4())
            self._prepared.clear()
            self.reason = reason
            # Keep the binding and unresolved job: reload is not proof of recovery.
            self._write_descriptor()

    def bind(self, project, scene):
        with self._lock:
            project = reject_links(project).resolve()
            if project == self.workspace or not project.is_relative_to(self.workspace):
                raise ValueError('Project must be inside the paired workspace')
            if self.project and (self.project != project or self.scene != scene):
                raise ValueError('Session is already bound to another project or scene')
            if not isinstance(scene, str) or not scene:
                raise ValueError('Explicit scene is required')
            self.project, self.scene = project, scene
            self._write_descriptor()
            return self.describe()

    def acquire(self, operation_id):
        uuid.UUID(operation_id)
        with self._lock:
            if self.active is not None:
                raise RuntimeError('BUSY: reconcile the active operation first')
            self.active = operation_id

    def release(self, operation_id):
        with self._lock:
            if self.active != operation_id:
                raise ValueError('Active operation mismatch')
            self.active = None

    def prepare(self, operation_id, request_hash, fingerprint):
        uuid.UUID(operation_id)
        with self._lock:
            now = time.time()
            self._prepared = {k: v for k, v in self._prepared.items() if v['expires_at'] > now}
            if len(self._prepared) >= 16:
                raise RuntimeError('BUSY: preparation capacity reached')
            result = {'operation_id': operation_id, 'session_id': self.session_id,
                      'generation': self.generation, 'token': secrets.token_hex(32),
                      'request_hash': request_hash, 'fingerprint': fingerprint, 'expires_at': now + 30}
            self._prepared[result['token']] = result
            return result.copy()

    def consume(self, prepared, request_hash, fingerprint):
        with self._lock:
            token = prepared.get('token') if isinstance(prepared, dict) else None
            saved = self._prepared.get(token) if isinstance(token, str) else None
            if (saved is None or saved != prepared or saved['generation'] != self.generation
                    or saved['expires_at'] <= time.time() or saved['request_hash'] != request_hash
                    or saved['fingerprint'] != fingerprint):
                raise ValueError('STALE_PREPARATION: inspect and prepare again')
            del self._prepared[token]

    def close(self):
        with self._lock:
            self._prepared.clear()
            self.generation = str(uuid.uuid4())
            self.reason = 'Bridge stopped'
            self._token = secrets.token_hex(32)
            reject_links(self.descriptor_path).unlink(missing_ok=True)
