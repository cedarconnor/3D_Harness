# Native observation reuse within one call

Version 0.4.8 measures each shared material graph once per `blender.observe()` call and each authored mesh/UV hash once per `continuity_blender.enhance()` call. Keys are actual Blender datablock pointers, not caller-assigned IDs. Duplicate-ID diagnostics still run for every material binding.

The next call starts with empty caches. Shader edits, shared source geometry/UV edits and changed external texture bytes are read again. Evaluated meshes, UV arrays, object transforms, bounds and modifiers remain object-specific. No persistent scene cache, dirty-handler dependency, observation schema change or new numerical tolerance is introduced. Returned observations do not share a cache with future calls.

This optimization helps scenes with many placements using the same definitions. It does not skip historical checkpoint verification or make general claims about DCC latency. File hashing, evaluated geometry, UV extraction, normalization and JSON handling remain part of the cost. Optional [compact storage](OBSERVATION_STORAGE.md) is a separate optimization.

## Reproduce the native checks

Build and install the baseline and candidate wheels into separate directories first. In a disposable background process:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/qualify_observation_cache.py -- --baseline BASELINE_INSTALL --candidate CANDIDATE_INSTALL --out NEW_FIXTURE_OUTPUT
```

The fixture compares both runtimes after eight native states: shared definitions with per-object bevel/placement differences, a shader edit, a shared geometry edit, an authored UV edit, changed external image bytes, conflicting material IDs, ID repair and mutation of a previously returned observation. Comparisons are exact except for `observed_at`. All edits occur in the disposable fixture, with no artist scene saved.

For a saved production scene, add `--source SCENE.blend --pairs 3`. The script opens it read-only, alternates baseline/candidate order in one Blender process and retains per-pair timings, revisions, runtime hashes and differences. Timing surrounds only `observe()`; JSON serialization and comparison are outside it. A mismatch fails and retains full observations for diagnosis. Do not relax equality to obtain a performance result.

The garden's strict comparison does fail because of evaluated bevel UV variability, also reproduced when both arguments point to the old runtime. [The retained attribution](OBSERVER_0_4_8_RESULTS.md) separately checks that all other fields are exact and that the unchanged version 3 UV policy admits those differences. That compatibility result does not change the strict report to a pass.

Close other evaluation workloads before a timing run. The paired benchmark is a same-machine measurement, with warm filesystem/Blender state after the first calls; it is not a controlled fleet benchmark. The script does not alter existing background applications.

The quality-review validator also fingerprints `observation_storage.py` from this release. Historical review bindings should be used with their retained runtime, or re-audited and reviewed explicitly under a new evidence filename.
