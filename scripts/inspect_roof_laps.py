"""Read-only qualification of the garden's parallel rectangular roof courses."""
import argparse,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
for name in ('repo','source','out'):p.add_argument('--'+name,required=True)
p.add_argument('--inject-intersection',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sys.path.insert(0,a.repo)
from dcc_harness.evidence import file_hash,write_json
assert bpy.app.background;sha=file_hash(a.source)
bpy.ops.wm.open_mainfile(filepath=a.source,load_ui=False)
native={o.get('dcc_instance_id'):o for o in bpy.context.scene.objects}
if a.inject_intersection:
    target=native['ext.building.roof.tile.-1.1.4']
    target.location-=(target.matrix_world.to_3x3()@Vector((0,0,1)))*.005
    bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get();tiles={};failures=[]
dot=lambda p,n:sum(float(x)*float(y) for x,y in zip(p,n))
def points(obj):
    evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
    try:return [tuple(evaluated.matrix_world@v.co) for v in mesh.vertices]
    finally:evaluated.to_mesh_clear()
decks={side:native[f'ext.building.roof.deck{side}'] for side in (-1,1)}
deck_data={side:((o.matrix_world.to_3x3()@Vector((0,0,1))).normalized(),points(o)) for side,o in decks.items()}
deck_gaps=[]
for iid,obj in native.items():
    if not iid or not iid.startswith('ext.building.roof.tile.'):continue
    side,row,col=map(int,iid.split('.')[-3:]);pts=points(obj)
    normal=tuple((obj.matrix_world.to_3x3()@Vector((0,0,1))).normalized());tangent=tuple((obj.matrix_world.to_3x3()@Vector((0,-side,0))).normalized())
    if len(obj.data.vertices)!=8 or any(abs(x-y)>2e-6 for x,y in zip(obj.dimensions,(.294,.45,.006))):failures.append('Tile rectangular dimensions differ')
    bevels=[m for m in obj.modifiers if m.type=='BEVEL']
    if len(bevels)!=1 or abs(bevels[0].width-.0006)>1e-8:failures.append('Tile bevel differs')
    dn,dp=deck_data[side];gap=min(dot(v,dn) for v in pts)-max(dot(v,dn) for v in dp);deck_gaps.append(gap)
    if gap<.0008-2e-6:failures.append('Tile penetrates declared deck clearance')
    tiles[side,row,col]={'id':iid,'points':pts,'normal':normal,'tangent':tangent,'x':(min(v[0] for v in pts),max(v[0] for v in pts))}
if set(tiles)!={(s,r,c) for s in (-1,1) for r in range(8) for c in range(22)}:failures.append('Tile identity layout differs')
pairs=[]
for (side,row,col),lo in tiles.items():
    if row==7:continue
    for upper_col in range(22):
        hi=tiles.get((side,row+1,upper_col))
        if hi is None or min(lo['x'][1],hi['x'][1])-max(lo['x'][0],hi['x'][0])<=.001:continue
        normal=lo['normal'];tangent=lo['tangent']
        if abs(dot(normal,hi['normal'])-1)>1e-6:failures.append('Adjacent tiles are not parallel')
        gap=min(dot(v,normal) for v in hi['points'])-max(dot(v,normal) for v in lo['points'])
        overlap=min(max(dot(v,tangent) for v in lo['points']),max(dot(v,tangent) for v in hi['points']))-max(min(dot(v,tangent) for v in lo['points']),min(dot(v,tangent) for v in hi['points']))
        if abs(gap-.0008)>2e-6:failures.append('Adjacent course clearance differs')
        if not .13<overlap<.15:failures.append('Adjacent course overlap differs')
        pairs.append({'lower':lo['id'],'upper':hi['id'],'gap_m':gap,'overlap_m':overlap})
if not pairs:failures.append('No adjacent roof pairs checked')
assert file_hash(a.source)==sha
write_json(a.out,{'passed':not failures,'failures':sorted(set(failures)),'source_sha256':sha,'blender':bpy.app.version_string,'native_saves':0,
 'tiles_checked':len(tiles),'adjacent_pairs':len(pairs),'gap_range_m':[min((r['gap_m'] for r in pairs),default=None),max((r['gap_m'] for r in pairs),default=None)],
 'overlap_range_m':[min((r['overlap_m'] for r in pairs),default=None),max((r['overlap_m'] for r in pairs),default=None)],
 'minimum_deck_gap_m':min(deck_gaps,default=None),'intentional_intersection':a.inject_intersection,'pairs':pairs,
 'limits':'Parallel rectangular tile courses and deck-plane separation only; not all roof joins, support hardware, weatherproofing, collision with trim or building qualification.'})
print('ROOF_LAPS',not failures,sorted(set(failures)),len(pairs))
if failures:raise RuntimeError('Roof lap qualification failed')
