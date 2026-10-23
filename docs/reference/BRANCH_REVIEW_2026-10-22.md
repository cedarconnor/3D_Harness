# Review: `codex/managed-execution-overhaul` vs `origin/main`

Scope: 25 commits, 168 files, +14,295 / -303 lines. Covers releases 0.19.0 → 0.23.0 (P19 managed execution, P20 combined MCP, P21 live Blender, P22 add-on capabilities). Twenty-two of the commits land within ~6.5 hours on 2026-10-22.

Test status: 591 passed, 2 skipped with `mcp==1.26.0` pinned. With system `mcp` 2.x, 3 tests fail (`mcp.server.fastmcp` import) — the pin is exact and correct, but the README still says the runtime is "stdlib-only". Blender is not available here, so all Blender-side code was reviewed by reading only.

Severity: **H** = fix before merge/advertise, **M** = fix soon, **L** = cleanup.

## A. Authority and policy (the stated invariants)

| # | Sev | Location | Defect |
|---|---|---|---|
| A1 | **H** | `dcc_harness/environment_workflow.py:16-21` `review_policy` | In an `autonomous` managed run every stage returns `agent_within_brief`, ignoring the manifest's per-stage `review` and the binding's `review_policies`. `run-create --mode autonomous` + `run-submit` are both MCP-exposed with no owner step, so an agent can complete an `artist_required` stage. `main` honoured the binding via `feedback.policy()`. The 0.23 "artist-policy downgrade" fix only covered `capability.bind`. Verified by probe. Fix: never relax below the binding (`max(binding, mode)`), or refuse autonomous creation when any bound stage is `artist_required`. No test covers the relaxing direction. |
| A2 | M | `execution.py:184-216` `submit` | Never checks `cancel.json` or the deadline; `create → cancel → submit` returns `COMPLETE` while `status()` says `CANCELLED`. Contradicts MANAGED_EXECUTION.md. |
| A3 | L | `execution.py:371-407` `reconcile` | No runtime-pin check (present in `_admit`). A different install can publish through reconcile. |
| A4 | L | `scripts/qualify_execution.py:47-51` | Shipped `SyntheticOwnerConsole` shows `owner.confirm` accepts any object with `environ/isatty/ask`. Fine as "guard not wall", but OWNER_APPROVAL.md should say so. |

## B. Managed execution service

| # | Sev | Location | Defect |
|---|---|---|---|
| B1 | M | `mcp_server.py:88-111` | Any `BaseException` during `run-execute`/`run-operation`/`live-execute` (client cancel, client tool timeout, 3600 s wait) calls `execution.cancel(root)`, which writes `cancel.json`. Nothing removes it; `_admit`, `check_publication`, `create` (`mkdir(exist_ok=False)`) and `require_service` all refuse afterwards. One Blender script longer than a client's default tool timeout strands the whole project. Cancel only the in-flight operation here; leave run-level cancel to `run-cancel`, or allow a successor run. |
| B2 | M | `execution.py:355-368` | `capabilities.record_operation` runs after `finish_edit` has published. If it raises (policy rebind during a long job, missing verification) the checkpoint is published, `failure.json` is written, and `reconcile(accept=True)` returns `PUBLISHED` without ever writing the receipt. Verified by probe. Build the receipt before publication. |
| B3 | M | `execution.py:67` + `reconcile` | `check_publication` raises on cancel/deadline, so `reconcile(accept=True)` of an already-verified candidate fails once the clock expires — exactly when operators reconcile. Docs say reconciliation "can finish an interrupted native check". Exempt `reconciled=True` from the time gate or document it. |
| B4 | M | `mcp_server.py:120-124` | Non-zero CLI exit discards parsed stdout; `check`/`diff`/`finish-edit`/`recipe-qualify` use exit 1 for legitimate "failed" outcomes, so the agent gets only "inspect <folder>" and must `harness_read` stdout.txt. Return the structured result. |
| B5 | M | `continuity.py:278`, `project.py:37`, `workflow.py:147,202` | `require_service` now blocks every unauthorized write once `state/execution/` exists; `revisions.accept_revision` is never wrapped, so `preview-revision`/`accept-revision` (README "Retains deliberate artist edits") stop working on any project that has had a managed run. Undocumented, untested. |
| B6 | L | `execution.py:155-156` | `status()` orders `CANCELLED` before `NEEDS_RECONCILIATION`, hiding an unresolved reservation that still blocks all writes. |
| B7 | L | `execution.py:123-127, 165` | Non-atomic run creation (folder then `run.json`); bare `FileNotFoundError` from `configuration()` and from `reconcile` on unknown id; live `status()` only catches `(OSError, ValueError)` around `read_binding`. |
| B8 | L | `execution.py:294-301` | Staging dir (with a possibly large `input.blend`) leaks on pre-rename failure; nothing lists or cleans it. |
| B9 | L | `distribution.py:50-83` | Rules bundle follows every Markdown link, so it includes `dcc_harness/*.py`, `scripts/*.py` and two test files (172 files, 14 `.py`). Editing any of them changes `catalog()` and fails `verify_rules` for previously bound projects. Restrict to docs. |
| B10 | L | `bootstrap.py:49-51` | `bind_rules` export is not idempotent on interruption or concurrent calls despite the "reuse the UUID" docstring. |
| B11 | L | `environments.py:19,35` | `inventory` leaks a temp dir per call; `create_profile` first write races. |
| B12 | L | `__main__.py:203-205` | `capability-bind` dereferences payload keys before validation → raw `KeyError` traceback over MCP. |
| B13 | L | docs | MANAGED_EXECUTION.md:66 says the wheel has "not a registered MCP server"; `pyproject.toml` registers `dcc-harness-mcp`. README still says stdlib-only. |

## C. Live Blender bridge

| # | Sev | Location | Defect |
|---|---|---|---|
| C1 | **H** | `blender_bridge.py:75-77`, `_request` 19-47 | Every paired command has a hard ≤2 s client deadline that also covers connect + the `get_addon_info` handshake (which re-hashes the add-on dir on the main thread) + the command, each needing a 50 ms timer tick. `attach_begin/apply`, `job_prepare`, `preview_capture`, `recovery_capture` each do 1-2 full `save_as_mainfile` copies, double file hashes and 3-5 depsgraph `measure_live` snapshots. All qualification fixtures are a single cube. On a real scene the timeout fires while Blender keeps working (bridge-side deadline is 10 s); for `recovery_capture` this leaves `request.json` without `refusal.json`, after which every reconcile raises "Recovery outcome is incomplete; never repeat" and the project can never run a live op again. The no-replay invariant holds; its consequence is unrecoverable. Size the deadline per command and make "bridge refused before writing" a transport-independent outcome. |
| C2 | M | `data/bridge/attachment.py:98-106` | `save_copy` sets `image.filepath` (triggers `rna_Image_reload_update`) and restores it, so every copy reloads every external texture twice. Use `filepath_raw`. Feeds C1. |
| C3 | M | `attachment.py:119-139` + `live.py:50-56` | `attach_begin` does `bind()+acquire()` before the pre-write checks; a refusal (e.g. unsaved painted image) leaves the session BUSY with no release path, and the harness has already created the destination with `attach-request.json`, so re-attach hits "Incomplete attachment". Only exit: restart the bridge and pick a new folder. Undocumented. |
| C4 | M | `live.py:236-237`, `session.py:106-112` | `refresh` refuses a new binding while the old descriptor file exists; the descriptor is only unlinked on clean `Session.close()`. After a Blender crash the user must hand-delete a private secret file. The reconnect fixture restarts cleanly, so untested. |
| C5 | M | `live.py:166`, `jobs.py:46-72`, `execution.py:362-366` | Binding is set BUSY before `job_prepare`; every bridge-side pre-mutation refusal (`UNSUPPORTED_COVERAGE`, `LIVE_DIVERGED`, `UNSAVED_IMAGE`, expired) fires before `acquire` and writes nothing, yet is handled as NEEDS_RECONCILIATION requiring archive + background verifier + rejected edit. An agent hits this on its first unsupported modifier. |
| C6 | L/M | `data/bridge/__init__.py:151-155`, `inspection.py:73` | Non-serializable results (NaN/inf in raw `matrix_world`) are swallowed: no reply until deadline, indistinguishable from a dead bridge. Serialize inside `execute_command` and return an error envelope. |
| C7 | L | `data/bridge/recovery.py:33-50` | Only `ValueError` counts as a refusal; a missing `live-prepared.json` or pre-copy raises after `mkdir` and becomes a permanent "incomplete" with nothing mutated. |
| C8 | L | `attachment.py:66-69`, `live.status`/`ensure_aligned` | A full-scene snapshot is written to `live/divergence/` on every mismatching check; polling while the artist edits fills the disk. |
| C9 | L | `blender_bridge.py:85-92`, `live_surface.sessions` | Bridge identity is self-asserted (server-reported hash); `sessions` sends each descriptor's token to whatever listens on its port. Fine for a localhost tool and documented as such, but the "no raw live Python" claim is protocol-level only: the bridge `exec`s project-resident adapter code (`recipes.py:118-124`) whose integrity hashes live in the same project tree. |

Sound: loopback bind, `hmac.compare_digest` on a 256-bit token in a 0600 file, strict command whitelist, one-shot prepared tokens bound to request hash + fingerprint + generation, all `bpy` on the main-thread timer, no path found that applies an operation twice, reload/stop/restart invalidation correct.

## D. Add-on capabilities and recipes

| # | Sev | Location | Defect |
|---|---|---|---|
| D1 | **H** | `data/bridge/recipes.py:61` | `measurements()` raises `UNSUPPORTED_COVERAGE` whenever `measure_live(scene)['issues']` is non-empty for the whole scene. `enhance()` adds an issue for every Geometry Nodes modifier that isn't the trivial transform tree, and `observe()` adds "Missing instance ID"/"Missing asset ID" for every unlabeled object. Any real artist scene with one GN setup or one unlabeled light on an unrelated object blocks every capability apply/verify in both backends. Qualification stamps IDs on a factory scene with no GN, so never seen. Scope the gate to the target. |
| D2 | H/M | `capabilities.py:171, 113-118, 271` | `benchmark_input` (geometry hashes + full material records + all modifier settings) is folded into every requirement's identity regardless of `rule['dependencies']`. A material tweak on a rule with `dependencies=['geometry']` invalidates the receipt and forces native re-execution. Contradicts "unchanged dependencies reuse evidence". Verified by probe. Make `dependency_fingerprint` the sole invalidation key. |
| D3 | M | `capabilities.py:134` vs `bridge/recipes.py:68,72-74` | Host and Blender projections differ: `transform` is rounded to 7 digits on the host and raw on the bridge (any rotated target → receipt never valid); `material_users` iterates all `bpy.data.objects` on the bridge but only labeled scene objects on the host. One shared projection is needed. |
| D4 | M | `bridge/recipes.py:198-209, 102-108` | Receipts prove the pinned entry point was *called*; the before/after delta is measured around the whole agent-authored adapter `apply`, and managed apply never checks `changed`. An adapter can call the provider with no-op params and create the `DCC::` modifier itself. Measure around `invoke_declared` and require the change there. |
| D5 | M | `bridge/recipes.py:139-142` | `python_function` always calls `fn(context, parameters, effect_id)` and must live in the pinned provider module. Unusable against an unmodified third-party API; only `operator`/`node_asset` kinds work for real providers. ADDON_RECIPES.md:183 is misleading. |
| D6 | M | `capabilities.py:202-203`, `_recipe_blender.py:67-77` | `best_qualified` requires the live target to hash-match the qualification cube and scores whole-worker wall time (two saves, two renders). No positive selection is proven anywhere (unit test patches `candidate_evidence`; native script asserts only `NO_COMPARABLE_EVIDENCE`). Remove or reduce. |
| D7 | M | `data/bridge/addons.py:158,173` | Live activation calls `extensions.repos.new` / `preferences.addons.new()` inside the artist's GUI session; Blender auto-saves prefs on quit, so entries persist. Contradicts "never saves global preferences". `enabled_delta` is never reverted. Needs Blender verification. |
| D8 | M | `provider_sources.py:183`, `capabilities.py:103` | "Unreviewed providers unavailable by default" is not implemented: only `network=='required'` or `license_required` is refused; every real legacy add-on is `network='unknown'` and accepted. `custom_properties` is read but never emitted by any observer. |
| D9 | L/M | `capabilities.py:296-303, 181, 279`, `recipes.py:113-117` | No caching: every `requirements`/`status`/submit re-hashes the whole add-on source tree and the qualification directory (including `.blend`s) per candidate per operation. |
| D10 | L | `recipes.py:148` | `require_qualified` raises on the first stale registration instead of skipping it. |
| D11 | L | `addons.py:141` | A provider already enabled in the artist's prefs is always `UNVERIFIED_LOADED_PROVIDER`; the doc doesn't say the artist must disable it first. |

Sound: discovery is import-free (`ast.literal_eval`/`tomllib`, size caps), source pinning binds what it claims (hash-on-import finder, compile-from-bytes), hand-rolled validators are strictly stricter than the shipped JSON schemas (differential-tested, ~55 mutations), owner guard on `capability.bind` is correct.

## E. Test gaps (claimed in docs, not exercised)

- Time-budget exhaustion, runtime-pin mismatch, `bootstrap.bind_rules`, `environments.inventory`, cancel-then-reconcile, receipt-after-publication: no tests.
- Socket server (`_handle_client`, deadline, semaphore, oversize request, client-gone race) and the real `Jobs` state machine: only in the GUI `qualify_live.py`; `test_lost_reply_is_status_only` uses a fake backend.
- No unit happy path for `live.attach`, `live_recovery.reconcile`, `live_surface.preview`, `live.refresh`.
- Capability fixtures are harness-shaped (operators accept `effect_id`); no adapter wraps a provider that knows nothing about effect IDs, which is every real add-on.
- No test for the policy-relaxing direction (A1), receipt survival across out-of-dependency edits (D2), transform round-trip (D3a), multi-scene material users (D3b), positive `best_qualified` (D6).
- No CI at all; every "N tests passed" claim is a locally asserted Windows result.

## F. Minor / hygiene

- `docs/BUILD_PLAN.md` gained UTF-8 mojibake on this branch (`Ã¢â‚¬â€œ` for en-dashes, lines 35, 137, 146, 156, 165, 185, 191, 195); clean on `main`.
- BUILD_PLAN section X still lists X1 (managed executor), X3 (MCP connector) and X9 (live revision token) as "deferred until the gate passes" although this branch shipped all three.
- Runtime style: 621 semicolon-joined statements, 179 lines over 140 chars, longest 371. `execute_operation` is ~130 lines in one try block.
- `bootstrap.create` imports `file_hash` mid-function; `execution.execute()` is a compat shim used only by tests/scripts; `OperationRequest` TypedDict is used only for its key set; `ensure_aligned` is called twice per live op.
