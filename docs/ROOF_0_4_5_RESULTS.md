# Roof lap repair and architecture helper — 0.4.5

The regular roof bands are removed by correcting the tile geometry. The harness gains a reusable lapped-course profile, four pure tests, a saved-garden lap inspector and focused architecture-skill guidance. The accepted ground, planting, materials and lighting remain protected. This is guided same-agent production, not a blind comparison or proof of general skill superiority.

## Diagnosis and change

The original 352 roof tiles overlapped adjacent rows by about 0.13958 m, but their top planes differed by only about 4.47e-8 m. The solids intersected by approximately 22 mm along their normal. The tile bottoms also penetrated the deck plane. A disposable render moved each row outward by 0.5 mm and removed the visible bands without changing any material or light. That diagnostic still intersected and was never adopted as a deliverable.

The final repair uses 6 mm tiles, a 0.6 mm bevel and a 0.8 mm gap between parallel neighboring courses. A slight tilt relative to the roof pitch creates the normal separation while retaining the original row gauge. Centers are raised to clear the deck. Tile X/Y positions, source UVs, mesh identities, asset identities and material assignments remain intact. Decks, ridge pieces, trim and all other objects are unchanged under the observation policy.

The pure helper [lapped_course_profile](../dcc_harness/roof.py) accepts roof pitch in radians, gauge measured along the roof, tile length, thickness and clearance. It rejects nonfinite, nonpositive or impossible configurations. See [usage and geometric limits](ROOF_RECIPE.md). It does not create Blender objects, schedule work or replace the existing MCP/workflow.

## Evidence

| Check | Result |
|---|---|
| Source and isolated installed-wheel suites | Each ran 157 tests: 155 passed, two Windows symlink skips |
| Package consistency | 24 source, pinned-runtime and installed Python modules have identical hashes |
| Native adjacent-course checks | 602 pairs on both slopes; evaluated gap 0.799502–0.799887 mm |
| Native overlap | 139.654532–139.655025 mm |
| Tile-to-deck plane clearance | Minimum 0.812806 mm after bevel evaluation |
| Fault control | A 5 mm tile displacement produced approximately 4.200092 mm penetration and was rejected |
| Unscoped preservation | 937 objects protected: 848 records exact, 89 differing only by the existing unchanged evaluated-UV noise policy |
| Materials and dependencies | All 54 material records preserved, 20 used images packed; external image paths invalidated in the disposable fixed-view renderer |
| Review views | Three original fixed cameras and two matched supplemental views inspected |
| Skill validation | Updated architecture skill passes frontmatter validation; its linked usage reference exists |

The source roof also fails the new native qualification, so the check distinguishes the observed defect from the repaired state. The fault control edits only an owned disposable process and does not save the native. The inspector uses actual evaluated vertices and separating-plane distances, without importing the profile helper to supply its expected geometry.

Scene totals remain unchanged: 1,289 objects, 2,355,438 evaluated triangles, 54 materials and 20 packed used images. No new object, material, external download or live artist-editor change was needed. Native SHA-256: `efb64030397fc571324ae8a444f51fa33555b420b8b7a4210e8829d2f9aa932d`.

## Visual selection and limits

The elevated garden view now shows coherent slate courses instead of alternating broad dark strips. Hero and context views show clearer seams; workbench detail and gate planting retain their previous appearance. All five images were directly inspected before publication. The diagnostic per-row offset and final repair are distinct artifacts, and only the final repair is selected.

The roof remains a regular procedural study. The helper and native inspector cover parallel rectangular courses and deck-plane clearance, not all roof joins, trim collisions, support hardware or weatherproofing. The 6 mm thickness is a scene design choice, not a universal construction standard. The distant field remains flat/repetitive with an abrupt edge, inherited foliage is still coarse, and the after-rain story remains weak.

No fresh-agent behavioral comparison, artist acceptance, repair-time savings, export or LOD qualification is established. Future art work should address distant terrain and its boundary. Future harness work should measure the repeated per-instance observation payload while preserving full-chain verification. The current geometry budget has only 144,562 triangles of headroom.

## Local artifacts

- [Portable scene and comparison package](../runs/roof-2026-10-05/potting-garden-roof-handoff.zip) and [five-view before/after gallery](../runs/roof-2026-10-05/handoff/index.html).
- [Verification summary](../runs/roof-2026-10-05/VERIFICATION.json), [visual review](../runs/roof-2026-10-05/roof-01/REVIEW.md) and [native lap checks](../runs/roof-2026-10-05/roof-01/native-laps.json).
- [Original fault measurement](../runs/roof-2026-10-05/lap-diagnosis.json) and [disposable diagnostic image](../runs/roof-2026-10-05/diagnostic-offset.png).
- [Scene-specific native inspector](../scripts/inspect_roof_laps.py) and [pure profile tests](../tests/test_roof.py).
- [Built wheel](../dist/dcc_harness-0.4.5-py3-none-any.whl), SHA-256 `6f7ebb697464ebd6a626896b79c926565fdc6183976d6d133a000252e34c410d`.

The gallery receives static local-reference checks and the ZIP receives CRC/member-hash checks. Browser rendering is not claimed. Full continuation history remains in the production project store; the ZIP is an artist handoff.

Publication produced checkpoint 000009. A fresh isolated installed-runtime resume verified the nine-checkpoint chain in 34.77 seconds and reported no pending operations, unresolved edits or metadata lock. This is a single timing, not a matched performance comparison. The approximately 214 MB observation remains a practical scaling concern for longer projects.
