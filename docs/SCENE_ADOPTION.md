# Start from an existing Blender file

Version 0.4.9 adds explicit initial identity adoption. It fills missing object, asset and material IDs in a **new native file**, then reopens that file in another Blender process to observe it. Use it when starting a continuity project from a saved scene that was authored without harness IDs.

This is separate from adopting an artist revision into an existing continuity history. For that case, retain the existing identities and use [external revision preview and acceptance](EXTERNAL_REVISIONS.md).

## Preview, inspect, apply

Save the artist's document to an owned input file first. Unsaved editor changes are not included. These commands launch background Blender; they do not connect to or save over the open editor. Use the same Blender version for both steps, and choose new output directories.

```powershell
python -m dcc_harness adopt-preview C:/project/input.blend --blender 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --output-dir C:/project/adoption-preview
```

Read `adoption-preview/plan.json`. It lists the native names and exact missing properties to be assigned, the saved source path/hash, active scene, and shared-data inventory. `READY` means the identity proposal can be applied; it does not mean the scene passes native checks. `BLOCKED` returns exit code 1 and a list of conflicts with no proposed writes.

When the proposal matches the intended scope, apply it:

```powershell
python -m dcc_harness adopt-apply C:/project/adoption-preview/plan.json --blender 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --output-dir C:/project/adopted
```

Apply verifies the source bytes, opens that source in a fresh process, and rebuilds the proposal against the actual inventory before the first property write. It saves `adopted/checkpoint.blend`, then a second process reopens it and writes `observation.json`. `receipt.json` records source integrity, assigned-property count, native checkpoint hash, observation path and remaining issues. Requests, plan and Blender logs remain alongside the result.

- `READY_FOR_START` means the saved observation has no issues and is clean. Review the scene and use the resulting checkpoint/observation with the existing `start` command and your brief, decisions and handoff.
- `NEEDS_REPAIR` returns exit code 1 and retains the saved candidate plus observation. Identity assignment succeeded but observer issues still prevent `start`. Inspect and repair a separate owned copy; do not treat this as an instruction to redispatch.
- An exception or interrupted process can leave partial outputs. Inspect those files and logs before continuing. Existing output directories are never reused, even after failure.

```powershell
python -m dcc_harness start C:/project/state --checkpoint C:/project/adopted/checkpoint.blend --observation C:/project/adopted/observation.json --brief-file C:/project/BRIEF.md --decisions C:/project/decisions.json --handoff C:/project/CONTINUE.md
python -m dcc_harness resume C:/project/state
```

These are example paths, not bundled inputs. Adoption does not create a project store or grant artistic acceptance automatically.

## Identity rules

| Situation | Result |
|---|---|
| Valid existing ID | Preserve it exactly |
| Missing object instance ID | Assign one unique placement ID |
| Missing asset IDs on objects sharing one mesh | Reuse an unambiguous existing asset ID among that mesh's users, otherwise generate one shared definition ID |
| Different meshes with missing asset IDs | Generate separate definitions; no semantic grouping is guessed |
| Explicit asset grouping across different meshes | Preserve it |
| Missing material ID | Assign one ID to that actual shared material |
| Present empty/invalid ID or duplicate instance/material ID touching the active scene | Block; do not guess an original or repair IDs |
| Missing asset ID with conflicting IDs among shared mesh users | Block for an explicit binding decision |
| A proposed write touches a linked/override object or material | Block for explicit local ownership |
| A proposed object write affects another scene, or a material has outside/indirect users | Block the entire plan |

Generated IDs are opaque UUIDs derived from the frozen plan's namespace and initial native names. They persist as custom properties after saving; later renaming does not regenerate them. Names locate targets during this initial adoption only. Previewing again creates a different namespace, so retain the chosen plan with its result.

All active-scene objects are included, including hidden ones. Global datablocks are inspected for collisions and sharing, but missing IDs outside the active scene are not assigned. Material ownership checks use Blender's [native datablock user map](https://docs.blender.org/api/5.1/bpy.types.BlendData.html#bpy.types.BlendData.user_map); indirect node-group users are conservatively left for explicit handling. Already identified shared datablocks need no identity write.

## Boundaries and validation

The helper writes identity metadata only. It does not repair topology, missing textures, unsupported instancing or observation coverage gaps. Separate observation can still reject the result. It neither packs external dependencies nor establishes correspondence for Geometry Nodes instances. Changes to external images/libraries are not covered by the source `.blend` hash.

Blender starts with factory settings and automatic script execution disabled. This is not a sandbox or a native transaction, and it does not fence other writers. Keep the input and external dependencies stable during the operation. A repeated deliberate apply of the same frozen plan to a different empty directory produces another copy with the same proposed IDs; there is no global consumed-plan ledger.

Run the portable suite normally. The separate native qualification creates disposable fixtures and checks source preservation, existing IDs, shared assets, independent content snapshots, saved start/resume, blocked cases, unsupported observation results and CLI paths containing spaces:

```powershell
python scripts/qualify_adoption.py --blender 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --runtime . --out runs/my-adoption-check
```

Omit `--runtime` when testing an installed wheel from outside the checkout. The probe script still comes from this repository. See [qualification results](ADOPTION_0_4_9_RESULTS.md) for the tested scope; identity adoption is not a visual-quality experiment.
