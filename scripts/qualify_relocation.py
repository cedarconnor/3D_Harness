"""Native qualification of external-revision relocation: unpacked textures packed into an owned copy.

Builds a panel whose material reads an external PNG by relative path, starts a project on it, and
saves an artist's candidate elsewhere with only the material roughness changed. Without --blender
the preview is refused. With it, the texture is packed into an owned copy, the contract (roughness
only) passes against the parent that still references the external file, and acceptance publishes
the owned copy. That checkpoint still observes READY after the texture file is renamed away. A
texture changed after the candidate was observed is refused.
"""
import shutil

from _launcher import Qualification
q = Qualification(__doc__)
a, runtime, out = q.args, q.runtime, q.out
from dcc_harness.evidence import read_json, write_json

builder = out / 'build.py'
builder.write_text(
    "import bpy, sys\n"
    "folder = sys.argv[sys.argv.index('--') + 1]\n"
    "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
    "image = bpy.data.images.new('grain', 64, 64)\n"
    "image.pixels = [((i // 4) % 7) / 7 if i % 4 != 3 else 1.0 for i in range(64 * 64 * 4)]\n"
    "image.filepath_raw = folder + '/tex/grain.png'; image.file_format = 'PNG'; image.save()\n"
    "mat = bpy.data.materials.new('panel_paint'); mat.use_nodes = True; mat['dcc_material_id'] = 'panel_paint'\n"
    "tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.name = 'Grain'; tex.image = image\n"
    "bsdf = mat.node_tree.nodes['Principled BSDF']; mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])\n"
    "bsdf.inputs['Roughness'].default_value = 0.4\n"
    "bpy.ops.mesh.primitive_plane_add(size=2)\n"
    "panel = bpy.context.object; panel.name = 'panel'; panel['dcc_instance_id'] = 'ext.panel'; panel['dcc_asset_id'] = 'panel'\n"
    "panel.data.materials.append(mat)\n"
    "bpy.context.scene.world = bpy.data.worlds.new('World')\n"
    "bpy.ops.wm.save_as_mainfile(filepath=folder + '/scene.blend', relative_remap=True)\n"
    "image.filepath = '//tex/grain.png'\n"
    "bpy.ops.wm.save_mainfile()\n", encoding='utf-8')
editor = out / 'edit.py'
editor.write_text(
    "import bpy, sys\n"
    "target = sys.argv[sys.argv.index('--') + 1]\n"
    "bpy.data.materials['panel_paint'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8\n"
    "bpy.ops.wm.save_as_mainfile(filepath=target, relative_remap=True)\n", encoding='utf-8')
(out / 'work').mkdir()
(out / 'artist').mkdir()
q.blender('build.log', '--python', builder, '--', (out / 'work').as_posix())
q.blender('edit.log', out / 'work/scene.blend', '--python', editor, '--', (out / 'artist/candidate.blend').as_posix())
base = q.cli('observe', out / 'work/scene.blend', '--blender', a.blender, '--output-dir', out / 'observe-scene')
candidate = q.cli('observe', out / 'artist/candidate.blend', '--blender', a.blender, '--output-dir', out / 'observe-candidate')
assert base['status'] == candidate['status'] == 'READY', (base['issues'], candidate['issues'])
image = read_json(candidate['observation'])['materials']['panel_paint']['graph']
grain = next(n['image'] for n in image['nodes'] if n.get('image'))
assert grain['packed'] is False and grain['exists'] is True, grain

(out / 'BRIEF.md').write_text('A textured panel; relocation fixture.\n', encoding='utf-8')
(out / 'HANDOFF.md').write_text('Started from the saved scene.\n', encoding='utf-8')
write_json(out / 'decisions.json', {})
project = out / 'project'
q.cli('start', project, '--checkpoint', out / 'work/scene.blend', '--observation', base['observation'], '--brief-file', out / 'BRIEF.md',
      '--decisions', out / 'decisions.json', '--handoff', out / 'HANDOFF.md')
write_json(out / 'contract.json', {'schema': 'dcc.continuity.contract.v1', 'allowed_new_prefixes': [],
           'allowed_material_inputs': {'panel_paint': {'Principled BSDF': {'Roughness': 0.8}}},
           'spec': {'schema': 'dcc.spec.v1', 'required': {'ext.panel': {'type': 'MESH'}}}})
write_json(out / 'updates.json', {'panel_roughness': 0.8})
parent = q.cli('next', project)['active']['id']


def preview(folder, *extra):
    return ('preview-revision', project, '--parent', parent, '--checkpoint', out / 'artist/candidate.blend', '--observation',
            candidate['observation'], '--contract', out / 'contract.json', '--handoff', out / 'HANDOFF.md', '--updates', out / 'updates.json',
            '--label', 'artist-roughness', '--note', 'Saved external roughness change', '--output-dir', out / folder, *extra)


summary = {'refused_without_blender': q.refused(preview('preview-plain'), 'pass --blender')}
ready = q.cli(*preview('preview', '--blender', a.blender))
assert ready['status'] == 'READY_FOR_REVIEW' and ready['passed'], ready['failures']
relocation = read_json(out / 'preview/relocation.json')
assert [i['name'] for i in relocation['packed_images']] == ['grain'], relocation
summary['preview'] = {'status': ready['status'], 'packed': ['grain'], 'changes': [(c['id'], c['field']) for c in ready['changes']]}
# A texture changed after the candidate was observed is refused by the packing worker.
original = (out / 'work/tex/grain.png').read_bytes()
(out / 'work/tex/grain.png').write_bytes(original + b'changed')
summary['changed_texture'] = q.refused(preview('preview-changed', '--blender', a.blender), 'Blender pack failed')
(out / 'work/tex/grain.png').write_bytes(original)
accepted = q.cli('accept-revision', project, out / 'preview', '--preview-sha', ready['preview_sha256'],
                 '--review-note', 'Qualification review of the packed roughness change')
assert accepted['status'] == 'PUBLISHED', accepted

# The published checkpoint carries its texture: rename the file away and observe it again.
stored = accepted['active']['checkpoint']
shutil.move(out / 'work/tex', out / 'work/tex-moved')
again = q.cli('observe', stored, '--blender', a.blender, '--output-dir', out / 'observe-published')
stored_grain = next(n['image'] for n in read_json(again['observation'])['materials']['panel_paint']['graph']['nodes'] if n.get('image'))
assert again['status'] == 'READY' and stored_grain['packed'] is True and stored_grain['sha256'] == grain['sha256'], (again['issues'], stored_grain)
summary['published'] = {'checkpoint': accepted['active']['id'], 'observes_without_texture_file': True, 'texture_sha256': grain['sha256']}

q.finish(summary)
