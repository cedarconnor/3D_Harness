---
name: blender-camera
description: Set up and animate Blender cameras like a cinematographer. Covers sensor and focal length, field of view and framing maths, perspective versus orthographic, depth of field, composition and aspect ratios, motivated camera moves, turntables and seamless loops, camera rigs, shake, and checking framing across the whole shot.
---

# Camera and cinematography

The camera decides what the viewer reads first. Choose the lens, the height and the framing for the story, then build the scene for that camera. Polishing objects the camera never sees is wasted work.

## Lens and sensor

- **Sensor.** Set it explicitly: `camera.sensor_width` (36 mm is full-frame and the default) and `sensor_fit`. The same focal length frames differently on different sensors. When matching a real camera or photo, use its sensor, or convert to the 36 mm equivalent.
- **Field of view.** Horizontal FOV = 2·atan(sensor_width / (2·focal)). To fit a subject of extent E across the frame, the distance is E / (2·tan(FOV/2)), which equals E × focal ÷ sensor width. Multiply by 1.1–1.25 for margin. A 2 m subject at 50 mm on a 36 mm sensor needs about 2.8 m before margin.
- **Lens character.** Perspective compression comes from **distance**; the focal length only crops.
  - 14–24 mm: wide, dynamic and distorting. Use it in interiors and to show scale.
  - 35–50 mm: natural, documentary.
  - 85–135 mm: portraits and products; flattering, low distortion.
  - 200 mm and up: compressed, catalogue product shots and telephoto stacking.

  Short lenses close to a product distort its ellipses and proportions.
- **Height.** Eye level (about 1.5–1.7 m) reads neutral. Low reads powerful or large, high reads small or overview. For products, a low elevation of a few degrees shows the shape without looking down on it.
- **Orthographic.** Use `type='ORTHO'` with `ortho_scale` equal to the visible width in metres, for technical views, isometric styles and silhouette checks. It is never a match for a perspective photo.
- **Clipping.** `clip_start` should be as large as the scene allows, because tiny values cause depth precision problems. Use 0.01–0.1 m for normal scenes and 0.001 m only for macro or tracked plates.

## Depth of field

- **Settings.** Use `camera.dof.use_dof`, and focus with `focus_object` (an empty on the subject) rather than a typed distance, so it follows animation.
- **Aperture.** `aperture_fstop` uses real f-numbers, but only in a real-scale scene. In a scene at the wrong scale, f-stops give the wrong blur. Products and miniatures at true scale with a wide aperture read as tiny, which is sometimes intended (tilt-shift) and often not.
- **Bokeh shape.** Use `aperture_blades` and `aperture_ratio` (anamorphic) for stylistic bokeh.

## Composition and aspect

- **Focal point.** Place the subject where the eye lands: thirds intersections, leading lines, frames within the frame, and value contrast at the focal point. Read the [visual design](../blender-visual-design/SKILL.md) skill for hierarchy and balance.
- **Horizon.** Keep it level unless tilting means something. Keep verticals vertical in architecture: use `shift_x` and `shift_y` (lens shift) instead of tilting the camera up.
- **Aspect ratios.** Frame each deliverable ratio separately (16:9, 9:16, 1:1, 2.39:1); a centre crop is not a reframe. Use the title- and action-safe overlays for text.
- **Front of an object.** Before animating around an unfamiliar object, decide its front. Render four quick low-resolution views (±X, ±Y), and ask if it is unclear.

## Camera moves

- **Motivation.** Every move needs a reason: reveal, follow, emphasize or establish scale. Common moves are the push-in, the pull-out, the orbit or arc, the crane or pedestal, the truck, and the dolly zoom (the camera moves and the focal length changes oppositely, so the subject size stays constant).
- **Rig layers.** Build `CAM_root` (path or dolly) → `CAM_aim` → `CAM_shake` → camera, so each layer animates one thing. A Track To constraint on the camera itself cancels any shake rotation; aim a parent or use a separate aim target.
- **Easing.** Ease in and out of moves; linear starts and stops look robotic. Exceptions are constant-speed turntables and loops.
- **Shake.** Treat shake as a finite impulse triggered by an event such as a landing or impact: about 0.1–0.35° for small contacts and 0.5–1.5° for heavy ones, decaying over 0.3–0.7 s. Use a Noise F-curve modifier on a dedicated shake layer, with its restricted range and blend in/out, and a fixed `phase` as the seed. Noise `scale` is measured in frames, not hertz.

## Turntables and seamless loops

- **Rig.** Use an empty at the subject's centre with the camera parented to it (or the subject on a rotating empty), and animate the empty's Z rotation.
- **Seamless loop.**
  1. Key 0° at frame 1 and 360° at frame N+1, and render frames 1..N.
  2. Make every key `LINEAR`; Bezier eases into a visible stutter at the seam.
  3. Keep everything else fixed: no lens, distance or light animation unless it also loops.
- **Speed ramps.** Use uneven key spacing with Bezier, not linear keys.

## Check the whole shot

Check framing at the first, middle and last frames and at the extremes of every move. Watch a playblast or low-sample preview at full speed: problems with timing and motion blur are invisible in stills. Lock one render recipe per continuous shot. In a harness project, fixed regression cameras stay separate from new presentation cameras; see [lighting review](../dcc-lighting-review/SKILL.md).

```python verify
import bpy, math
from bpy_extras import anim_utils

scene = bpy.context.scene
cam_data = bpy.data.cameras.new('shot'); cam_data.sensor_width, cam_data.lens = 36.0, 50.0
cam = bpy.data.objects.new('shot', cam_data); scene.collection.objects.link(cam); scene.camera = cam

# Field of view and fit distance from the lens maths, against Blender's own angle.
fov = 2 * math.atan(cam_data.sensor_width / (2 * cam_data.lens))
assert abs(fov - cam_data.angle_x) < 1e-6
extent = 2.0
distance = extent / (2 * math.tan(fov / 2)) * 1.15
# Because 2*tan(FOV/2) = sensor/focal, the fit distance is simply extent x focal / sensor (2 m at 50 mm: 2.78 m).
assert abs(distance - extent * cam_data.lens / cam_data.sensor_width * 1.15) < 1e-9, distance

# Depth of field that follows an empty on the subject.
focus = bpy.data.objects.new('focus', None); scene.collection.objects.link(focus)
cam_data.dof.use_dof, cam_data.dof.focus_object, cam_data.dof.aperture_fstop = True, focus, 2.8

# Turntable: camera on a pivot empty, aimed with Track To; 360 degrees keyed at N + 1, all LINEAR.
pivot = bpy.data.objects.new('CAM_root', None); scene.collection.objects.link(pivot)
cam.parent, cam.location = pivot, (0, -distance, 0.4)
track = cam.constraints.new('TRACK_TO'); track.target, track.track_axis, track.up_axis = focus, 'TRACK_NEGATIVE_Z', 'UP_Y'
frames = 48
scene.frame_start, scene.frame_end = 1, frames
pivot.rotation_euler.z = 0; pivot.keyframe_insert('rotation_euler', index=2, frame=1)
pivot.rotation_euler.z = 2 * math.pi; pivot.keyframe_insert('rotation_euler', index=2, frame=frames + 1)
bag = anim_utils.animdata_get_channelbag_for_assigned_slot(pivot.animation_data)
curve = bag.fcurves.find('rotation_euler', index=2)
for key in curve.keyframe_points:
    key.interpolation = 'LINEAR'

# Equal angular steps on every rendered frame, including across the seam.
steps = []
for f in range(1, frames + 1):
    steps.append((curve.evaluate(f + 1) - curve.evaluate(f)) % (2 * math.pi))
assert max(steps) - min(steps) < 1e-6 and abs(steps[0] - 2 * math.pi / frames) < 1e-6

# The camera always faces the focus empty at the subject's centre.
for f in (1, 13, 37):
    scene.frame_set(f)
    forward = cam.matrix_world.to_3x3().col[2] * -1
    to_subject = (focus.matrix_world.translation - cam.matrix_world.translation).normalized()
    assert forward.dot(to_subject) > 0.999, f
```
