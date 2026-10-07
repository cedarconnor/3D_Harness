# Structured feedback and environment workflow qualification

Version 0.5.0, October 6, 2026. Source/installed technical qualification, corrected fresh-agent continuation and separate review are complete. Three technical notes passed independent review; the visual note remains uncertain and unresolved.

The implementation is described in [usage](STRUCTURED_FEEDBACK.md). It adds optional coordination above the existing native store, with persistent notes, separate response/verification records, pinned skills and seven environment stages. It does not add a scheduler or establish artist acceptance.

## Retained findings

The first source/installed suites each ran 232 tests, with 230 passes and two Windows symlink-permission skips. The source and installed native exercises completed all seven stages on a synthetic bench micro-environment, rejected a protected-lighting fault, rejected stale-image feedback, rejected a forgotten-note submission and recovered a committed metadata receipt without a duplicate event. These first exercises predate the view-definition correction below.

An actual image review was provided by the coordinating agent after inspecting all before/after whole and detail images. It found the requested longer top and a modestly more matte timber response under broad lighting. These simple fixtures qualify mechanics, not environment realism or general skill effectiveness.

The first independent fresh agent received only an owned project copy, pinned runtime/skills, resume packet and revision brief. It successfully reopened and checked the native baseline, then identified a reproducibility gap: retained render receipts contained only a settings hash, not the settings themselves. It did not guess the crop, reserve an edit or mutate the native scene. Recorded work was 169.664 seconds plus approximately 25 seconds of initial reading. This is a retained failed packet-sufficiency trial, not a passing continuation.

The correction requires a retained settings JSON artifact for every feedback/stage render, with its canonical digest equal to the render receipt's `views_digest`. A new negative regression covers missing/mismatching definitions. The renderer retains camera matrix, lens, frame, render settings and detail crop. Input completeness remains the producer's responsibility; a nonempty settings object alone is not a general camera reconstruction validator.

After that correction, the final source and installed suites each ran **233 tests: 231 passed, two Windows symlink-permission skips**. The corrected `source-v2/` and `installed-v2/` native exercises both passed. Both sets of actual before/after images were inspected by the coordinator before visual verification. Four updated skills passed the structure validator. The 34 runtime/template files in the wheel match source bytes, and 96 local documentation links resolve.

The tested wheel SHA-256 is `a005dce4dddea48af5715e15847e9be7eca2c699cf8017d0ed17d29b769736b0`, retained under `runs/feedback-2026-10-06/wheels-v2/`. A separate 0.4.10 reader successfully resumed the corrected native checkpoint chain, while ignoring coordination as expected. Older clients therefore cannot enforce the new stage/feedback rules.

The final release wheel, rebuilt after the README update, has SHA-256 `ea97b841e91ba2126f074128e55728ec67833daf1ebf7c2998fa04239fa07c37`. Every runtime/template member is byte-identical to the fully tested wheel. Its separately installed `workflow-template` and `resume` commands also passed.

The corrected fresh agent received a new sealed copy with the actual retained view definitions, pinned runtime/skills and a held-out material revision. It published timber roughness 0.8 while retaining the accepted 2 m bench top and seven shared material users. Its narrow contract and separate Blender reopen passed. It recorded responses for all four current or stale notes, leaving independent verification pending. All 220 pre-existing pinned files were unchanged. Recorded elapsed time was **372.578 seconds (6m 12.6s)**, including reading, execution, image inspection and reporting; three owned background Blender processes accounted for 8.216 seconds. It authored one candidate with no native-process failure. These are tiny-fixture timings, not larger-environment throughput estimates.

The independent reviewer received only a copied brief, four notes, narrow contract, three native checkpoints/observations, fixed images and matching runtime. Builder commentary and pass reports were excluded. It independently reopened the candidate, recomputed the preservation/spec checks, inspected all six fixed images and verified all 55 packet inputs plus their manifest stayed unchanged. Recorded review time was **203.765 seconds**, excluding initial packet reading.

Its technical passes cover the 2 m top with original leg placements, camera/lighting/unrelated geometry preservation, and one timber datablock with the same seven users at roughness 0.8. The candidate's fresh observation exactly matches its supplied observation. Parent-to-candidate preservation is **tolerance-qualified**: 72 evaluated UV coordinates across nine meshes differ by at most `2.9802322387695312e-08`. Authored mesh/UV hashes, evaluated geometry and modifier settings match, satisfying the existing qualified UV guard below its `2e-7` absolute limit. The literal brief and builder's no-other-field-change wording were too strong; those retained reports are not rewritten. Review guidance now explicitly requires disclosing such tolerances.

The reviewer's original native command omitted `--python-exit-code 1`. The coordinator repeated its read-only checks with that flag and separate outputs; the process returned 0 and preserved every input. That additional reopen reproduced the tiny evaluated-UV variation, so its exact-array comparison failed while the existing guarded comparison passed. An overly strict assertion in the evidence-aggregation helper was corrected to retain both facts. No native file, runtime or tolerance policy changed. The reviewer's earlier exact-match result describes its particular reopen, not a guarantee across processes.

The reviewer rated the visual gloss reduction **uncertain**. Broad soft lighting and small images made the difference too subtle for confident visual acceptance, despite correct numeric roughness. Its four verdicts were registered separately against the exact responses: three notes resolve at the new checkpoint; the visual note stays awaiting verification. Materials and downstream stages therefore remain incomplete in this fresh trial. This differs from the coordinator's earlier bounded visual pass and is retained as reviewer disagreement, not averaged into approval. The skill now explicitly directs an uncertain verdict when the evidence cannot reveal the requested effect. No artist acceptance or artist repair-time measurement is available.

One qualification-script mistake was also retained: its visual review named two views while the response supplied one. The existing gate correctly refused it. The corrected response supplies both images; the gate was not relaxed.

Local evidence is retained under `runs/feedback-2026-10-06/`: `source/`, `installed/`, `fresh-worker/`, corrected `source-v2/`, `installed-v2/`, `fresh-worker-v2/`, and `independent-review/`. `VERIFICATION.json` summarizes package/runtime results; `fresh-reviewed-resume.json` preserves the final unresolved visual state. Run artifacts and native files are excluded from Git. The accepted production environment is outside these exercises and remains untouched.

## Implementation boundaries

- Metadata uses immutable ordered event bundles with request replay and a short cooperating-writer lock. Partial bundles stop for inspection; no automatic repair or native redispatch occurs.
- Native publication and feedback records are separate commits. A successful checkpoint does not close a note or complete a stage.
- Technical contracts are recomputed. Visual assessments and reviewer/producer identities are caller-attributed; independent tool execution and genuine image inspection must be demonstrated separately.
- All current blockers are listed in resume. Older resolutions need rechecking at a changed checkpoint. Stage receipts remain historical facts; new blockers/upstream revisions invalidate dependent readiness.
- Inheritance records missing evidence as gaps; delivery cannot hide those gaps. Artifact records are inspected, not a certificate of unmeasured native dependencies.
- Runtime/skill pinning is local and explicit. No in-place workflow/runtime upgrade command, cross-client installer, automatic global taste learning, arbitrary workflow language or image-annotation UI is included.
- Blocking deferrals require an attributed artist decision; supersession uses a new note plus explicit disposition. This is narrower than a general delegated waiver system.

The next creative investment gate remains sustained detailed-environment work and measured artist repair effort. The present fixtures do not demonstrate a comparative aesthetic or long-horizon advantage over plain MCP.
