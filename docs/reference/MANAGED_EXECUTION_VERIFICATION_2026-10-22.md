# Adversarial fixes and managed execution verification

Implementation: v0.20.0 on `codex/managed-execution-overhaul`, based on `0b8c30c`. The original [adversarial review](ADVERSARIAL_PACKAGE_REVIEW_2026-10-22.md) is retained as the baseline audit.

## Findings addressed

| Finding | Change | Regression evidence |
|---|---|---|
| F1 Incorrect physical GLB scale | Reject source unit scale other than 1 before writing a GLB. Successful records explicitly use metres. | Native scales 1, .01 and .1, positive gap and penetration fixtures; source hashes preserved; independent GLB position extent at scale 1. |
| F2 Stale stage readiness | Derive current validity from blocking feedback, checkpoint evidence and pinned checks; propagate to downstream admission and guidance. Historical receipts remain. Required objects include bound material dependencies; inherited stages use their binding evidence. | Changed target, unchanged observation, completed/inherited material change, blocked downstream submission. |
| F3 Partial review import | Validate all items before approval/writes. Stable page/item request identities recover earlier committed items after interruption. Committed items cannot silently change. | Invalid first/last note, corrected export, exact replay, interrupted approval then corrected uncommitted note. |
| F4 Relation units | Convert footprint/reach to scene coordinates; measured gaps and penetration return metres with source scale recorded. | Six native cases across scales 1/.01/.1, positive gap and negative penetration. |
| F5 Malformed dimensional evidence | Shared finite numeric/vector validation across assertion and comparison consumers; malformed requested dimensions and tolerance rejected before comparison. | Empty/short/long/non-numeric/boolean dimensions, malformed tolerances, old synthetic fixture updated to carry measured dimensions. |
| F6 Stale adoption qualification | Positive collection-instance case plus actually unsupported vertex instancer. | Maintained adoption qualifier completes its negative, identity-preservation, CLI and source-unchanged cases. |

## Managed execution

`execution.py` is the application service behind run creation/status/execution/submission/cancellation/reconciliation. Managed roots reject direct public native-journal/checkpoint mutation. Stage policy selects agent review or owner review; the native execution/check/publication path is shared. A caller-provided durable operation UUID cannot dispatch twice, even after a controller interruption.

The independent final reviewer found five further defects. Each received a failing reproduction and a fix: admission after a concurrent stage completion, bound-material dependency freshness, inherited evidence freshness, a new review cycle after stage reopen, and journal-pointer recovery after an interrupted reservation. No reviewer findings were deferred.

Additional checks exercise two concurrent controllers, actual controller-process termination, timeout and cancellation of owned subprocesses, retained-input changes, rejected legacy bypasses, failed worker responses, and interruption before/after native checking and publication. `brief`, `next` and `requirements` use the effective managed policy and point to managed commands.

## Release verification

The maintained command is:

```powershell
python scripts/verify_release.py --out runs/overhaul/release-020-verified --blender "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
```

All release gates passed against the final runtime. Source and installed Python files were compared byte-for-byte after verification: no differences.

| Gate | Result |
|---|---|
| Source suite | 467 run, 465 passed, two Windows symlink-permission skips; 227.809 s |
| Wheel build and isolated install | Passed; no runtime dependencies |
| Installed-runtime suite | 467 run, 465 passed, the same two skips; 206.224 s; imported module path verified outside checkout |
| Installed CLI | Passed |
| Installed native units | Six scale/gap cases passed, with unchanged source hashes and independent GLB extent check |
| Installed native adoption | Passed all positive/negative cases, including supported collection instancing and unsupported vertex instancing |
| Installed native execution | Two publications in each mode; identical requests replay receipts; owner gate enforced using a synthetic authority fixture |
| Native timeout and cancellation | Passed; accepted checkpoint unchanged, explicit rejection closes each retained attempt |
| Final whitespace check | `git diff --check` passed |

Artifact: `runs/overhaul/release-020-verified/wheels/dcc_harness-0.20.0-py3-none-any.whl`.
SHA-256: `e5ecaf61252e1b48459047ce3e333f74e30ac69a5b540dc6ba8c2a1d91a09d9c`.
Machine-readable evidence and complete logs: `runs/overhaul/release-020-verified/VERIFICATION.json`.

The source suite emitted the existing `ResourceWarning` from the detached-render path (`render.start_detached` drops its `Popen` handle). A focused warning-enabled render run also passed all 19 tests and reproduced the warning. The installed suite did not emit it. The new managed execution path terminates/reaps its owned child and is tested separately.

## Boundaries

- Non-unit-scale GLB conversion is deliberately unsupported; rejection replaces false certification.
- The calling agent supplies reasoning, scripts, visual inspection and stage evidence. This release does not embed an LLM backend or MCP server.
- The gated native qualification uses a synthetic owner console in disposable projects. It verifies the authority path, not actual human approval or artistic quality.
- Controller termination during dispatch was tested at the process boundary. A controller crash while holding `workflow.lock`, a partial checkpoint bundle, or damaged immutable files remains an explicit inspection stop. A surviving Blender child must be inspected/stopped before reconciliation; scripts are trusted local code, not sandboxed code.
- Old exact runtime pins are not silently migrated. Budgets and mode are immutable per run; an exhausted/cancelled run requires a separately authorized new project/run from its accepted checkpoint.
- Installed-runtime tests still use source tests and some documentation fixtures. This is not a clean-machine installer, skills distribution or combined-MCP handshake test.
- No live artist scene, user MCP configuration, Git remote or `main` branch is modified.
