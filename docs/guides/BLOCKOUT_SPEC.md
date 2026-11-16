# Blockout spec

Version 0.25.0, build-plan item G5 (which absorbs P16). A blockout spec states a layout as numbers before any detailed modelling: named primitives in metres, proportions with tolerances, and rules for what must never happen. Three commands use it.

```powershell
python -m dcc_harness spec-check "<spec.json>"
python -m dcc_harness blockout-build "<spec.json>" --blender "<BLENDER>" --output "<work>/blockout.blend" --output-dir "<work>/build-1"
python -m dcc_harness spec-compare "<spec.json>" "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/compare-1"
```

| Command | What it does | Exits 1 when |
|---|---|---|
| `spec-check` | Validates the spec alone, including against its own proportions and never rules | The spec is invalid |
| `blockout-build` | Builds the parts into an owned, tagged collection and saves a new file | The build is refused |
| `spec-compare` | Measures a saved file against the spec; never saves | Any finding |

## The spec

```json
{"schema": "dcc.blockout.v1", "name": "yard", "units": "metres", "up": "Z",
 "tolerance": {"size": 0.1, "position": 0.1},
 "parts": [
   {"name": "ground", "category": "ground", "primitive": "plane", "position": [0, 0, 0], "size": [8, 8, 0]},
   {"name": "shed", "category": "structure", "primitive": "box", "position": [0, 1.5, 0], "size": [3, 2, 2.2], "group": "building", "rests_on": "ground"},
   {"name": "bench", "category": "furniture", "primitive": "box", "position": [-2, -1, 0], "size": [1.6, 0.6, 0.9], "yaw": 30,
    "rests_on": "ground", "ids": ["ext.bench.*"]}],
 "proportions": [
   {"id": "bench-top", "value": {"part": "bench", "measure": "top"}, "min": 0.85, "max": 0.95},
   {"id": "bench-to-shed", "ratio": [{"part": "bench", "measure": "height"}, {"part": "shed", "measure": "height"}], "target": 0.4, "tolerance": 0.05}],
 "never": [
   {"id": "bench-clear-of-shed", "rule": "no_overlap", "parts": ["bench", "building"]},
   {"id": "bench-above-ground", "rule": "not_below", "part": "bench", "z": 0},
   {"id": "bench-in-yard", "rule": "within", "part": "bench", "footprint": "ground"}],
 "avoid": ["The shed must not read as a house."]}
```

**Parts.** Each part has these fields:

- **`name`** is a unique lowercase name. A built part gets it as its stable ID.
- **`category`** is one of `structure`, `opening`, `roof`, `ground`, `path`, `furniture`, `prop`, `vegetation`, `boundary` or `other`.
- **`primitive`** is `box`, `cylinder`, `plane`, `wedge` (a ramp rising toward +Y), `cone` or `sphere`.
- **`position`** is the centre of the part's base, so a part with `z = 0` stands on the ground.
- **`size`** is width, depth and height before yaw. A plane has height 0.
- **`yaw`** is degrees about Z. Optional.
- **`group`** names a set of parts that rules can refer to as one box. Optional.
- **`rests_on`** names the part this one stands on. `blockout-build` turns these into a `relations` definition. Optional.
- **`ids`** are ID globs for the scene objects that stand for this part once real modelling replaces the primitive. The default is the part's own name.

**Proportions** judge one measure (`value`) or the quotient of two (`ratio`), with either `target` and `tolerance` or `min` and/or `max`. Measures are `width`, `depth`, `height`, `bottom`, `top`, `x` and `y`. A reference names a part or a group.

**Never rules** are `no_overlap` (two boxes interpenetrate), `not_below` (a part reaches below a level) and `within` (a part leaves another's footprint).

**`avoid`** holds sentences that cannot be measured. They travel with the spec and `spec-compare` lists them under `not_measured`.

**`tolerance`** sets the allowed size error as a fraction (never less than 1 cm) and the allowed position error in metres. The defaults are 0.1 and 0.1.

**`review_views`** may hold a `dcc.review.views.v1` definition, validated by the same rules as `render`.

Validation is strict. An unknown field is an error. A number outside its range is an error, not clamped: sizes run from 1 mm to 1 km, coordinates to 10 km, and a spec holds at most 500 parts. A spec that breaks its own proportions or never rules is refused, so the plan is consistent before anything is built.

## Building

`blockout-build` creates one mesh object per part in a collection named `dcc.blockout.<spec name>`. Each object is built at true size with scale 1, outward normals, the part's name as `dcc_instance_id`, and a tag recording what the build left. Without `--source` the file is new and empty; with it, the blockout is added to a copy of that file. The source is opened and never written, and the output must be a new path.

When the source already holds this spec's blockout, the build replaces it, staging the new collection before removing the old. It refuses with `BLOCKOUT_EDITED` when the old collection is not exactly what a build left:

- a part was moved, reshaped or given a modifier;
- a part was removed;
- the collection holds an object the build did not make, or a child collection.

It also refuses when an object outside the collection already uses a part's ID. Work that has started on the blockout is therefore never overwritten.

The result names `relations.json` when any part has `rests_on`. Run `relations --spec` with it on the built file to confirm each part stands on its support. Run `observe` on the built file to start or continue a project from it.

## Comparing

`spec-compare` finds the render-visible objects each part's `ids` match and takes their bounding box in the part's yaw frame. Each finding has a `code`, a `path` into the spec, a `message` with the numbers, and a `remediation`.

| Code | Meaning |
|---|---|
| `PART_MISSING` | No object matches the part's `ids` |
| `SIZE` | The measured box differs from the spec size by more than the size tolerance |
| `POSITION` | The base centre is off by more than the position tolerance |
| `PROPORTION` | A proportion is outside its range |
| `NEVER_OVERLAP` / `NEVER_BELOW` / `NEVER_OUTSIDE` | A never rule is broken |
| `UNMEASURED` | A proportion or never rule needs a part that was not measured |

It fails closed: a part that cannot be measured fails, and so does every rule that refers to it. The report binds to the file's hash and to the spec's digest.

## Limits

- **Bounding boxes only.** A part's shape, yaw and detail are not compared. An L-shaped bench and a box of the same extent measure the same.
- **Proportions are as good as the `ids`.** A door part that matches the lintel measures wider than the opening.
- **`avoid` sentences are not checked.** They are for the reader.
- **Metres with Z up only.** A scene with another unit scale is built and measured in metres.
- **A match is not quality.** It says the layout has the planned proportions.

## Qualification

`scripts/qualify_blockout.py` passed from source on Blender 5.1.1 and 5.2.1.

- **`spec-check`:** a valid spec passes, and eight broken specs are each refused for their own reason.
- **`blockout-build`:** the built file observes `READY`, audits without an error and passes its five generated relations. A rebuild over an untouched blockout replaces it; four altered sources are each refused, with the source unchanged.
- **`spec-compare`:** the built file matches, and five edited files each report exactly their own codes. A part whose objects carry other IDs is missing until `ids` names them. A part declared to rest on another but placed above it fails its relation with `GAP`.

### The potting-shed study

[`potting-shed.blockout.json`](../studies/potting-shed.blockout.json) expresses the production garden as ten parts, ten proportions and four never rules. The garden's brief has no numbers, so the part sizes and positions were read from checkpoint 9 and pass by construction. The independent test is the proportions, which are ordinary human-scale ranges written without looking at the result, and the never rules.

The first comparison passed eight proportions and all four never rules and failed two: the door frame measured 1.48 m wide and 2.46 m tall against ranges of 0.8 to 1.3 m and 1.9 to 2.3 m. The door part matches the head, both jambs, the lintel and the threshold, so those are the outside of the frame with the lintel included, and the ranges had been written for a door leaf. The owner judged the door as built to be right on November 15. The ranges were the error: they now run to 1.6 m and 2.6 m, and checkpoint 9 passes.

The lesson for writing a spec: say what a part's `ids` cover before choosing its range. A frame with its lintel is not a door opening.
