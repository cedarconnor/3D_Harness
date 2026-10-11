"""Private fresh-process worker for render.py; never run in an artist editor and never saves.

Review-only cameras are created in this disposable process and discarded with it.
"""
from pathlib import Path
import sys
import time

# Blender executes this file by path, including when the package is wheel-installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bpy
from mathutils import Vector
from dcc_harness.evidence import digest, file_hash, read_json, write_json
from dcc_harness.render import strip_png_text


def camera_record(obj):
    data = obj.data
    return {'matrix_world': [list(row) for row in obj.matrix_world], 'type': data.type, 'lens': data.lens,
            'ortho_scale': data.ortho_scale, 'sensor_width': data.sensor_width, 'sensor_height': data.sensor_height,
            'sensor_fit': data.sensor_fit, 'shift_x': data.shift_x, 'shift_y': data.shift_y,
            'clip_start': data.clip_start, 'clip_end': data.clip_end}


def resolve_camera(scene, view):
    spec = view['camera']
    if 'object_id' in spec:
        obj = next((o for o in scene.objects if o.get('dcc_instance_id') == spec['object_id']), None)
        if obj is None or obj.type != 'CAMERA':
            raise ValueError(f'View {view["id"]}: no camera with stable ID {spec["object_id"]}')
        return obj
    data = bpy.data.cameras.new('dcc-review-' + view['id'])
    obj = bpy.data.objects.new('dcc-review-' + view['id'], data)
    scene.collection.objects.link(obj)
    obj.location = Vector(spec['location'])
    obj.rotation_euler = (Vector(spec['target']) - Vector(spec['location'])).to_track_quat('-Z', 'Y').to_euler()
    data.lens = spec['lens']
    bpy.context.view_layer.update()
    return obj


def main():
    if not bpy.app.background:
        raise RuntimeError('Review rendering requires a fresh background process')
    action, request_path = sys.argv[sys.argv.index('--') + 1:]
    if action != 'render':
        raise ValueError('Unknown render worker action')
    request = read_json(request_path)
    source, out, definition = request['source'], Path(request['out']), request['definition']
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed before native open')
    bpy.ops.wm.open_mainfile(filepath=source['path'], load_ui=False)
    if file_hash(source['path']) != source['sha256']:
        raise ValueError('Source changed during native open')
    scene = bpy.context.scene
    settings = definition['render']
    scene.render.engine = settings['engine']
    scene.render.resolution_x, scene.render.resolution_y = settings['resolution']
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    if settings['engine'] == 'CYCLES':
        scene.cycles.samples = settings['samples']
        scene.cycles.seed = settings['seed']
    elif settings['engine'].startswith('BLENDER_EEVEE'):
        scene.eevee.taa_render_samples = settings['samples']
    for key in ('view_transform', 'look', 'exposure'):
        if key in settings:
            setattr(scene.view_settings, key, settings[key])
    # No burned-in or embedded stamps: dates, timings and local paths would make identical renders differ.
    for name in dir(scene.render):
        if name.startswith('use_stamp'):
            setattr(scene.render, name, False)
    resolved = {'frame': scene.frame_current, 'engine': scene.render.engine,
                'resolution': [scene.render.resolution_x, scene.render.resolution_y],
                'pixel_aspect': [scene.render.pixel_aspect_x, scene.render.pixel_aspect_y],
                'film_transparent': scene.render.film_transparent, 'stamps': 'none',
                'color': {'display_device': scene.display_settings.display_device,
                          'view_transform': scene.view_settings.view_transform, 'look': scene.view_settings.look,
                          'exposure': scene.view_settings.exposure, 'gamma': scene.view_settings.gamma},
                'views': {}}
    images, seconds = {}, {}
    for view in definition['views']:
        camera = resolve_camera(scene, view)
        scene.camera = camera
        border = view.get('border')
        scene.render.use_border = border is not None
        scene.render.use_crop_to_border = border is not None
        if border is not None:
            (scene.render.border_min_x, scene.render.border_max_x,
             scene.render.border_min_y, scene.render.border_max_y) = border
        path = out / (view['id'] + '.png')
        scene.render.filepath = str(path)
        started = time.monotonic()
        bpy.ops.render.render(write_still=True)
        seconds[view['id']] = round(time.monotonic() - started, 3)
        if not path.is_file():
            raise RuntimeError(f'View {view["id"]} produced no image')
        strip_png_text(path)
        images[view['id']] = {'path': path.name, 'sha256': file_hash(path)}
        resolved['views'][view['id']] = {'camera': camera_record(camera), 'border': border,
                                         'review_only_camera': 'object_id' not in view['camera']}
    view_settings = {'schema': 'dcc.review.render-settings.v1', 'definition': definition, 'resolved': resolved}
    write_json(out / 'views.json', view_settings)
    write_json(out / 'receipt.json', {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': source['sha256'],
                                      'views_digest': digest(view_settings), 'images': images})
    write_json(out / 'report.json', {'schema': 'dcc.render.report.v1', 'blender': bpy.app.version_string,
                                     'device': getattr(scene.cycles, 'device', None) if settings['engine'] == 'CYCLES' else None,
                                     'seconds': seconds})
    if file_hash(source['path']) != source['sha256']:
        raise RuntimeError('Input file changed during native work')


if __name__ == '__main__':
    main()
