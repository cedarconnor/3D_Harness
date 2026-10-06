"""Blender consumer for the bounded broadleaf study recipe.

Creates only new meshes/materials in a supplied collection. It does not place,
journal, save, or certify them. Call through the normal reserved edit workflow.
"""
import math
from .vegetation import leaf_surface, shrub_structure


def leaf_materials(prefix='site.broadleaf.v1'):
    import bpy
    ids = [prefix + '.' + str(i) for i in range(4)]
    if any(m.get('dcc_material_id') in ids for m in bpy.data.materials):
        raise ValueError('Material identities already exist; explicitly reuse their actual users')
    result = []
    for i, mid in enumerate(ids):
        mat = bpy.data.materials.new(mid); mat['dcc_material_id'] = mid; mat.use_nodes = True
        tree = mat.node_tree; tree.nodes.clear()
        output = tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Roughness'].default_value = .43 + i*.025
        bsdf.inputs['IOR'].default_value = 1.4
        uv = tree.nodes.new('ShaderNodeTexCoord')
        noise = tree.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 7
        tree.links.new(uv.outputs['UV'], noise.inputs['Vector'])
        ramp = tree.nodes.new('ShaderNodeValToRGB')
        f = .86 + i*.10
        ramp.color_ramp.elements[0].position = .15
        ramp.color_ramp.elements[0].color = (.018*f, .045*f, .007*f, 1)
        ramp.color_ramp.elements[1].position = .85
        ramp.color_ramp.elements[1].color = (.065*f, .125*f, .019*f, 1)
        tree.links.new(noise.outputs['Fac'], ramp.inputs[0]); tree.links.new(ramp.outputs[0], bsdf.inputs['Base Color'])
        # Subtle central rib in leaf-local UV coordinates, independent of size.
        separate = tree.nodes.new('ShaderNodeSeparateXYZ'); tree.links.new(uv.outputs['UV'], separate.inputs[0])
        subtract = tree.nodes.new('ShaderNodeMath'); subtract.operation = 'SUBTRACT'; subtract.inputs[1].default_value = .5
        absolute = tree.nodes.new('ShaderNodeMath'); absolute.operation = 'ABSOLUTE'
        rib = tree.nodes.new('ShaderNodeMath'); rib.operation = 'LESS_THAN'; rib.inputs[1].default_value = .018
        tree.links.new(separate.outputs['X'], subtract.inputs[0]); tree.links.new(subtract.outputs[0], absolute.inputs[0]); tree.links.new(absolute.outputs[0], rib.inputs[0])
        bump = tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .16; bump.inputs['Distance'].default_value = .0003
        tree.links.new(rib.outputs[0], bump.inputs['Height']); tree.links.new(bump.outputs[0], bsdf.inputs['Normal'])
        translucent = tree.nodes.new('ShaderNodeBsdfTranslucent'); tree.links.new(ramp.outputs[0], translucent.inputs['Color'])
        mix = tree.nodes.new('ShaderNodeMixShader'); mix.inputs[0].default_value = .16
        tree.links.new(bsdf.outputs[0], mix.inputs[1]); tree.links.new(translucent.outputs[0], mix.inputs[2]); tree.links.new(mix.outputs[0], output.inputs[0])
        result.append(mat)
    return result


def build_shrub(collection, prefix, bark, foliage, *, seed=41, height=1.2, leaf_scale=1.0):
    """Return (wood, leaves, receipt) at local origin, ready for placement.

    Meshes contain disconnected intersecting stem tubes and open leaf surfaces.
    Parenting describes intended growth connectivity; no welded topology,
    species accuracy, self-collision or simulation-readiness is claimed.
    """
    import bpy
    from mathutils import Vector
    ids = [prefix + '.wood', prefix + '.leaves']
    if len(foliage) != 4 or bark is None or any(m is None for m in foliage):
        raise ValueError('Supply bark and four actual foliage materials')
    if any(o.get('dcc_instance_id') in ids for o in bpy.data.objects):
        raise ValueError('Object identity already exists')
    structure = shrub_structure(seed, height, leaf_scale=leaf_scale)
    verts, faces = [], []
    for stem in structure['stems']:
        a, b = Vector(stem['start']), Vector(stem['end']); direction = (b-a).normalized()
        u = direction.cross(Vector((0, 0, 1)))
        if u.length < .01: u = direction.cross(Vector((0, 1, 0)))
        u.normalize(); v = direction.cross(u)
        sides = 3 if stem['kind'] == 'petiole' else 7
        offset = len(verts)
        for center, radius in ((a, stem['radius']), (b, stem['end_radius'])):
            verts.extend([tuple(center + radius*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides))) for i in range(sides)])
        faces.extend([tuple(offset+i for i in reversed(range(sides))), tuple(offset+sides+i for i in range(sides))])
        faces.extend([(offset+i, offset+(i+1)%sides, offset+(i+1)%sides+sides, offset+i+sides) for i in range(sides)])

    def mesh_object(iid, vertices, polygons, materials):
        mesh = bpy.data.meshes.new(iid+'.mesh'); mesh.from_pydata(vertices, [], polygons); mesh.update()
        obj = bpy.data.objects.new(iid, mesh); collection.objects.link(obj)
        obj['dcc_instance_id'] = iid; obj['dcc_asset_id'] = 'broadleaf-study.seed' + str(seed)
        for material in materials: mesh.materials.append(material)
        for poly in mesh.polygons: poly.use_smooth = True
        return obj

    wood = mesh_object(ids[0], verts, faces, [bark])
    verts, faces, uv_coords, shades, base_indices = [], [], [], [], []
    for leaf in structure['leaves']:
        mesh = leaf_surface(leaf['length'], leaf['width'], arch=leaf['arch'], droop=leaf['droop'])
        forward = Vector(leaf['direction']); right = forward.cross(Vector((0, 0, 1))).normalized(); normal = right.cross(forward)
        origin = Vector(leaf['base']); offset = len(verts); base_indices.append(offset)
        verts.extend([tuple(origin + right*x + forward*y + normal*z) for x, y, z in mesh['vertices']])
        faces.extend([tuple(offset+i for i in f) for f in mesh['faces']])
        uv_coords.extend(mesh['uvs']); shades.extend([leaf['shade']]*len(mesh['faces']))
    leaves = mesh_object(ids[1], verts, faces, foliage)
    uv = leaves.data.uv_layers.new(name='LeafUV')
    uv.data.foreach_set('uv', [x for loop in leaves.data.loops for x in uv_coords[loop.vertex_index]])
    leaves.data.polygons.foreach_set('material_index', shades)
    error = max((leaves.data.vertices[i].co - Vector(leaf['base'])).length for i, leaf in zip(base_indices, structure['leaves']))
    return wood, leaves, {'schema': 'dcc.shrub-mesh-receipt.v1', 'seed': seed, 'leader_height': height, 'leaf_scale': leaf_scale,
                          'leaves': len(structure['leaves']), 'stem_segments': len(structure['stems']),
                          'max_leaf_base_error_m': error, 'leaf_length_range_m': [min(l['length'] for l in structure['leaves']), max(l['length'] for l in structure['leaves'])],
                          'limits': 'Base positions checked against recipe; no manifold, botanical, collision or aesthetic certification.'}
