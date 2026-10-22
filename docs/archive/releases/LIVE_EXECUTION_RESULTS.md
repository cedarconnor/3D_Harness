# Live Blender execution qualification

Target: 0.22.0, Python 3.11, MCP SDK 1.26.0 and Blender 5.1.1 on Windows. The maintained release gate is running; this document does not yet claim installed-release qualification.

## Implemented scope

- Shared background/live execution with immutable UUIDs, stage admission, budgets, retained inputs and independent publication checks.
- Explicit session/scene pairing, reload generations, full bridge manifests, bounded structured inspection, and recoverable adoption of dirty/untitled scenes.
- Transform, Principled material input, bounded modifier and independently qualified node-asset operations.
- Explicit external-edit import, reconnect, cooperative cancellation, ambiguity-preserving status, and recovery that archives current state before a requested restore.
- Real stdio MCP/CLI live controls, fixed-setting previews, autonomous stage advancement and separate owner-gated completion.

## Retained evidence

The current machine-readable release gate writes to `runs/overhaul/p21-release-final/VERIFICATION.json`, with per-check logs and a fresh installed runtime. The live matrix retains one result and audit per case under its `native-live` directory. Local run data is excluded from the distributed rule bundle.

The first candidate passed 532 source and installed tests (two permission skips each), artifact parity and the existing native gates, then failed at the live verifier's package-layout import. The fresh independent review found that defect plus four material issues: unsaved image buffers, definitive pre-mutation recovery refusals, descriptor disclosure through the general MCP reader, and a handshake that measured disk bytes rather than the loaded implementation. All five received focused regressions and fixes; the full rebuilt release gate must pass before acceptance.

`p21-review-dirty-red` reproduces acceptance of a dirty external-image buffer as a recoverable copy. `p21-review-preservation-final` proves refusal before copying/restoring, with original pixels and disk files unchanged, plus pre-mutation busy refusal and refusal of unqualified external audio. Portable regressions cover package imports, in-place bridge replacement, private descriptor reads and recovery retries after known refusal versus no replay after a lost reply.

The conservative external-dependency check initially also rejected Blender's empty default sequence editor. `p21-review-empty-sequencer-red` reproduces that defect; `p21-review-empty-sequencer-green` verifies the corrected strip-based check. `p21-review-attach-green-r2` and `p21-review-recovery-green` additionally prove native package imports, untitled adoption/replay and mutation-before-error followed by independently verified archive/restore. The intermediate `p21-release-fixed` artifact is superseded by this correction.

Before the artifact gate, the source suite ran 529 tests: 527 passed and two existing Windows permission cases skipped. Focused manifest tests additionally reproduce and fix altered/missing exports, incompatible bridge code before authentication, and private-token redaction during handshake failures.

Native development evidence includes `p21-task4-*` and `p21-task5-*` under `runs/overhaul`: source-file preservation, archived texture reopen, repeat modifier/node reuse, shared material scope, before/after publication races, queued reload/cancellation, non-cooperative eventual outcomes, lost replies, stale recovery refusal, explicit refresh/reconnect, previews and owner-import/stale-review behavior. These development runs are narrower than the required installed release matrix.

## Qualification limits

This is owned fixture evidence, not artist approval or production-scene qualification. Live built-ins require supported Object-mode scenes and refuse unmeasured animation/rig/simulation/linked/override/cross-scene contexts. Initial node assets support group input/output and Geometry Node Transform; arbitrary operators and third-party add-ons are not live-executable through this increment. Background trusted scripting remains available in background projects.

Unsaved image pixels must be explicitly saved before managed snapshots, copies or recovery. Audio, video/sequence data, volumes/cache datablocks and unpacked external fonts are refused because their preservation has not been qualified. An installed add-on replacement requires restarting Blender; reloading only the package initializer cannot certify its already-loaded sibling modules. Known structured pre-mutation recovery refusals permit another explicit attempt; missing or ambiguous responses still block replay.

The old telemetry-free upstream derivative and MIT notice are retained. The add-on makes no automatic external calls and registers no user-activity handlers. Explicit local job/verification records are retained. No user-wide client registration, upstream provider installation or GitHub push is part of this release work.
