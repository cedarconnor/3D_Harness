# Lapped rectangular course profile

`dcc_harness.roof.lapped_course_profile` is a small geometry helper for repeated overlapping rectangular panels. The Blender host or author still owns object identities, placement, materials, edit reservation, saving and verification. This is not a complete roofing design or a general mesh collision solver.

```python
import math
from dcc_harness.roof import lapped_course_profile

pitch = math.atan2(.84, 2.2)  # radians above horizontal
gauge = .29 / math.cos(pitch) # distance along the roof, not horizontal Y
profile = lapped_course_profile(pitch, gauge, .45, .006, .0008)
```

Use consistent units for gauge, panel length, thickness and clearance. Pitch must lie strictly between zero and pi/2. Dimensions must be positive and clearance nonnegative. The helper rejects a profile without positive remaining uphill pitch or overlap.

Tile centers advance along a plane parallel to the roof. A tile slightly shallower than that plane produces a normal separation between adjacent courses. For gauge `g`, thickness `t` and clearance `c`, the tilt difference is `asin((t+c)/g)`. `tile_pitch` is the roof pitch minus that difference; `normal_step` is `t+c`. The returned overlap is measured along the tile tangent. `deck_center_offset` is the required distance along the roof normal from the deck's top plane to a tile center, so the lowest un-beveled corner clears the deck by `c`.

The caller must orient the downhill/uphill direction correctly on both sides of a roof. Do not treat along-slope gauge as horizontal spacing, or apply a thickness twice through mesh dimensions and object scale. A bevel should remain small relative to thickness. Native validation must use evaluated world geometry, not merely restate the authoring parameters. Positive separation along the common panel normal establishes a separating plane for those parallel solids; it does not establish collision clearance against unrelated trim or support contact.

The shed example preserves tile X/Y centers, source UVs, mesh identities and all materials. It revises thickness, tilt, center Z and bevel on exactly 352 existing tiles, leaving decks, ridge and trim untouched. Its 6 mm thickness and 0.8 mm clearance are visual-study inputs, not universal construction standards. A disposable diagnostic showed that tiny per-row offsets removed the bands, but that arrangement still intersected and was never adopted.

Use this helper when its rectangular, parallel-course assumptions match the asset. Curved/warped panels, irregular courses and physical roof hardware require other methods. Keep camera, material and lighting fixed while diagnosing geometry. Inspect both the broad roof and close joins; a clean top view cannot certify unseen construction.

The [results report](ROOF_0_4_5_RESULTS.md) records the saved-scene qualification. `scripts/inspect_roof_laps.py` checks this garden's exact tile layout and can inject an in-memory intersection as a negative control. It never saves the native. Pure tests exercise multiple pitches, scales and impossible profiles.
