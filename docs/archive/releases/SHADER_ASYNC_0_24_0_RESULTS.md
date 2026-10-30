# Shader and asynchronous recipes: 0.24.0 qualification

October 30, 2026. Implementation follows the [approved design](../../superpowers/specs/2026-10-30-shader-async-capabilities-design.md)
and [implementation plan](../../superpowers/plans/2026-10-30-shader-async-capabilities.md).

Version-two recipes support standalone owned materials and shader nodes, including
nested shader groups, without a modifier. Source-pinned providers can submit, poll,
cancel and collect asynchronous work through the existing managed execution service.
Version-one recipes retain their modifier and synchronous contracts.

## Observed results

All final proof runs in the table use runtime `0.24.0`, source digest
`f70cbf77b53073a5f8a1dd65d0b77a5ee88cfdc7c9a8da96dfb82fc01cecce31`.
Native tests use Windows and Blender 5.1.1, build `b70da489d7f4`. Full host suites
use Python 3.13.11; all 101 runtime Python modules also compile under Python 3.11.

| Check | Observed result | Retained evidence |
| --- | --- | --- |
| Source suite | 823 tests, successful; 2 skipped | [Source log](../../../runs/shader-async-release-final4/source-tests.log) |
| Installed-wheel suite | 823 tests, successful; 3 skipped; installed import path asserted | [Installed log](../../../runs/shader-async-release-final4/installed-tests.log) |
| Native source matrix | 24/24 passed; every host/worker source stamp unchanged | [Native report](../../../runs/shader-async-native-20261030-final5/VERIFICATION.json) |
| Installed native subset | 4/4 selected cases passed, explicitly partial; source stamps match the source matrix | [Installed native report](../../../runs/shader-async-installed-native-20261030-final/VERIFICATION.json), [installed import/bootstrap proof](../../../runs/shader-async-installed-native-20261030-final/INSTALLED_IMPORT_PROOF.json) |
| Managed asynchronous materials | All 4 background/live and autonomous/approval-gated combinations passed publication, UUID replay, receipt reuse and enforcement checks | [Material MCP report](../../../runs/shader-async-managed-20261030-final6/VERIFICATION.json) |
| Managed asynchronous shaders | Both autonomous backends passed publication, reuse and enforcement checks with isolated owned shader containers | [Shader MCP report](../../../runs/shader-async-shader-managed-20261030-final4/VERIFICATION.json) |
| Legacy modifier recipes | Both autonomous backends passed existing synchronous onboarding, publication, reuse and enforcement checks | [Legacy MCP report](../../../runs/shader-async-legacy-20261030-final3/VERIFICATION.json) |
| Distribution | 10 release checks passed: source and installed suites, wheel/sdist/rebuilt member parity, clean install, CLI/MCP entry points, identical standalone bridge exports | [Release report](../../../runs/shader-async-release-final4/VERIFICATION.json), [qualified artifact hashes](../../../runs/shader-async-release-final4/ARTIFACT_SHA256.json) |

The 24 native cases include material and nested-shader apply/repeat/update, visible
Cycles-render pixel changes, independent saved-file reopening, single-user copies,
declared all-users changes, no-op refusal, shared-group preservation refusal, provider
failure, caller cancellation, deadline cancellation and unconfirmed cancellation.
All 12 positive reopen checks reject a deliberate protected-world edit and accept
the restored state. Both unconfirmed-cancellation cases retain their lease until
termination is explicitly confirmed, then restore preferences without collecting
output. Live asynchronous cases demonstrate independent UI/provider timer progress
and exactly three submits/collects for initial application, repeat and update.

The installed subset exercises a synchronous material, background/live asynchronous
shader copies, and live uncertain-stop cleanup. Actual background and GUI process
command lines point to the installed `_profile_blender.py`; host module paths and
all seven apply/reopen requests point to the installed package directory.

Managed tests use synthetic owner consoles in disposable projects. They verify
missing/stale evidence blocks stages, MCP cannot approve its own work, artist policy
cannot be downgraded by an agent, and unchanged effects reuse a receipt without
another operation. They do not represent human artistic acceptance.

## Preservation and lifecycle changes

- Independent effect evidence measures native ownership, bindings, supported RNA,
  shader links, nested groups, interfaces and image hashes. Muted/invalid paths do
  not establish a shader contribution. Unowned existing effects cannot be adopted.
- Native preservation protects other nodes, material slots, material datablocks and
  worlds, including shared nested groups. A retained protected-state fingerprint is
  checked after reopening. Owned fixture providers retain a displaced last-user
  material so saving cannot silently discard the original.
- Exact `allowed_unbound_material_ids` and `allowed_material_graphs` continuity
  declarations authorize intentional observed binding/topology transitions while
  keeping unrelated material state protected. Their scope is explicit and tested.
- Submit, cancel and collect intent is durable before dispatch. Restoring an
  unfinished journal never replays mutation. Polling yields to Blender; cancellation
  scheduling respects remaining deadlines/grace rather than a slow regular poll.
- Temporary preferences and offline auditing have explicit cross-tick leases.
  Recovery refuses an unresolved lease, including a lost execution mapping. An
  explicit stop can poll for terminal state and restore the lease before a separate
  recovery decision. Failure to confirm termination retains reconciliation state.
- Adapter import, inspectors and saved validators cannot supply their own mutations
  as provider output. Full-suite regression also caught and removed an eager
  `addon_utils` import from the portable recovery verifier.

Positive qualification fixtures allow 30 seconds for provider work and native
verification under concurrent runs. Explicit timeout negatives retain a 0.2-second
deadline; other negative budgets remain 5 seconds. Earlier short positive budgets
were correctly cancelled and are retained as failed attempts, not counted here.

## Owned GUI shutdown regression

The user's pasted crash report exactly matches an owned GUI verifier crash, SHA256
`69aa58fb3a2c8e69f841fc9deac56abe907b72948bb5fdb8306a27d452810946`.
Verification had written its result, then called Blender's quit operator in the
same timer callback that reopened the candidate. The native stack ended in
`wm_exit_schedule_delayed` with an access violation; the process correctly failed
qualification despite its previously written result.

Shutdown now runs on a fresh timer tick with a valid window context. The owned
qualification continuation timer survives baseline file loading. Regression tests
and [the direct native rerun](../../../runs/gui-verify-shutdown-fixed/shutdown-proof.json)
show zero process exit and no crash artifacts; all final managed/native workers
also complete cleanly. Saved owned baselines are reopened before invoking effects
so transient zero-user factory data is not mistaken for saved input data.

## Evidence hashes and limits

Final native report SHA256:
`1ca770de79d58da949d11d209036dd3ca9e0413223d666417d1e4a7a4d30ea9d`.
Its full runtime/qualifier stamp is
`e76c6320e7338ebec0dfa4d104a43ac2812d6718a728d56f31754aadf97a4a86`,
identical in the installed native subset. Installed native report SHA256:
`f958ccf958a826af367ff25109d0db11f4d561cfc807755ff93bf0cccfd0b729`.

The release runner's `native_qualified: false` means it was invoked without its
older native matrix. The separate source/installed native and managed reports above
supply this feature's native proof. Final documentation packaging is recorded in
[the documentation package proof](../../../runs/shader-async-documentation-final/VERIFICATION.json)
and its external artifact manifest; runtime and bridge bytes must remain identical
to the fully tested wheel. Exact final package hashes live there to avoid embedding
an artifact's own hash recursively in its rules bundle.

These are synthetic technical MESH fixtures with declared engines and contexts.
They do not qualify a specific third-party add-on or artistic quality. Raw modal
operators need explicit completion/cancellation wrappers; GUI-dependent jobs do
not acquire background execution qualification merely by passing live cases.
Unknown relevant native state remains a coverage refusal. Existing projects keep
their pinned runtime and require fresh qualification to adopt changed code.
