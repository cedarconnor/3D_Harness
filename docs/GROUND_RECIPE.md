# Ground masks and support sampling

Version 0.4.4 adds two small helpers. They run inside the existing reserved-edit workflow; they do not execute MCP calls, save a scene, manage jobs or certify collision-free navigation.

```python
from dcc_harness.ground import corridor_mask
from dcc_harness.ground_blender import SurfaceSampler

# Coordinates and widths use the same scene units, meters in this project.
clear = corridor_mask((x, y), [(0, -6), (0, 1.6)],
                      half_width=0.82, feather=0.55)
support = SurfaceSampler([terrain, base_ground])
hit = support.sample(x, y, top=10, bottom=-10)
if hit is None:
    raise ValueError('No declared support here')
z = hit['position'][2]
```

`corridor_distance(point, path)` measures the shortest planar distance to a finite polyline. The mask is one inside the corridor, falls smoothly to zero across its feather, and has rounded caps and corners. Repeated points are permitted when a nonzero segment remains. These are geometric masks, not routes solved by a navigation system.

`SurfaceSampler` takes a nonempty list of mesh objects with unique `dcc_instance_id` values. It snapshots evaluated geometry, including modifiers and world transforms, into scoped BVHs. Downward world-space rays return the highest hit among those surfaces or `None`. Rebuild the sampler after moving or editing a source. It does not follow subsequent edits, include undeclared objects or infer a fallback elevation.

Rays exactly on open mesh edges can miss. In the garden qualification, sampling y=16 hit the lower base plane while y=15.9999 hit the terrain roughly 25 cm above it. A new overlay built from those samples exposed the original terrain between grid points, although its original vertex-only check passed. The repaired scene uses evaluated source vertices at aligned grid knots in addition to scoped rays. A dense interior probe then checks for breakthrough. This scene-specific construction is not a general remeshing algorithm: different grids, transforms, overhangs or topology require appropriate construction and additional checks. Do not convert an observed edge failure into an arbitrary global ray tolerance.

The garden example keeps work and path cores clear, feathers soil into grass, and introduces leaf litter around shrub bases. Grass roots are sampled against the actual new cover mesh. The two-channel blend mask lives in `SurfaceMask`; metric soil UVs and normal-map tangents use `MetricUV`. The two added scanned surfaces use world position divided by their recorded physical tile width. The original two ground objects and their shared material are preserved.

Keep source channels, color spaces, physical dimensions, license and content hashes with the job. Compare packed bytes and actual connected scaling nodes after reopening. Review all fixed cameras, including distant terrain boundaries. More grass triangles cannot fix a poor silhouette or repetitive background.

Qualification scripts: `scripts/qualify_ground_sampler.py` exercises transformed and evaluated supports, misses, overlaps and stale snapshots; `scripts/inspect_ground.py` checks this particular saved garden. The latter includes an optional disposable 10 mm root fault and never saves the native file. It is not a general validator for arbitrary environments. See [the measured results](GROUND_0_4_4_RESULTS.md) for evidence and limits.
