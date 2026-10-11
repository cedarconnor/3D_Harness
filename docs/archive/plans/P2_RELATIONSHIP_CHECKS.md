# P2: Relationship checks

Plan for [build-plan](../../BUILD_PLAN.md) item P2, written October 10, 2026, at version 0.8.0. Target version: 0.9.0, because it adds commands and a project record.

## Problem

Contracts compare measured fields such as bounds, dimensions and transforms. They cannot say whether a bench's four feet stand on the ground, because that depends on where the feet meet a surface, not on any object's own fields. The quality loop showed that measurement at the place that matters catches what images miss: the birdbath visibility gate failed two candidates that looked acceptable ([overnight study](../studies/OVERNIGHT_EVALUATION.md)).

Two further gaps come from the [repository ideas](../../reference/REPOSITORY_IDEAS_2026-10-06.md), items 1 to 3:

- **Evidence strength.** A bounding-box estimate can suggest a problem but cannot establish it. On sloped ground a bench's bounds overlap the terrain's bounds even when every foot rests correctly. A finding must say how it was established and what it permits.
- **Repair memory.** A later agent cannot see that lowering the whole bench produced penetration and raising it produced a gap. It may repeat the same ineffective repair. When some feet float while others sink, no rigid move can fix the bench, and the record should say so.

## Scope: one relation family, `supported_by`

### Relation definition

`dcc.relations.v1`, held by a project as the decision `relations` or passed as a file:

```json
{
  "schema": "dcc.relations.v1",
  "relations": [
    {"id": "bench-on-ground", "kind": "supported_by",
     "subjects": ["bench.leg.0", "bench.leg.1", "bench.leg.2", "bench.leg.3"], "support": ["ground"],
     "max_gap": 0.005, "max_penetration": 0.01, "footprint": 0.002}
  ]
}
```

Each subject must rest on one of the support surfaces. Its footprint is its evaluated vertices within `footprint` metres of its lowest point.

### Native measurement and classification

```text
python -m dcc_harness relations SAVED.blend --blender PATH --output-dir NEW_FOLDER (--project PROJECT | --spec FILE) [--strategy TEXT]
```

- A fresh background Blender opens the saved file and never saves it. For each subject it casts a vertical ray through every footprint point against the support's evaluated mesh, giving a signed distance: positive is a gap, negative is penetration. It also computes the bounds-only estimate from the subject's and support's world bounds.
- Each subject gets one finding:
  - **Codes.** `OK`, `GAP`, `PENETRATION`, `OFF_SUPPORT` (no footprint point is over the support) or `MISSING_TARGET`.
  - **Error.** The signed error in metres, from the footprint point closest to contact, against the tolerances.
  - **Evidence.** `native_raycast` for the measured finding. A bounds estimate that disagrees is reported as `bounds_only` with the permitted action `inspect`, never `repair`.
  - **Coverage.** Footprint points and hits are counted. A partial miss is reported.
- A relation whose subjects have both `GAP` and `PENETRATION` in the same measurement is marked `CONFLICT`: a rigid move of the whole group cannot fix it.
- `report.json` is bound to the source hash and the definition digest. The command exits 1 when any relation fails.

### Repair history

- With `--project`, each measurement is appended to the project's `relations/` record, under the workflow lock. It keeps the parent checkpoint, the measured file's hash, the optional `--strategy` text describing the repair just attempted, and the findings. Entries are never rewritten.
- History analysis per relation and subject, over the recorded attempts:
  - `OPPOSING`: the last two failing attempts have opposite codes.
  - `NO_PROGRESS`: the last two have the same code and the error shrank by less than 20%.
  - `IMPROVING`: the same code with the error shrinking by at least 20%; no warning.
  - `CONFLICT`, carried forward from the latest measurement.
- `next` and `brief` show the warnings with the strategies already tried, and offer a `relations` step when the project has a `relations` decision.

## Qualification

- **Portable tests.** Definition validation; classification of synthetic measurements, including tolerance edges, partial coverage, off-support, conflict and a bounds disagreement; history patterns, including that only ineffective repetition warns, an improving gap does not, and an unrelated subject is unaffected; the record is append-only and bound to the parent; guidance steps and warnings.
- **Native, source and installed.** Generated scenes:
  - a bench resting on flat ground (`OK`);
  - the bench raised 3 cm (`GAP`) and sunk 3 cm (`PENETRATION`);
  - a leg moved past the ground's edge (`OFF_SUPPORT`);
  - a bench on sloped ground with legs cut to fit, which passes natively while its bounds estimate reports penetration (`bounds_only`, `inspect`);
  - the same bench with equal legs (`CONFLICT`);
  - two recorded rigid translations that produce `OPPOSING`.

  The source file stays unchanged.
- **Fresh-agent continuation.** A packet holds the sloped-ground bench with equal legs and a history of two recorded whole-bench translations. A fresh agent is asked to make the bench stand on the ground. A control packet without the history isolates the effect. Record whether each agent tries a whole-bench translation and how it repairs the bench. Two runs are directional.

## Out of scope

- Other relation families: clearance along a path, a downpipe meeting a gutter. The record and classification are written so that they can join later.
- `relation_report` as a coordination evidence kind. It can follow once the family is qualified.
- Collision between arbitrary objects and physical stability.
