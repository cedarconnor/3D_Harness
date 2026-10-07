---
name: verification-before-completion-dcc
description: Use when about to claim an asset, stage, task, or export is done, clean, applied, or ready — requires running the measuring tool and reading its output in this message before any success claim
---

# Verification Before Completion (DCC)

Adapted from superpowers `verification-before-completion`.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the check in this message, you cannot claim it passes. A render is not a check unless the thing you're claiming is visible in it.

## The Gate

```
BEFORE claiming any status:
1. IDENTIFY  which tool proves this claim (assert_scene / measure / check_asset_ready / verify_export / a named REVIEW_* render)
2. RUN       it, fully, now
3. READ      the full output; count failures
4. VERIFY    does the output confirm the claim?
   NO  → state the actual status with the evidence
   YES → state the claim WITH the evidence
5. ONLY THEN claim
```

## Claims → Evidence

| Claim | Requires | Not sufficient |
|---|---|---|
| "Model is clean" | `measure`: 0 non-manifold, 0 loose, 0 inverted, 0 doubles | render looked fine; script ran without error |
| "Within budget" | `measure`: tri_count vs spec, with the number | "it's low poly" |
| "Correct scale / placement" | `assert_scene` bbox + pivot within tol | looks right in viewport |
| "UVs done" | `assert_uv`: overlap 0, density in tol, island count | UV editor screenshot |
| "Textures applied" | `assert_material`: all slots bound, 0 missing images, colorspace per channel | material shows in viewport |
| "Material matches reference" | lookdev turntable from fixed cams + narrow VLM questions answered | one hero render |
| "Export works" | `verify_export`: re-import round-trip, counts/bounds/materials match | file exists on disk |
| "Asset ready" | `check_asset_ready` against spec: all rules pass | all tasks complete in ledger |
| "Task done" (as controller) | implementer report has RED + GREEN evidence; reviewer approved; scene_delta matches `Produces` | implementer said DONE |
| "Nothing regressed" | re-run every prior task's assert → all pass | current task's assert passes |
| "Fixed the seam" | before/after render from the same `REVIEW_*` cam + the assert that caught it | code changed |

## Red Flags — STOP

- "should", "probably", "looks like", "seems clean"
- "Great!", "Perfect!", "Done!" before output is in front of you
- trusting an implementer's DONE without reading its report
- checking one object and extrapolating to the asset
- a render from a camera you just moved
- claiming export success because the operator returned `{'FINISHED'}`

## Rationalizations

| Excuse | Reality |
|---|---|
| "The viewport shows it" | Viewport doesn't show overlap, manifoldness, scale, colorspace |
| "measure passed last task" | Last task. Run it now. |
| "Agent said success" | Read `scene_delta`. Agents misreport. |
| "It's a 2-second fix, no need to re-assert" | 2-second fixes flip normals. Re-assert. |
| "Export returned FINISHED" | FINISHED ≠ correct. Round-trip it. |
| "Different words so the rule doesn't apply" | Spirit over letter. |

## Patterns

```
✅ [run check_asset_ready] [see: 23/23 rules pass] "Asset ready — 23/23"
❌ "All tasks complete, asset should be ready"

✅ [render REVIEW_3q before + after] [see seam gone] [run assert that caught it → PASS] "Seam fixed"
❌ "Adjusted the mirror modifier, seam should be gone"

✅ [re-run all 11 prior asserts] [see 11/11] "No regressions"
❌ "Only touched the shade, nothing else affected"
```
