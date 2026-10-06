# Practical craft skills — 0.4.x

Four focused project skills extend the existing planning/build/review procedures. They are selectively loaded by `dcc-harness`; ordinary work does not require independent agents or the blind-test coordinator.

| Skill | Practical method | Executable support |
|---|---|---|
| `dcc-architecture` | Human-scale openings, reveals, wall/roof joins, physical texture scale, dependent-part revision | `craft.wall_sections` for rectangular apertures; `roof.lapped_course_profile` for rectangular overlapping courses |
| `dcc-materials` | Channel/scale interpretation, shared-user inspection, controlled lookdev, glass and motivated weathering | `craft_blender.set_material_scalar`: guarded unlinked surface controls |
| `dcc-environment-assembly` | Site boundaries, ground/contact, planting layers, circulation, purposeful activity | Protected-core terrain expansion, ground corridor masks, evaluated support snapshots, seeded broadleaf study and existing native checks |
| `dcc-lighting-review` | Motivated light, focal hierarchy, explicit comparison/presentation cameras, narrow critiques | Existing checkpoint-bound captures and quality review records |

The methods derive from observed project failures and visual critique, not copied third-party skill implementations. Each SKILL.md contains a concrete worked task and a revision/review procedure. The skills remain project-scoped and depend on the runtime; four markdown files are not four proven general-purpose production systems.

## Recipe boundaries

`wall_sections(6, 3, .24, [{'x': 4, 'z': 0, 'width': .95, 'height': 2.1}])` returns local cuboid centers/dimensions. X begins at the wall's left edge, Z at floor level, and Y is centered on its depth. Parameters must be finite with positive dimensions. Openings must lie inside the wall and cannot overlap. Partitioned cuboids touch; the recipe does not weld topology, construct frames, solve load-bearing structure or create UVs. The caller supplies identities, placement, materials and native geometry.

The construction qualification widens a door from .95 to 1.2 m while retaining a separate window and 6 × 3 × .24 m wall bounds. Native rays sample both apertures and a solid-wall control. Pure tests additionally verify remaining volume and reject invalid/overlapping input. These checks establish the bounded recipe, not architectural beauty or structural safety.

`set_material_scalar('metal', 'Principled BSDF', 'Roughness', .46, expected_users)` changes one native scalar only when every bound object has an unambiguous scoped identity. Hidden objects and other scenes are included. Missing/duplicate materials, unexpected users, driven sockets and invalid scalar ranges are rejected before mutation. Supported inputs are Roughness, Metallic, IOR and Transmission Weight. It does not infer artistic values, edit an upstream texture, save or journal.

The saved-shed qualification changes roughness on its actual shared metal from .38 to .46, reopens the result independently, and applies a contract preserving all other observed geometry, placements, materials, cameras and lighting. Omitted users and a linked control are rejection cases. This is a deliberately separate engineering branch; it does not complete the interrupted realism trial or its withheld revision.

## Evidence limits

The [0.4.7 terrain helpers](TERRAIN_RECIPE.md) preserve a declared regular-grid core while expanding/shaping the surround. [Three native-passing studies](TERRAIN_0_4_7_RESULTS.md) were rejected visually. The resulting skill lessons cover off-frame crowns, unrealistic nonuniform scaling and common-contract bias against an unchanged control. These failures establish useful checks and review distinctions; they do not establish improved environment quality.

The [0.4.5 roof profile](ROOF_RECIPE.md) addresses a measured coplanar-overlap defect. Its [qualification](ROOF_0_4_5_RESULTS.md) checks actual evaluated lap/deck clearances and detects a deliberate intersection. It leaves ridge/verge/hardware details outside scope and does not certify a complete roof. The architecture skill distinguishes a diagnostic rendering offset from a sound geometric repair.

The [0.4.4 ground helpers](GROUND_RECIPE.md) add reusable corridor masks and explicit evaluated-support snapshots. Their [garden qualification](GROUND_0_4_4_RESULTS.md) retains a failed overlay caused by open-boundary ray misses, verifies its repair with interior samples, and detects an intentional floating grass root. Materials guidance now distinguishes blend-mask UVs from physical texture coordinates and verifies packed source hashes. These are scoped observations and binding checks, not general continuous-contact or aesthetic certification.

The [0.4.3 broadleaf recipe](VEGETATION_RECIPE.md) adds attached branch/leaf generation and explicit shared definitions. Its [garden evaluation](VEGETATION_0_4_3_RESULTS.md) distinguishes whole-plant review, native connection/support checks and camera-distance crown coverage. These checks do not establish botanical accuracy or generally realistic vegetation.

Frontmatter/reference checks establish that the skill files are valid and navigable. Recipe tests and native probes establish specific executable behavior. No fresh-agent behavioral comparison of the new skills, artist repair-time measurement, or general improvement in visual quality is yet established. The guided shed continuation exercised environment assembly, shared glass revision and UV-only timber repair. It exposed sparse procedural foliage, cross-grain on vertical timber and overlapping diagonal stepping stones; the corresponding skills now explain those specific failure modes. Artist feedback and further production use are still needed before calling these qualified craft methods. Lighting was preserved in this exercise rather than independently tested.

Keep future lessons conditional and example-backed. Expand recipes when repeated work warrants them, not by turning every critique into another mandatory gate. Prior frozen skill packets and evaluator versions remain unchanged.
