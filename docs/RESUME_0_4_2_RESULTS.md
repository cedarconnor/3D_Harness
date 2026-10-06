# Version 0.4.2 — faster verified continuation

October 5, 2026. A narrow refactor reduces repeated serialization during continuity reads and publication. On the saved six-checkpoint garden project, median resume time fell from **36.83 to 13.22 seconds** across three alternating pairs: **2.79× faster, or 64.1% less time**. All six resume packets were byte-identical and all 115 retained project files remained unchanged.

## What changed

The previous loader serialized a complete observation, its measured payload, several nested mappings, and each object again while deriving the registry. It then derived that registry again in the caller. Large evaluated UV arrays made these repeated passes expensive.

The loader now validates the measured payload through its existing revision digest, validates metadata outside that digest separately, and performs the same mapping/key/dependency checks without serializing those already-validated values again. It returns its derived registry to the status/publication caller for immediate reuse. The existing observation-only loader remains compatible for workflow, quality and trial callers.

There is no persistent verification cache or new dependency. Every status call still verifies the complete checkpoint chain, retained file hashes, observation/native binding, observation revision, derived registry, decision history and journal. Publication still validates the copied observation and rechecks source/copy hashes. The observation format, hash algorithm, UV policy, contracts and CLI commands are unchanged.

## Measurements

| Pair | Installed 0.4.1 baseline | 0.4.2 source |
|---|---:|---:|
| 1 | 38.299 s | 13.286 s |
| 2 | 36.816 s | 13.220 s |
| 3 | 36.827 s | 13.199 s |
| Median | 36.827 s | 13.220 s |

Each measurement used a fresh Python process on the same workstation and project. Baseline and candidate alternated. Integrity hashing before/after the timed call warmed the filesystem cache equally; this is not a cold-disk test. The source project contains six checkpoints, a final 1,461-object scene and an approximately 87 MB final observation. No Blender authoring or rendering was included in these timings.

A separate candidate profile took 13.41 seconds. JSON encoder self time fell from 29.50 seconds in the earlier profile to 5.94 seconds; canonical serialization calls fell from 16,502 to 114. Both profiles still show six observation-digest validations and 95 file-hash calls. Parsing and required digest generation now account for most remaining time. Full-history verification remains linear in retained history; this change does not qualify arbitrarily large projects.

Reproduce one measurement with a new output directory:

```powershell
python scripts/benchmark_resume.py --runtime . --project runs/shed-production-2026-10-05/project --out runs/my-resume-measurement
```

The helper hashes the source inventory outside the timed region, saves the complete packet and timing, and refuses to place outputs inside the project. Add `--profile` for a separate diagnostic run. Compare timing samples only under comparable load and cache conditions.

## Regression and packaging checks

- Source and installed-wheel suites each ran 144 tests: 142 passed, two Windows symlink-permission cases skipped.
- Four new tests cover nonfinite payload/extra metadata (including exponent overflow), valid-digest malformed mappings, tampered registry content with an updated inventory hash, and changed bytes in an older checkpoint with unchanged size and modification time. These tests pass on both the baseline and optimized loader.
- The new tests' first run had an incorrect assertion that initialization would not create an empty checkpoints directory. Inspection confirmed existing initialization creates that directory; the assertion now checks that no checkpoint was created. The rejected nonfinite input behavior itself already passed, and the original log is retained.
- The installed wheel contains 19 modules with identical hashes to the source package. Wheel SHA-256: `e2c675a9cee1084f7663a8be8b3e217c13e2dcc6e5b6eacb1d5fd4340f4c0160`.
- The installed wheel completed the native continuation qualification in Blender 5.1.1: independently observe the saved garden, start a separate project, reserve a shared-metal edit, save a candidate, detect the unresolved operation in a fresh Python process, reopen the candidate in a separate Blender process, reconcile without redispatch, publish and review. The check passed and the artistic source file remained unchanged. Two aperture configurations and guarded material controls also passed in disposable fixtures.
- A fresh process using the installed 0.4.2 wheel resumed the original production project in 13.11 seconds and returned the same packet and file inventory. The new qualification store was also read by both installed 0.4.1 and 0.4.2 runtimes with byte-identical packets, confirming compatibility in this exercised case.

## Evidence and limits

Local evidence is under `runs/resume-0.4.2-2026-10-05/`: six paired measurement directories, `benchmark-summary.json`, the candidate profile, baseline/candidate test logs, source/installed full-suite logs and package verification. The baseline runtime and source snapshot remain retained. The original garden store and artistic handoff are unchanged.

[Machine-readable verification](../runs/resume-0.4.2-2026-10-05/VERIFICATION.json) records final results. The [built wheel](../dist/dcc_harness-0.4.2-py3-none-any.whl) is a local runtime artifact; project skills remain separate in `.agents/skills/`.

This improves verified project continuation latency. It does not improve rendered appearance, demonstrate independent-agent skill gains, qualify the live MCP transport, or add scheduling/multi-DCC support. The [garden production assessment](PRODUCTION_0_4_1_RESULTS.md) still describes the current artwork and its foliage, ground and roof limitations.
