# Lossless observation storage — 0.4.6

Engineering evaluation, October 5, 2026. The accepted garden remains checkpoint 9 from [the roof repair](ROOF_0_4_5_RESULTS.md). This release improves the cost of retaining and reading future evidence; it does not change the scene or establish a visual-quality advantage.

## Result on the accepted environment

The observation contains 1,289 objects and 9,136,228 evaluated UV scalar values across 1,180 arrays. Only 406 arrays are unique. Broadleaf plants account for 7,308,000 of those values; many instances repeat an identical evaluated array.

| Representation | Bytes | Decimal MB |
| --- | ---: | ---: |
| Existing formatted observation | 214,365,648 | 214.37 |
| Same ordinary JSON with compact whitespace, calculated size | 103,109,788 | 103.11 |
| Compact whitespace plus pooled UV arrays | 21,849,138 | 21.85 |

The complete format reduces storage by 89.81%. Pooling alone reduces the already compact JSON size by 78.81%. The calculated unpooled size includes LF rather than the Windows writer's CRLF, a one-byte difference. There is no lossy precision reduction. Full expanded canonical content, including metadata, has the same digest: `4b49a25076b6800b0ea29b7b7f61dbf1884ed367ba3d1cea002e445243b16036`. The observation revision remains `bd456d3cbfbcd23d21fe991624e7ecfdf782c44269ebbe682e24a9da52a0815c`.

Three paired trials used the installed 0.4.6 runtime in six fresh Python processes. Pair order alternated. Source hashing warmed the filesystem cache outside the timed region; no other qualification work ran during these timings.

| Read plus logical validation | Plain JSON | Compact storage |
| --- | ---: | ---: |
| Pair 1 | 5.249 s | 4.150 s |
| Pair 2 | 5.310 s | 4.092 s |
| Pair 3 | 5.409 s | 4.148 s |
| Median | 5.310 s | 4.148 s |

This is **1.28× faster** for reading and validating this observation. One packing run took 7.80 seconds, including logical validation, hashing, pooling, serialization and writing. Encoding is an additional cost when the evidence is first produced.

The original nine-checkpoint store was verified separately by 0.4.6 in 32.49 seconds. Its continuation packet and complete retained-file inventory matched the 0.4.5 baseline exactly. Old observation files were not rewritten. That timing is an integrity check, not a matched full-history speedup claim; the baseline was profiled and the new run was not.

## Implementation and checks

`dcc_harness.observation_storage` supplies an opt-in storage envelope. `evidence.read_json` restores ordinary observations; `write_json(..., compact_observation=True)` writes new compact files. `pack-observation` makes a new validated copy and refuses an existing destination. Default writing remains plain JSON.

Source and isolated installed-wheel suites each ran **165 tests: 163 passed, two Windows symlink tests skipped**. Eight added tests cover:

- Exact canonical round-trip, including signed zero and integer/float distinctions; independent arrays after decoding.
- Modified blocks, missing/extra references, unused blocks, unknown storage versions, invalid numeric values and bounded expansion.
- A rehashed changed block that still fails the original logical observation revision.
- CLI source preservation and exclusive destination creation.
- Identical UV/material regression verdicts before and after storage conversion.
- Mixed plain/compact history, unresolved-operation reconciliation and rejection of tampering in either retained format.

The `dcc-harness` skill and everyday workflow now describe the opt-in path and compatible readers. The skill validator passes. This is a narrow documentation update, not a new independent agent behavior trial.

## Native qualification

The installed wheel completed a separate Blender 5.1.1 continuation using the accepted checkpoint as read-only input:

1. Independently observed the source and established a plain-JSON baseline in a new engineering project.
2. Reserved and executed one retained script changing shared metal roughness from approximately .38 to .46. An omitted-user negative control was rejected before mutation.
3. A fresh OS process returned `RECONCILE` while the result was unresolved.
4. A separate background Blender process reopened the saved candidate and wrote a compact observation.
5. `finish_edit(..., reconciled=True)` recomputed the contract and published checkpoint 2 without redispatch. A subsequent full review returned `READY_FOR_INSPECTION`.

The published compact observation has 335 pooled blocks and is 21,951,643 bytes; its supplied bytes are preserved exactly. This is a newly observed engineering revision, so its block count differs from the earlier accepted observation used for the storage benchmark. Existing UV-noise tolerances remain unchanged. The architectural aperture and linked-material controls in the qualification runner also passed.

The production source native SHA-256 remains `efb64030397fc571324ae8a444f51fa33555b420b8b7a4210e8829d2f9aa932d`. The installed wheel and source have 25 matching Python modules. Wheel SHA-256: `c1e9be26fc11c33ea880e0bb2a9a09d014cce4bac33253272b74bcde0aeac922`.

This is an authored engineering test using independent processes, not a blind agent comparison or a real dropped-transport injection. The engineering material revision is not published to the artist's production project.

## Boundaries and evidence

Compact files require harness 0.4.6 or later and the `evidence.read_json` decoder. Expanded arrays still occupy memory, and canonical logical validation still visits the full content. There is a 50-million-UV-value expansion limit. Full history verification remains mandatory and grows with history. No cache bypass, reduced measurement coverage, scheduler, automatic recovery, external-write interception or multi-DCC support was added.

Use [the storage guide](OBSERVATION_STORAGE.md) for usage and compatibility. Local evidence is in [the run folder](../runs/compact-observation-2026-10-05/): `payload-profile.json`, `packed/result.json`, `storage-attribution.json`, `paired-benchmark.json`, `legacy-history-check/result.json`, `native-qualification/qualification.json`, both test logs and the isolated wheel/runtime. [VERIFICATION.json](../runs/compact-observation-2026-10-05/VERIFICATION.json) binds the results, module hashes and package. Existing native scene and observation hashes remain unchanged.
