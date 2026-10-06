"""Private fresh-process worker for adoption.py; never run in an artist editor."""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.adoption import plan_identities, validate_plan, verify_applied_plan
from dcc_harness.evidence import file_hash, read_json, write_json


def inventory():
    scene = bpy.context.scene
    active = set(scene.objects)
    used_materials = {slot.material for o in active for slot in o.material_slots if slot.material}
    material_users = bpy.data.user_map(subset=list(bpy.data.materials))

    def scoped_object(obj):
        return obj in active and set(obj.users_scene) == {scene}

    def outside_material_users(mat):
        outside = []
        for user in material_users.get(mat, set()):
            if isinstance(user, bpy.types.Object):
                allowed = scoped_object(user)
            elif hasattr(user, 'materials'):
                owners = [o for o in bpy.data.objects if o.data == user]
                allowed = bool(owners) and all(scoped_object(o) for o in owners)
            else:
                # Node groups and other indirect users need a deliberate ownership decision.
                allowed = False
            if not allowed:
                outside.append(type(user).__name__ + ':' + user.name_full)
        return sorted(outside)

    def properties(item, names):
        # Preserve invalid types as diagnostics without serializing arbitrary IDProperty groups.
        return {p: item[p] if isinstance(item[p], str) else {'invalid_type': type(item[p]).__name__}
                for p in names if p in item}

    def base(item, scope, props):
        return {'name': item.name_full, 'scope': scope, 'properties': properties(item, props),
                'read_only': bool(item.library or item.override_library)}

    objects = []
    for obj in sorted(bpy.data.objects, key=lambda o: o.name_full):
        record = base(obj, obj in active, ('dcc_instance_id', 'dcc_asset_id'))
        record.update(type=obj.type, mesh=obj.data.name_full if obj.type == 'MESH' else None,
                      scenes=sorted(s.name for s in obj.users_scene))
        objects.append(record)
    materials = []
    for mat in sorted(bpy.data.materials, key=lambda m: m.name_full):
        record = base(mat, mat in used_materials, ('dcc_material_id',))
        record['outside_users'] = outside_material_users(mat)
        materials.append(record)
    return {'scene': scene.name, 'objects': objects, 'materials': materials}


def main():
    if not bpy.app.background:
        raise RuntimeError('Identity adoption requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    request = read_json(request_path)
    out = Path(request['out'])
    source = request['plan']['source'] if action == 'apply' else request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed during native open')
    if action == 'preview':
        write_json(out / 'plan.json', plan_identities(inventory(), source))
    elif action == 'apply':
        plan = request['plan']
        validate_plan(plan, inventory(), source)
        # Resolve and check every target before the first property write.
        targets = []
        for assignment in plan['assignments']:
            pool = bpy.data.objects if assignment['kind'] == 'object' else bpy.data.materials
            item = next(x for x in pool if x.name_full == assignment['name'])
            if assignment['property'] in item:
                raise ValueError('Identity property appeared after preview')
            targets.append((item, assignment['property'], assignment['value']))
        for item, prop, value in targets:
            item[prop] = value
        checkpoint = out / 'checkpoint.blend'
        if checkpoint.exists():
            raise FileExistsError(checkpoint)
        bpy.ops.wm.save_as_mainfile(filepath=str(checkpoint))
    elif action == 'observe':
        verify_applied_plan(request['plan'], inventory())
        from dcc_harness.continuity_blender import observe
        write_json(out / 'observation.json', observe(), compact_observation=True)
    else:
        raise ValueError('Unknown adoption worker action')
    if file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')


if __name__ == '__main__':
    main()
