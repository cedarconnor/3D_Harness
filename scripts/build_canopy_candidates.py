"""Owned native canopy study: keep previous workshop layout and all surfaces."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo', required=True); p.add_argument('--round', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
assert bpy.app.background
sys.path.insert(0, a.repo)
from dcc_harness.evidence import read_json, write_json, file_hash
from dcc_harness.continuity_blender import observe
from dcc_harness.continuity_checks import validate_contract
from dcc_harness.quality import reserved_space

root = Path(a.round).resolve(); source = root/'unchanged/scene.blend'
source_hash = file_hash(source); design = read_json(root/'design.json')
validate_contract(design['contract'])
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
preflight = reserved_space(observe(), design['reservations'], ['ext.pergola.'])
write_json(root/'preflight.json', preflight)
if not preflight['passed']: raise RuntimeError('Preflight blocked')
variants = {'open_timber': [1,3,5,7], 'central_opening': [3,4,5]}
produced = {}
for name, rafters in variants.items():
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    deleted = [f'ext.pergola.rafter.{i:02d}' for i in rafters]+['ext.pergola.batten.01','ext.pergola.batten.02']
    assert set(deleted) <= set(design['contract']['allowed_deleted_ids'])
    transform = Matrix.Translation(Vector((8.25,0,0))) @ Matrix.Diagonal((.93,1,1/.84,1)) @ Matrix.Translation(Vector((-8.25,0,0)))
    for obj in list(bpy.context.scene.objects):
        iid = obj.get('dcc_instance_id','')
        if iid in deleted:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif iid.startswith('ext.pergola.'):
            obj.matrix_world = transform @ obj.matrix_world
    bpy.context.view_layer.update()
    out = root/name; out.mkdir(exist_ok=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
    produced[name] = {'sha256':file_hash(out/'scene.blend'), 'deleted':deleted, 'x_scale':.93, 'z_scale':1/.84}
assert file_hash(source) == source_hash
write_json(root/'build.json', {'source_unchanged':True,'source_sha256':source_hash,'candidates':produced,
                            'design_sha256':file_hash(root/'design.json'),'script_sha256':file_hash(__file__)})
print('CANOPIES_BUILT')
