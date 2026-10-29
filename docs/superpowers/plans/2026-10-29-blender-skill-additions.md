# Blender skill additions

Implement the first batch accepted in chat: style references under visual design,
a discoverable vegetation skill, and expanded LOD acceptance in realtime assets.
Keep managed execution, project direction and artist review authoritative.
Do not import upstream orchestration or engine-specific export presets.

- [x] Test baseline retrieval/application against the existing skills.
- [x] Add vegetation with saved/native and GLB attribute checks; register it in the index and required-area test.
- [x] Add conditional cel, retro, isometric, voxel and horror style references; link from visual design.
- [x] Extend LOD guidance and its native example to cover shader attributes and material assignments, including a rejected damaged LOD.
- [x] Retain upstream MIT attribution and pinned provenance in the library guide.
- [x] Validate skill structure, links, packaged rule bytes and native examples on installed Blender 5.1 and 5.2.
- [x] Re-test application with the new guidance; record evidence and limits.

The code examples prove API mechanics and persistence on owned fixtures. Style
references need rendered project review; attribute round trips do not prove engine
wind, performance, LOD transitions or artistic quality. New references remain
selectively loaded through the existing craft index.

Evidence: `runs/blender-skills-final-2026-10-29-51/summary.json` and
`runs/blender-skills-final-2026-10-29-52/summary.json` each report four passing
blocks. The built wheel's 197 rule resources match source bytes exactly, including
the added references and license, recorded in
`runs/blender-skills-package-final-2026-10-29/rules-verification.json`.
Focused unit checks: 15 passed, one sdist regression skipped because the base
interpreter has setuptools 65.5 rather than the required 77+. The actual wheel
build used isolated build dependencies. Three skill validators passed; independent
application/review reported no remaining actionable findings after corrections.
