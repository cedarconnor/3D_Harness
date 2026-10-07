# DCC Harness Research and Adoption Decisions

Research appendix. The [active build plan](./DCC_HARNESS_BUILD_PLAN.md) and [decision log](./DESIGN_DECISIONS.md) determine what to build and when. Candidate capability does not make adoption an initial milestone.

Research date: October 3, 2026, America/Los_Angeles. All links supplied in the request were screened. Depth varies: repository documentation and papers for the landscape; selected pinned implementation files for the most consequential runtime claims. No linked project was installed or qualified in a live DCC during this review.

Recommendations below are judgments for this Blender-first environment harness. Repository feature descriptions are reported capabilities, not independently reproduced results. Tool counts and star counts were not used as selection criteria.

For entry-point and distribution research, see [Packaging and Entry Points](./DCC_HARNESS_PACKAGING_AND_ENTRY_POINTS.md). It uses current official Codex, Claude Code and Cursor documentation to propose a plugin with shared skills and a local runtime above existing MCP servers, with optional background agent execution.

The follow-up addition, **db-lyon/ue-mcp**, received selected source inspection and an isolated reproduction of its Git restore command. It materially strengthens the proposed capability/inspection interface and is now the leading third-party Unreal candidate. The [focused review](./DCC_HARNESS_UE_MCP_REVIEW.md) separates reusable design patterns, source limitations and proposed qualification work.

## Projects most relevant to the foundation

| Source | Evidence and relevance | Adoption decision |
|---|---|---|
| [Mixar app](https://github.com/Mixar-AI/mixar-app) | Public Blender fork and desktop overlay; the hosted AI backend is explicitly excluded. GPL-family file licensing requires attention when reusing implementation. Selected execution and history modules were inspected. | Use for architecture patterns and interaction design. Do not fork Blender for the MVP or assume access to the backend orchestration. |
| [MAX-786 claude-3d-harness](https://github.com/MAX-786/claude-3d-harness) | Registry, pinned skill libraries, workflows, effort profiles and staged load plans directly address method consistency. Its README distinguishes Windows end-to-end experience from more limited platform CI. | Adapt registry and workflow concepts. Supply our own durable state and revision semantics rather than relying only on prompt compliance. |
| [DCC-MCP organization](https://github.com/dcc-mcp) | Current upstream ecosystem covers host integration, skills, gateways, jobs and operational capabilities. | Conditional infrastructure candidate. Evaluate only against a concrete gap in the pilot's existing transport or later executor. |
| [MooseGoose dcc-mcp-core](https://github.com/MooseGooseConsulting/dcc-mcp-core) | GitHub metadata identifies this as a fork of `dcc-mcp/dcc-mcp-core`; its README describes a Rust-first control plane. | Compare useful fork changes if needed; prefer a deliberately selected upstream revision as the baseline. |
| [loonghao dcc-mcp](https://github.com/loonghao/dcc-mcp) | README announces migration to the DCC-MCP organization and says this repository no longer receives active updates. | Follow the migration; do not start on this old entry point. |
| [leolee9086 blender_mcp](https://github.com/leolee9086/blender_mcp) | Describes itself as a Blender Lab mirror with local modifications. Documents separate MCP and add-on processes plus API/manual retrieval. | Inspect as a downstream reference. Select the actual upstream source explicitly rather than treating the mirror as authoritative. |
| [Blender Lab MCP](https://www.blender.org/lab/mcp-server/) | Vendor page describes the add-on/server arrangement and warns about unguarded generated-code execution. | Primary fallback transport and a comparison baseline. The harness still owns durable execution and verification. |

Current DCC-MCP is substantial enough to keep on the shortlist, but a framework evaluation should earn its cost by solving a measured problem. Its Blender adapter README also incorrectly says there is no Blender-official MCP server, conflicting with Blender Lab's own page. Test operational claims and consult vendor sources rather than trust comparison sections. [Pinned adapter README](https://github.com/dcc-mcp/dcc-mcp-blender/blob/eee4f242925597398563fdbba5cf926dd02d8131/README.md)

## Research patterns worth carrying forward

| Source | What the work supports | How to use it here |
|---|---|---|
| [SceneCraft paper page](https://huggingface.co/papers/2403.01248) and [paper](https://arxiv.org/html/2403.01248v1) | Scene decomposition, spatial relationships expressed as constraints, render feedback, and a reusable library of spatial functions. | Use an environment relationship graph and tested layout recipes. Put learned routines through review and held-out scenes before promotion. This does not prove production recovery or general artistic competence. |
| [BlenderAlchemy](https://github.com/ianhuang0630/BlenderAlchemyOfficial) | Searches edit candidates using vision-based generation and evaluation, including procedural geometry, material and lighting edits. | Branch from an accepted checkpoint, render a few alternatives under matched conditions, and promote the strongest candidate. Keep branch counts bounded by quality improvement and budget. |
| [LL3M](https://arxiv.org/html/2508.08228v1) | Planner, retrieval, coding, critic and verification roles; prior code helps refinement preserve an existing asset. The paper's examples and ablations are narrower than a production reliability claim. | Separate proposal from checking, and preserve the source recipe plus artifact state across handoffs. Benchmark whether the split helps our tasks. |
| [Evan1108 cinematic modeling skill](https://github.com/Evan1108-Coder/blender-cinematic-modeling-skill) | Reference mapping, physical depth, materials, motivated lighting and explicit verification limits. The repository states that package validation is not a Blender integration test. | Use as a method reference for environment quality. Build our own executed fixtures and examples. |

## Other Blender options

| Source | Relevant distinction from its documentation | Disposition |
|---|---|---|
| [ahujasid mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | Community bridge with general scene/code tools and asset or generation integrations. | Useful compatibility candidate and exploratory baseline. Wrap any adopted access in the same project and execution policy. |
| [dhakalnirajan blender-open-mcp](https://github.com/dhakalnirajan/blender-open-mcp) | Local-first bridge with configurable LLM providers, including local and compatible endpoints. | Learn from provider configuration; keep model routing in our orchestration layer to avoid nested hidden agents. |
| [marble810 blender-mcp-connect](https://github.com/marble810/blender-mcp-connect) | Explicit unofficial Blender Lab downstream focused on automatic instance discovery, dynamic ports and authenticated connection. | Evaluate discovery and pairing patterns. Verify worker identity and process incarnation, not just port availability. |
| [zorak1103 blender-mcp](https://github.com/zorak1103/blender-mcp) | In-Blender Streamable HTTP server with a stdio proxy; documented GUI requirement. | Candidate for an interactive adapter, with a separate background execution path if adopted. |
| [jlpschell blender-mcp-server](https://github.com/jlpschell/blender-mcp-server) | Broad in-application HTTP tools, queueing and automatic dependency installation; repository is a fork. | Source of operation coverage ideas. Test thread dispatch and package behavior before adoption; README quality claims are insufficient. |
| [RFingAdam mcp-blender](https://github.com/RFingAdam/mcp-blender) | Broad asset/generation operations and a render-refine loop. README includes an MIT statement while the repository LICENSE is AGPL-3.0. | Inspect useful patterns, but resolve file provenance and licensing before importing implementation. [LICENSE](https://github.com/RFingAdam/mcp-blender/blob/main/LICENSE) |
| [3D-Agent](https://3d-agent.com/blender-mcp) | Commercial agent product; its page describes a packaged workflow and external-agent delegation interface. | Product/UX reference or optional external service. A delegated task must return assets and usable evidence to join our durable project model. |

## Unreal options

| Source | Relevant distinction from its documentation | Disposition |
|---|---|---|
| [tahooki unreal-blender-mcp](https://github.com/tahooki/unreal-blender-mcp) | One server routes to Blender and an Unreal Python bridge. Its README identifies a more structured Unreal API as future work. | Example of dual-host routing; not evidence of verified asset synchronization or look preservation. |
| [conaman unreal-mcp-ue4](https://github.com/conaman/unreal-mcp-ue4) | Deliberately UE4.27-first Python Remote Execution integration. | Relevant only if UE4 compatibility becomes a real requirement. |
| [radial-hks MCP-Unreal-Server](https://github.com/radial-hks/MCP-Unreal-Server) | Instance discovery and remote Python execution with logging. | Lightweight reference for legacy/editor discovery; not the default environment production layer. |
| [runeape-sats unreal-mcp](https://github.com/runeape-sats/unreal-mcp) | Python Remote Control integration, CLI and an example castle build/verify/reset workflow. | Useful example of a bounded environment recipe and semantic checks. |
| [GenOrca unreal-mcp](https://github.com/GenOrca/unreal-mcp) | Domain-oriented action discovery and Python/C++ extension paths, including materials and sequences. | Candidate when richer native Unreal operations are needed. Test exact project and engine compatibility. |
| [FFZackFair92 unreal-engine-mcp](https://github.com/FFZackFair92/unreal-engine-mcp) | Separates process-level operations from Remote Control/editor calls and documents capability detection. README distinguishes engine-free tests from native use. | Useful reference for worker supervision and version-aware dispatch. Shortlist for legacy engine support or uncovered vendor capabilities. |
| [sam-david unreal-mcp](https://github.com/sam-david/unreal-mcp) | Multiple transports and broad subsystem coverage; explicitly marked beta with ongoing UE validation. | Alternative adapter candidate. The evidence does not justify the supplied document's unconditional “most complete base” recommendation. |
| [Epic Unreal MCP](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor) | Vendor documentation for UE5.8's experimental MCP and Toolset Registry, including Python and C++ tool authoring. | First candidate for supported current-engine projects. Retain a fallback and qualify its experimental limitations. |
| [db-lyon ue-mcp](https://github.com/db-lyon/ue-mcp) | Native bridge, capability/schema discovery, instance reflection, workflows, guards and focused animation methods; can also wrap Epic tools. Selected source review found useful unknown-outcome handling but in-memory history and a reproduced optional snapshot-restore defect. | Leading third-party Unreal candidate; compare with direct Epic access. Adapt discovery and observation patterns now; keep project persistence and recovery ownership in the harness. |

Unreal selection and its contract comparison follow the Blender creative and continuity gates. No need to maintain several Unreal forks in the first release.

## Cinema 4D and broader production systems

The [supplied CG Channel article](https://www.cgchannel.com/2026/09/maxon-releases-cinema-4d-2026-4-with-a-new-mcp-server/) led to [Maxon's own MCP documentation and FAQ](https://www.maxon.net/en/cinema-4d/features/mcp-server). Maxon describes native scene operations, undo, toolset controls and separate Python permissions. It also states that a partially failed batch leaves already-executed changes in the scene. The adapter therefore needs reconciliation and saved checkpoints even with a first-party connection.

For motion graphics, C4D is a strong second-host candidate because its native system explicitly centers on cloners and effectors, with procedural control over repeated elements. The portable layer should express distribution and timing intent while keeping the native editable implementation. [Maxon MoGraph](https://www.maxon.net/en/cinema-4d/features/mograph-basics)

[AI Forge MCP](https://github.com/HurtzDonutStudios/ai-forge-mcp) is useful as a product-scope reference across disciplines. Its current public page describes commercial compiled components, protected pipeline internals and license mechanisms. Do not assume the advertised whole system is an open-source codebase available to adopt. Its scale is also a reason to keep the first release focused.

## Staged adapter qualification

Use the already exposed Blender transport for the creative experiment after a live connectivity and disposable-file check. Timebox initial diagnosis and suitability to half a day. A read-only check during feedback review returned a connection failure at localhost:9876, so current tool exposure must not be described as a working live connection.

Only compare DCC-MCP Blender, upstream Blender Lab or another transport when an observed gap warrants it. Scope that comparison to the gap. The complete list below is a later managed/unattended qualification checklist, not a multi-day prerequisite for first geometry.

Qualification probes, staged by the active plan:

1. Identify the intended instance, document, version and capabilities; reject the wrong target.
2. Create a reusable object, material and instance with stable identities; inspect actual native state.
3. Apply a scoped change on the host thread and detect changes outside the expected targets.
4. Save, close, reopen and render the same checkpoint with dependencies resolved.
5. Lose a response after a mutation and reconcile without silently duplicating it.
6. Reject stale revisions after a manual edit or a worker restart.
7. Report and recover from a failed operation and a hung owned worker.
8. Cancel a render/job and distinguish cancelled dispatch from still-running native work.
9. Exercise foreground and background execution separately.
10. Confirm localhost access policy, credential boundaries and reproducible pinned installation on Windows.

An upstream missing a recovery primitive does not automatically disqualify it if our wrapper can implement that primitive reliably. If it cannot expose enough observation or identity to reconcile changes, reject it for unattended operation.

## Source snapshots and limits

| Project | Inspected commit | Selected inspection |
|---|---|---|
| Mixar | `3696b05bbcfc477ffb820f5f10375f35c263e0cb` | Request envelope, pump, script lanes, history store and repository documentation |
| DCC-MCP core | `b617caa1e35d314f663651f438c42296d014100b` | Workflow persistence/resume and checkpoint API documentation |
| DCC-MCP Blender | `eee4f242925597398563fdbba5cf926dd02d8131` | Adapter README, compatibility and execution policy descriptions |
| db-lyon UE-MCP | `6975fc5cfbf513c19d2c8c8348f095c02401929e` | Bridge timeout/history, flow integration/events/rollback/snapshots, guards, reflection surface, selected tests and workflow/animation documentation |
| majidmanzarpour blender-game-skills | `f0ef29385a03de139957e6f700b801cdc00b7e29` | Skill, build template, world and normalized silhouette measurement, native validation, export reimport, evaluation prompts and license |
| RobLe3 cc-blender-skill | `11016c9a5847897491dde935c346571bd7548e3d` | Manifest, entry/routing and selected discipline skills, handoff contracts, motion skills, image-report helpers, validation notes and license |

The core's checkpoint documentation explicitly describes a best-effort file lock that can degrade to a lost checkpoint, while workflow idempotency persistence requires the configured SQLite store. These are configuration and ownership concerns for the evaluation, not proof that our intended guarantees already exist. [Checkpoint API](https://github.com/dcc-mcp/dcc-mcp-core/blob/b617caa1e35d314f663651f438c42296d014100b/docs/api/checkpoint.md), [workflow API](https://github.com/dcc-mcp/dcc-mcp-core/blob/b617caa1e35d314f663651f438c42296d014100b/docs/guide/workflows.md)

Some Blender vendor pages could be retrieved only through indexed source text; direct fetches of the Lab page and several latest manual pages failed. The review does not infer current USD importer limits from older manual versions. Compatibility must be checked against the selected runtime during initial live setup and later adapter qualification.

## Native implementation sources added after feedback

The active plan uses separate asset libraries and local collection instances, with explicit overrides or new versions for edits. Blender's [Link and Append manual](https://docs.blender.org/manual/en/5.0/files/linked_libraries/link_append.html) establishes the distinction between linked references and local copies; the installed runtime still needs a fixture check.

Blender's [ID node documentation](https://docs.blender.org/manual/en/5.2/modeling/geometry_nodes/geometry/read/id.html) says it falls back to an index when the id attribute is absent. The harness therefore cannot promise persistent procedural identity merely by reading that node.

The [viewport rendering manual](https://docs.blender.org/manual/en/latest/editors/3dview/viewport_render.html) ties viewport rendering to viewport settings and distinguishes it from a full camera render. GUI capture and background rendering are separate qualification paths.

[Poly Haven](https://polyhaven.com/license) supplies an initial source for a fixed HDRI/PBR/secondary-prop kit; its asset license is CC0, while site and API access have separate terms. The experiment uses pinned, preselected files rather than an open-ended acquisition agent.

These sources support an implementation direction. They do not establish comparative uptime, multi-day autonomy, security isolation or final visual quality on the user's workstation.

## Additional skill libraries: selective adoption

Reviewed October 3, 2026, at the revisions above. This was source and documentation inspection, not a Blender execution test. Upstream skill instructions were reviewed as design material; their installation, scene mutation, approval, delegation and publication instructions were not activated.

**Recommendation:** draw from both libraries while keeping our three trial skills and existing MCP. The first is the stronger starting point for an individual reference-driven asset; the second offers a wider recipe library and useful motion exercises. Neither establishes the project continuity and recovery required by this harness.

| Library | Useful material | Best fit here |
|---|---|---|
| [blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills/tree/f0ef29385a03de139957e6f700b801cdc00b7e29) | One substantial `blender-image-to-3d` skill: measured briefs, scale calibration, staged silhouette review, modular assembly, UV/material checks, bpy helpers and export reimport | Reference-driven architectural pieces and props; selected measurements for condition C |
| [cc-blender-skill](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/manifest.json) | The inspected manifest lists 30 skills, including modeling, materials, UVs, lighting, cameras, reference fitting, motion and orchestration | On-demand procedural knowledge inside condition B; later targeted motion-design exercises |

### What needs adaptation before reuse

1. **Preserve the environment.** CC's entry skill instructs a world reset and supplies code that removes every world node. Its subject-lighting recipe replaces lights with particular key/fill/rim name prefixes. These are unsuitable defaults when the approved HDRI and lighting must survive a prop revision. Make them explicit new-scene or owned-rig operations. [Entry skill](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/text-to-blender/SKILL.md), [lighting recipe](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/blender-lighting/SKILL.md)

2. **Rebuild ownership is not edit preservation.** The game skill's build template deletes objects with its phase owner tag and saves over the master with Blender backup versions disabled. Edits to those owned objects are therefore lost on rebuild; a phase-only tag also needs an asset scope when multiple assets share a file. Adapt recipes to asset ownership, dependency invalidation and new checkpoint filenames. Review renders should run against disposable snapshot copies. [Build template](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/skills/blender-image-to-3d/assets/build_template.py)

3. **Measurement needs a valid comparison.** `compose_review.py` normalizes silhouette height and centers the masks, so its overlap score cannot establish absolute size or placement. `world_gate.py` addresses that by retaining a calibrated orthographic world window. Use it only with suitable mattes, scale and view alignment; an environment mood board is not an orthographic specification. Its successful completion reports measurements without enforcing the phase threshold. The wrapper must validate inputs and interpret results explicitly. [Normalized comparison](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/skills/blender-image-to-3d/scripts/compose_review.py), [world gate](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/skills/blender-image-to-3d/scripts/world_gate.py)

4. **Require evidence that the target was checked.** The game validator skips absent requested collections and does not fail merely because no requested mesh was inspected. Add expected-target and nonempty-coverage checks before using its pass status. CC's look helper uses brightness/saturation masks and color statistics; that is a diagnostic for suitable imagery, not a general material or aesthetic validator. [Native validator](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/skills/blender-image-to-3d/scripts/validate.py), [look helper](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/reference-look-calibration/scripts/look_fit_report.py)

5. **Bind to the selected runtime.** CC assumes ahujasid-style MCP action names; its manifest also declares that integration. Map recipes to the actually discovered transport. The game skill's external comparison script needs Pillow; CC's image-analysis recipes use dependencies including OpenCV, NumPy, SciPy and Pillow. Install only dependencies of adopted helpers, and qualify Blender API/render behavior on the chosen Windows version. Neither a declared version range nor the presence of a manifest proves portability across our three clients.

### Motion graphics and design taste

CC's [orbital HUD method](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/orbital-hud-motion/SKILL.md) is a useful narrow recipe: relate secondary shapes to the composition, separate layers and preserve subject dominance. Its [texture-state method](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/texture-state-animation/SKILL.md) adds registration and transitions chosen per layer. Treat these as candidate exercises after the environment gate, not a full motion-design system.

The [contact-sheet helper](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/animation-quality-gate/scripts/animation_contact_sheet.py) computes mean RGB changes between supplied images. It does not evaluate timing, trajectories, frame cadence or motion-compensated flicker. Use sheets for sampled appearance checks and full-speed playback for motion; separately check frame range, loop boundaries and target playback/export behavior. Do not assume all Blender material keyframes transfer through GLB.

Most relevant to taste, the upstream [chair validation notes](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/plugin/skills/text-to-blender/assets/v0.8.0-chair-validation/README.md) explicitly distinguish improved construction and material readability from successful design. This supports retaining artist-led comparisons, curated visual precedents and the project's style record. Fixed roughness, light ratios and overlap distances are recipe parameters to adapt, not universal quality rules.

### Evidence, incorporation and scope

The game repository includes [evaluation prompts and expected outputs](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/skills/blender-image-to-3d/evals/evals.json); those are not executed benchmark results. CC publishes scene examples and failure histories, while its [trigger evaluation](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/docs/test-results/test_round3.md) explicitly describes itself as a self-assessment. These are useful development evidence, not independent proof of environment consistency, multi-hour autonomy or reliable quality.

Both inspected roots contain MIT licenses: [game skill license](https://github.com/majidmanzarpour/blender-game-skills/blob/f0ef29385a03de139957e6f700b801cdc00b7e29/LICENSE), [CC license](https://github.com/RobLe3/cc-blender-skill/blob/11016c9a5847897491dde935c346571bd7548e3d/LICENSE). If incorporating source or substantial instructions, retain the applicable copyright/license notices and record the upstream revision and local changes. Track rights to external reference and asset files separately.

For the pilot, adapt a small fixed set of written methods into B and reserve additional executable feedback for C. Keep the independent evaluator equal across conditions. Exclude whole-library installation, competing orchestrators, mandatory rigging/export stages, unbounded render/refinement cycles and automatic rewriting of active skills. The [skill catalog](./DCC_HARNESS_SKILL_SYSTEM.md#selective-reuse-from-the-two-additional-skill-libraries) maps this reuse without adding packages to the first milestone.
