"""Paired local adapter for the pinned upstream MCP for Blender add-on.

upstream.py is a reduced observation-only derivative; see LICENSE.upstream and
upstream.json for its original and bundled hashes. Only this module is registered. Construction belongs to managed checkpoint execution.
"""
import json
import queue
import socket
import threading
import time
import bpy
from . import upstream, inspection
from .session import Session

bl_info = {'name': '3D Harness observation bridge', 'author': '3D Harness contributors; Siddharth Ahuja (upstream)',
           'version': (0, 21, 1), 'blender': (5, 1, 0), 'category': 'Interface',
           'location': 'View3D > Sidebar > 3D Harness'}
COMMANDS = ('ping', 'get_addon_info', 'get_scene_info', 'get_object_info', 'list_scene_items')
PAIRED_COMMANDS = ('session_describe', 'inspect')
FEATURES = ('paired_sessions', 'document_generation', 'scoped_inspection')
server = None


class ObservationServer(upstream.BlenderMCPServer):
    def __init__(self, port=9878, workspace=None):
        super().__init__(host='127.0.0.1', port=port)
        self._slots = threading.BoundedSemaphore(16)
        self.session = Session(workspace, port) if workspace else None

    def stop(self):
        super().stop()
        if self.session:
            self.session.close()

    def execute_command(self, command):
        try:
            if not isinstance(command, dict) or set(command) != {'type', 'params'}:
                raise ValueError('Expected type and params')
            name, params = command['type'], command['params']
            if name not in COMMANDS + PAIRED_COMMANDS or not isinstance(params, dict):
                raise ValueError('Only observation commands are allowed')
            if name in PAIRED_COMMANDS:
                if self.session is None or set(params) != {'auth', 'payload'}:
                    raise ValueError('Unauthorized paired session')
                auth = params['auth']
                if not isinstance(auth, dict) or set(auth) != {'token', 'session_id', 'generation'}:
                    raise ValueError('Unauthorized paired session')
                self.session.authorize(**auth)
                if not isinstance(params['payload'], dict):
                    raise ValueError('Invalid paired payload')
                if name == 'session_describe':
                    result = {**self.session.describe(), 'filepath': bpy.data.filepath,
                              'scenes': [s.name for s in bpy.data.scenes]}
                else:
                    result = inspection.inspect(params['payload'])
            elif name == 'ping':
                result = {'pong': True}
            elif name == 'get_addon_info':
                result = {'harness_protocol': 3, 'protocol_version': upstream.ADDON_PROTOCOL_VERSION,
                          'upstream_commit': '5a3618fccb2d982d0dd61e7a1879912c3100073b',
                          'capabilities': list(COMMANDS), 'features': list(FEATURES),
                          'paired_commands': list(PAIRED_COMMANDS), 'blender_version': bpy.app.version_string}
            else:
                result = getattr(self, name)(**params)
            if isinstance(result, dict) and 'error' in result:
                raise ValueError(result['error'])
            return {'status': 'success', 'result': result}
        except Exception as exc:
            message = str(exc)
            if self.session:
                message = message.replace(self.session._token, '[redacted]')
            return {'status': 'error', 'message': message}

    def _handle_client(self, client):
        if not self._slots.acquire(blocking=False):
            client.close()
            return
        done = threading.Event()
        try:
            with self._clients_lock:
                self._clients.add(client)
            client.settimeout(0.2)
            deadline, data = time.monotonic() + 10, b''
            while self.running and time.monotonic() < deadline:
                try:
                    chunk = client.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    return
                data += chunk
                if len(data) > 65536:
                    return
                try:
                    command = json.loads(data.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                self.command_queue.put((command, client, done, deadline))
                done.wait(max(0, deadline - time.monotonic()))
                return
        except OSError:
            pass
        finally:
            with self._clients_lock:
                self._clients.discard(client)
            client.close()
            self._slots.release()

    def _drain_command_queue(self):
        if not self.running:
            return None
        for _ in range(16):
            try:
                command, client, done, deadline = self.command_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if time.monotonic() < deadline:
                    response = json.dumps(self.execute_command(command), allow_nan=False).encode('utf-8')
                    if len(response) > 8 * 1024 * 1024:
                        response = b'{"status":"error","message":"Response exceeds byte limit; narrow query"}'
                    client.sendall(response)
            except (OSError, ValueError):
                pass
            finally:
                done.set()
        return 0.05


class HARNESS_OT_start(bpy.types.Operator):
    bl_idname = 'dcc_harness.start_bridge'
    bl_label = 'Start bridge'

    def execute(self, context):
        global server
        if server is None:
            workspace = context.scene.dcc_harness_workspace
            server = ObservationServer(context.scene.dcc_harness_port, workspace or None)
        server.start()
        if not server.running:
            self.report({'ERROR'}, 'Bridge did not start; inspect Blender console and port')
            return {'CANCELLED'}
        return {'FINISHED'}


class HARNESS_OT_stop(bpy.types.Operator):
    bl_idname = 'dcc_harness.stop_bridge'
    bl_label = 'Stop observation bridge'

    def execute(self, context):
        global server
        if server is not None:
            server.stop()
            server = None
        return {'FINISHED'}


class HARNESS_PT_bridge(bpy.types.Panel):
    bl_label = '3D Harness'
    bl_idname = 'HARNESS_PT_bridge'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '3D Harness'

    def draw(self, context):
        self.layout.label(text='Pair a workspace for managed live access')
        self.layout.prop(context.scene, 'dcc_harness_port')
        self.layout.prop(context.scene, 'dcc_harness_workspace')
        if server and server.session:
            self.layout.label(text='Session: ' + server.session.session_id[:8])
        self.layout.operator('dcc_harness.stop_bridge' if server and server.running else 'dcc_harness.start_bridge')


CLASSES = (HARNESS_OT_start, HARNESS_OT_stop, HARNESS_PT_bridge)


@bpy.app.handlers.persistent
def document_loaded(_):
    if server and server.session:
        server.session.invalidate('Document loaded; reattach explicitly')


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dcc_harness_port = bpy.props.IntProperty(name='Port', default=9878, min=1024, max=65535)
    bpy.types.Scene.dcc_harness_workspace = bpy.props.StringProperty(name='Workspace', subtype='DIR_PATH')
    bpy.app.handlers.load_post.append(document_loaded)


def unregister():
    global server
    if server is not None:
        server.stop()
        server = None
    del bpy.types.Scene.dcc_harness_port
    del bpy.types.Scene.dcc_harness_workspace
    if document_loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(document_loaded)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
