# Continuity method

Use the same creative brief and requests as supplied. The additional method here is a durable project record plus measured preservation checks. It does not design geometry for you or grant artistic approval.

Set sys.dont_write_bytecode=True before importing from this packet's helper/. Do not import repository or other trial helpers. Copy the entire frozen state/ directory once to output/state/ with shutil.copytree; refuse an existing destination rather than overwriting it. All subsequent journal and state updates belong to output/state/. Read Continuity(output/state).status() first: it verifies retained bytes and the parent chain, and supplies active checkpoint, decisions, completed steps and actual asset/material users. Old absolute filenames in journal records are provenance; use retained bundle files and this packet's start.blend.

Use the following real APIs (all paths are local to this packet/output):

```python
from dcc_harness.continuity import Continuity
from dcc_harness.project import Project
from dcc_harness.evidence import read_json, write_json
from dcc_harness.continuity_checks import evaluate_stage
# Inside Blender, after saving a new .blend:
from dcc_harness.continuity_blender import observe

store = Continuity(working_state_path)
status = store.status()
parent_id = status['active']['id']
```

The store's initialize/publish docstrings and returned status explain paths. For accepted work, produce a saved native checkpoint, its observe() JSON (including actual checkpoint_sha256), a passed evaluate_stage(before,after,CONTRACT.json) report with matching revision, and a factual handoff. Keep the measured baseline fixed. Never weaken the contract to obtain a pass. A failed result remains an unfinished task and must be reported.

```python
state = store.publish(
    step_id='session-NN', expected_parent=parent_id,
    checkpoint=scene_path, observation=observation_path,
    handoff=handoff_path, decision_updates=explicit_decisions_dict,
    check=check_report_path)
```

Use meaningful decision keys, such as table_width_m, stone_base_color, stool_seat_width_m, artist_stool01_center and delivery_plaque_count. Carry forward earlier decisions unless a current request changes them. This is also where brief interpretations and unresolved artistic choices belong. Observation registries describe native asset/material dependencies; they do not prove artistic merit or hidden geometry quality.

Before dispatching a bounded native mutation, log its saved script through Project(output/state).begin(label,script_path); after native inspection, finish(op_id,evidence_json). One coarse script per task group is sufficient. Pending operations block new dispatches and accepted publication through these APIs. The system is advisory; direct MCP calls are not intercepted.

When EVENT.md and EVENT_CONTRACT.json are present, compare the supplied start.blend/input-observation.json against the previous store observation before normal authoring. For the artist-edit event, retain the changed placement, record it as an explicit decision, and publish an 'artist-edit' checkpoint using that narrow event check. For a missing acknowledgement, first inspect whether the described object exists exactly once, write reconciliation evidence, and call Project.finish(pending_id,evidence_path,reconciled=True). Do not execute PENDING_OPERATION.py blindly. Then publish 'recovered-delivery' using the supplied event contract. These steps connect externally changed native state to the existing accepted history. Continue only after the uncertainty is settled; never invent evidence.

After every successful publication, refresh parent_id from the returned state['active']['id'] before publishing another step. In particular, an adopted artist edit or recovered delivery becomes the parent of the current session; do not reuse the original pre-event parent.

Perform the current session against its supplied input-observation.json and CONTRACT.json. A new context must receive output/state/, output/scene.blend and output/CONTINUE.md. Include output/observation.json, output/check.json and output/USAGE.json as evidence. The coordinator independently reopens and grades both methods. An accepted store bundle is a validated record of supplied evidence, not independent proof that a scene is correct.
