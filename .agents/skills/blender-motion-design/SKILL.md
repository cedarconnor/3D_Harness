---
name: blender-motion-design
description: Make motion graphics, title sequences, product animations, explainer and social videos in Blender 5.x. Covers storyboard and animatic, timing to beats and audio, typography with text objects, procedural motion with Geometry Nodes and drivers, easing and overlap for graphic motion, transitions, the Video Sequencer API (5.1 strip timing names), aspect ratios and safe areas, and delivering video.
---

# Motion design

Motion design is graphic animation. Composition, typography and rhythm matter more than physical realism, but the motion still needs weight, ease and a clear focal point at every moment. Read [animation](../blender-animation/SKILL.md) for timing and the Action API, and [camera](../blender-camera/SKILL.md) for framing.

## Plan before animating

- **Brief.** Write down the length, the delivery formats (16:9, 9:16, 1:1, with resolution and fps), the message per beat, the brand palette and typefaces, and the audio.
- **Storyboard.** One frame per beat, with the focal point marked. Then an **animatic** with timed holds at real playback speed. Check that each message stays on screen long enough to read: about 0.3 s per word plus 0.5–1 s, never less than about 1.5 s for a short line.
- **Audio.** Cut to it. Load the music or voice-over in the Video Sequencer and put markers on the beats (`scene.timeline_markers.new(name, frame=...)`). Key important motion on beats, but not everything on every beat.

## Typography

- **Text objects.** Use `bpy.data.curves.new(name, 'FONT')` with `body`, `size`, `align_x`, `space_character`, `extrude` and `bevel_depth`. Load brand fonts with `bpy.data.fonts.load(path)` and check the font licence. Convert to mesh only when you need mesh operations; text stays editable as a curve.
- **Hierarchy.** One dominant line, one supporting, small details last. Keep at most two typefaces. Use generous tracking for all-caps.
- **Safe areas.** Keep text inside the title-safe area. Each aspect ratio needs its own layout, because a 9:16 crop of a 16:9 layout cuts titles.
- **Legibility.** Check the luminance contrast of text against what is behind it in the frame, not in isolation. Add a backing plate, shadow or blur when it falls short.

## Graphic motion

- **Easing.** Graphic elements ease out of fast starts and settle with a small overshoot. Use Bezier handles, or the `BACK` and `ELASTIC` easings sparingly. Linear motion is for constant drifts and loops.
- **Overlap and stagger.** Stagger related elements by 2–4 frames (letters, list items, cards) for rhythm. Uniform simultaneous motion reads as mechanical.
- **Anticipation and follow-through.** These apply to shapes too: a small counter-move before a big move, and a settle after it.
- **Focal path.** Each beat has one focal point, and motion leads the eye to the next. Transitions carry the eye: match cuts, wipes along the motion direction, scale-throughs.
- **Procedural motion.**
  - Use a Geometry Nodes graph driven by Scene Time or an exposed "progress" input (0..1) that you key once. Arrays of instances, reveals by index (`index / count < progress`) and noise-driven offsets stay editable and in sync.
  - Use drivers for linked parameters, such as a counter's digits from a single value.
  - Use the Build and Dash modifiers for line reveals in Grease Pencil (see [Grease Pencil](../blender-grease-pencil/SKILL.md)).
- **Seamless loops.** For social loops, use the N+1 rule from the camera skill, with every motion either cycling or returning.

## Product animation

Hero shots use turntables, slow push-ins and reveals of features. Keep the [lighting](../blender-lighting/SKILL.md) rig locked to the camera or to the product, so the reflections do not swim unless intended. Motion blur is on for moving products, and the shutter is about 0.5 (180°).

## Video Sequencer (5.x)

- **Sequencer scene.** The sequencer works on `context.sequencer_scene` (5.0+), which may differ from the 3D scene. Strips are in `sequence_editor.strips` and `strips_all`; `sequences` is gone.
- **Adding strips.** Use `strips.new_movie`, `new_sound`, `new_image` and `new_scene`, and `new_effect(name, type, channel, frame_start, length=...)` for colour, text, transforms and cross-dissolves.
- **Timing names (5.1).** `left_handle` and `right_handle` (formerly `frame_final_start` and `frame_final_end`), `duration` (formerly `frame_final_duration`) and `content_start` (formerly `frame_start`). The old names are deprecated until 6.0.
- **Use.** Edit the animatic and the final cut here, with scene strips for 3D shots. Put text strips in the sequencer for simple supers, and use real 3D or 2D text when type must move in space.

## Delivery

1. Render an image sequence, then encode (see [rendering](../blender-rendering/SKILL.md)): H.264 with `yuv420p` for social and review, ProRes 4444 with alpha for compositing.
2. Encode at the platform's frame rate and resolution, and use 9:16 renders, not crops, for vertical.
3. Check audio sync on the final file.
4. Watch the final file at full speed, on the target device size where possible, before calling it done.

```python verify
import bpy

scene = bpy.context.scene
scene.render.fps, scene.render.resolution_x, scene.render.resolution_y = 30, 1080, 1920      # a 9:16 deliverable

# Beats as markers; a 4-word title held long enough to read (0.3 s per word + 0.5 s, at least 1.5 s).
for name, seconds in (('title_in', 0.5), ('title_out', 3.0), ('logo', 3.5)):
    scene.timeline_markers.new(name, frame=round(seconds * scene.render.fps) + 1)
words = len('Built for long projects'.split())
hold = max(1.5, 0.3 * words + 0.5) * scene.render.fps
marks = {m.name: m.frame for m in scene.timeline_markers}
assert marks['title_out'] - marks['title_in'] >= hold

# A text object with extrusion and a staggered, overshooting entrance.
font = bpy.data.curves.new('title', 'FONT'); font.body = 'Built for long projects'
font.size, font.align_x, font.extrude, font.bevel_depth = 0.12, 'CENTER', 0.01, 0.002
title = bpy.data.objects.new('title', font); scene.collection.objects.link(title)
title.location.z = -0.3; title.keyframe_insert('location', index=2, frame=marks['title_in'])
title.location.z = 0.0; title.keyframe_insert('location', index=2, frame=marks['title_in'] + 12)
from bpy_extras import anim_utils
curve = anim_utils.animdata_get_channelbag_for_assigned_slot(title.animation_data).fcurves.find('location', index=2)
curve.keyframe_points[0].interpolation, curve.keyframe_points[0].easing = 'BACK', 'EASE_OUT'
curve.keyframe_points[0].back = 1.2
assert max(curve.evaluate(f) for f in range(marks['title_in'], marks['title_in'] + 13)) > 0.0      # overshoots, then settles

# Sequencer: strips (not sequences), new_effect with length, and the 5.1 timing names.
editor = scene.sequence_editor_create()
backdrop = editor.strips.new_effect(name='backdrop', type='COLOR', channel=1, frame_start=1, length=120)
supers = editor.strips.new_effect(name='super', type='TEXT', channel=2, frame_start=marks['title_in'], length=60)
supers.text, supers.font_size = 'Built for long projects', 64
assert (backdrop.left_handle, backdrop.right_handle, backdrop.duration) == (1, 121, 120)
assert not hasattr(editor, 'sequences') and len(editor.strips) == 2
```
