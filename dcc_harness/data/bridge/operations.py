"""Bounded built-ins: direct data edits, explicit targets and independently checkable results."""
import math
import json
from pathlib import Path
import bpy
from . import attachment, inspection
try:
    from .recipe_contracts import validate, MODIFIERS
    from .files import file_hash, reject_links
    from .node_asset_blender import describe as describe_asset, modifier_record
    from .evidence import digest
except ModuleNotFoundError:
    from dcc_harness.live_recipes import validate, MODIFIERS
    from dcc_harness.files import file_hash, reject_links
    from dcc_harness.node_asset_blender import describe as describe_asset, modifier_record
    from dcc_harness.evidence import digest

QUALIFICATIONS = {}


def load_qualification(reference, parameters):
    path = reject_links(reference['path'])
    if file_hash(path) != reference['sha256']:
        raise ValueError('Node asset qualification changed')
    report = json.loads(path.read_text())
    source = reject_links(parameters['path']).resolve()
    if (report['source'] != {'path': str(source), 'sha256': parameters['sha256']}
            or report['group'] != parameters['group'] or file_hash(source) != parameters['sha256']
            or digest(report['description']) != report['graph_sha256']):
        raise ValueError('Node asset source or qualification mismatch')
    QUALIFICATIONS[(parameters['sha256'], parameters['group'])] = report


def node_asset(obj, parameters):
    report = QUALIFICATIONS.get((parameters['sha256'], parameters['group']))
    if report is None or file_hash(reject_links(parameters['path'])) != parameters['sha256']:
        raise ValueError('Node asset has no current independent qualification')
    inputs = {s['identifier']: s for s in report['description']['interface']
              if s['direction'] == 'INPUT' and s['socket_type'] != 'NodeSocketGeometry'}
    if set(parameters['inputs']) - set(inputs):
        raise ValueError('Unknown node asset input')
    for key, v in parameters['inputs'].items():
        spec = inputs[key]
        vector = spec['socket_type'] == 'NodeSocketVector'
        if vector != isinstance(v, list) or (vector and len(v) != 3):
            raise ValueError('Node asset input dimension mismatch')
        if spec['socket_type'] == 'NodeSocketInt' and type(v) is not int:
            raise ValueError('Integer node input required')
        for item in v if vector else [v]:
            if not spec.get('min_value', -math.inf) <= item <= spec.get('max_value', math.inf):
                raise ValueError('Node asset input outside bounds')
    modifier = obj.modifiers.get(parameters['modifier'])
    if modifier and (modifier.type != 'NODES' or not modifier.node_group
                     or modifier.node_group.get('dcc_asset_group') != parameters['group']):
        raise ValueError('Refusing to replace an unrelated modifier')
    return report, modifier, inputs


def coverage(scene):
    """Refuse features whose dependencies are not qualified by these built-ins."""
    attachment.assert_copyable()
    if scene != bpy.context.scene or any(o.mode != 'OBJECT' for o in scene.objects):
        raise ValueError('BUSY: select Object mode in the paired scene')
    for obj in scene.objects:
        if (obj.type not in ('MESH', 'EMPTY', 'CAMERA', 'LIGHT') or obj.library or obj.override_library
                or obj.animation_data or obj.constraints or obj.instance_type != 'NONE'
                or len(obj.users_scene) != 1 or getattr(obj.data, 'animation_data', None)
                or getattr(obj.data, 'shape_keys', None)):
            raise ValueError('UNSUPPORTED_COVERAGE: linked, animated, rigged or cross-scene object')
        if any(mod.type not in set(MODIFIERS) | {'NODES'} for mod in obj.modifiers):
            raise ValueError('UNSUPPORTED_COVERAGE: modifier is not yet qualified')
        for modifier in obj.modifiers:
            if modifier.type == 'NODES':
                modifier_record(modifier)
    if scene.animation_data or (scene.world and scene.world.animation_data):
        raise ValueError('UNSUPPORTED_COVERAGE: animated scene or world')
    for material in bpy.data.materials:
        if material.animation_data or (material.node_tree and material.node_tree.animation_data):
            raise ValueError('UNSUPPORTED_COVERAGE: animated material')


def material_socket(scene, obj, params):
    matches = [m for m in bpy.data.materials if m.get('dcc_material_id') == params['material_id']]
    if len(matches) != 1 or matches[0].library or matches[0].override_library:
        raise ValueError('Material identity missing, ambiguous or read-only')
    material = matches[0]
    users = [o for o in bpy.data.objects if any(s.material == material for s in o.material_slots)]
    if obj not in users or set(params['shared_users']) != {o.get('dcc_instance_id') for o in users}:
        raise ValueError('Shared material users differ from the declared scope')
    if any(o not in list(scene.objects) for o in users):
        raise ValueError('UNSUPPORTED_COVERAGE: material users outside paired scene')
    node = material.node_tree.nodes.get(params['node']) if material.node_tree else None
    if node is None or node.bl_idname != 'ShaderNodeBsdfPrincipled':
        raise ValueError('Only qualified Principled material inputs are supported')
    sockets = [s for s in node.inputs if s.identifier == params['socket']]
    if len(sockets) != 1 or sockets[0].is_linked or not hasattr(sockets[0], 'default_value'):
        raise ValueError('Socket is linked, ambiguous or has no editable value')
    socket = sockets[0]
    current, wanted = inspection.plain(socket.default_value), params['value']
    if isinstance(current, list) != isinstance(wanted, list) or (isinstance(current, list) and len(current) != len(wanted)):
        raise ValueError('Socket value type or dimension differs')
    for v in wanted if isinstance(wanted, list) else [wanted]:
        if not getattr(socket, 'min_value', -math.inf) <= v <= getattr(socket, 'max_value', math.inf):
            raise ValueError('Socket value outside native bounds')
    return socket


def prepare(scene, value):
    validate(value); coverage(scene)
    if value['recipe'] == 'external.capture':
        if value['target'] != scene.name:
            raise ValueError('External import scene mismatch')
        observed = attachment.measure_live(scene)
        if observed['issues']:
            raise ValueError('UNSUPPORTED_COVERAGE: external state requires explicit identity/dependency repair')
        return {'recipe': value['recipe'], 'scene': scene.name}
    obj = inspection.target(scene, value['target'])
    params = value['parameters']
    if value['recipe'] == 'material.input':
        material_socket(scene, obj, params)
    elif value['recipe'] == 'modifier.settings':
        if obj.type != 'MESH':
            raise ValueError('Modifier recipe requires a mesh')
        modifier = obj.modifiers.get(params['name'])
        if modifier and modifier.type != params['type']:
            raise ValueError('Existing modifier type differs; never replace it implicitly')
    elif value['recipe'] == 'node.asset':
        if obj.type != 'MESH':
            raise ValueError('Node asset requires a mesh')
        node_asset(obj, params)
    return {'recipe': value['recipe'], 'target': value['target'], 'mode': obj.mode}


def execute_step(scene, value):
    prepare(scene, value)
    if value['recipe'] == 'external.capture':
        return  # Capture an explicit external change; do not invent a native mutation.
    obj, params = inspection.target(scene, value['target']), value['parameters']
    if value['recipe'] == 'object.transform':
        for key, vector in params.items():
            setattr(obj, key, vector)
    elif value['recipe'] == 'material.input':
        material_socket(scene, obj, params).default_value = params['value']
    elif value['recipe'] == 'modifier.settings':
        modifier = obj.modifiers.get(params['name']) or obj.modifiers.new(params['name'], params['type'])
        for key, v in params['settings'].items():
            setattr(modifier, key, v)
    elif value['recipe'] == 'node.asset':
        report, modifier, inputs = node_asset(obj, params)
        matches = [g for g in bpy.data.node_groups if g.get('dcc_asset_source') == params['sha256']
                   and g.get('dcc_asset_group') == params['group']]
        if len(matches) > 1:
            raise ValueError('Ambiguous owned node asset')
        if matches:
            tree = matches[0]
        else:
            with bpy.data.libraries.load(str(Path(params['path']).resolve()), link=False) as (source, target):
                if params['group'] not in source.node_groups:
                    raise ValueError('Qualified node group disappeared')
                target.node_groups = [params['group']]
            tree = target.node_groups[0]
            tree.name = 'DCC::' + params['sha256'][:12] + '::' + params['group']
            tree['dcc_asset_source'], tree['dcc_asset_group'] = params['sha256'], params['group']
        if describe_asset(tree) != report['description']:
            raise ValueError('Imported node graph differs from qualification')
        modifier = modifier or obj.modifiers.new(params['modifier'], 'NODES')
        modifier.node_group = tree
        for key, v in params['inputs'].items():
            kind = inputs[key]['socket_type']
            modifier[key] = [float(x) for x in v] if isinstance(v, list) else int(v) if kind == 'NodeSocketInt' else float(v)
        obj.update_tag()
    bpy.context.view_layer.update()
    verify_live(scene, value)


def verify_live(scene, value):
    prepare(scene, value)
    if value['recipe'] == 'external.capture':
        return
    obj, params = inspection.target(scene, value['target']), value['parameters']
    def equal(a, b):
        if isinstance(a, (list, tuple)):
            return isinstance(b, (list, tuple)) and len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return abs(a - b) <= 1e-6 * max(1, abs(b))
    if value['recipe'] == 'object.transform':
        checks = [(list(getattr(obj, k)), v) for k, v in params.items()]
    elif value['recipe'] == 'material.input':
        checks = [(inspection.plain(material_socket(scene, obj, params).default_value), params['value'])]
    elif value['recipe'] == 'modifier.settings':
        modifier = obj.modifiers.get(params['name'])
        if modifier is None:
            raise ValueError('Expected modifier was not created')
        checks = [(getattr(modifier, k), v) for k, v in params['settings'].items()]
    elif value['recipe'] == 'node.asset':
        report, modifier, _ = node_asset(obj, params)
        if modifier is None or modifier.node_group.get('dcc_asset_source') != params['sha256']:
            raise ValueError('Qualified node asset was not applied')
        observed = modifier_record(modifier)
        if observed['description'] != report['description']:
            raise ValueError('Node graph changed after qualification')
        checks = [(observed['inputs'].get(k), v) for k, v in params['inputs'].items()]
    else:
        raise ValueError('Unsupported live output validator')
    if not all(equal(a, b) for a, b in checks):
        raise ValueError('Live output does not satisfy the requested parameters')
