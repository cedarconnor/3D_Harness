---
name: blender-reference-modeling
description: Turn photos, drawings or orthographic views into a correctly proportioned Blender model. Covers the reference brief, scale anchors, orthographic reference setup, matching a perspective photo's camera, blockout-first alignment and measured comparison against the reference. Use when a task starts from images rather than dimensions.
---

# Model from reference without guessing

A reference is evidence about shape, not a template to trace. Good results come from three habits:

- Decide which dimensions are known.
- Build the silhouette first and compare it at the reference's own camera.
- Fix the largest deviation before adding detail.

Detail never rescues wrong proportions.

## 1. Write the reference brief first

- **List every image** with its kind:
  - an orthographic drawing (front, side or top);
  - a perspective photo, with its lens if known;
  - a mood or material reference, which carries no geometry.

  Keep the original files unchanged. Record a hash if the project keeps evidence.
- **Tag every dimension** as *given* (annotated or specified), *measured* (from pixels against a known length) or *assumed*. Write assumed millimetre values as assumptions. Without any scale reference, work in proportions and say so.
- **Choose one scale anchor** before the first real geometry: a door (about 2.0–2.1 m clear), a storey (about 2.7–3.2 m), a 1.75 m human, a standard part, or a printed dimension.
  - Place a proxy of that size in a `00_Reference` collection that is excluded from rendering.
  - Reconcile several anchors when you have them; one anchor can mislead.
- **Gather the reference in order:** silhouette, orthographic views, scale, materials, then small detail. Matching blueprints to a silhouette you have not checked wastes the work that follows.

## 2. Set up the references in Blender

- **Orthographic drawings.** Use an Image empty per view (`empty_display_type='IMAGE'`).
  - Align each view to the shared origin, and scale each so that a measured landmark matches the anchor.
  - Set `empty_image_side='FRONT'` and a low opacity.
  - Check that the front and side views agree on shared heights before modeling. Drawings often disagree with each other, and that disagreement must be resolved, not averaged.
- **Perspective photos.** Never model a photographed object as if the photo were orthographic: it bakes the lens and viewpoint into the mesh, and the model then looks right from one angle only. Match the camera instead:
  1. **Lens.** Use the photo's EXIF focal length and sensor width if known. Set `camera.sensor_width` and `sensor_fit` explicitly, because a 50 mm lens means different framing on different sensors.
  2. **Camera solve.** Without metadata, solve the camera from two or three vanishing directions of known parallel edges. fSpy is the common external tool, with a third-party importer. Guessing by genre (24–35 mm for interiors, 50 mm general, 85–135 mm for products) is a last resort, and must be recorded as an assumption.
  3. **Background.** Show the photo as a camera background image: `camera.data.background_images`, with `show_background_images=True`. Match the render resolution to the photo's aspect ratio, or the overlay will not register.
- **Several photos of one object** constrain it far better than one. Match each photo with its own camera, and keep the object fixed while you adjust the cameras.

## 3. Block out, then align

1. Build primitives for the main masses only, at the anchor's scale. Do not add bevels or detail yet.
2. Look through the reference camera. Compare the silhouette, the landmark ratios (for example, handle height over body height), the tilt of the long axis, thickness and occlusion.
3. Change one thing at a time, and decide first whether the error is the camera or the geometry. A uniformly wrong outline usually means the camera; one wrong part usually means geometry. Never non-uniformly scale a solid to fit one view: it breaks every other view.
4. Hold the camera and lights fixed across rounds. Log any change to them, or later comparisons mean nothing.
5. Fix the top one to three deviations per round. If a round brings no improvement, re-diagnose instead of nudging values.

## 4. Measure, don't eyeball

- **World-space bounds.** Read them from the evaluated object: `obj.evaluated_get(depsgraph)`, then `bound_box` corners through `matrix_world`. Compare the ratios with the reference ratios.
- **Image positions.** Project 3D landmarks into the reference camera with `bpy_extras.object_utils.world_to_camera_view(scene, cam, point)`. It returns normalized (x, y) with the origin at bottom-left, and depth. Compare them with the landmark's pixel position divided by the image size.
- **Circles.** A circle seen in perspective is an ellipse. Its width-to-height ratio tells you the viewing angle and is a strong check on the camera.
- **Scope of a match.** One matching metric proves only that metric. Also check a side or three-quarter view: hero views hide floating parts, and a gray override hides missing internals behind glass.

## 5. Review

Render the reference camera view and an independent angle with the same settings. Then ask a reviewer for at most three issues. Use a fresh-context agent if no person is available, and give it only the reference and the render. For each issue, get the location, the evidence and the likely cause (camera, geometry or not enough information). Do not report an unmeasured "similarity %". "Reviewed" does not mean "matches": keep unresolved differences listed.

Keep the reference images available in the saved file: pack them, and give images that may lose all users a fake user so they survive saving. In a harness project, a reference camera worth keeping becomes a `review_views` decision; see [lighting review](../dcc-lighting-review/SKILL.md).

```python verify
import bpy, math
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1600, 1200   # match the photo's 4:3 aspect

# A matched camera: explicit sensor and lens, looking at the origin from the front.
cam_data = bpy.data.cameras.new('ref_cam')
cam_data.sensor_fit, cam_data.sensor_width, cam_data.lens = 'HORIZONTAL', 36.0, 85.0
cam = bpy.data.objects.new('ref_cam', cam_data); scene.collection.objects.link(cam)
cam.location = (0, -6, 0.5)
cam.rotation_euler = (math.pi / 2, 0, 0)
scene.camera = cam

# The photo as a camera background image (a generated stand-in here), packed so it survives saving.
photo = bpy.data.images.new('reference_photo', 1600, 1200); photo.pack(); photo.use_fake_user = True
bg = cam_data.background_images.new(); bg.image = photo; bg.alpha = 0.5
cam_data.show_background_images = True

# A scale anchor in a reference collection excluded from rendering.
ref = bpy.data.collections.new('00_Reference'); scene.collection.children.link(ref)
anchor = bpy.data.objects.new('anchor_1.75m', None); anchor.empty_display_type = 'SINGLE_ARROW'
anchor.empty_display_size = 1.75; ref.objects.link(anchor)
ref.hide_render = True

# Blockout: a 1 x 0.5 x 1 m box centred at z = 0.5.
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5)); box = bpy.context.object
box.scale = (1, 0.5, 1); bpy.context.view_layer.update()

# World bounds from the evaluated object, then landmark projection into the reference camera.
depsgraph = bpy.context.evaluated_depsgraph_get()
ev = box.evaluated_get(depsgraph)
corners = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
size = [max(c[i] for c in corners) - min(c[i] for c in corners) for i in range(3)]
assert [round(s, 4) for s in size] == [1.0, 0.5, 1.0], size
top = world_to_camera_view(scene, cam, Vector((0, -0.25, 1.0)))
bottom = world_to_camera_view(scene, cam, Vector((0, -0.25, 0.0)))
centre = world_to_camera_view(scene, cam, Vector((0, -0.25, 0.5)))
assert abs(centre.x - 0.5) < 1e-4 and abs(centre.y - 0.5) < 1e-4 and top.y > 0.5 > bottom.y, (centre, top, bottom)
# Pixel height of the 1 m box in the 1200 px photo, to compare against the measured landmark.
pixel_height = (top.y - bottom.y) * scene.render.resolution_y
# Pinhole check: focal length in pixels = lens / sensor width x image width; height = f_px x size / depth.
f_px = cam_data.lens / cam_data.sensor_width * scene.render.resolution_x
assert abs(pixel_height - f_px * 1.0 / 5.75) < 0.5, (pixel_height, f_px)
```
