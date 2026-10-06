"""Create disposable adoption fixtures, or compare native content without identity metadata."""
import argparse
from pathlib import Path
import sys
import shutil

import bpy

p = argparse.ArgumentParser()
p.add_argument('action', choices=['fixtures', 'snapshot'])
p.add_argument('--runtime', required=True)
p.add_argument('--out', required=True)
p.add_argument('--source')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.runtime)
from dcc_harness.evidence import write_json

out = Path(a.out)
if a.action == 'snapshot':
    bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False)
    objects = {}
    for o in bpy.context.scene.objects:
        rec = {'matrix': [list(row) for row in o.matrix_world], 'type': o.type,
               'parent': o.parent.name if o.parent else None,
               'hidden': [o.hide_render, o.hide_viewport, o.hide_get()],
               'slots': [s.material.name if s.material else None for s in o.material_slots],
               'collections': sorted(c.name for c in o.users_collection),
               'artist_note': o.get('artist_note')}
        if o.type == 'MESH':
            rec.update(data=o.data.name, vertices=[list(v.co) for v in o.data.vertices],
                       faces=[list(poly.vertices) for poly in o.data.polygons],
                       uv={layer.name: [list(loop.uv) for loop in layer.data] for layer in o.data.uv_layers},
                       modifiers=[(m.name, m.type) for m in o.modifiers])
        if o.type == 'CAMERA':
            rec['lens'] = o.data.lens
        if o.type == 'LIGHT':
            rec['light'] = [o.data.energy, list(o.data.color)]
        objects[o.name] = rec
    mats = {m.name: {'roughness': m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value,
                     'color': list(m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)}
            for m in bpy.data.materials if m.use_nodes and m.node_tree.nodes.get('Principled BSDF')}
    write_json(out, {'objects': objects, 'materials': mats,
                     'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None})
else:
    out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    original = bpy.context.object
    original.name = 'ArtistCube'
    original['dcc_instance_id'] = 'artist.cube'
    original['dcc_asset_id'] = 'artist.shared-cube'
    original['artist_note'] = 'Keep the bevel and physical scale'
    original.modifiers.new('ArtistBevel', 'BEVEL').width = .08
    mat = bpy.data.materials.new('ArtistMaterial')
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .63
    original.data.materials.append(mat)
    linked = bpy.data.objects.new('LinkedCube', original.data)
    bpy.context.scene.collection.objects.link(linked)
    linked.location.x = 3
    linked.hide_render = True
    linked.parent = original
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, location=(-3, 0, 1))
    bpy.context.object.name = 'SeparateSphere'
    bpy.ops.object.camera_add(location=(7, -7, 5))
    bpy.context.scene.camera = bpy.context.object
    bpy.ops.object.light_add(type='AREA', location=(1, -2, 5))
    bpy.context.object.data.energy = 125
    base = out / 'base.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(base))
    library = out / 'library.blend'
    shutil.copyfile(base, library)
    for case in ('duplicate-instance', 'duplicate-material', 'invalid-id', 'ambiguous-asset',
                 'shared-object', 'shared-material', 'shared-material-object', 'node-material-user',
                 'linked-object', 'unsupported-instance'):
        bpy.ops.wm.open_mainfile(filepath=str(base), load_ui=False)
        original = bpy.data.objects['ArtistCube']
        linked = bpy.data.objects['LinkedCube']
        if case == 'duplicate-instance':
            linked['dcc_instance_id'] = original['dcc_instance_id']
        elif case == 'duplicate-material':
            mat = bpy.data.materials['ArtistMaterial']
            mat['dcc_material_id'] = 'duplicated'
            second = mat.copy()
            bpy.data.objects['SeparateSphere'].data.materials.append(second)
        elif case == 'invalid-id':
            linked['dcc_instance_id'] = ''
        elif case == 'ambiguous-asset':
            another = bpy.data.objects.new('Ambiguous', original.data)
            bpy.context.scene.collection.objects.link(another)
            another['dcc_asset_id'] = 'conflicting-asset'
        elif case == 'shared-object':
            bpy.data.scenes.new('Outside').collection.objects.link(linked)
        elif case == 'shared-material':
            another = bpy.data.objects.new('Outside', bpy.data.objects['SeparateSphere'].data.copy())
            bpy.data.scenes.new('Outside').collection.objects.link(another)
            another.data.materials.append(bpy.data.materials['ArtistMaterial'])
        elif case == 'shared-material-object':
            # Object already has complete IDs; only its shared material would be edited.
            bpy.data.scenes.new('Outside').collection.objects.link(original)
        elif case == 'node-material-user':
            tree = bpy.data.node_groups.new('UnscopedNodeTree', 'GeometryNodeTree')
            tree.use_fake_user = True
            tree.nodes.new('GeometryNodeSetMaterial').inputs['Material'].default_value = bpy.data.materials['ArtistMaterial']
        elif case == 'linked-object':
            with bpy.data.libraries.load(str(library), link=True) as (available, selected):
                selected.objects = ['SeparateSphere']
            bpy.context.scene.collection.objects.link(selected.objects[0])
        else:
            empty = bpy.data.objects.new('CollectionInstance', None)
            bpy.context.scene.collection.objects.link(empty)
            empty.instance_type = 'COLLECTION'
            empty.instance_collection = bpy.data.collections.new('UnsupportedCollection')
        bpy.ops.wm.save_as_mainfile(filepath=str(out / (case + '.blend')))
    print('ADOPTION_FIXTURES_READY')
