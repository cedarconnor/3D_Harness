# Native observation optimization — version 0.4.8

On the accepted 1,289-object garden, median native observation time fell from **41.52 to 22.53 seconds**, a **1.84×** speed ratio across three alternating pairs. The optimization reuses shared material graphs and authored mesh/UV hashes within one observation call. It does not retain those caches between observations, change the observation schema, skip history verification or change a numerical tolerance.

## Implementation and qualification

Material cache keys are actual Blender material datablocks; duplicate caller IDs still produce diagnostics. Source mesh hashes are cached by the native mesh datablock. Evaluated meshes, UV arrays, transforms, bounds and modifier settings remain specific to each object. See [behavior and reproduction commands](OBSERVATION_PERFORMANCE.md).

The source and isolated installed-wheel suites each ran 171 tests: 169 passed and two Windows symlink-permission cases skipped. Twenty-six module hashes match the source and installed 0.4.8 package. The first installed-suite invocation had an incorrect relative `PYTHONPATH`; its discovery failure is retained, and the corrected invocation ran outside the checkout against the isolated install.

Eight native fixture states in Blender 5.1.1 matched the prior installed 0.4.7 observer **exactly except timestamps**: shared meshes/materials with object-specific bevel and transforms; shader changes; shared source geometry changes; authored UV changes; changed external texture bytes; distinct datablocks sharing a caller ID; repaired identity; and mutation of a previously returned observation. The deliberate edits were detected on the following call. The fixture never saved over artist work.

The quality validator now includes `observation_storage.py` in its runtime fingerprint. A regression test confirms that a changed decoder or continuity loader invalidates an old review binding. Old reviews remain usable with their retained runtime; upgrading requires a new audit and review rather than overwriting historical evidence.

## Retained strict-comparison failure

The production-scene comparison did **not** achieve bitwise identity: evaluated bevel UVs varied by tiny float32 amounts. The original exact-comparison reports remain failed. A separate old-observer-versus-old-observer control reproduced the same class of variability, without the optimization.

An attribution pass requires exact equality of every other observed field, including authored mesh/UV hashes, material graphs, evaluated geometry, transforms, settings, coverage and checkpoint binding. Only evaluated UV values and their derived hashes differ. These differences pass the already-qualified version 3 UV policy and a no-edit continuity contract. That policy and its limits are unchanged. This supports compatibility with the existing preservation contract; it does not support a bitwise-identical large-scene claim.

| Alternating pair | Prior observer | Optimized observer |
|---|---:|---:|
| 1, prior first | 40.01 s | 22.53 s |
| 2, optimized first | 42.78 s | 23.63 s |
| 3, prior first | 41.52 s | 22.42 s |

Timers surround `observe()` only. Serialization, startup and comparison are excluded. The process uses the same saved native file and warms Blender/filesystem state; other resident applications were not disabled. This is one workstation and one scene, not a general performance guarantee. The earlier profile was diagnostic and was not used for this timing claim.

## Continuation and artifacts

The installed wheel is exercised by a separate native continuation: observe the saved shed, reserve a shared-material revision, save it once, detect the unresolved write from a fresh Python process, reopen through a fresh Blender process, reconcile without redispatch and publish a compact observation. Its construction fixture also checks widened apertures. This is an engineering branch, not an accepted art revision.

Both runtimes verify the real production checkpoint history and produce identical continuation packets. Retained checkpoint files remain unchanged, checkpoint 9 is still active, and the three rejected context studies have closed outcomes. The [terrain study](TERRAIN_0_4_7_RESULTS.md) documents their visual shortcomings.

Local receipts: [verification](../runs/observe-cache-2026-10-05/VERIFICATION.json), [UV attribution](../runs/observe-cache-2026-10-05/uv-attribution.json), [native fixture](../runs/observe-cache-2026-10-05/native-fixture/report.json), [installed native continuation](../runs/observe-cache-2026-10-05/native-continuation/qualification.json), [production history](../runs/observe-cache-2026-10-05/production-history.json), and [continuation handoff](../runs/observe-cache-2026-10-05/CONTINUE.md).

Background Blender supplies this evidence; live MCP execution, independent agent behavior, visual-quality superiority, animation, multi-DCC adapters and managed dispatch fencing remain outside the qualification.
