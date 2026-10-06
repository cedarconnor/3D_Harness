# Longer continuity experiment — October 4, 2026

Sixteen fresh agents completed four successive sessions on each of four environment workflows. Fourteen saved stages passed the original independent native checks; three workflows completed all requests and one stopped after stage 2. The incomplete stages remain in the results and gallery. This round demonstrates useful continuation and failure evidence, but does not establish a harness advantage.

For an assessment with fewer cues, review the [anonymous gallery](../runs/continuity-round-2026-10-04/review/index.html) using the [review guide](CONTINUITY_REVIEW.md) before reading the technical findings below. The [portable review ZIP](../runs/continuity-round-2026-10-04/continuity-review.zip) contains the same public files. Artist scores are blank. The assignment mapping remains private; filenames in the gallery do not identify methods.

## What was tested

Two plain-MCP workflows and two workflows with the minimal continuity prototype started from identical copies of the artist's preferred earlier courtyard. Each session used a new agent with no prior producer conversation. Requests accumulated: extend the environment, develop the garden and props, revise dimensions/materials around an artist placement edit, then reconcile a delivered plaque and finish lanterns/signage. Each received the same frozen requirements and preservation rules. The harness condition additionally retained accepted checkpoint history, decisions and executable checks.

One agent owned the live Blender writer at a time. Independent background evaluation read immutable accepted files. Controlled events moved a stool and created a plaque with withheld acknowledgement; these were actual native changes with simulated uncertainty, not editor crashes. The [frozen protocol](CONTINUITY_EXPERIMENT.md) records budgets and exclusions.

| Evidence | Result |
|---|---|
| Production sessions | 16 fresh agents; all required output packages retained |
| Independent native checks | 14/16 passed; two failures retained |
| Plain-MCP completion | Both workflows completed; 8/8 stages passed |
| Continuity completion | One complete, one interrupted; 6/8 stages passed |
| Final plaque | Exactly one in each final native scene; this does not prove visibility |
| Review evidence | 96 independent stage images plus six shared baseline images |
| Export integrity | All 102 decoded images match their captures; 104-file ZIP verified |
| Independent image QA | Two fresh reviewers inspected all 102 unique images; both also inspected the baseline |
| Artist acceptance / native editability | Unassessed; no scores or repair minutes invented |

The two reviewers found no broken image references, explicit method labels or private paths in the public package. They identified framing limitations: pergolas obscure some garden details, and tabletop props/signs are too small for exact inspection. One incomplete sequence does not visibly demonstrate later requested additions. These findings do not assign an artistic winner. Browser layout, score interaction and download behavior remain untested because local-file browser navigation was blocked; file and image checks do not establish interactive behavior.

## What the longer sequence exposed

**A measurement error stopped valid progress.** During the controlled stool translation, four leg widths derived from world-space bounds changed by approximately `4.768e-7 m`. Read-only native inspection found unchanged authored geometry, linear transform, topology and source UV data. Float32 subtraction at the new world position caused the apparent resize. The continuity agent followed its strict preservation gate, refused to adopt the event and left the stage unfinished. The next fresh agent inherited that blocked history and could not finish either. This is a harness failure in the original experiment, not a successful recovery or an agent time-limit failure.

**Reconciliation and publication are separate.** Both continuity workflows explicitly reconciled the supplied plaque operation with no pending journal operation afterward and no duplicate registration of the same payload. In the blocked workflow, the begin/reconciliation events remain outside the last accepted checkpoint, which is still stage 2. Clearing an uncertain operation therefore did not make the creative work complete or the history current. These journal facts do not establish interception or exactly-once native execution.

The completed continuity workflow passed the artist-edit adoption audit. Its delivery checkpoint had different saved-file bytes from the supplied event file, so the original byte-identity audit did not pass. A separate supplement reopened the supplied file, published file and parent with the original observer: all measured-state equivalence comparisons and event-check recomputations passed, and the plaque count was one after delivery versus zero in the parent. The original byte mismatch is retained; unmeasured native state is not certified equivalent.

**Later requirements can conflict with earlier preservation rules.** One workflow added a tray in stage 1. Stage 2 introduced a future plaque reservation over that tray while forbidding changes to earlier objects. The agent's handoffs explicitly recorded the conflict. Later instructions restricted repairs to other targets. Read-only inspection confirmed that all five tray objects stayed unchanged through stage 4; six of nine vertical sample rays hit the tray before the plaque, while three reached an exposed plaque edge. This confirms partial obstruction, not total invisibility or exact solid intersection. The frozen numeric checks do not test this clearance and still pass. A future preflight should detect the contradiction and identify the specific preservation rule that needs revision.

Together these cases support a narrower next step: reliable measured gates, explicit conflicting requirements, and a bounded recovery process. They do not justify broadening the scheduler, DCC adapters or client installers yet.

## Separately qualified correction

Only after all sixteen original evaluations finished, version **0.1.1** changed dimension measurement to evaluated world-oriented extents with translation excluded before subtraction. World bounds still describe placement. The correction adds no tolerance or preservation waiver. Observation coverage is now version 2; matching v1 remains supported, mixed/unknown versions fail, and old histories are not silently migrated. A second validation defect found during qualification is also fixed: nonfinite authored/evaluated coordinates are explicitly rejected, including a later-vertex NaN that extrema could hide.

Validation of the integrated and installed package:

- Full suite: **96 tests, 94 passed, two Windows symlink-permission skips**.
- New wheel installed in a separate environment and exercised outside the checkout; all 16 frozen packet seals verified and both legacy final stores remained readable.
- Installed native evaluator: **15 cases matched their expected outcomes**—two valid cases passed and thirteen fault cases were rejected. Four verified nonfinite injections were rejected. Native input hashes stayed unchanged.
- The retained translation event passes when freshly observed as v2. Its original v1 failure and mixed-version rejections remain reproducible.
- A reusable native regression builds its own disposable fixtures and checks near/far translation, geometry/scale/rotation faults, empty/degenerate extents and later-vertex NaN rejection.

The fix has not been used to replay or regrade the failed creative stages. It establishes the corrected measurement behavior, not the outcome of a new creative comparison. See [usage and version compatibility](CONTINUITY_USAGE.md) and [qualification details](VALIDATION.md).

## Time, scope and remaining decision

Agents reported **186.94 minutes** across sixteen sessions; coordinator-observed intervals total **193.72 minutes**, including scheduling latency. Individual sessions stayed within the 20-minute cap. There were **57 producer captures** and **96 independent stage captures**, plus the shared baseline. Reported timed producer rendering totals **155.26 seconds** and independent stage rendering **235.89 seconds**; these exclude process startup, authoring, review, baseline rendering and infrastructure qualification. One producer capture was viewed inline but could not be retained locally; its count remains included. Timing sources vary, including direct timers and final-session PNG metadata. These are measured/reported usage bounds, not billing or throughput benchmarks.

Token usage, dollars, artist repair time and native editing effort are unavailable. The interrupted workflow did less work, so its shorter duration cannot support an efficiency claim. The scene and controlled revisions are more sustained than the earlier comparison, but this is still four bounded sessions per workflow on one environment, with two repeats per method. Shared tools, ambient skill descriptions and filesystem access limit isolation. General multi-hour autonomy, crash recovery, production topology/UV quality and cross-DCC continuity remain unqualified.

Next, assess the four-stage visual sequences and inspect native editing effort. Then define a small conflict-preflight and blocked-checkpoint recovery test, followed by a held-out environment if the workflow remains useful. Artist review and the held-out brief remain investment gates.

Blender has been restored to the original saved engineering scene, with its file hash unchanged and 257 objects in the active scene. All trial files remain available for inspection. No generated scene was substituted for the original.

## Local evidence index

Generated files are excluded from Git. Technical receipts below contain method information; keep them closed during anonymous visual scoring. Paths are relative to `runs/continuity-round-2026-10-04/`.

| Evidence | Local path |
|---|---|
| Original session measurements and native reports | `private/final-measurements.json`, `private/evaluation/` |
| Immutable accepted files / packet seals | `private/accepted/`, `private/issued/`, `private/results/` |
| Original evaluator snapshot | `private/evaluator-source-v2/inventory.json` (snapshot name; observation semantics are v1) |
| Export and ZIP verification | `private/export-qualification.json` |
| Public-only reviewer reports | `private/anonymous-qa-1/`, `private/anonymous-qa-2/` |
| Original translation failure proof | `private/diagnostics/stool-translation-aabb/native-proof.json` |
| State protocol audits and byte-equivalence supplement | `private/diagnostics/state-protocol-audit/` |
| Tray/plaque scope and native visibility samples | `private/diagnostics/plaque-clearance/receipt.json` |
| Integration / installed wheel checks | `private/extent-v2-integration.json`, `private/package-smoke-v3.json` |
| Installed native regression | `private/installed-native-qualification/qualification.json`, `private/installed-extent-regression/qualification.json` |
| Original scene restoration | `private/restoration.json`, `private/restoration-scope-check.json` |

The initial restoration receipt compared all 259 object datablocks with the original 257 active-scene objects. A live follow-up found the two extra datablocks were the out-of-scene `Camera` and `Light`; the active-scene count, expected path, clean editor state and saved-file hash all match. The initial receipt and scope correction are both retained. A separate coordinator ordering receipt records one early evaluation dispatch during acceptance; hashes and timestamps confirm the completed acceptance receipt preceded observation, with unchanged sources. Neither diagnostic changed any creative grade.
