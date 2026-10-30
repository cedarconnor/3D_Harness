# Shader effects and asynchronous add-on recipes

Status: approved by the user on October 30, 2026; implemented and qualified in 0.24.0.

## Intent and acceptance

Remove the harness's modifier-only and synchronous-only integration limits. A
standalone material/shader effect must qualify and execute without creating a
dummy modifier. A provider operation may finish later and still use the existing
managed reservation, cancellation, verification and publication path.

Success requires source tests and owned Blender fixtures, including saved-file
reopen, repeat updates without duplicates, stale-receipt detection, cancellation,
timeout, provider failure and uncertain-response handling. Technical qualification
does not assert artistic quality or compatibility with untested commercial add-ons.

## Approach

Recommended: extend the existing recipe and managed-job system with explicit effect
types and a cooperative asynchronous lifecycle. Keep existing modifier recipes and
synchronous adapters working. Use a new recipe schema version for the new contracts,
so old pinned projects and immutable recipe bundles retain their meanings.

Merely removing admission checks cannot establish effect ownership or completion.
A separate async executor would duplicate operation identity and publication logic.
Neither is a suitable implementation of the requested support.

## Shader effect contract

- A v2 recipe declares an effect kind and bounded native selectors. Support native
  modifiers, material effects and shader-node effects; geometry-only output is a
  separate feature and is not implied by this change.
- A material effect names its owned material identity and target slot bindings. A
  shader-node effect names its material and owned nodes or node group. Keep the full
  effect key in evidence and use deterministic bounded native names. Existing,
  unowned artist data cannot silently become an owned effect.
- Independently measure the selected native graph, its links into the material,
  values, bindings, image content hashes and shared users before and after provider
  invocation and after reopening. Adapter output alone cannot establish ownership
  or success. UI-only changes and success flags are insufficient.
- Extend graph observation to nested shader groups with deterministic traversal,
  cycle detection and explicit limits. Include supported RNA settings, sockets,
  interface defaults, ramps, links and images; unknown effect-relevant state must
  remain an explicit coverage failure. Do not clear unsupported flags indiscriminately.
- Apply existing shared-material policies to both `materials` and `nodes` writes.
  A single-user copy must leave other users unchanged; all-users edits must declare
  the actual affected users. Reject undeclared mutation outside the permitted scope.
  Include the transitive users of shared shader node groups in other materials and
  worlds; refuse a mutation if that affected-user closure cannot be measured.
- Update, reuse, deletion and stale-input checks resolve the declared effect type.
  Reopen verification compares retained native evidence. Changed dependencies may
  not be satisfied by an unrelated modifier or an inspector's claimed output.

## Asynchronous contract

- A v2 asynchronous recipe declares source-pinned submit, poll, cancel and collect
  entry points, bounded polling interval, deadline and cancellation grace period.
  Callable ownership and argument validation use the existing provider checks.
  Submission returns a JSON-serializable provider handle, not a success receipt.
- Persist the managed operation UUID, invocation intent, handle, progress and each
  lifecycle transition. Submit exactly once. Repeated status requests never submit
  again. Restart or response loss without a provable resumable handle produces an
  explicit reconciliation state; it never starts replacement work automatically.
- Poll reports pending, succeeded, failed or cancelled. Collect runs once after
  terminal success and identifies the native output. Independent output measurement
  and saved-file verification still determine whether publication is allowed.
  Persist intent before both submit and collect. A crash between either dispatch and
  result persistence requires reconciliation; neither call may be automatically replayed.
- Live execution advances through Blender timer callbacks and returns control to
  Blender between steps. Never sleep on the UI thread waiting for a modal operator,
  timer or worker callback. A modal operator needs an explicit completion/cancel
  adapter; `RUNNING_MODAL` alone cannot prove a job is complete.
- Background execution supports provider jobs whose progress is independent of a
  GUI event loop. GUI-dependent modal providers qualify for live use only; independent
  background reopen still verifies the completed saved result. An owned GUI
  qualification process must remain alive while its timer-driven job progresses.
- Keep the scene reservation until work is terminal or reconciled. Revalidate scene,
  session generation, provider pins, dependencies and permitted mutation scope across
  ticks. Poll and cancellation adapters must not perform undeclared scene edits.
  Compare preservation state outside declared writes between ticks, permitting
  measured provider progress within the write scope. Changes to declared inputs or
  protected scene state require reconciliation. Scene reservations cannot prevent
  manual artist edits; edits within the effect's write scope cannot always be
  attributed independently, so the UI/status must identify the active target scope.
- Request cancellation once and wait for measured termination within its grace
  period. Deadline expiry starts cancellation. Failed or uncertain termination
  requires reconciliation and blocks candidate publication. Never kill artist Blender.
- Temporary profile settings must remain usable during provider callbacks and must
  be restored after terminal cleanup. Preference autosave, offline auditing and
  provider activation need lifecycle scopes that work across timer callbacks;
  do not leave thread-local/context-manager scopes suspended across unrelated UI work.

## Integration boundaries

Change recipe validation and serialized schemas, bundle/scaffold handling, native
effect measurement, capability projection/freshness, bridge invocation, live jobs,
owned background/GUI qualification workers and adapter fixtures. CLI/MCP retain the
existing public onboarding and execution routes; async progress appears through
the existing status APIs. Update bridge manifests and distribution checks for any
new modules. Prior qualified reports become stale when their runtime identity changes.

README and active guides describe the supported contracts and evidence limits only
after qualification passes. Historical release reports keep their original claims.
No external service installation or proprietary provider redistribution is implied.

## Verification and delivery

1. Add portable regression tests for v1 compatibility, v2 closed schemas, effect
   attribution, shader/group changes, scope guards and async state transitions.
2. Add synthetic standalone material and nested shader providers plus delayed,
   timer/modal and failing/cancellation providers. Prove visible shader output with
   a shader-capable render; Workbench previews cannot establish shader behavior.
3. Qualify background and live paths independently on owned fixtures: first apply,
   repeat/update, save/reopen, managed publication, reuse, stale/deleted effects,
   shared users and unchanged artist preferences. Prove UI ticks continue during
   delayed live execution.
4. Exercise duplicate-submit refusal, lost response, cancellation before/after
   mutation, failure, timeout, failed termination and source/session change. Pending,
   failed and uncertain jobs must never create completion-valid receipts.
5. Run the full source suite, installed-wheel suite, wheel/source-archive parity,
   standalone bridge parity and relevant existing capability/native qualifiers.
   Retain commands, outcomes and artifact hashes with clear qualification limits.

Implementation can proceed in dependency order: contracts and measurement; shader
execution; async lifecycle; live/background integration; native and packaging proof.
The implementer may choose internal helper boundaries and test organization. Changes
to these public semantics or to the acceptance criteria require revisiting this design.

Builder review found no remaining questions requiring user input. The sharing
closure, between-tick preservation comparison and collect replay rules above record
the implementation choices resolved during that review.

Implementation notes: exact optional `allowed_unbound_material_ids` and
`allowed_material_graphs` continuity declarations represent intentional material
transitions without weakening existing contracts. A protected-state fingerprint
also verifies original material/world state after reopening. See the
[qualification results](../../archive/releases/SHADER_ASYNC_0_24_0_RESULTS.md).
