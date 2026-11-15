"""Private fresh-process worker for review_sheet.py; never run in an artist editor and never saves.

Copies the targets' evaluated geometry, in world space, into a temporary scene and renders a grid
of Workbench tiles, then joins them into one PNG. Everything it creates dies with the process.
"""
import colorsys
import fnmatch
import hashlib
import math
from pathlib import Path
import shutil
import sys

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
import numpy as np
from mathutils import Vector
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.review_sheet import encode_png
from dcc_harness.visibility_blender import _included_objects

KINDS = ('MESH', 'CURVE', 'SURFACE', 'FONT', 'META')
WIRE_BUDGET = 300_000   # faces; above this the wireframe row is left out and said so
GAP = 2                 # pixels between tiles
ELEVATION = 25.0
ORBIT = (30.0, 120.0, 210.0, 300.0)
BACKGROUND = {'silhouette': (1, 1, 1), 'clay': (0.19, 0.2, 0.22), 'wireframe': (0.38, 0.4, 0.43), 'backface': (0.19, 0.2, 0.22)}
GREY, WHITE, BLACK, RED = (0.62, 0.62, 0.62, 1), (0.92, 0.92, 0.92, 1), (0, 0, 0, 1), (0.9, 0.05, 0.05, 1)


def tint(name):
    """A stable, well-separated colour per object."""
    hue = int(hashlib.sha256(name.encode('utf-8')).hexdigest()[:8], 16) / 0xffffffff
    return (*colorsys.hsv_to_rgb(hue, 0.65, 0.9), 1.0)


def copy_geometry(scene, obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    if not len(mesh.polygons):
        bpy.data.meshes.remove(mesh)
        return None
    matrix = evaluated.matrix_world.copy()
    mesh.transform(matrix)
    if matrix.to_3x3().determinant() < 0:
        mesh.flip_normals()   # keep a mirrored object's faces the way Blender draws them
    mesh.update()

    def place(data, suffix):
        made = bpy.data.objects.new(f'dcc-sheet-{len(scene.objects)}-{suffix}', data)
        scene.collection.objects.link(made)
        return made
    reverse = mesh.copy()
    reverse.flip_normals()
    return {'front': place(mesh, 'front'), 'back': place(reverse, 'back'), 'mesh': mesh, 'faces': len(mesh.polygons)}


def look(camera, centre, radius, azimuth, elevation):
    a, e = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
    camera.location = centre + direction * radius * 4
    camera.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()


def read_tile(path, width, height, background):
    """A tile over a flat background. Blender versions disagree on where Workbench takes its background, so none is rendered."""
    image = bpy.data.images.load(str(path))
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    pixels = pixels.reshape(height, width, 4)[::-1]
    alpha = pixels[:, :, 3:]
    return ((pixels[:, :, :3] * alpha + np.array(background, dtype=np.float32) * (1 - alpha)) * 255 + 0.5).astype(np.uint8)


def main():
    if not bpy.app.background:
        raise RuntimeError('Review sheets require a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'sheet':
        raise ValueError('Unknown review-sheet worker action')
    request = read_json(request_path)
    source, out = request['source'], Path(request['out'])
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    globs = request['targets']
    chosen = []
    for obj in _included_objects(bpy.context.scene):
        name = obj.get('dcc_instance_id') if isinstance(obj.get('dcc_instance_id'), str) and obj.get('dcc_instance_id') else obj.name
        if obj.type in KINDS and (not globs or any(fnmatch.fnmatchcase(name, g) for g in globs)):
            chosen.append((name, obj))
    unmatched = [g for g in globs if not any(fnmatch.fnmatchcase(name, g) for name, _ in chosen)]
    if unmatched:
        raise ValueError('No render-visible geometry matches: ' + ', '.join(unmatched))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.data.scenes.new('dcc-review-sheet')
    parts, notes = {}, []
    for name, obj in sorted(chosen, key=lambda item: item[0]):
        part = copy_geometry(scene, obj, depsgraph)
        if part is not None:
            parts[name] = part
    if not parts:
        raise ValueError('The targets have no faces to render')
    points = []
    for part in parts.values():
        co = np.empty(len(part['mesh'].vertices) * 3)
        part['mesh'].vertices.foreach_get('co', co)
        points.append(co.reshape(-1, 3))
    points = np.concatenate(points)
    low, high = points.min(axis=0), points.max(axis=0)
    centre, radius = Vector(((low + high) / 2).tolist()), float(np.linalg.norm(high - low)) / 2
    if not radius > 0 or not math.isfinite(radius):
        raise ValueError('The targets have no finite extent')
    faces = sum(part['faces'] for part in parts.values())
    rows = ['silhouette', 'clay', 'wireframe', 'backface']
    if faces > WIRE_BUDGET:
        rows.remove('wireframe')
        notes.append(f'Wireframe row left out: {faces} faces is over the {WIRE_BUDGET}-face budget. Name fewer targets.')
    else:
        for name, part in parts.items():
            wire = bpy.data.objects.new(part['front'].name + '-wire', part['mesh'])
            scene.collection.objects.link(wire)
            modifier = wire.modifiers.new('wire', 'WIREFRAME')
            modifier.thickness, modifier.use_replace, modifier.use_even_offset = radius * 0.012, True, False
            part['wire'] = wire
    views = [{'id': f'orbit-{int(a):03d}', 'azimuth': a, 'elevation': ELEVATION} for a in ORBIT]
    if request['views'] == 6:
        views += [{'id': 'top', 'azimuth': 270.0, 'elevation': 90.0}, {'id': 'bottom', 'azimuth': 270.0, 'elevation': -90.0}]
    tile_w = (request['width'] - GAP * (len(views) - 1)) // len(views)
    tile_h = tile_w * 3 // 4
    data = bpy.data.cameras.new('dcc-review-sheet')
    data.type, data.clip_start, data.clip_end = 'ORTHO', radius * 0.01, radius * 10
    data.ortho_scale = 2 * radius * 1.06 * tile_w / tile_h   # the scale spans the width; the height must hold the sphere
    camera = bpy.data.objects.new('dcc-review-sheet', data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    render, shading = scene.render, scene.display.shading
    render.engine = 'BLENDER_WORKBENCH'
    render.resolution_x, render.resolution_y, render.resolution_percentage = tile_w, tile_h, 100
    render.pixel_aspect_x = render.pixel_aspect_y = 1
    render.film_transparent = True
    render.image_settings.file_format, render.image_settings.color_mode = 'PNG', 'RGBA'
    for name in dir(render):
        if name.startswith('use_stamp'):
            setattr(render, name, False)
    scene.display.render_aa = '8'
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform, scene.view_settings.look = 'Standard', 'None'
    scene.view_settings.exposure, scene.view_settings.gamma = 0, 1
    shading.show_shadows, shading.show_xray, shading.show_specular_highlight = False, False, False
    shading.studio_light, shading.studiolight_rotate_z, shading.cavity_type = 'paint.sl', 0, 'BOTH'
    shading.object_outline_color = (0, 0, 0)
    random = request['colour'] == 'random'

    def stage(row):
        """Which copies are visible, in what colour, under which Workbench settings."""
        shading.light = 'FLAT' if row in ('silhouette', 'wireframe') else 'STUDIO'
        shading.color_type = 'OBJECT'
        shading.show_cavity = row == 'clay'
        shading.show_object_outline = row == 'clay'
        shading.show_backface_culling = row == 'backface'
        for name, part in parts.items():
            part['front'].color = BLACK if row == 'silhouette' else WHITE if row == 'wireframe' else tint(name) if random and row == 'clay' else GREY
            part['back'].color = RED
            part['back'].hide_render = row != 'backface'
            if 'wire' in part:
                part['wire'].color = BLACK
                part['wire'].hide_render = row != 'wireframe'

    tiles = out / 'tiles'
    tiles.mkdir()
    sheet = np.full((len(rows) * tile_h + GAP * (len(rows) - 1), len(views) * tile_w + GAP * (len(views) - 1), 3), 128, dtype=np.uint8)
    for r, row in enumerate(rows):
        stage(row)
        for c, view in enumerate(views):
            look(camera, centre, radius, view['azimuth'], view['elevation'])
            path = tiles / f'{row}-{view["id"]}.png'
            render.filepath = str(path)
            bpy.ops.render.render(write_still=True, scene=scene.name)
            if not path.is_file():
                raise RuntimeError(f'Tile {row}/{view["id"]} produced no image')
            y, x = r * (tile_h + GAP), c * (tile_w + GAP)
            sheet[y:y + tile_h, x:x + tile_w] = read_tile(path, tile_w, tile_h, BACKGROUND[row])
    shutil.rmtree(tiles)
    height, width = sheet.shape[:2]
    (out / 'sheet.png').write_bytes(encode_png(width, height, sheet.tobytes()))
    settings = {key: request[key] for key in ('targets', 'views', 'colour', 'width')}
    if random:
        notes.append('Clay row: one colour per object, from its ID or name.')
    write_json(out / 'receipt.json', {
        'schema': 'dcc.review.sheet.v1', 'checkpoint_sha256': source['sha256'], 'settings': settings, 'settings_digest': digest(settings),
        'image': {'path': 'sheet.png', 'sha256': file_hash(out / 'sheet.png')},
        'layout': {'size': [width, height], 'tile': [tile_w, tile_h], 'gap': GAP, 'rows': rows, 'columns': views},
        'targets': sorted(parts), 'faces': faces, 'centre': [round(c, 6) for c in centre], 'radius': round(radius, 6),
        'blender': bpy.app.version_string, 'notes': notes})
    if file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')


main()
