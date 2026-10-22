"""Private fresh-process worker for adoption.py; never run in an artist editor."""
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from dcc_harness.adoption import plan_identities, validate_plan, verify_applied_plan
from dcc_harness.evidence import file_hash, read_json, write_json


from dcc_harness.adoption_inventory_blender import inventory


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
            pool = {'object': bpy.data.objects, 'material': bpy.data.materials,
                    'collection': bpy.data.collections}[assignment['kind']]
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
