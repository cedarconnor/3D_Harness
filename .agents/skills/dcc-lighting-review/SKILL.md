---
name: dcc-lighting-review
description: Establish or critique Blender lighting, camera framing and color consistency using reference-based intent, fixed comparison views and focused material/readability diagnosis.
---

# Light and review with a specific intention

Read the approved camera, daylight/time, palette and exposure decisions. During a scoped asset/material revision, these are controls to preserve. Change lighting only when the task explicitly includes it; a universal studio rig is not an environment recipe.

The current continuity checker can scope existing camera/light object fields, but fixes scene/world settings and rejects new lights. Check that the intended change is expressible before dispatch. Extending unsupported lighting coverage is a runtime task; do not reinitialize accepted history or weaken checks to pass a lighting edit.

Work from motivated light sources, then inspect focal hierarchy, shadow direction, value separation and believable material response. Use a temporary grayscale diagnostic if useful, preserving the saved color pipeline. Do not cure every dark recess by adding fill lights; check whether the modeled opening, surface response or environment explains it.

Keep two kinds of views explicit: fixed regression cameras for comparison and newly proposed composition cameras for presentation. A framing improvement is a separate candidate, not a silent replacement of the evidence camera. Store projection/lens, pose, frame, resolution, renderer, exposure and view transform with captures.

Worked review: the shed context camera crops the roof while the detail view explains the bench well. Preserve that frozen camera in its trial. In a new production task, propose a slightly wider/shifted context camera, check the building's silhouette and path destination, then save it as a new view version. Judge whether the improvement justifies changing the approved composition.

Ask narrow questions of each view: Does the glass read as glass? Does the focal tool separate from the bench? Does the foreground meet the distant scene plausibly? Is wetness consistent with shelter and drainage? Attribute findings to a specific view/object; prefer a concrete diagnosis over 'more cinematic'.

Render unchanged and revised candidates with matching settings for the variable under test. Retain ties and uncertainty. Record artist preference separately from numerical checks and agent critique. Motion needs full-speed playback and temporal checks; a still-lighting review does not qualify an animation. See [qualification](../../../docs/CRAFT_SKILLS.md).
