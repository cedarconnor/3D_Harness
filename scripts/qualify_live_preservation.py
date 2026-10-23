"""Owned Blender regression: dirty image buffers must block save/restore before mutation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--blender', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.runtime).resolve()))
    from dcc_harness.distribution import export_addon
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    export_addon(out / 'bridge.zip')
    with zipfile.ZipFile(out / 'bridge.zip') as archive: archive.extractall(out / 'addon')
    script = out / 'fixture.py'
    script.write_text('OUT = ' + repr(str(out)) + '\n' + '''
import bpy, json, sys, types, hashlib, uuid
from pathlib import Path
out = Path(OUT); sys.path.insert(0, str(out / 'addon'))
import dcc_harness_bridge as bridge
bpy.ops.wm.read_factory_settings(use_empty=True)
image = bpy.data.images.new('Painted image', width=2, height=2)
image.filepath_raw = str(out / 'texture.png'); image.file_format = 'PNG'; image.save()
bpy.data.images.remove(image)
image = bpy.data.images.load(str(out / 'texture.png'))
bpy.ops.mesh.primitive_cube_add()
material = bpy.data.materials.new('Painted material'); material.use_nodes = True
bpy.data.objects['Cube'].data.materials.append(material)
texture = material.node_tree.nodes.new('ShaderNodeTexImage'); texture.image = image
material.node_tree.links.new(texture.outputs['Color'], material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
_ = image.pixels[:]
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'artist.blend'))
disk = hashlib.sha256((out / 'texture.png').read_bytes()).hexdigest()
artist = hashlib.sha256((out / 'artist.blend').read_bytes()).hexdigest()
image.pixels[0] = .123; image.update()
assert image.is_dirty
pixels = tuple(image.pixels[:])
session = types.SimpleNamespace(project=out / 'state', scene=bpy.context.scene.name, active=None, generation='fixture')
def refused(call):
    try: call()
    except ValueError as error:
        assert 'UNSAVED_IMAGE' in str(error), str(error)
    else: raise AssertionError('Dirty image buffer was accepted as a recoverable save-copy')
refused(lambda: bridge.attachment.save_copy(session, out / 'copy.blend'))
assert not (out / 'copy.blend').exists()
refused(lambda: bridge.attachment.snapshot(bpy.context.scene))
op = 'fixture'; folder = out / op; folder.mkdir()
jobs = types.SimpleNamespace(session=session, folder=lambda _:folder,
    status=lambda _:{'state':'NEEDS_RECONCILIATION', 'generation':'fixture'})
result = bridge.recovery.capture(jobs, {'operation_id':op, 'decision':'restore-precopy', 'expected_fingerprint':'a' * 64, 'attempt_id':str(uuid.uuid4())})
assert result['state'] == 'REFUSED_BEFORE_MUTATION', result
assert 'UNSAVED_IMAGE' in result['reason'], result
assert not (folder / 'recovery').exists()
assert tuple(image.pixels[:]) == pixels and image.is_dirty
assert hashlib.sha256((out / 'texture.png').read_bytes()).hexdigest() == disk
assert hashlib.sha256((out / 'artist.blend').read_bytes()).hexdigest() == artist
assert bpy.data.filepath == str(out / 'artist.blend')
image.reload()
bridge.attachment.assert_copyable()  # Empty default sequence editors carry no external dependencies.
# A queued job is a known no-effect refusal; the same explicit decision can be
# retried after it settles, while ambiguous dispatch remains non-repeatable.
jobs.status = lambda _:{'state':'QUEUED', 'generation':'fixture'}
result = bridge.recovery.capture(jobs, {'operation_id':op, 'decision':'keep-current', 'expected_fingerprint':'a' * 64, 'attempt_id':str(uuid.uuid4())})
assert result['state'] == 'REFUSED_BEFORE_MUTATION' and 'BUSY' in result['reason'], result
assert not (folder / 'recovery').exists()
# Broader external dependency classes are explicitly unqualified in P21.
import wave
with wave.open(str(out / 'audio.wav'), 'wb') as audio:
    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(8000); audio.writeframes(b'\\x00\\x00' * 80)
bpy.data.sounds.load(str(out / 'audio.wav'))
try: bridge.attachment.save_copy(session, out / 'audio-copy.blend')
except ValueError as error: assert 'UNSUPPORTED_DEPENDENCIES' in str(error)
else: raise AssertionError('Unqualified external audio was accepted')
assert not (out / 'audio-copy.blend').exists()
(out / 'VERIFICATION.json').write_text(json.dumps({'passed':True, 'dirty_image_refused_before_copy':True,
    'dirty_image_refused_before_restore':True, 'artist_pixels_and_files_unchanged':True,
    'busy_refused_before_mutation':True, 'external_audio_refused':True}))
''', encoding='utf-8')
    with (out / 'native.log').open('w') as log:
        result = subprocess.run([args.blender, '-b', '--factory-startup', '--offline-mode', '--disable-autoexec',
            '--python-exit-code', '1', '--python', str(script)], stdout=log, stderr=subprocess.STDOUT, timeout=90)
    if result.returncode or not (out / 'VERIFICATION.json').exists():
        raise RuntimeError('Native preservation qualification failed; inspect ' + str(out / 'native.log'))
    print((out / 'VERIFICATION.json').read_text())


if __name__ == '__main__': main()
