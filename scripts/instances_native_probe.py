"""Disposable instanced scenes and libraries for P3 qualification. Background Blender only.

blender --background --factory-startup --python-exit-code 1 --python THIS -- build --out NEW_FOLDER
blender ... --python THIS -- edit-library --out FOLDER        (rebuild lib/crate-v1.blend in place, taller)

build writes lib/crate-v1.blend, lib/crate-v2.blend, lib/vanishing.blend and scenes:
  scene.blend          two local bench instances, one linked crate, one nested set, ground, camera, light
  moved-a.blend        bench.a moved +0.5 m in x
  moved-ab.blend       bench.a and bench.b moved +0.5 m in x
  swapped.blend        moved-a with crate.a switched to the crate-v2 library
  no-asset-id.blend    a local instanced collection without dcc_asset_id
  verts.blend          a vertex instancer
  override.blend       a library override of the linked crate
  missing-library.blend  links lib/vanishing.blend, which the launcher deletes
"""
import argparse
from pathlib import Path
import sys

import bpy

p = argparse.ArgumentParser()
p.add_argument('action', choices=['build', 'edit-library'])
p.add_argument('--out', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
out = Path(a.out)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, mid=None):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    if mid:
        mat['dcc_material_id'] = mid
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*rgb, 1)
    return mat


def box(name, center, dims, mat, collection):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object; obj.name = name; obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def library(path, height):
    reset()
    col = bpy.data.collections.new('crate-asset'); col['dcc_asset_id'] = 'crate'
    bpy.context.scene.collection.children.link(col)
    box('crate.body', (0, 0, height / 2), (0.5, 0.5, height), material('crate-wood', (.3, .15, .05)), col)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def link(path):
    with bpy.data.libraries.load(str(path), link=True, relative=True) as (src, dst):
        dst.collections = ['crate-asset']
    return dst.collections[0]


def instancer(name, collection, location, parent_collection):
    empty = bpy.data.objects.new(name, None); empty.instance_type = 'COLLECTION'; empty.instance_collection = collection
    empty.location = location; empty['dcc_instance_id'] = name
    parent_collection.objects.link(empty)
    return empty


def scene(bench_id='bench'):
    reset()
    s = bpy.context.scene
    bench = bpy.data.collections.new('bench-asset')
    if bench_id:
        bench['dcc_asset_id'] = bench_id
    wood = material('bench-wood', (.24, .10, .035))
    box('bench.top', (0, 0, .85), (1.6, .6, .1), wood, bench)
    for side, x in (('left', -.7), ('right', .7)):
        box(f'bench.leg.{side}', (x, 0, .4), (.1, .5, .8), wood, bench)
    instancer('bench.a', bench, (0, 0, 0), s.collection)
    instancer('bench.b', bench, (3, 0, 0), s.collection)
    pair = bpy.data.collections.new('bench-pair'); pair['dcc_asset_id'] = 'bench-pair'
    instancer('pair.member.0', bench, (0, 0, 0), pair)
    instancer('pair.member.1', bench, (0, 1.5, 0), pair)
    instancer('set.a', pair, (0, 6, 0), s.collection)
    crate = link(out / 'lib/crate-v1.blend')
    instancer('crate.a', crate, (5, 0, 0), s.collection)
    mesh = bpy.data.meshes.new('ground')
    mesh.from_pydata([(-3, -3, 0), (8, -3, 0), (8, 10, 0), (-3, 10, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new('ground', mesh); s.collection.objects.link(ground)
    ground['dcc_instance_id'] = 'ground'; ground['dcc_asset_id'] = 'ground'; mesh.materials.append(material('stone', (.2, .2, .2), 'stone'))
    bpy.ops.object.camera_add(location=(10, -12, 8)); bpy.context.object['dcc_instance_id'] = 'review.camera'
    s.camera = bpy.context.object
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10)); bpy.context.object['dcc_instance_id'] = 'light.sun'
    return s


def save(name):
    bpy.ops.wm.save_as_mainfile(filepath=str(out / name))


if a.action == 'edit-library':
    library(out / 'lib/crate-v1.blend', 0.9)
    sys.exit(0)

out.mkdir(parents=True, exist_ok=False)
library(out / 'lib/crate-v1.blend', 0.5)
library(out / 'lib/crate-v2.blend', 0.7)
library(out / 'lib/vanishing.blend', 0.4)
scene(); save('scene.blend')
bpy.data.objects['bench.a'].location.x += .5; save('moved-a.blend')
bpy.data.objects['bench.b'].location.x += .5; save('moved-ab.blend')
scene(); bpy.data.objects['bench.a'].location.x += .5
bpy.data.objects['crate.a'].instance_collection = link(out / 'lib/crate-v2.blend'); save('swapped.blend')
scene(bench_id=None); save('no-asset-id.blend')
scene()
bpy.ops.mesh.primitive_plane_add(size=1); host = bpy.context.object
host.name = 'scatter'; host['dcc_instance_id'] = 'scatter'; host['dcc_asset_id'] = 'scatter'; host.instance_type = 'VERTS'
save('verts.blend')
scene()
crate = bpy.data.objects['crate.a'].instance_collection
crate.override_hierarchy_create(bpy.context.scene, bpy.context.view_layer)
save('override.blend')
scene()
instancer('vanish.a', link(out / 'lib/vanishing.blend'), (6, 0, 0), bpy.context.scene.collection)
save('missing-library.blend')
print('DCC_INSTANCE_SCENES built')
