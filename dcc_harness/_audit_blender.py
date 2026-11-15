"""Private fresh-process worker for audit.py; never run in an artist editor and never saves.

Measures geometry defects on the evaluated, render-visible meshes of a saved file, in world space:
winding and closure per connected island, degenerate faces, object scale, faces on empty material
slots, coplanar overlapping faces between islands, islands that touch nothing, and two material
graph facts (an image used only as data but tagged sRGB, an image mapped by UV on a mesh without
UVs). It records numbers only; audit.py turns them into findings for a profile.
"""
import fnmatch
from pathlib import Path
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
from dcc_harness.evidence import file_hash, read_json, write_json
from dcc_harness.visibility_blender import _included_objects

COINCIDENT = 5e-5    # of the bounding diagonal: two planes closer than this are one plane
CONTACT = 1e-3       # of the bounding diagonal: surfaces closer than this touch
COINCIDENT_CAP, CONTACT_CAP = 0.0005, 0.005   # metres
ZERO_SIDE = 1e-6     # of the bounding diagonal: a face smaller than this squared has no area
ISLAND_LIMIT = 2000  # an object with more islands is treated as one part by the contact check
QUERY_BUDGET = 3_000_000   # nearest-surface queries
PAIR_BUDGET = 20_000       # coplanar island pairs rasterized
CLUSTER_LIMIT = 3000       # islands on one plane
RASTER = 32
EXAMPLES = 5
DATA_SINKS = {('ShaderNodeNormalMap', 'Color'), ('ShaderNodeBump', 'Height'), ('ShaderNodeDisplacement', 'Height'),
              ('ShaderNodeVectorDisplacement', 'Vector')}
PASS_THROUGH = {'NodeReroute', 'ShaderNodeSeparateColor', 'ShaderNodeSeparateRGB', 'ShaderNodeSeparateXYZ', 'ShaderNodeMath',
                'ShaderNodeVectorMath', 'ShaderNodeInvert', 'ShaderNodeMapRange', 'ShaderNodeClamp', 'ShaderNodeRGBToBW'}
UV_SOURCES = {('ShaderNodeTexCoord', 'UV'), ('ShaderNodeUVMap', 'UV')}


def load(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        def ints(collection, attribute, width=1):
            data = np.empty(len(collection) * width, dtype=np.int64)
            if len(collection):
                collection.foreach_get(attribute, data)
            return data
        co = np.empty(len(mesh.vertices) * 3)
        if len(mesh.vertices):
            mesh.vertices.foreach_get('co', co)
        matrix = np.array(evaluated.matrix_world)
        mesh.calc_loop_triangles()
        iid = obj.get('dcc_instance_id')
        return {'name': obj.name, 'id': iid if isinstance(iid, str) and iid else None, 'matrix': matrix,
                'world': co.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3],
                'edges': ints(mesh.edges, 'vertices', 2).reshape(-1, 2),
                'loop_vertex': ints(mesh.loops, 'vertex_index'), 'loop_edge': ints(mesh.loops, 'edge_index'),
                'loop_start': ints(mesh.polygons, 'loop_start'), 'loop_total': ints(mesh.polygons, 'loop_total'),
                'material_index': ints(mesh.polygons, 'material_index'),
                'tri': ints(mesh.loop_triangles, 'vertices', 3).reshape(-1, 3), 'tri_face': ints(mesh.loop_triangles, 'polygon_index'),
                'uv_layers': len(mesh.uv_layers),
                'slots': [slot.material.name if slot.material else None for slot in evaluated.material_slots]}
    finally:
        evaluated.to_mesh_clear()


def components(count, a, b):
    """Connected-component label per vertex: hook each edge's roots to the lower one, then compress."""
    label = np.arange(count, dtype=np.int64)
    while len(a):
        before = label
        label = label.copy()
        ra, rb = label[a], label[b]
        low = np.minimum(ra, rb)
        np.minimum.at(label, ra, low)
        np.minimum.at(label, rb, low)
        while True:
            jumped = label[label]
            if np.array_equal(jumped, label):
                break
            label = jumped
        if np.array_equal(label, before):
            break
    return label


def analyse(m, sizes):
    """One object's own measurements, plus the arrays the scene-wide checks need."""
    world, edges = m['world'], m['edges']
    vertices, faces, edge_count = len(world), len(m['loop_start']), len(edges)
    linear = m['matrix'][:3, :3]
    mirrored = bool(np.linalg.det(linear) < 0)
    # Blender renders a mirrored object with its winding reversed, so judge normals as it draws them.
    flip = -1.0 if mirrored else 1.0
    follow = np.arange(len(m['loop_vertex'])) + 1
    if faces:
        follow[m['loop_start'] + m['loop_total'] - 1] = m['loop_start']
    a, b = m['loop_vertex'], m['loop_vertex'][follow] if faces else m['loop_vertex']
    uses = np.bincount(m['loop_edge'], minlength=edge_count)
    forward = np.bincount(m['loop_edge'], weights=(a < b), minlength=edge_count)
    # Two faces sharing an edge agree on which way is out exactly when they cross it in opposite directions.
    inconsistent = (uses == 2) & (forward != 1)
    label = np.unique(components(vertices, edges[:, 0], edges[:, 1]), return_inverse=True)[1].reshape(-1) if vertices else np.zeros(0, np.int64)
    islands = int(label.max()) + 1 if vertices else 0
    edge_island, tri_island = label[edges[:, 0]], label[m['tri'][:, 0]]
    faces_per = np.bincount(label[m['loop_vertex'][m['loop_start']]], minlength=islands) if faces else np.zeros(islands, np.int64)
    mixed = np.bincount(edge_island, weights=inconsistent, minlength=islands)
    closed = (faces_per > 0) & (np.bincount(edge_island, weights=(uses != 2), minlength=islands) == 0)
    P = world[m['tri']]
    cross = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]) * flip
    area = 0.5 * np.linalg.norm(cross, axis=1)
    Q = P - (world.mean(axis=0) if vertices else 0.0)
    volume = np.bincount(tri_island, weights=np.einsum('ij,ij->i', Q[:, 0], np.cross(Q[:, 1], Q[:, 2])), minlength=islands) / 6 * flip
    inward_closed = closed & (mixed == 0) & (volume < -sizes['volume'])
    # Open islands have no inside. Compare each face's direction with the direction from the island's
    # centre instead: an estimate from the island's shape, never proof.
    unit = cross / np.maximum(2 * area, 1e-300)[:, None]
    middle = P.mean(axis=1)
    island_area = np.bincount(tri_island, weights=area, minlength=islands)
    centre = np.stack([np.bincount(tri_island, weights=area * middle[:, d], minlength=islands) for d in range(3)], 1) \
        / np.maximum(island_area, 1e-300)[:, None]
    lean = np.einsum('ij,ij->i', unit, middle - centre[tri_island]) * area
    outward = np.bincount(tri_island, weights=lean, minlength=islands)
    weight = np.bincount(tri_island, weights=np.abs(lean), minlength=islands)
    inward_open = (faces_per >= 4) & ~closed & (mixed == 0) & (weight > 1e-3 * island_area * sizes['diagonal']) \
        & (outward < -0.5 * weight)
    empty = [i for i, name in enumerate(m['slots']) if name is None]
    used = sorted({m['slots'][i] for i in np.unique(m['material_index']).tolist() if i < len(m['slots']) and m['slots'][i]})
    lo, hi = np.full((islands, 3), np.inf), np.full((islands, 3), -np.inf)
    np.minimum.at(lo, label, world)
    np.maximum.at(hi, label, world)
    record = {
        'id': m['id'], 'faces': faces, 'triangles': len(P), 'islands': int((faces_per > 0).sum()), 'closed_islands': int(closed.sum()),
        'scale': [round(float(s), 6) for s in np.linalg.norm(linear, axis=0)], 'mirrored': mirrored,
        'inconsistent_edges': int(inconsistent.sum()),
        'inward_closed_islands': int(inward_closed.sum()), 'inward_closed_faces': int(faces_per[inward_closed].sum()),
        'inward_open_islands': int(inward_open.sum()), 'inward_open_faces': int(faces_per[inward_open].sum()),
        'boundary_edges': int((uses == 1).sum()), 'nonmanifold_edges': int((uses > 2).sum()), 'loose_edges': int((uses == 0).sum()),
        'loose_vertices': vertices - len(np.unique(edges)),
        'zero_area_faces': int((np.bincount(m['tri_face'], weights=area, minlength=faces) <= sizes['zero_area']).sum()),
        'empty_slots': empty, 'empty_slot_faces': int(np.isin(m['material_index'], empty).sum()),
        'uv_layers': m['uv_layers'], 'materials': used}
    sealed = (faces_per > 0) & (np.bincount(edge_island, weights=(uses == 1), minlength=islands) == 0)
    keep = area > sizes['zero_area']
    # An inside-out closed part is reported once; for the plane check, read its faces the way they were meant.
    facing = unit * np.where(inward_closed[tri_island], -1.0, 1.0)[:, None]
    return record, {'world': world, 'tri': m['tri'], 'label': label, 'tri_island': tri_island, 'faces_per': faces_per, 'sealed': sealed,
                    'lo': lo, 'hi': hi, 'P': P[keep], 'unit': facing[keep], 'plane_island': tri_island[keep]}


def inside(triangles, px, py):
    """For each sample point: is it strictly inside any of these 2D triangles?"""
    hit = np.zeros(len(px), dtype=bool)
    for start in range(0, len(triangles), 2048):
        t = triangles[start:start + 2048, :, :, None]
        ax, ay, bx, by, cx, cy = t[:, 0, 0], t[:, 0, 1], t[:, 1, 0], t[:, 1, 1], t[:, 2, 0], t[:, 2, 1]
        d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
        d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
        d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)
        hit |= (((d1 > 0) & (d2 > 0) & (d3 > 0)) | ((d1 < 0) & (d2 < 0) & (d3 < 0))).any(axis=0)
    return hit


def coincident(parts, sizes):
    """Coplanar faces of different islands that overlap, by rasterizing each pair over its shared region."""
    offsets = np.cumsum([0] + [len(p['faces_per']) for p in parts])
    P = np.concatenate([p['P'] for p in parts])
    unit = np.concatenate([p['unit'] for p in parts])
    island = np.concatenate([p['plane_island'] + offsets[i] for i, p in enumerate(parts)])
    sealed = np.concatenate([p['sealed'] for p in parts])
    owner = np.repeat(np.arange(len(parts)), [len(p['faces_per']) for p in parts])
    count = len(P)
    found, state = {}, {'pairs': 0, 'complete': True}
    if count < 2:
        return [], True
    # One representative direction per plane, whichever way its faces point.
    first = np.argmax(np.abs(unit) > 1e-6, axis=1)
    sign = np.sign(unit[np.arange(count), first])
    sign[sign == 0] = 1
    canon = unit * sign[:, None]
    key = np.round(canon, 3) + 0.0
    depth = np.einsum('ij,ij->i', canon, P[:, 0])
    order = np.lexsort((depth, key[:, 2], key[:, 1], key[:, 0]))
    k, d = key[order], depth[order]
    start = np.ones(count, dtype=bool)
    start[1:] = (k[1:] != k[:-1]).any(axis=1) | (d[1:] - d[:-1] > sizes['coincident'])
    cluster = np.cumsum(start) - 1
    pairs = np.unique(cluster * (int(island.max()) + 1) + island[order])
    crowded = np.bincount(pairs // (int(island.max()) + 1)) >= 2
    chosen = np.nonzero(crowded[cluster])[0]
    for group in np.split(chosen, np.nonzero(np.diff(cluster[chosen]))[0] + 1) if len(chosen) else []:
        index = order[group]
        normal = canon[index[0]]
        axis = np.eye(3)[np.argmin(np.abs(normal))]
        u = np.cross(normal, axis); u /= np.linalg.norm(u)
        flat = np.stack([P[index] @ u, P[index] @ np.cross(normal, u)], axis=-1)
        units, member = np.unique(island[index] * 2 + (sign[index] > 0), return_inverse=True)
        member = member.reshape(-1)
        if len(units) > CLUSTER_LIMIT:
            state['complete'] = False
            continue
        lo, hi = np.full((len(units), 2), np.inf), np.full((len(units), 2), -np.inf)
        np.minimum.at(lo, member, flat.min(axis=1))
        np.maximum.at(hi, member, flat.max(axis=1))
        shared = np.minimum(hi[:, None], hi[None]) - np.maximum(lo[:, None], lo[None])
        for i, j in zip(*np.nonzero(np.triu((shared > sizes['min_side']).all(axis=2), 1))):
            one, two = int(units[i]) // 2, int(units[j]) // 2
            same = units[i] % 2 == units[j] % 2
            # Opposed faces of two parts without open edges are a hidden contact, such as a box standing on a floor.
            if one == two or (not same and sealed[one] and sealed[two]):
                continue
            if state['pairs'] >= PAIR_BUDGET:
                state['complete'] = False
                break
            state['pairs'] += 1
            a, b = index[member == i], index[member == j]
            anchor = a[np.argmax(np.linalg.norm(np.cross(P[a, 1] - P[a, 0], P[a, 2] - P[a, 0]), axis=1))]
            plane, level = canon[anchor], canon[anchor] @ P[anchor, 0]
            a = a[(np.abs(P[a] @ plane - level) <= sizes['coincident']).all(axis=1)]
            b = b[(np.abs(P[b] @ plane - level) <= sizes['coincident']).all(axis=1)]
            low, high = np.maximum(lo[i], lo[j]), np.minimum(hi[i], hi[j])
            cell = (high - low) / RASTER
            # Sample off-centre, differently on each axis, so a face diagonal through the region does not swallow a row of samples.
            gx, gy = np.meshgrid(low[0] + (np.arange(RASTER) + 0.37) * cell[0], low[1] + (np.arange(RASTER) + 0.61) * cell[1], indexing='ij')
            px, py = gx.reshape(-1), gy.reshape(-1)
            both = inside(np.stack([P[a] @ u, P[a] @ np.cross(normal, u)], -1), px, py) \
                & inside(np.stack([P[b] @ u, P[b] @ np.cross(normal, u)], -1), px, py)
            overlap = float(both.sum() * cell[0] * cell[1])
            if overlap < sizes['min_side'] ** 2:
                continue
            at = np.nonzero(both)[0][0]
            point = px[at] * u + py[at] * np.cross(normal, u) + level * plane
            names = tuple(sorted((int(owner[one]), int(owner[two]))))
            entry = found.setdefault((names, bool(same)), {'area': 0.0, 'planes': 0, 'point': [round(float(c), 6) for c in point]})
            entry['area'] += overlap
            entry['planes'] += 1
    return [{'objects': list(names), 'facing': 'same' if same else 'opposed', **entry} for (names, same), entry in sorted(found.items())], \
        state['complete']


def floating(parts, sizes):
    """Parts (islands, or whole objects past the island limit) with no other surface within the contact distance."""
    reach, budget = sizes['contact'], {'left': QUERY_BUDGET}
    unit_object, unit_island, unit_of = [], [], []
    for o, p in enumerate(parts):
        with_faces = np.nonzero(p['faces_per'] > 0)[0]
        whole = len(with_faces) > ISLAND_LIMIT
        mapping = np.full(len(p['faces_per']), -1, dtype=np.int64)
        if whole and len(with_faces):
            mapping[with_faces] = len(unit_object)
            unit_object.append(o); unit_island.append(-1)
        else:
            mapping[with_faces] = len(unit_object) + np.arange(len(with_faces))
            unit_object += [o] * len(with_faces); unit_island += with_faces.tolist()
        unit_of.append(mapping)
        p['whole'] = whole
    total = len(unit_object)
    if total < 2:
        return None, True
    object_lo = np.array([p['world'].min(axis=0) if len(p['world']) else [np.inf] * 3 for p in parts]) - reach
    object_hi = np.array([p['world'].max(axis=0) if len(p['world']) else [-np.inf] * 3 for p in parts]) + reach
    unit_lo = np.array([parts[o]['lo'][parts[o]['faces_per'] > 0].min(axis=0) if i < 0 else parts[o]['lo'][i] for o, i in zip(unit_object, unit_island)])
    unit_hi = np.array([parts[o]['hi'][parts[o]['faces_per'] > 0].max(axis=0) if i < 0 else parts[o]['hi'][i] for o, i in zip(unit_object, unit_island)])
    units_in = np.bincount(unit_object, minlength=len(parts))
    trees = {}

    def tree(o):
        if o not in trees:
            trees[o] = BVHTree.FromPolygons(parts[o]['world'].tolist(), parts[o]['tri'].tolist(), all_triangles=True)
        return trees[o]

    def spend():
        budget['left'] -= 1
        return budget['left'] >= 0

    def mine(o, i, triangle):
        return i < 0 or parts[o]['tri_island'][triangle] == i

    def candidates(u):
        o = unit_object[u]
        near = np.nonzero(((object_lo <= unit_hi[u]) & (object_hi >= unit_lo[u])).all(axis=1))[0]
        return [int(p) for p in near if p != o or units_in[o] > 1]

    touched = np.zeros(total, dtype=bool)
    unknown = np.zeros(total, dtype=bool)
    # First from each part's own vertices to other surfaces; a hit settles both parts.
    for u in range(total):
        if touched[u]:
            continue
        o, i = unit_object[u], unit_island[u]
        points = parts[o]['world'] if i < 0 else parts[o]['world'][parts[o]['label'] == i]
        for p in candidates(u):
            if p == o:
                others = np.nonzero((parts[o]['faces_per'] > 0) & (np.arange(len(parts[o]['faces_per'])) != i))[0]
                near = np.zeros(len(points), dtype=bool)
                for begin in range(0, len(others), 512):
                    block = others[begin:begin + 512]
                    near |= ((points[:, None] >= parts[o]['lo'][block] - reach) & (points[:, None] <= parts[o]['hi'][block] + reach)).all(axis=2).any(axis=1)
            else:
                near = ((points >= object_lo[p]) & (points <= object_hi[p])).all(axis=1)
            for point in points[near].tolist():
                if not spend():
                    unknown[u] = True
                    break
                if p == o:
                    hit = next((t for _, _, t, _ in tree(o).find_nearest_range(point, reach) if not mine(o, i, t)), None)
                else:
                    hit = tree(p).find_nearest(point, reach)[2]
                if hit is not None:
                    touched[u] = touched[unit_of[p][parts[p]['tri_island'][hit]]] = True
                    break
            if touched[u] or unknown[u]:
                break
    # Then the other way round, and by intersection, for the parts still unsettled: a large flat
    # face has no vertex near the small part standing on it.
    for u in np.nonzero(~touched & ~unknown)[0]:
        o, i = unit_object[u], unit_island[u]
        own = BVHTree.FromPolygons(parts[o]['world'].tolist(), parts[o]['tri'][parts[o]['tri_island'] == i].tolist(), all_triangles=True) \
            if i >= 0 else tree(o)
        for p in candidates(u):
            points = parts[p]['world']
            near = ((points >= unit_lo[u] - reach) & (points <= unit_hi[u] + reach)).all(axis=1)
            if p == o:
                near &= parts[o]['label'] != i
            for point in points[near].tolist():
                if not spend():
                    unknown[u] = True
                    break
                if own.find_nearest(point, reach)[2] is not None:
                    touched[u] = True
                    break
            if not touched[u] and not unknown[u]:
                touched[u] = any(p != o or not mine(o, i, other) for _, other in own.overlap(tree(p)))
            if touched[u] or unknown[u]:
                break
    # A part that touches nothing is floating, except the largest: something has to be the body.
    span = np.linalg.norm(unit_hi - unit_lo, axis=1)
    alone = ~touched & ~unknown
    alone[int(np.argmax(span))] = False
    result = {}
    for o, p in enumerate(parts):
        mine_units = np.nonzero(np.array(unit_object) == o)[0]
        if not len(mine_units):
            continue
        adrift = mine_units[alone[mine_units]]
        result[o] = {'parts': len(mine_units), 'floating': len(adrift), 'unmeasured': int(unknown[mine_units].sum()), 'islands_as_one': p['whole'],
                     'examples': [{'faces': int(p['faces_per'].sum() if unit_island[u] < 0 else p['faces_per'][unit_island[u]]),
                                   'centre': [round(float(c), 6) for c in (unit_lo[u] + unit_hi[u]) / 2],
                                   'size': [round(float(c), 6) for c in unit_hi[u] - unit_lo[u]]} for u in adrift[:EXAMPLES]]}
    return result, not unknown.any()


def material_facts(material):
    """Images that feed only data inputs yet are tagged sRGB, and whether any image is mapped by UV."""
    tree = material.node_tree if material.use_nodes else None
    facts = {'data_srgb': [], 'uses_uv': False}
    if tree is None:
        return facts
    for node in tree.nodes:
        if node.bl_idname != 'ShaderNodeTexImage' or node.image is None:
            continue
        vector = node.inputs['Vector']
        seen, queue, by_uv = set(), [link.from_socket for link in vector.links], not vector.is_linked
        while queue:
            socket = queue.pop()
            if (socket.node.name, socket.identifier) in seen:
                continue
            seen.add((socket.node.name, socket.identifier))
            if (socket.node.bl_idname, socket.name) in UV_SOURCES:
                by_uv = True
            queue += [link.from_socket for entry in socket.node.inputs for link in entry.links]
        facts['uses_uv'] = facts['uses_uv'] or by_uv
        sinks, colour, seen, queue = [], False, set(), [link.to_socket for link in node.outputs['Color'].links]
        while queue:
            socket = queue.pop()
            target = socket.node
            if (target.name, socket.identifier) in seen:
                continue
            seen.add((target.name, socket.identifier))
            if (target.bl_idname, socket.name) in DATA_SINKS:
                sinks.append(f'{target.name}.{socket.name}')
            elif any(out.type == 'SHADER' for out in target.outputs) or target.bl_idname.startswith('ShaderNodeOutput'):
                if socket.type in ('VALUE', 'VECTOR'):
                    sinks.append(f'{target.name}.{socket.name}')
                else:
                    colour = True
            elif target.bl_idname in PASS_THROUGH:
                queue += [link.to_socket for out in target.outputs for link in out.links]
            else:
                colour = True   # a mix, ramp or group: the use is not known to be data, so say nothing
        if sinks and not colour and node.image.colorspace_settings.name == 'sRGB':
            facts['data_srgb'].append({'node': node.name, 'image': node.image.name, 'colorspace': 'sRGB', 'feeds': sorted(sinks)})
    return facts


def main():
    if not bpy.app.background:
        raise RuntimeError('Audit requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'measure':
        raise ValueError('Unknown audit worker action')
    request = read_json(request_path)
    source = request['source']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    scene = bpy.context.scene
    unit_scale = scene.unit_settings.scale_length
    if not unit_scale > 0:
        raise ValueError(f'Unsupported scene unit scale: {unit_scale}')
    included = _included_objects(scene)
    ids = [o.get('dcc_instance_id') for o in included if isinstance(o.get('dcc_instance_id'), str) and o.get('dcc_instance_id')]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError('Duplicate dcc_instance_id, so a finding could name the wrong object: ' + ', '.join(duplicates))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = [load(o, depsgraph) for o in included if o.type == 'MESH']
    meshes = [m for m in meshes if len(m['world'])]
    select = request.get('select')
    chosen = [m for m in meshes if select is None or fnmatch.fnmatchcase(m['id'] or m['name'], select)]
    if not chosen:
        raise ValueError('No render-visible mesh with vertices' + (f' matches {select}' if select else ''))
    points = np.concatenate([m['world'] for m in chosen])
    diagonal = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    if not diagonal > 0 or not np.isfinite(diagonal):
        raise ValueError('The audited meshes have no finite extent')
    # Scaled to the asset, and capped so that a whole scene is not judged more loosely than one prop.
    same_plane = min(COINCIDENT * diagonal, COINCIDENT_CAP / unit_scale)
    sizes = {'diagonal': diagonal, 'coincident': same_plane, 'min_side': 10 * same_plane, 'contact': min(CONTACT * diagonal, CONTACT_CAP / unit_scale),
             'zero_area': (ZERO_SIDE * diagonal) ** 2, 'volume': (ZERO_SIDE * diagonal) ** 3}
    objects, parts = {}, []
    for m in meshes:
        objects[m['name']], part = analyse(m, sizes)
        parts.append(part)
    names = [m['name'] for m in meshes]
    overlaps, overlaps_complete = coincident(parts, sizes)
    adrift, contact_complete = floating(parts, sizes)
    for o, name in enumerate(names):
        objects[name]['contact'] = adrift.get(o) if adrift is not None else None
    materials = {name: material_facts(bpy.data.materials[name]) for name in sorted({n for record in objects.values() for n in record['materials']})}
    skipped = {}
    for obj in included:
        if obj.type in ('CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME', 'POINTCLOUD', 'CURVES'):
            skipped[obj.type] = skipped.get(obj.type, 0) + 1
    write_json(Path(request['out']) / 'measurement.json', {
        'schema': 'dcc.audit.measurement.v1', 'checkpoint_sha256': source['sha256'], 'select': select, 'unit_scale': unit_scale,
        'sizes': {key: value * unit_scale ** {'zero_area': 2, 'volume': 3}.get(key, 1) for key, value in sizes.items()},
        'objects': objects, 'materials': materials,
        'coincident': [{**entry, 'objects': [names[i] for i in entry['objects']], 'area': round(entry['area'] * unit_scale ** 2, 9),
                        'same_material': objects[names[entry['objects'][0]]]['materials'] == objects[names[entry['objects'][1]]]['materials']}
                       for entry in overlaps],
        'complete': {'coincident': overlaps_complete, 'contact': contact_complete, 'contact_measured': adrift is not None},
        'not_audited': skipped})


main()
