---
name: blender-sculpt-retopo
description: Sculpt organic forms and turn them into clean, animatable topology in Blender 5.x. Covers choosing multires, dynamic topology or voxel remeshing, sculpting in scale order, organic edge flow and pole placement for deformation, automatic retopology with QuadriFlow, manual retopology with shrinkwrap and snapping, projecting detail back, and measuring topology quality.
---

# Sculpting and retopology

Sculpting finds the form; retopology makes it usable. Keep them separate: sculpt freely on dense or dynamic meshes, then build clean topology for UVs, deformation and export, and bake the sculpted detail onto it (see [baking](../blender-baking/SKILL.md)).

## Choose the sculpting base

- **Voxel remesh.** `mesh.remesh_voxel_size`, then `bpy.ops.object.voxel_remesh()`, gives uniform density for concept and blockout passes. Remesh again whenever the shape stretches. It discards UVs and attributes. A voxel size of about 1–2% of the object's size suits blockout, smaller for detail.
- **Dynamic topology.** Detail is added where you stroke. Use it for concepting and additive shapes; it destroys UVs and other data layers and makes uneven density.
- **Multiresolution.** The Multires modifier keeps subdivision levels over a base cage, so you can work low-to-high and go back down. Use it for detailing a mesh that already has good topology (a retopologized character), because detail stays projectable and bakeable. Apply Base and Reshape move between levels.
- **5.x API changes.** Brush scripting changed: `brush.sculpt_brush_type` replaces `sculpt_tool`, `brush.stroke_method` replaces the stroke booleans (5.1), and radial symmetry lives on `mesh.radial_symmetry`. Interactive strokes need a viewport, so in background mode use modifiers and operators, not brushes.

## Sculpt in scale order

Primary forms first (gesture, masses, proportion), then secondary forms (muscle groups, folds, planes), then tertiary detail (pores, wrinkles, scratches). Check the silhouette from several angles and against references at each stage. Detail on wrong primary forms is wasted. Work with symmetry until the asymmetric pass, then break it on purpose.

## Topology for deformation

- **Quads, evenly sized.** Triangles and n-gons are acceptable only on flat, non-deforming regions.
- **Edge loops follow the deformation.** Concentric loops around the eyes and mouth, a loop from the nose wings around the mouth, and loops across the forehead for brows.
- **Joints.** Elbows and knees get 2–3 loops across the bend, plus a supporting loop above and below. Shoulders and hips need extra density and loops that allow raising and twisting.
- **Poles** (vertices with 3 or 5+ edges) go on flat, low-deformation areas such as cheeks, the forehead and the chest, never on a hinge line or a silhouette edge.
- **Density follows motion.** More density where things bend and on the silhouette, less on flat areas. Game assets need far fewer loops than film assets; set the budget first (see [realtime assets](../blender-realtime-assets/SKILL.md)).

## Retopology

- **QuadriFlow.** `bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=N, use_mesh_symmetry=True, use_preserve_sharp=False, seed=0)`. It gives all-quad output with roughly even flow. It needs clean, manifold input (merge by distance, remove non-manifold geometry first) and discards all data layers. It works well for props and statues, less well for faces that will animate, where the loops must follow the features.
- **Manual retopology.**
  - Make a new mesh on top of the sculpt with face snapping (`snap_elements` including `'FACE'`, with project individual elements on).
  - Or use a Shrinkwrap modifier (`wrap_method='PROJECT'` or `'NEAREST_SURFACEPOINT'`, a small `offset`) targeting the sculpt.
  - Build the key loops (eyes, mouth, joints) first, then fill between them.
  - Mirror with clipping for symmetrical characters.
- **Detail.** Bring detail back with a normal (and displacement) bake from the sculpt to the retopo, or by adding Multires to the retopo and reprojecting the sculpt with Shrinkwrap at the top level.

## Measure topology

Report these from bmesh:

- the quad ratio (`sum(len(f.verts) == 4) / len(faces)`);
- the valence histogram of interior vertices (most should have valence 4) and the pole positions;
- the face-area spread (the coefficient of variation of `f.calc_area()`), for evenness;
- non-manifold and boundary edge counts.

Compare pole positions with joint locations: a pole within a few centimetres of a hinge will pinch. The final judgment is a deformation test in the [skinning](../blender-skinning/SKILL.md) stress poses.

```python verify
import bpy, bmesh
import numpy as np

def topology(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    interior = [len(v.link_edges) for v in bm.verts if not v.is_boundary]
    areas = np.array([f.calc_area() for f in bm.faces])
    report = {'faces': len(bm.faces), 'quads': sum(len(f.verts) == 4 for f in bm.faces) / len(bm.faces),
              'valence4': interior.count(4) / len(interior), 'area_cv': float(areas.std() / areas.mean()),
              'non_manifold': sum(not e.is_manifold for e in bm.edges)}
    bm.free()
    return report

# A lumpy "sculpt": a UV sphere pushed out of shape, then voxel-remeshed to uniform density.
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16); sculpt = bpy.context.object
for v in sculpt.data.vertices:
    v.co.z *= 1.4 if v.co.z > 0 else 1.0
assert topology(sculpt)['quads'] < 1.0                       # UV spheres have triangle fans at the poles
sculpt.data.remesh_voxel_size = 0.08
assert bpy.ops.object.voxel_remesh() == {'FINISHED'}
assert topology(sculpt)['non_manifold'] == 0

# QuadriFlow retopology to a face budget: all quads, mostly valence-4 vertices.
retopo = sculpt.copy(); retopo.data = sculpt.data.copy(); bpy.context.scene.collection.objects.link(retopo)
bpy.ops.object.select_all(action='DESELECT'); retopo.select_set(True); bpy.context.view_layer.objects.active = retopo
assert bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=800, use_mesh_symmetry=False, seed=0) == {'FINISHED'}
report = topology(retopo)
assert report['quads'] > 0.99 and report['valence4'] > 0.8 and 400 < report['faces'] < 1600, report

# Multires on the clean topology for detailing; Shrinkwrap keeps a retopo layer on the sculpt surface.
multires = retopo.modifiers.new('detail', 'MULTIRES')
with bpy.context.temp_override(object=retopo, active_object=retopo):
    bpy.ops.object.multires_subdivide(modifier='detail', mode='CATMULL_CLARK')
assert multires.total_levels == 1
wrap = retopo.modifiers.new('fit', 'SHRINKWRAP'); wrap.target, wrap.wrap_method, wrap.offset = sculpt, 'NEAREST_SURFACEPOINT', 0.001
assert retopo.modifiers[-1].target == sculpt
```
