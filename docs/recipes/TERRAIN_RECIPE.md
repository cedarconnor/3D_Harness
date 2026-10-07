# Extending terrain around a protected scene

Version 0.4.7 supplies two pure Python helpers in `dcc_harness.terrain`. They support an existing regular grid with an explicitly protected central square. They do not generate an environment, resample an arbitrary sculpt, place vegetation or prove collision-free geometry.

```python
from dcc_harness.terrain import expand_axis, surrounding_height

nx = expand_axis(x, protected_extent=16.5, source_extent=39.5, target_extent=180)
ny = expand_axis(y, protected_extent=16.5, source_extent=39.5, target_extent=180)
dz = surrounding_height(nx, ny, protected_extent=16.5, feather=20,
                        hills=[(-48, 60, 55, 30, 7), (30, 90, 45, 45, 11)])
# New vertex is (nx, ny, existing_z + dz).
```

All quantities use the same coordinate frame and scene units. Extents are positive half-widths, so 180 means a 360-unit span. `expand_axis` preserves coordinates within the core, maps both outer edges exactly, remains monotonic, and joins the unchanged axis with derivative one. It accepts expansion or equal extents, not shrinking. Out-of-bounds input is rejected.

Each hill is `(center_x, center_y, radius_x, radius_y, height)`; radii are Gaussian standard deviations. `surrounding_height` returns a nonnegative **offset**, fading to zero at the protected square. Multiple hills add together, so their combined height can exceed any individual hill's height. Use actual resulting bounds to set support-ray origins; a default ray starting at height 10 may miss taller terrain.

For a Blender grid, preserve the mesh datablock, face indices, object transform and shared materials. Keep protected positions and their UV loop values exact. Update physically scaled UV coordinates only where vertices move; preserve separately authored mask layers. World-position textures can remain consistent, but UV-based normal maps still need the declared metric UV mapping. Verify actual users before editing a shared mesh.

Native validation should compare the protected subset with a retained source snapshot, check row/column ordering and projected triangle areas, and sample the evaluated surface between vertices against any underlying terrain. Rebuild surface samplers after edits. A non-folded XY grid can still have inappropriate slopes or unwanted intersections with other assets; declared placement exclusions and visual review remain necessary.

Review whole-scene and background detail views at fixed settings. Moving a rectangular edge farther away can leave it visible from another camera; bare repeating ground can still look artificial. Match the intended place through landform, boundary planting, material scale and foreground-to-background relationships. The native checks establish bounded preservation and sampled support, not realistic landscape design.
