# P22 final review and implementation rulings

A fresh read-only reviewer examined the whole feature branch from `0b8c30c` to
`9575bf1`, with particular attention to P22 and its execution/publication seams.
It established three Important findings, no Critical finding, and one formatting-only
minor. The author accepted all three Important findings and made one fix pass.
There was no second reviewer pass; regressions and renewed release qualification
provide the fix evidence.

## Findings and fixes

1. **Artist policy authority could be removed.** An agent could replace an
   artist-confirmed required policy with an empty newer policy and then complete the
   stage. Rebinding now preserves prior artist authority. The regression verifies
   that an agent cannot change the event history or clear required evidence, while
   the owner can explicitly confirm a new version. Agent-authored policies remain
   revisable by the agent.
2. **Owner capability binding had no usable CLI confirmation.** The generic action
   route skipped `owner.authorize`. The CLI now confirms the exact policy, passes the
   approval into the shared transaction and preserves identical-request retry without
   another prompt. A separate regression proves agent terminals remain refused.
3. **Native node-group names were treated as portable identifiers.** Node-asset
   entries now accept bounded native text, including spaces and Unicode; function and
   operator entries use callable syntax. The serialized schema matches. Native
   onboarding now uses `Fixture Geometry 模型` in both GUI and background cases.

`final-review-red.log` retained all five failing focused regressions; the corresponding
green log passes all five. The renewed source and clean-installed suites each ran 593 tests: 591 passed and
two existing Windows permission cases skipped. `runs/p22-owner-stdio/VERIFICATION.json` proves all four
backend/mode combinations refuse both agent downgrade and artist impersonation through
the actual MCP route, while execution, retry, reuse and valid completion still work.
All 17 renewed release gates passed, including all 26 live scenarios, preservation,
native spaced/Unicode node-asset qualification and the complete add-on matrix.
The report is retained at `runs/p22-final/VERIFICATION.json`.

## Deferred minor

Whole-branch `git diff --check` reports extra blank lines at EOF in
`dcc_harness/bootstrap.py` and `scripts/qualify_mcp.py`. These have no behavior impact
and were left outside the material-fix pass.

## Decisions and qualification boundaries

The following is the complete chronological ruling ledger, including explicit
dispositions of every behavior the reviewer declined to judge. Each entry records
the decision, its reason and its practical cost or limitation. Provider-dependent
preview/recovery beyond the retained fixtures remains an unverified integration
concern; no general support is claimed for those paths.

- Ruling: continue inline in the existing isolated feature branch with one fresh final reviewer, preserving the qualified P21 artifact and all evidence — this is the approved execution sequence; no push, merge, global MCP registration or commercial add-on install — development changes will intentionally require fresh project runtime pins.

- Task 1: Ruling: inventory's file hashing exceeded the live socket deadline — capture registered state and paths on Blender's main thread, then hash sources on the host; explicit activation and worker validation still recheck source pins — a source change during discovery must be rejected again at activation.

- Task 1: Ruling: a pre-enabled provider has no reliable loaded-byte identity — refuse an unproven loaded provider rather than silently reload it; clean explicit activation records pins and a session-only delta — existing desktop add-ons may require restarting the owned/paired session before qualification.

- Task 1: Ruling: bundled extension wheels and unavailable license/network requirements cannot be reproduced offline without installation — declare them unavailable and never install automatically; profiles hash bundled source/assets and whitelist non-secret scalar preferences — some real providers need later explicit dependency support.

- Task 1: Ruling: the shared execution run closure propagates the profile to both backend execution and observation rather than duplicating it in BackgroundBackend — preserve one worker path and old no-profile call shape — backend changes must retain this propagation.

- Task 2: Ruling: Blender's Python does not include the host JSON Schema dependency — use one strict shared JSON Schema subset (closed objects, typed scalars/arrays, enums and bounds), rejecting refs and unknown keywords rather than accepting unsupported validation — advanced schemas require explicit later support. No undeclared JSON Schema import is introduced.

- Task 3: Ruling: negative qualification cases initially could succeed for an unrelated setup failure — require a specific failure substring and check it against the actual failing phase, in addition to positive/reopen/repeat cases — adapters with unstable error text need explicit updates instead of silently inheriting a pass.

- Task 3: Ruling: GUI qualification runs in fresh owned processes with isolated configuration, extension and temporary directories; GUI-only invocation and GUI verification are separate from background cases — only owned workers may be reaped on timeout; paired artist Blender remains outside this mechanism.

- Task 3: Ruling: Blender truncates modifier names at 63 bytes — retain full SHA-256 effect IDs in evidence and expose a bounded deterministic native-name prefix to adapters — adapters must preserve full identity in their output and detect ownership/duplication, not treat a visible name as the entire receipt.

- Task 3: Ruling: background Blender retains screen-layout data — never construct a viewport override in background mode; viewport-only fixture explicitly requires a GUI and is not registered for background use — real products still need their own poll/context cases.

- Task 3: Ruling: qualification reports additionally pin the harness runtime, not only recipe/provider/profile/Blender identities — changing verification code invalidates old qualification — development/runtime upgrades require new qualification reports rather than silently reusing old proof.

- Task 3: Ruling: qualification outputs must live in a fresh project capabilities/qualifications directory; registration checks its intent, complete retained artifacts, profile sources and cases — caller-provided success JSON elsewhere is refused; this retains the existing trusted-local filesystem authority boundary, not a hostile-user sandbox.

- Task 3: Ruling: Python socket guards cover explicit managed provider calls; owned qualification workers additionally audit their whole lifetime — no ambient artist activity is recorded and native libraries/subprocesses/deferred work are not claimed to be sandboxed — third-party source/network review remains necessary.

- Task 4: Ruling: capability execute needs explicit Blender, continuity contract and handoff arguments in addition to the planned semantic arguments — preserve the existing execution admission and publication contract rather than introduce defaults that bypass it — callers must supply these retained inputs.

- Task 4: Ruling: best_qualified initially supports measured execution time on matching fixture inputs, parameters, engine, context and build only — no comparative artistic quality evidence exists — other comparisons return NO_COMPARABLE_EVIDENCE until qualified measurements are implemented.

- Task 4: Ruling: live recipes must pass an independent background reopen in addition to GUI invocation/reopen — managed publication uses the existing background verifier — GUI-only providers without this verification path remain unavailable for managed publication.

- Task 4: Ruling: native routing copies immutable qualification artifacts into each owned project and re-registers their new local report paths, retaining the original qualified input paths and bytes — qualification concerns provider/runtime/case identity rather than the destination project name — no claim is made that the copied report is a new qualification run.

- Task 4: Ruling: the owned live factory fixture had an unused Dots Stroke material omitted by Blender on reopen — reopen the fixture baseline before attachment, preserving the strict production inventory comparison — artist scenes with unsaved orphan data remain a deliberate verification refusal until explicitly made save-stable.

- Task 4: Ruling: inherited output freshness is implemented with Task 5 lifecycle checks, while Task 4 requires the exact published checkpoint — the current gate is conservative and cannot reuse stale evidence — unrelated revisions temporarily require reapplication until Task 5 lands.

- Task 4: Ruling: capability-specific stage enforcement tests live in test_capabilities.py and exercise the real environment_workflow service in both modes — keep the existing workflow fixture shared instead of duplicating it in test_environment_workflow.py — the full legacy workflow suite still runs unchanged.

- Task 4: Ruling: flatten qualification registrations to capabilities/registered/<full-report-sha256>.json — Blender's embedded Python failed to open the prior 263-character path containing both recipe and report hashes, while the host Python could read it — retain both full identities inside the record and filter by full recipe digest, with no hash truncation or migration of previously qualified runtimes.

- Task 5: Ruling: managed eligibility rejects recipe custom-property coverage rather than extending P21 into an unqualified universal observer — the live guard and saved observation do not measure those arbitrary properties — such recipes may qualify in isolation but cannot be selected for managed publication until explicit coverage is added.

- Task 5: Ruling: policy dependencies must include every recipe read and dependency field — otherwise caller policy could understate when to refresh — underspecified policies are unavailable rather than silently trusted.

- Task 5: Ruling: freshness compares the entire declared observed recipe scope, plus current qualification and policy identity — this safely detects edited/deleted effects and allows unrelated checkpoints — overlapping effects can conservatively require an extra update; no repair loop or universal effect-specific graph inference is claimed.

- Task 5: Ruling: reuse is a read-only result under the execution lock and consumes no operation UUID/reservation or budget — it references the original published operation and current checkpoint — clients must distinguish REUSED from a newly PUBLISHED job. Identical previously dispatched UUIDs still return their original outcome.

- Task 6: Ruling: expose profile, bind, scaffold and prepare alongside the plan's minimum MCP actions — onboarding and managed execution need these shared APIs to be complete without an alternate engine — the public action surface is slightly larger but remains closed and contains no approval/install action.

- Task 6: Ruling: blender_execute now uses generic run-operation for both backends — preserve one execution, cancellation and configured-binary path — existing live callers keep their payload shape; background callers can use the same tool.

- Task 6: Ruling: native target IDs use the observation text contract, including spaces, colons and Unicode, rather than the portable recipe-ID regex — valid Blender identities otherwise fail receipt publication — empty or malformed observation identities still fail their existing validators.

- Task 6: Ruling: read-only receipt reuse precedes mutation-only stage/budget admission and independently checks the pinned run runtime — unchanged output needs no new work — clients must not mistake reuse for a new authorized edit or stage approval.

- Task 6: Ruling: a current best_qualified receipt can be reused even when its already-modified scene no longer matches the original benchmark input — the verified effect is current and no new provider is selected — a new mutation still requires comparable selection evidence.

- Task 6: Ruling: bridge manifests explicitly support canonical nested members and reject extra directories, traversal and redirects — capability schemas must ship with the standalone bridge — exact member hashes still require re-export/restart after any runtime change.

- Task 6: Ruling: capability-requirements returns unmet requirements as successful query data — the generic CLI passed=false exit policy hid the result from MCP, reproduced in task6-query-red.log and fixed in task6-query-green.log — stage submission/completion retain their failure exits and missing-evidence guards.

- Final: Ruling: preserve all revisions of an artist-confirmed policy behind owner authority, including additions — distinguishing semantic weakening of arbitrary provider/selector/parameter policies is unreliable — even a harmless addition requires owner confirmation; agent-authored policies remain autonomous.

- Final: Ruling: node-group entries use bounded native text while Python/operator entries use explicit callable syntax — native identities are not portable paths — unusual control-character or longer-than-255-character group names remain unsupported.

- Final: Ruling: artistic quality and provider superiority remain unproven — synthetic native checks measure technical behavior only — user visual evaluation is still needed.

- Final: Ruling: commercial/private product compatibility, licenses and installation remain provider-specific — no such product was supplied — each future add-on needs its own reviewed recipe and qualification.

- Final: Ruling: broad rigs, animation, simulation, modal completion and arbitrary-property coverage remain outside the qualified subset — existing explicit refusals stand — some Blender tasks remain unavailable through managed live recipes.

- Final: Ruling: hostile same-user filesystem/Python attacks and OS-level network isolation remain outside the trust boundary — local automation is not a sandbox — untrusted third-party code needs separate isolation/review.

- Final: Ruling: no automatic migration of runtime-pinned projects — verification-code changes invalidate old proof — users retain old runtimes or perform explicit fresh qualification/adoption.

- Final: Ruling: provider-dependent recovery/preview behavior beyond retained fixtures is an unverified integration concern, not an established supported failure — do not claim general provider-dependent preview/recovery support — such products need additional native proof and may refuse or fail those paths.

- Final: Ruling: unchanged static saved output can retain a valid receipt after general provider deactivation — no supported counterexample was established and reuse still checks sources, measurements and live alignment — effects requiring ongoing provider activation need their own qualified coverage.

- Final: Ruling: final documentation packaging remains a separate required gate — do not attribute native proof to changed runtime bytes — any non-rules package difference requires renewed runtime qualification.

- Final: Ruling: global configuration, publishing, merging and artist-scene qualification remain outside this authorized delivery — preserve the local feature branch and owned evidence — deployment and product-specific artist validation are still separate actions.
