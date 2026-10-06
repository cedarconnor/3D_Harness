"""Read-only fresh Blender validation of the seeded shrub study and placement.

Run via blender --background --python-exit-code 1 --python this.py -- ...
This measures actual saved mesh ring/leaf coordinates, not the writer's receipt
alone. Receipts and observers are trusted producers, not authenticated evidence.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('--repo', required=True)
p.add_argument('--source', required=True)
p.add_argument('--before', required=True)
p.add_argument('--placement', required=True)
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0, a.repo)
from dcc_harness.vegetation import shrub_structure, leaf_surface
from dcc_harness.vegetation_blender import build_shrub, leaf_materials
from dcc_harness.evidence import file_hash, read_json, write_json

assert bpy.app.background
sha = file_hash(a.source); old_sha = file_hash(a.before)
receipt = read_json(a.placement)
bpy.ops.wm.open_mainfile(filepath=a.before, load_ui=False)
old = {o.get('dcc_instance_id'): o for o in bpy.context.scene.objects}
anchors = {i: sum((old[f'ext.site.shrub.trunk{i}'].matrix_world@v.co for v in list(old[f'ext.site.shrub.trunk{i}'].data.vertices)[:7]), Vector())/7 for i in range(29)}
bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False)
native = {o.get('dcc_instance_id'): o for o in bpy.context.scene.objects}
failures, definitions, placements = [], [], []
if any(i.startswith('ext.site.shrub.') for i in native if i): failures.append('Old shrub object remains')
if len([i for i in native if i and i.startswith('ext.site.broadleaf.')]) != 58: failures.append('Expected exactly 58 new shrub objects')
for index, record in enumerate(receipt['definitions']):
    prefix = f'ext.site.broadleaf.{index:02}'
    wood, leaves = native[prefix+'.wood'], native[prefix+'.leaves']
    structure = shrub_structure(record['seed'], record['leader_height'], leaf_scale=record.get('leaf_scale',1.))
    wood_vertices = list(wood.data.vertices)
    ends, starts, offset, errors = [], [], 0, []
    for stem in structure['stems']:
        sides = 3 if stem['kind'] == 'petiole' else 7
        # Stored vertices are float32; sum in double precision so the check
        # does not introduce a second round of float32 accumulation error.
        start = tuple(math.fsum(v.co[axis] for v in wood_vertices[offset:offset+sides])/sides for axis in range(3))
        end = tuple(math.fsum(v.co[axis] for v in wood_vertices[offset+sides:offset+2*sides])/sides for axis in range(3))
        if stem['parent'] is None: expected = (0., 0., 0.)
        else: expected = tuple(a*(1-stem['attachment'])+b*stem['attachment'] for a,b in zip(starts[stem['parent']],ends[stem['parent']]))
        errors.append(math.dist(start,expected))
        starts.append(start); ends.append(end); offset += 2*sides
    if offset != len(wood.data.vertices): failures.append('Unexpected wood vertex count: '+prefix)
    vertices_per_leaf = len(leaf_surface()['vertices'])
    errors.extend(math.dist(leaves.data.vertices[i*vertices_per_leaf].co,ends[leaf['parent']]) for i, leaf in enumerate(structure['leaves']))
    if len(leaves.data.vertices) != len(structure['leaves'])*vertices_per_leaf: failures.append('Unexpected leaf vertex count: '+prefix)
    uv = leaves.data.uv_layers.active
    if not uv or any(not 0 <= x <= 1 for item in uv.data for x in item.uv): failures.append('Leaf UV outside 0..1: '+prefix)
    if any(len(poly.vertices) != 3 or poly.area <= 0 for poly in leaves.data.polygons): failures.append('Degenerate/non-triangle leaf face: '+prefix)
    if max(errors) > 3e-7: failures.append('Detached stem or leaf base: '+prefix)
    definitions.append({'id':prefix,'seed':record['seed'],'leaves':len(structure['leaves']),'max_connection_error_m':max(errors),'wood_mesh':wood.data.name,'leaf_mesh':leaves.data.name})
for i in range(29):
    wood, leaves = (native[f'ext.site.broadleaf.{i:02}.{kind}'] for kind in ('wood', 'leaves'))
    if wood.matrix_world != leaves.matrix_world: failures.append('Wood/leaf transforms differ: '+str(i))
    if (wood.location.xy-anchors[i].xy).length > 1e-6: failures.append('Root XY moved: '+str(i))
    hits=[]
    for iid in ('ext.ground','ext.site.terrain'):
        obj=native[iid];inv=obj.matrix_world.inverted()
        hit,point,normal,face=obj.ray_cast(inv@Vector((wood.location.x,wood.location.y,10)),(inv.to_3x3()@Vector((0,0,-1))).normalized())
        if hit:hits.append((obj.matrix_world@point).z)
    gap=wood.location.z-max(hits) if hits else None
    if gap is None or abs(gap+.002)>1e-6: failures.append('Root support differs: '+str(i))
    for kind,obj in (('wood',wood),('leaves',leaves)):
        if obj.data != native[f'ext.site.broadleaf.{i%4:02}.{kind}'].data: failures.append('Definition sharing differs: '+str(i))
    placements.append({'id':i,'root_gap_m':gap,'xy_drift_m':(wood.location.xy-anchors[i].xy).length})

# Failure cases must refuse before creating anything in the saved example.
counts=(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.materials))
for operation in (lambda: leaf_materials(), lambda: build_shrub(native['ext.site.broadleaf.00.wood'].users_collection[0], 'ext.site.broadleaf.00', native['ext.site.broadleaf.00.wood'].data.materials[0],list(native['ext.site.broadleaf.00.leaves'].data.materials))):
    try: operation()
    except ValueError: pass
    else: failures.append('Duplicate identity was accepted')
if counts != (len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.materials)): failures.append('Rejected operation changed datablocks')
assert file_hash(a.source)==sha and file_hash(a.before)==old_sha
write_json(a.out,{'passed':not failures,'failures':failures,'definitions':definitions,'placements':placements,'source_sha256':sha,'before_sha256':old_sha,'native_saves':0,'blender':bpy.app.version_string,'duplicate_guards_unchanged':counts==(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.materials)),'limits':'Growth attachment, local UV bounds, scoped root samples and shared definitions only; no botanical, general collision, welded topology or artist acceptance claim.'})
print('VEGETATION_NATIVE',not failures, failures)
if failures: raise RuntimeError('Vegetation checks failed')
