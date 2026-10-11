# P6: Evidence and coverage depth, first part

Plan for [build-plan](../../BUILD_PLAN.md) item P6, written October 11, 2026, at version 0.14.0, alongside its tests. Target version: 0.15.0.

## Problem

Three gaps make the record either too strict to use or too eager to throw work away.

- **Lighting.** Contracts refuse every new light, so a lighting stage cannot add a lamp through a scoped edit.
- **World and scene settings.** No contract can permit a world or other scene-setting change, although the comparator supports it.
- **Rechecks.** Every published checkpoint marks every resolved note `needs_recheck`, even when the edit could not have touched it.

The E5 continuation exposed a fourth: the agent hid an object from render instead of deleting it, because a deleted target makes the note impossible to verify.

## Scope

- **Contract permissions.**
  - `allowed_new_lights`: prefixes beneath `ext.`. A new light matching one is not a failure, but it still needs `allowed_new_prefixes` to be created.
  - `allowed_scene_fields`: distinct top-level scene field names, such as `world`, that may change.
- **Dependency-aware rechecks.** A closed note stays `current` after a later checkpoint in two cases:
  - nothing observed changed, so the revisions are equal; this applies to any note;
  - for a technical note with targets, its objects and their materials, plus its named materials, are unchanged.

  Visual notes depend on everything an image could show, so any other observed change still needs a recheck. Every note carries a `validity_reason`.
- **Deliberate removal.** A feedback response may list `removed_targets`. Each must be one of the note's objects, absent at the response's checkpoint, and permitted for deletion (`allowed_deleted_ids`) by a contract in the response's evidence. Verification then accepts those targets as missing.

## Qualification

- **Portable tests.**
  - Each permission and its refusal.
  - Validity across an unchanged re-save, a world change and a target change, for technical and visual notes.
  - Removal with and without a permitting contract.
- **Native.** `scripts/qualify_coverage.py` on the relations probe's bench scenes:
  - a lamp and world change is refused without permissions and published with them;
  - a verified technical note on one leg stays current through that edit;
  - the note needs a recheck after the bench is sunk into the ground.

## Moved to P13

The remainder of P6's original scope needs new native observer fields and moves to P13:

- UV overlap;
- texel density;
- fine-grained modifier and node permissions.
