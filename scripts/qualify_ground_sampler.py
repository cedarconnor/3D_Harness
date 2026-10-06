"""Owned Blender fixture for evaluated, transformed world-space support rays."""
import argparse,sys,math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,a.repo)
from dcc_harness.ground_blender import SurfaceSampler
from dcc_harness.evidence import write_json
assert bpy.app.background
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.mesh.primitive_plane_add(size=4);plane=bpy.context.object;plane['dcc_instance_id']='fixture.sloped'
plane.location=(3,-2,1);plane.rotation_euler=(0,.25,.2);plane.scale=(2,.7,1.4)
mod=plane.modifiers.new('Actual solidify','SOLIDIFY');mod.thickness=.4;mod.offset=1
bpy.context.view_layer.update();sampler=SurfaceSampler([plane])
# Solve the transformed local top plane independently, including solidify.
origin=plane.matrix_world@Vector((0,0,.4));normal=(plane.matrix_world.inverted().transposed().to_3x3()@Vector((0,0,1))).normalized()
records=[]
for x,y in [(3,-2),(3.2,-2.1),(2.6,-1.8)]:
    expected=origin.z-(normal.x*(x-origin.x)+normal.y*(y-origin.y))/normal.z
    hit=sampler.sample(x,y);assert hit is not None and abs(hit['position'][2]-expected)<2e-6
    assert abs(Vector(hit['normal']).dot(normal)-1)<2e-6
    records.append({'xy':[x,y],'actual':hit['position'][2],'expected':expected})
assert sampler.sample(50,50) is None
assert sampler.sample(3,-2,top=0,bottom=-1) is None
bpy.ops.mesh.primitive_plane_add(size=1,location=(3,-2,4));upper=bpy.context.object;upper['dcc_instance_id']='fixture.upper';bpy.context.view_layer.update()
overlap=SurfaceSampler([plane,upper]);assert abs(overlap.sample(3,-2)['position'][2]-4)<1e-6
upper.location.z=5;bpy.context.view_layer.update()
assert abs(overlap.sample(3,-2)['position'][2]-4)<1e-6 # Documented snapshot semantics.
assert abs(SurfaceSampler([plane,upper]).sample(3,-2)['position'][2]-5)<1e-6
for objects in ([],[plane,plane]):
    try:SurfaceSampler(objects)
    except ValueError:pass
    else:raise AssertionError('Invalid surface list accepted')
for args in [(True,0,10,-10),(0,0,1,2),(float('nan'),0,10,-10)]:
    try:sampler.sample(args[0],args[1],top=args[2],bottom=args[3])
    except ValueError:pass
    else:raise AssertionError('Invalid ray accepted')
write_json(a.out,{'passed':True,'sloped_evaluated_cases':records,'nonuniform_transform':True,'highest_surface':True,'explicit_misses':True,'snapshot_requires_rebuild':True,'invalid_inputs_refused':True,'blender':bpy.app.version_string,'native_saves':0})
print('GROUND_SAMPLER_PASSED')
