# Audit

Unreleased, build-plan item G3. `audit` checks a saved file for geometry defects: flipped faces, doubled surfaces, parts that touch nothing, and a few material mistakes that show up as geometry problems. It works like `uv-report`: a fresh background Blender measures the file, never saving it, and the runtime turns the numbers into findings. It needs no project, no targets file and no stable IDs.

```powershell
python -m dcc_harness audit "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/audit-1"
python -m dcc_harness audit "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/audit-2" --profile game --select "ext.prop.*"
```

The command exits 1 when any finding is an error. Warnings are listed and do not fail it.

## Profiles

`--profile` sets each check to an error, a warning or skip. The default is `render`.

| Code | What it means | `render` | `game` | `print` |
|---|---|---|---|---|
| `NORMALS_INCONSISTENT` | Neighbouring faces disagree about which side is out | error | error | error |
| `NORMALS_INWARD` | A closed part has every face pointing inward | error | error | error |
| `NORMALS_INWARD_ESTIMATE` | An open part's faces mostly point toward its own centre | warning | warning | warning |
| `OPEN_EDGES` | Boundary edges: the surface is not closed | skip | warning | error |
| `NON_MANIFOLD_EDGES` | An edge shared by more than two faces | warning | error | error |
| `LOOSE_GEOMETRY` | Vertices or edges that belong to no face | warning | error | error |
| `ZERO_AREA_FACES` | Faces with no area | warning | error | error |
| `COINCIDENT_FACES` | Two parts have overlapping faces in one plane, facing the same way (z-fighting) | error | error | error |
| `COINCIDENT_FACES_MATCHED` | The same overlap, where both objects use the same materials, so it does not show yet | warning | warning | warning |
| `BACK_TO_BACK_FACES` | The same, facing opposite ways, where at least one part has open edges | warning | warning | error |
| `FLOATING_PART` | A connected part with no other surface within the contact distance | warning | warning | error |
| `SCALE_UNAPPLIED` | A uniform object scale that is not 1 | skip | warning | skip |
| `SCALE_NONUNIFORM` | A non-uniform object scale | warning | error | skip |
| `SCALE_NEGATIVE` | The object is mirrored by a negative scale | warning | error | error |
| `EMPTY_SLOT_FACES` | Faces assigned to a material slot with no material | error | error | skip |
| `DATA_MAP_SRGB` | An image used only as data is tagged sRGB | error | error | skip |
| `TEXTURE_WITHOUT_UV` | A material maps an image by UV on a mesh with no UV layer | error | error | skip |
| `UNMEASURED` | A check stopped at its work budget | warning | warning | error |

`render` does not require closed meshes, because foliage cards, cloth and ground planes are open on purpose. `print` skips the material checks and requires closed, connected parts.

## The report

The command prints a summary and up to 40 findings, errors first, with `omitted` counting the rest. `report.json` in the output folder holds every finding, and `measurement.json` holds the raw numbers per object.

```json
{"code": "COINCIDENT_FACES", "severity": "error", "object": "ext.crate", "name": "Crate", "other": "ext.plate",
 "evidence": "native_measurement", "permitted": "repair", "area": 0.18, "planes": 2, "point": [0.31, 0.21, 1.0],
 "cause": "Faces of two parts lie in the same plane, face the same way and overlap, so they will flicker (z-fighting).",
 "fix": "Move one part off the plane, delete the hidden face, or join the parts and remove the doubled surface."}
```

- **`object`** is the stable ID, or null when the object has none; **`name`** is always the Blender object name.
- **`evidence` and `permitted`** use the same vocabulary as `relations`. A `native_measurement` permits repair. `NORMALS_INWARD_ESTIMATE` is `bounds_only`: it comes from the part's shape alone, permits inspection only, and is never an error. A room interior or a sky dome faces inward on purpose.
- **`cause` and `fix`** say what the defect is and one way to repair it.
- **`source`** binds the report to the file's path and SHA-256. The command refuses to report if the file changed while it was measured.
- **`tolerances`** lists the distances used, in metres.
- **`notes`** say what was not checked, such as curves and text objects.

`--select` takes one glob over stable IDs, or over names for objects without an ID. It limits which objects are reported and sets the tolerances from their extent. Other objects still count as surfaces to touch or overlap.

## How it measures

The worker reads each render-visible mesh with its modifiers applied, in world space, and splits it into connected parts.

- **Normals.** Two faces that share an edge agree on direction exactly when they cross that edge in opposite directions. A closed, consistent part is inside out when its signed volume is negative. A mirrored object is judged the way Blender draws it.
- **Coplanar overlap.** Faces are grouped by plane. Where parts from different groups share a plane, the worker rasterizes each pair over the region they share, on a 32 × 32 grid. The reported area is that grid estimate. Opposed faces of two parts without open edges are a hidden contact, such as a box standing on a floor, and are not reported.
- **Contact.** A part touches another when any of its vertices is within the contact distance of the other's surface, in either direction, or when their triangles intersect. A part that touches nothing is floating. The largest part in the file is never reported, because something has to be the body. An object with more than 2,000 parts is treated as one part.
- **Tolerances.** Each scales with the bounding diagonal of the audited meshes: 0.005% for two planes to count as one, capped at 0.5 mm; 0.1% for contact, capped at 5 mm; and a millionth for a face to count as having no area. The caps keep a whole scene from being judged more loosely than one prop.
- **Data maps.** An image is reported when it is tagged sRGB and every use of it is a data input: a Normal Map, Bump or Displacement node, or a scalar or vector input of a shader. An image that also feeds a colour input, a mix or a node group is left alone.
- **UV use.** An image texture uses UVs when its vector input is unlinked or traces back to a UV output.

## Limits

- **Meshes only.** Curves, text, volumes and geometry that modifiers instance are not audited. The notes list what was skipped.
- **Between parts, not within one.** Coplanar overlap and contact compare connected parts. A surface folded onto itself is not reported as coincident.
- **Planes are matched after rounding their direction,** so two nearly coplanar faces can be missed. Curved surfaces that overlap are not detected at all.
- **Node groups are not opened** by the material checks.
- **Budgets.** Past 3,000,000 contact queries or 20,000 coplanar pairs the check stops and the report carries `UNMEASURED`.
- **Not appearance.** A clean audit says the geometry has none of these defects, not that the model looks right.

## Qualification

`scripts/qualify_audit.py` builds a clean control and eighteen files that each differ from it by one defect. The control reports nothing under all three profiles, and each defect file reports its own code alone. It passed from source on Blender 5.1.1 and 5.2.1.

The production garden (1,285 meshes, 2.36 million triangles) audits in about 18 s and fails under `render` with 522 errors. They were reviewed in Blender and are real: 519 closed parts were built inside out (`NORMALS_INWARD`; a bench apron has none of its six faces pointing outward), and three pairs of different materials overlap in one plane. Nobody had measured this before. The 129 warnings are flush joints of one material, sheets lying on surfaces, shrub foliage that touches nothing, scaled soil grains and degenerate faces.
