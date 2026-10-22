"""Bounded, read-only client of the pinned upstream Blender socket protocol."""
import json
import socket
import time

from .distribution import upstream

COMMANDS = frozenset(('ping', 'get_addon_info', 'get_scene_info', 'get_object_info', 'list_scene_items'))
MAX_RESPONSE = 8 * 1024 * 1024


def _request(port, command, params, timeout):
    deadline = time.monotonic() + timeout
    with socket.create_connection(('127.0.0.1', port), timeout=timeout) as connection:
        connection.sendall(json.dumps({'type': command, 'params': params}, allow_nan=False).encode('utf-8'))
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
    if (not isinstance(info, dict) or info.get('harness_protocol') != meta['adapter_protocol']
            or info.get('protocol_version') != meta['protocol'] or info.get('upstream_commit') != meta['commit']
            or set(info.get('capabilities', [])) != COMMANDS):
        raise ValueError('Incompatible Blender bridge; install the bundled observation add-on')
    result = info if command == 'get_addon_info' else _request(port, command, params or {}, timeout)
    return {'provenance': 'live_advisory_not_checkpoint_evidence', 'result': result}
