# Isometric kits and dioramas

Freeze projection, camera pose, orthographic scale, aspect and output resolution
for the asset family. True isometric projects the three world axes with equal
foreshortening. Dimetric and other oblique views can be useful but should be named
and kept consistent. For Z-up geometry, a camera above the (1, -1, 1) direction
aimed at the origin gives a true-isometric view; its elevation is about 35.264°
above the ground. Do not confuse elevation with Blender's Euler rotation fields.

Record cell size, tile footprint, height increments, snap origin and pivot rule.
Build neighboring sample tiles before detailing the kit. Place a camera with a
look-at rotation rather than transferring unexplained Euler angles from another
coordinate convention. Orthographic scale controls framing, not perspective.

Spend detail on the top and side planes visible from the chosen view. Review
occlusion between tall modules and the read of doors/paths at gameplay scale.
Ground-level appearance can matter for another camera, but is not sufficient
acceptance for an isometric kit.

Check a small assembled grid for tile joins, shadows, silhouettes and material
density, then inspect at final pixel size with any UI-safe margins. Keep the
comparison camera fixed across variants; a better-looking angle cannot prove
compatibility with the approved kit view.
