# Separate-agent comparison — October 4, 2026

The first six-trial comparison is complete. Twelve fresh production contexts performed six builds and six file-based continuations through the live Blender MCP. The artist review is ready; no method winner has been selected.

Artist feedback, October 4: the user described the differences as subtle, preferred `R-1f85f481c52535af`, and ranked `R-0d39c8ed36edf675` second. Both are condition A, plain MCP, one from each block. The preference was expressed before revealing those assignments. Other entries remain unranked; numeric scores, practical acceptance and native editability were not supplied. This small comparison has not demonstrated an added visual-quality benefit from B or C. The original gallery and blank score form remain intact; the direct feedback is recorded separately in `private/artist-preference-2026-10-04.json`.

The user's proposed emphasis is continuity over a longer development horizon. A follow-on experiment should compare cumulative revisions, context replacements, manual edits and interrupted operations from identical native starting points. Measure unintended changes, lost decisions, recovery effort and artist repair time alongside visual quality. This is a proposed next experiment; the current run tested only one context replacement and one bounded late revision per scene, and does not qualify unattended operation.

Open the [anonymous gallery](../runs/blind-round-2026-10-03/review/index.html), or extract the [review ZIP](../runs/blind-round-2026-10-03/review.zip) and open `index.html`. Generated artifacts are local and excluded from Git. Keep the private assignment files closed until scores are saved.

| Evidence | Result |
|---|---|
| Builders / fresh revision agents | 6 / 6; each dispatched with no inherited conversation |
| Frozen input checks | All build and revision packets verified |
| Initial checkpoint checks | 6 of 6 passed |
| Revised checkpoint and preservation checks | 6 of 6 passed under the uniformly corrected evaluator |
| Anonymous review | 6 entries, each with 3 matched views before and after; 36 images total |
| Export integrity | 36 decoded images exactly match native capture pixels; 38-file ZIP verified |
| Independent anonymous audit | All images and both public text files inspected; complete, readable, no method/source-path leakage or gross framing drift |
| Unit tests | 35 passed; 1 Windows symlink-permission skip |
| Independent evaluator qualification | 11 native checks matched expectations: 4 valid/baseline passes, 6 detected faults, 1 corrupt-evidence rejection |
| Original working scene | Restored in live Blender; native file checksum unchanged |

The common late revision widened the bench seat and cooled the shared stone material while preserving measured placements, lighting, cameras and unrelated assets. Revision agents received only their assigned frozen methods, native checkpoint and handoff, excluding the builder's scripts and transcript. Production agents wrote sequentially because they shared one live Blender editor.

The independent evaluator exposed nondeterministic evaluated bevel UV values in unchanged files. Its initial `1e-7` guard produced one false failure; an unchanged-file reopen reproduced the `1.1920928955078125e-7` difference. The final `2e-7` limit still requires exact authored mesh/UV, evaluated geometry and modifier state. A separate auditor confirmed that a native authored UV edit of `5.96e-8` still fails. All twelve immutable checkpoints were reobserved with the same corrected coverage. The original failed report is retained; production outputs and review images were not regenerated. This qualifies the measured fields on this workstation, not every Blender field or version.

Across the six trials, agents declared 64 captures and independent evaluation produced 36, totaling 100. Declared and independently timed render calls totaled about 227.48 seconds; this excludes agent reasoning, startup, observation and review. All observed build/revision wall times and declared capture/render usage stayed within their caps. Token usage and dollar cost were unavailable. This is not enforced resource isolation.

Score composition, proportion, materials and lighting for both stages on the gallery's 1–5 scale; 4 means usable with minor cleanup. Native editability intentionally remains blank until inspecting the scenes. Save those scores before opening private mappings or the AI critic's notes. Browser form interaction/download remains untested; `scores.json` is also provided as an editable review record.

This is a single-blind artist comparison with procedural isolation. Agents share filesystem access, tool/skill descriptions and the host's general memory summary. Two repeats per method support the project's investment decision, not statistical superiority. Artist acceptance, native editability and an unseen brief remain outstanding. The larger unattended runtime and other DCC integrations remain gated on those results.

For another round, invoke the project coordinator skill `$dcc-blind-test`; see the [protocol](./BLIND_TRIALS.md). Evidence is under `runs/blind-round-2026-10-03/private/`: `round-summary-v2.json` supersedes the original summary, `requalification-v2/` holds the current technical reports, and `evaluator-correction-05.json` records the final correction. `export-check.json` verifies the public package. Method mappings remain private until artist scoring.
