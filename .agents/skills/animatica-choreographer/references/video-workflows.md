# Animatica video workflow notes

Reviewed 2026-10-27. Four videos supplied English automatic captions. All six were inspected at selected timestamps through Chrome playback after local media downloads returned HTTP 403. This is a caption-and-sampled-frame review, not continuous playback or local add-on qualification. No transcription backend or additional software was installed. The two early Kimodo tutorials had no available caption tracks; their notes below rely on visible UI and burned-in text only.

Video titles can change; the IDs in these links identify the reviewed sources. Prefer the installed version and current vendor documentation for control names and compatibility. These are original workflow summaries, not copied transcripts.

## Marionette

### Beginner tutorial — Y9kkkaGboTA

[Posing and animating with Marionette](https://www.youtube.com/watch?v=Y9kkkaGboTA)

- [1:45–2:10](https://www.youtube.com/watch?v=Y9kkkaGboTA&t=105s): the narration introduces handle move/rotate, hand presets, mirroring and pinning. These shortcuts require the appropriate tool/selection context; do not send keys blindly into an arbitrary Blender editor.
- [2:18–2:46](https://www.youtube.com/watch?v=Y9kkkaGboTA&t=138s): build a short animation from deliberate poses, key each, then play it. The example's frames 1, 15 and 30 are teaching choices, not required production timing.
- [2:56–3:34](https://www.youtube.com/watch?v=Y9kkkaGboTA&t=176s): onion skin, trails and zoetrope serve different inspection needs. The 2:56 frame visibly compares these displays; the captions explain trail edits and Reach.
- [4:20–5:14](https://www.youtube.com/watch?v=Y9kkkaGboTA&t=260s): select the generated Rigify rig rather than the metarig, enter Pose Mode, and inspect the relationship between handles, controls and IK/FK matching. The 4:27 frame shows the Pose Mode shortcut cue. Keep the documented animated-IK exception from the skill.

### Short overview — 2-AS-_lcDGw

[Marionette overview](https://www.youtube.com/watch?v=2-AS-_lcDGw)

The [0:27–0:54](https://www.youtube.com/watch?v=2-AS-_lcDGw&t=27s) captions recap edits across frames, trail reshaping/retiming, brushing and Motion Check; the 0:36 frame shows a hand trajectory. This confirms tool selection already covered by the skill and does not add a new execution contract. Broad rig compatibility and speed claims in promotional narration are not measured guarantees. In particular, retain the current documentation's control-rig exception for neighboring-frame handle edits.

## Choreographer and earlier interfaces

### Mixamo workflow — O6Rf9kQBzjM

[Kimodo with Mixamo characters in Blender](https://www.youtube.com/watch?v=O6Rf9kQBzjM)

- [0:18–0:25](https://www.youtube.com/watch?v=O6Rf9kQBzjM&t=18s): download the chosen character as FBX in T-pose for this workflow.
- [1:19–1:44](https://www.youtube.com/watch?v=O6Rf9kQBzjM&t=79s): import the FBX, target its armature, and clean unwanted imported keys before placing intentional poses. Preserve a source action and scope cleanup; the tutorial is not permission to erase all animation. At 1:42, the sampled frame shows a pose-generation dialog on the imported character.
- [1:49–2:02](https://www.youtube.com/watch?v=O6Rf9kQBzjM&t=109s): position the destination pose and fit the action block to the desired interval before generation.

The narration uses Proscenium-era panel names. Text-to-pose availability must be checked against the connected model and installed add-on.

### Gap-jump tutorial — mP7Il2JXadc

[Animatica Tutorial 01](https://www.youtube.com/watch?v=mP7Il2JXadc)

No caption track was available. Confirmed visual samples:

- 0:20 in the initial browser pass: a gap scene, two timeline keys, and a burned-in cue about setting two motion keyframes.
- [0:54](https://www.youtube.com/watch?v=mP7Il2JXadc&t=54s): text-to-pose dialog for a pose at the current frame.
- [1:30](https://www.youtube.com/watch?v=mP7Il2JXadc&t=90s): a prompt interval labeled unconditioned.
- [2:06](https://www.youtube.com/watch?v=mP7Il2JXadc&t=126s): a cue to add a hold-pose frame, with a running/jumping/landing prompt block.
- [2:42](https://www.youtube.com/watch?v=mP7Il2JXadc&t=162s): a following walking block beside the earlier action block.

Reusable lesson: refine the first generated shot through intentional pose timing and action segmentation. Assess clearance and landing contacts independently; visible scene geometry does not prove collision-aware generation. Sparse frames do not establish every click between these states or the final motion's quality.

### Setup tutorial — Wc349qOwjfM

[Animatica Tutorial 00](https://www.youtube.com/watch?v=Wc349qOwjfM)

No caption track was available. At [0:22](https://www.youtube.com/watch?v=Wc349qOwjfM&t=22s), the video shows a Proscenium 0.1.0 release ZIP and Blender 4.x installation instructions. At [0:44](https://www.youtube.com/watch?v=Wc349qOwjfM&t=44s), preferences show a connection, model information and sign-in UI. A 1:06 sample shows the Blender scene afterward.

Treat this as historical setup evidence. It does not override the current Blender 5.0+ requirement or justify installing that old ZIP. Useful diagnostic order: inspect enabled add-on, backend connection, discovered models, then selected armature.

### Proscenium tutorial — DyJukkBpkWo

[Proscenium Tutorial](https://www.youtube.com/watch?v=DyJukkBpkWo)

The captions describe manual/text poses, prompt timing and seed reuse. [1:18–1:34](https://www.youtube.com/watch?v=DyJukkBpkWo&t=78s) motivates retaining a seed while adjusting timing or constraints; use this to control randomness, not to promise unchanged output for a changed request.

At [1:41–2:25](https://www.youtube.com/watch?v=DyJukkBpkWo&t=101s), the narration describes a Characters tab, FBX import, shoulder Lift/Spread and BVH/FBX export. The sampled 1:59 interface differs from Blender's sidebar. Keep these as Proscenium workflow evidence; do not invent corresponding Choreographer controls or silently broaden the Blender skill into a separate application workflow.
