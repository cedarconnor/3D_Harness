# P21 final review and implementation rulings

The independent whole-branch reviewer inspected the implementation candidate read-only. All five findings were accepted as release blockers and fixed in one pass. There were no deferred minor findings.

| Finding | Proof and disposition |
| --- | --- |
| Source/installed bridge import omitted integrity module | Portable import and installed native attachment reproduced failure; package-layout support fixed, full native matrix passed. |
| Unsaved external image pixels were omitted by recovery copies | Old material texture reopened with red 0.0 rather than 0.123. Copy, snapshot and recovery now refuse dirty images before mutation; owned pixels and files remain unchanged. |
| Known pre-mutation recovery refusal poisoned future attempts | Immutable attempt/refusal records permit a new explicit attempt after definitive BUSY/STALE refusal. Lost or ambiguous replies still block replay. |
| General MCP reader exposed pairing descriptors | Private descriptor paths and copied descriptor text are refused through the actual MCP adapter. |
| Handshake identified changed disk files instead of loaded modules | Import-time manifest identity is pinned; changed installation refuses access until restart. Source package imports remain usable by independent workers. |

Four portable regressions were observed failing and then passing. Native preservation regressions were also observed red then green, including a correction for Blender's empty default sequence editor. Final source and clean-installed suites each ran 536 tests: 534 passed, two existing Windows permission skips. All 16 maintained release checks passed, including 26 live native scenarios and the separate preservation fixture.

## Rulings retained from the execution ledger
- continue in the existing codex/managed-execution-overhaul checkout — this is the approved plan's populated working directory and qualified runtime, already isolated from main by its feature branch; avoid moving the user's active work. A recoverable source archive and baseline commit preserve every existing file.
- inline execution under executing-plans with one fresh final reviewer; preserve the approved sequencing P21 qualification before P22 live integration. No push or global client configuration change.
- introduced qualifier in Task 2 to prove lifecycle before attachment; first fixture failed on startup context accessor, corrected to explicit bpy.data lookup.
- resolve bounded built-ins via shared closed recipe validation plus prepare/execute_step/verify_live functions, rather than per-recipe classes; all operations remain independently observed with unsupported coverage refusal.
- previews use bounded saved-copy Workbench renders with fixed comparison settings, retain image/provenance evidence with the project, and remove only the disposable copy after success; no automatic image expiry that could invalidate stage evidence. Task 6 manifest red tests were drafted and observed failing; parked under this ledger workspace until Task 5 suite completes.
- existing-project attachment is explicit refresh/reconnect of an existing live project; immutable background backend/runtime pins are not migrated. A new live adoption is required for a background project, so its old history remains separate.
- run the required fresh whole-branch review on the committed final implementation candidate while release verification runs; acceptance remains pending both results, and any material fixes receive red/green tests plus renewed relevant release checks. This overlaps read-only work without changing the pinned runtime under active fixtures.
- dirty image pixels are not qualified by a .blend copy — refuse snapshots, operation coverage, save-copy and restore before mutation until the user explicitly saves images — limits live texture-painting workflows until buffer preservation is separately qualified.
- additional external dependencies have no preservation proof — refuse audio/video/sequence data, volumes/cache datablocks and unpacked external fonts before live copying; no claim of generic external-cache recovery — conservative refusal may exclude otherwise safe scenes.
- P22, rigs/animation/simulations/modal operators and broad Geometry Nodes remain outside P21's executable subset — retain explicit unsupported states and proceed to P22 only after the release gate — unsupported scenes require a separately qualified recipe or workflow.
- same-user malicious Python/journal modification is outside the trusted local boundary — fix MCP disclosure without claiming an OS sandbox — users must trust local code and providers.
- final release success is judged by source/installed/native verifier output; artistic quality remains unassessed by synthetic fixtures — technical qualification must not be presented as visual acceptance.
- finalize documentation after qualification without rerunning identical native code — rebuild wheel/sdist, prove every runtime member byte-identical to the qualified wheel except rules.zip, reinstall and test rules/MCP surfaces — a mismatch blocks delivery and requires renewed runtime qualification.
- retain the local feature branch while continuing the separately approved P22 plan — no merge, push or global registration is authorized or needed here — publication remains a separate decision.
