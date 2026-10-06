---
name: dcc-architecture
description: Build or revise believable modular Blender architecture with measured openings, construction joins and editable dimensions, especially walls, sheds and repeated environment structures.
---

# Construct architecture at human scale

Establish wall thickness, floor level, opening clear sizes and structural spans from the project brief. Distinguish measured references from inferred dimensions. Plan the door's usable opening and window reveal before adding a frame; a dark rectangle on a wall is not an aperture.

Use `dcc_harness.craft.wall_sections(width, height, depth, openings)` for simple rectangular walls. Local X spans 0..width and Z starts at the floor; opening records contain x, z, width, height. It returns cuboids surrounding apertures and rejects overlap/out-of-bounds input. Transform the whole assembly into the site. The result is touching components, not a welded manifold wall; do not claim fabrication topology. Keep panel IDs and recipe parameters in the project, and use a new owned candidate when regenerating.

Worked configuration: a 6 × 3 × 0.24 m wall, a door at x=4, z=0 of 0.95 × 2.1 m and a window at x=0.8, z=1.15 of 1.5 × 1.1 m. Verify unobstructed openings and wall bounds before adding separate jambs, lintels, sill, flashing and hardware. Add real depth at visible reveals; compare the reference's construction rather than copying surface detail indiscriminately.

Revise an opening by changing its recipe dimensions, then adjust only the dependent frame/trim parts. Preserve unrelated placements, cameras and lighting. Use material coordinates tied to meters so extending a wall does not enlarge its bricks. Check that wall returns/corners maintain the intended brick course and that timber grain follows the member; separate end grain where visible.

When a timber texture's grain runs along U, map the member's long physical axis to U: automatic face projection can make vertical posts read as stacked cross-grain blocks. Verify one upright and one horizontal member before repeating the kit. A UV-only repair should preserve geometry, material bindings and tile size; do not rotate the shared texture globally to fix one family.

Review human-height whole and close views for joins, roof overhang, plausible drainage, repeating seams and overly sharp edges. Small bevels should follow physical edge treatment; do not add random damage to every edge. Geometry count and manifoldness alone cannot establish believable construction.

When repeated roof courses show bands or flickering, measure their overlapping top planes before changing shading. Coplanar overlapping panels can produce material-dependent stripes even when every object is valid. The bounded [lapped-course profile](../../../docs/ROOF_RECIPE.md) derives a tile pitch from roof pitch, along-slope gauge, thickness and clearance. Check the saved evaluated geometry for adjacent-course and deck separation. Preserve material/light settings during diagnosis; a tiny per-row offset may confirm the cause but still leave intersecting solids. This profile does not solve ridge, verge, flashing, batten or weatherproofing details.

Qualify a reusable recipe with at least one changed opening and retained bounds/clearance evidence. See [craft qualification](../../../docs/CRAFT_SKILLS.md) for executed coverage and limits.
