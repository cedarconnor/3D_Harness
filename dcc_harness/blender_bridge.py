"""Bounded local bridge client; no automatic retry, including after lost replies."""
import json
import hashlib
import os
import socket
import time

from .distribution import upstream, bridge_manifest
from .files import reject_links, json_bytes

COMMANDS = frozenset(('ping', 'get_addon_info', 'get_scene_info', 'get_object_info', 'list_scene_items'))
MAX_RESPONSE = 8 * 1024 * 1024
MAX_REQUEST = 65536
FEATURES = frozenset(('paired_sessions', 'document_generation', 'scoped_inspection'))
PAIRED_COMMANDS = frozenset(('session_describe', 'inspect', 'attach_begin', 'attach_apply', 'attach_check', 'attach_acknowledge', 'attach_rebind',
                            'job_prepare', 'job_submit', 'job_status', 'job_cancel', 'job_check', 'job_acknowledge',
                            'recovery_capture', 'recovery_acknowledge', 'preview_capture', 'addons_inventory'))
COPY_COMMANDS = frozenset(('attach_begin', 'attach_apply', 'job_prepare', 'recovery_capture', 'preview_capture'))
DURABLE_COMMANDS = COPY_COMMANDS | {'job_submit', 'attach_acknowledge', 'job_acknowledge', 'recovery_acknowledge'}


class BridgeTransportError(RuntimeError):
    """No response; native outcome remains unknown unless durable evidence resolves it."""
    def __init__(self, message, *, unavailable=False):
        super().__init__(message)
        self.unavailable = unavailable


def retained_outcome(command, payload, private):
    if command not in DURABLE_COMMANDS:
        return None
    identity = {'command': command, 'payload': payload, 'session_id': private['session_id'],
                'generation': private['generation']}
    name = hashlib.sha256(json_bytes(identity)).hexdigest() + '.json'
    path = reject_links(os.path.join(private['workspace'], '.harness-mcp', 'outcomes', private['session_id'], name))
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record, dict) or set(record) != set(identity) | {'result'} or any(record[k] != v for k, v in identity.items()):
        raise ValueError('Retained bridge request identity changed')
    if private.get('token') and private['token'] in json.dumps(record['result']):
        raise ValueError('Bridge returned sensitive session material')
    return record['result']


def _process_alive(pid):
    if type(pid) is not int or pid <= 0:
        return None
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False if ctypes.get_last_error() == 87 else None
        try:
            code = ctypes.c_ulong()
            return code.value == 259 if kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)) else None
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None


def session_presence(binding):
    """Timeouts never establish death; keep stale descriptors as evidence."""
    private = descriptor(binding)
    if _process_alive(private.get('pid')) is False:
        return 'DEAD'
    try:
        call('session_describe', {}, binding=binding)
        return 'PRESENT'
    except ConnectionRefusedError:
        return 'UNAVAILABLE'
    except BridgeTransportError as exc:
        return 'UNAVAILABLE' if exc.unavailable else 'UNKNOWN'
    except Exception:
        return 'UNKNOWN'


def _request(port, command, params, timeout):
    encoded = json.dumps({'type': command, 'params': params}, allow_nan=False).encode('utf-8')
    if len(encoded) > MAX_REQUEST:
        raise ValueError('Blender request exceeds byte limit')
    deadline = time.monotonic() + timeout
    with socket.create_connection(('127.0.0.1', port), timeout=timeout) as connection:
        connection.sendall(encoded)
        data = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Blender observation deadline exceeded; no automatic retry')
            connection.settimeout(remaining)
            chunk = connection.recv(min(65536, MAX_RESPONSE + 1 - len(data)))
            if not chunk:
                raise ConnectionError('Incomplete Blender response; no automatic retry')
            data.extend(chunk)
            if len(data) > MAX_RESPONSE:
                raise ValueError('Blender response exceeds byte limit')
            try:
                response = json.loads(data.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(response, dict) or response.get('status') not in ('success', 'error'):
                raise ValueError('Invalid Blender response envelope')
            if response['status'] == 'error':
                raise RuntimeError('Blender observation failed: ' + str(response.get('message')))
            if 'result' not in response:
                raise ValueError('Missing Blender response result')
            return response['result']


def observe(command, params=None, *, port=9878, timeout=10):
    if command not in COMMANDS:
        raise ValueError('Only observation commands are allowed')
    if type(port) is not int or not 1024 <= port <= 65535 or not 0 < timeout <= 30:
        raise ValueError('Invalid bridge port or timeout')
    meta = upstream()
    info = _request(port, 'get_addon_info', {}, timeout)
    if (not isinstance(info, dict) or info.get('harness_protocol') not in (2, meta['adapter_protocol'])
            or info.get('protocol_version') != meta['protocol'] or info.get('upstream_commit') != meta['commit']
            or set(info.get('capabilities', [])) != COMMANDS):
        raise ValueError('Incompatible Blender bridge; install the bundled observation add-on')
    result = info if command == 'get_addon_info' else _request(port, command, params or {}, timeout)
    return {'provenance': 'live_advisory_not_checkpoint_evidence', 'result': result}


def descriptor(path):
    value = json.loads(reject_links(path).read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('schema') != 'dcc.blender.session.v1'
            or type(value.get('port')) is not int or not 1024 <= value['port'] <= 65535
            or not isinstance(value.get('token'), str) or len(value['token']) != 64
            or any(not isinstance(value.get(k), str) or not value[k] for k in ('session_id', 'generation', 'workspace'))):
        raise ValueError('Invalid private session descriptor')
    return value


def call(command, payload, *, binding, timeout=None, expected=None):
    """Resolve an explicit private descriptor; never expose its pairing token."""
    timeout = (180 if command in COPY_COMMANDS else 10) if timeout is None else timeout
    if command not in PAIRED_COMMANDS or not isinstance(payload, dict) or not 0 < timeout <= 180:
        raise ValueError('Invalid paired bridge command or deadline')
    private = descriptor(binding)
    if expected is not None and (private['session_id'], private['generation']) != expected:
        raise ValueError('Session or document generation changed before dispatch')
    retained = retained_outcome(command, payload, private)
    if retained is not None:
        return retained
    meta = upstream()
    try:
        info = _request(private['port'], 'get_addon_info', {}, min(timeout, 10))
    except Exception as exc:
        raise BridgeTransportError(str(exc).replace(private['token'], '[redacted]'),
                                   unavailable=isinstance(exc, ConnectionRefusedError)) from None
    if (not isinstance(info, dict) or info.get('harness_protocol') != 3
            or info.get('protocol_version') != meta['protocol'] or info.get('upstream_commit') != meta['commit']
            or not FEATURES <= set(info.get('features', [])) or command not in info.get('paired_commands', [])):
        raise ValueError('Incompatible live bridge: protocol 3 and required features are necessary')
    if info.get('bridge_manifest') != bridge_manifest():
        raise ValueError('Incompatible live bridge manifest; install the add-on exported by this runtime')
    auth = {key: private[key] for key in ('token', 'session_id', 'generation')}
    try:
        result = _request(private['port'], command, {'auth': auth, 'payload': payload}, timeout)
    except Exception as exc:
        # Error replies are untrusted; do not reflect authentication material.
        retained = retained_outcome(command, payload, private)
        if retained is not None:
            return retained
        raise BridgeTransportError(str(exc).replace(private['token'], '[redacted]'),
                                   unavailable=isinstance(exc, ConnectionRefusedError)) from None
    if private['token'] in json.dumps(result):
        raise ValueError('Bridge returned sensitive session material')
    return result
