"""Independent saved-copy checks; never executes within the user's Blender process."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bpy
from dcc_harness.evidence import read_json, write_json, file_hash
from dcc_harness.adoption_inventory_blender import inventory
from dcc_harness.data.bridge.attachment import snapshot
from dcc_harness.live_snapshot import equivalent, fingerprint


def main():
    if not bpy.app.background:
        raise RuntimeError('Live-copy verifier requires an owned background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'verify':
        raise ValueError('Unsupported live verification action')
    request = read_json(request_path)
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Candidate changed before verification')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    scene = bpy.data.scenes.get(request['scene'])
    if scene is None:
        raise ValueError('Saved scene missing')
    bpy.context.window.scene = scene
    current = snapshot(scene)
    write_json(Path(request['out']) / 'saved-snapshot.json', current)
    expected = read_json(request['snapshot'])
    if (fingerprint(expected) != request['fingerprint'] or inventory(scene) != request['inventory']
            or not equivalent(expected, current)):
        raise ValueError('Saved copy does not match the measured live scene')
    if 'recipe' in request:
        from dcc_harness.data.bridge.operations import verify_live, load_qualification
        if request['recipe']['recipe'] == 'node.asset':
            load_qualification(request['asset_qualification'], request['recipe']['parameters'])
        verify_live(scene, request['recipe'])
    from dcc_harness.continuity_blender import observe
    observation = observe(scene)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Candidate changed during verification')
    write_json(Path(request['out']) / 'observation.json', observation, compact_observation=True)
    write_json(Path(request['out']) / 'verified.json', {'saved_inventory_matches': True,
                                                      'saved_fingerprint_matches': True})


if __name__ == '__main__':
    main()
