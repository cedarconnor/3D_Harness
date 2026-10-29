# Retro and deliberately low-poly

Separate low triangle count from a particular console-era appearance. Choose
reference hardware or games, output resolution/aspect, texel density, filtering,
palette and shading model before budgeting a kit. Low-poly can use modern PBR;
PSX-inspired work can choose affine warping or vertex jitter as additional effects.

Block recognizable masses first. Allocate geometry to silhouettes and articulation;
put repeated panel detail into textures when it survives at the target distance.
Avoid universal triangle or texture-size limits: judge a representative hero,
background prop and environment module in the intended frame.

Set texture interpolation to Closest when crisp texels are part of the brief.
Align UVs and density consistently across related pieces and test atlas margins
under minification. Keep the low-resolution render and upscale as a separate
presentation step with nearest filtering when desired. Analog VHS/CRT treatments
are independent aesthetic choices, not automatic requirements for all retro work.

Affine texture mapping, vertex snapping and screen-space jitter need explicit
shader/geometry implementations. A small texture or low-resolution render does
not reproduce those effects. Geometry jitter can open seams, destroy contacts or
flicker; retain the editable source and inspect motion before accepting it.

Compare at the actual output size, including motion and thin geometry. Check
silhouette, palette, readable interaction cues and texture shimmer. Fog can support
the mood or mask distance; use it only where the brief calls for it.
