---
name: blender-matchmove
description: Track real footage and integrate CG with it in Blender's Movie Clip editor. Covers footage preparation, camera sensor and focal length, feature choice and counts, tracker settings, solver keyframes and parallax, solve error targets and cleaning, refining intrinsics, lens distortion, orienting and scaling the scene, object and plane tracking, shadow catchers and holdouts, and validating a solve.
---

# Matchmove and camera tracking

A matchmove recovers the real camera from footage, so that CG rendered through it sticks to the plate. A low solve error is necessary but not sufficient. Validate the solve by watching a test object sit on the floor through the whole shot.

## Prepare the footage

- **Image sequence.** Convert the video to PNG or EXR (`ffmpeg -i shot.mov shot_%04d.png`). Frames are then exact, and the tracker does not decode video on every step. Build proxies (25–50%) for scrubbing.
- **One shot at a time.** Solve each continuous shot separately, and cut at edits; one camera never spans a cut. Note variable frame rates.
- **Camera data.** Set the camera data **before solving**: `clip.tracking.camera.sensor_width` (mm, from the camera body) and `focal_length` (mm, from metadata or the lens). A wrong sensor width shows up as a wrong focal length. Zoom shots need a fixed focal length or a much harder solve.
- **Distortion.** It matters for wide lenses. Solve on the original pixels, then undistort CG or redistort renders with the Movie Distortion node in the compositor. Never resample the plate twice.

## Track

- **Features.** Use stationary, high-contrast physical corners and small details spread across the **whole frame**, **every depth** (near, mid and far) and the **whole shot**: paint corners, cracks, bolt heads, tile intersections.
  - **Reject** reflections, cast shadows, moving people, leaves, specular highlights, edges of round objects (they slide), burnt-in graphics and repetitive patterns, where the tracker jumps between identical features.
- **Counts.** At least 8 tracks must be common to both solver keyframes, and the solver refuses with fewer. Aim for 20–30+ good tracks per frame, with short useful tracks kept. A tripod (nodal) solve needs only 5–10.
- **Settings** (`clip.tracking.settings`). `default_pattern_size` about 21 px and `default_search_size` about 71 px for normal motion; raise the search size for fast motion. `default_motion_model`: `Loc` for most features, `Affine` or `Perspective` for features that rotate or scale. Turn on normalization (`use_default_normalization`) for lighting changes. `default_correlation_min` about 0.75; raise it to stop drift.
- **Operators.**
  - `bpy.ops.clip.detect_features` for a starting set; lower `min_distance` and `threshold` give more candidates.
  - `track_markers(sequence=True)` forwards, then backwards from the end frame for features that enter late.
  - Inspect and delete drifting tracks.

## Solve

1. **Keyframes.** Choose solver keyframes (`tracking_object.keyframe_a` and `keyframe_b`) with real **parallax** between them, where the camera has translated, not only rotated. Both must share at least 8 tracks; keyframes too far apart lose tracks, too close lack parallax. `settings.use_keyframe_selection` picks them automatically.
2. **Solve.** `bpy.ops.clip.solve_camera()`, then read `clip.tracking.reconstruction.average_error` (px) and `is_valid`. Below 0.3 px is good, 0.3–1 is usable, and above 1–3 means bad tracks or wrong camera data.
3. **Clean.** `bpy.ops.clip.clean_tracks(frames=10, error=1.0, action='DELETE_TRACK')` removes short and high-error tracks. Re-solve. Make sure enough tracks remain on both keyframes.
4. **Refine intrinsics.** Refine the focal length and radial distortion (K1, K2) only after a good base solve, with sane starting values, and only if the error drops on tracks held out of the solve. A refined focal length far from the lens's value means the solve is compensating for something else.
5. **Planar or rotation-only shots.** These cannot give a metric 3D solve. Use a tripod solve or plane tracking instead.

## Orient, scale and set up the scene

- **Orientation.** `clip.set_plane(plane='FLOOR')` (three tracks on the floor), `set_origin` (one track), `set_axis` (one track along X or Y), and `set_scale` with `settings.distance` equal to a measured real distance between two tracks. Until scale is set, units are arbitrary, and lights, physics and depth of field will be wrong.
- **Scene.** `clip.setup_tracking_scene` adds the camera solver constraint, the background plate, and foreground and background collections. The camera's sensor and lens must match the clip's tracking camera.
- **Rendering on the plate.**
  - Turn on `film_transparent`.
  - Make the ground a shadow catcher (`obj.is_shadow_catcher = True`, Cycles) so CG shadows land on the plate, and enable the shadow catcher pass for indirect light.
  - Rebuild real objects that occlude CG as holdouts (`obj.is_holdout`, or a collection's holdout flag).
  - Composite over the plate with Alpha Over. Match the black level, saturation, grain and lens softness of the plate.
- **Object tracking.** Add a tracking object (`clip.tracking_object_new`), track features on the moving object, and drive the object with an Object Solver constraint.
- **Plane tracking.** Four tracks make a plane track (`clip.create_plane_track`) for screen replacements and signs.

## Validate

1. Put simple test geometry on the solved floor and at real tracked points: a cube, a grid, a cone per track.
2. Watch them through the whole shot at full speed. Sliding, floating or drifting means a bad solve, whatever the error number says.
3. Check the first and last frames and the fastest motion.
4. Check the solved camera's focal length and path for plausibility: a hand-held shot should not have its camera fly through the floor.

Record the solve error, the track count, the keyframes and the camera data used.

```python verify
import bpy, math, random

scene = bpy.context.scene
# A synthetic plate with a known camera: 160 distinct boxes at varied depth, rendered flat.
rng = random.Random(3)
base = bpy.data.materials.new('feature'); nodes = base.node_tree.nodes; nodes.clear()
emission = nodes.new('ShaderNodeEmission'); output = nodes.new('ShaderNodeOutputMaterial')
base.node_tree.links.new(emission.outputs[0], output.inputs[0])
for _ in range(160):
    bpy.ops.mesh.primitive_cube_add(size=rng.uniform(0.08, 0.3), location=(rng.uniform(-4, 4), rng.uniform(-1, 8), rng.uniform(0, 2.5)),
                                    rotation=(rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3)))
    mat = base.copy(); mat.node_tree.nodes['Emission'].inputs['Color'].default_value = (rng.random(), rng.random(), rng.random(), 1)
    bpy.context.object.data.materials.append(mat)
cam = bpy.data.objects.new('plate_cam', bpy.data.cameras.new('plate_cam')); scene.collection.objects.link(cam)
cam.data.lens, cam.data.sensor_width, scene.camera = 35, 36, cam
scene.frame_start, scene.frame_end = 1, 24
for frame, x in ((1, -1.0), (24, 1.0)):                     # a 2 m truck with a little pan: real parallax
    cam.location, cam.rotation_euler = (x, -6, 1.2), (math.radians(85), 0, math.radians(-5 * x))
    cam.keyframe_insert('location', frame=frame); cam.keyframe_insert('rotation_euler', frame=frame)
scene.render.engine, scene.view_settings.view_transform = 'BLENDER_WORKBENCH', 'Standard'
scene.display.shading.light, scene.display.shading.color_type = 'FLAT', 'MATERIAL'
scene.render.resolution_x, scene.render.resolution_y = 640, 360
scene.render.filepath = str(WORK / 'plate_')
bpy.ops.render.render(animation=True)

# Load the sequence, set the camera data before solving, and track with a borrowed Clip Editor area.
clip = bpy.data.movieclips.load(str(WORK / 'plate_0001.png'))
assert clip.frame_duration == 24
clip.tracking.camera.sensor_width, clip.tracking.camera.focal_length = 36, 35
settings = clip.tracking.settings
settings.default_pattern_size, settings.default_search_size, settings.default_motion_model = 21, 71, 'Loc'
window = bpy.context.window_manager.windows[0]; area = window.screen.areas[0]
area.type = 'CLIP_EDITOR'; space = area.spaces.active; space.clip = clip
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=window, area=area, region=region, space_data=space, edit_movieclip=clip):
    scene.frame_set(1)
    bpy.ops.clip.detect_features(placement='FRAME', margin=16, threshold=0.02, min_distance=20)
    bpy.ops.clip.select_all(action='SELECT')
    bpy.ops.clip.track_markers(backwards=False, sequence=True)
    camera_object = clip.tracking.objects[0]
    camera_object.keyframe_a, camera_object.keyframe_b = 1, 14   # parallax, and enough shared tracks
    bpy.ops.clip.solve_camera()
    first = clip.tracking.reconstruction.average_error
    bpy.ops.clip.clean_tracks(frames=10, error=1.0, action='DELETE_TRACK')
    bpy.ops.clip.solve_camera()
    cleaned = clip.tracking.reconstruction.average_error
    assert clip.tracking.reconstruction.is_valid
    assert cleaned < 0.3 and cleaned < first, (first, cleaned)  # cleaning the bad tracks is what gets it under 0.3 px
    assert bpy.ops.clip.setup_tracking_scene() == {'FINISHED'}

solved = scene.camera
assert any(c.type == 'CAMERA_SOLVER' for c in solved.constraints)

# Integration: a shadow-catching ground and a transparent film over the plate.
bpy.ops.mesh.primitive_plane_add(size=20); ground = bpy.context.object
ground.is_shadow_catcher = True
scene.render.film_transparent = True
assert ground.is_shadow_catcher and scene.render.film_transparent
```
