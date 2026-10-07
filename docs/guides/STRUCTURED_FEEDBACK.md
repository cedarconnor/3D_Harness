# Structured feedback and environment stages

Version 0.5.0 adds optional coordination records above the existing native checkpoint store. Use the normal agent chat and existing Blender transport. The CLI records feedback and stage evidence; it does not launch agents, inspect pixels itself, or execute native edits.

`resume PROJECT` and `review PROJECT` return a `coordination` section once enabled. It includes all note IDs, response IDs, current/historical validity, unresolved blockers, the pinned skill root and stage states. Nothing is silently limited to the most recent five notes. Projects without coordination retain their prior packet shape.

## Record and address a note

Put a JSON payload and its referenced artifacts in an owned input folder. Paths inside payloads are relative to that folder, with SHA-256 hashes. `--evidence-root` selects another base when necessary. Paths cannot traverse outside the base or pass through links/reparse points.

```powershell
python -m dcc_harness feedback-add PROJECT --note INPUT/note.json --expected-revision none --request-id UUID --out INPUT/add-receipt.json
```

Use a new canonical UUID for each new logical request, retained for a retry. Replace `none` with `coordination.revision` after the first event. Other uppercase terms here are placeholders. A lost acknowledgement may be retried with the exact request ID and payload; `ALREADY_COMMITTED` returns the original result without adding an event or executing Blender. Changed content under an old request ID is rejected. A partial bundle or stale workflow lock requires inspection.

Since 0.5.1, a committed result whose `result.passed` is false exits with status 1, like a rejected `finish-edit`; examples include a `fail` or `uncertain` verification. The event is still committed, and a retry returns the same result and status. Status 2 means the result was printed but its `--out` receipt could not be written.

An input note has no `id`; the runtime allocates it:

```json
{
  "schema": "dcc.feedback.note.v1",
  "source": {"role": "agent", "author": "reviewer", "reference": "Review of checkpoint and fixed detail image"},
  "stage_id": "materials",
  "category": "visual",
  "priority": "blocking",
  "text": "The post grain runs across its length.",
  "acceptance": "Grain follows the post; geometry and lighting remain within the declared contract.",
  "requires": ["technical", "visual"],
  "review_policy": "agent_within_brief",
  "anchor": {
    "checkpoint_id": "CHECKPOINT_MANIFEST_SHA256",
    "checkpoint_sha256": "BLEND_SHA256",
    "instance_ids": ["post.front"],
    "render": {
      "receipt": {"path": "before/receipt.json", "sha256": "RECEIPT_SHA256"},
      "settings": {"path": "before/views.json", "sha256": "SETTINGS_SHA256"},
      "view_id": "REVIEW_POST",
      "pin": {"x": 0.4, "y": 0.6}
    }
  }
}
```

Hash strings in this illustration must be replaced with real 64-character lowercase hashes. `checkpoint_id` is `active.id`, not the `.blend` hash. Targets are stable IDs present in that checkpoint's observation. `stage_id` may be null. Optional `material_ids` follow the same rule. Render receipts use `dcc.quality.renders.v1`; their images are resolved relative to the receipt and frozen with the event. The actual settings JSON is also required: its canonical digest must equal `views_digest`. Retain enough camera, crop, frame and render settings for a fresh agent to reproduce the views; the hash alone cannot do that. Completeness of those settings still needs native qualification. A pin requires a bound image and normalized coordinates. Optional `anchor.frame` has `number`, `fps_numerator` and `fps_denominator`; it records an exact frame but does not validate animation.

Categories are `technical`, `visual`, `preference`; priorities are `blocking`, `advisory`. `requires` defaults to the category's evidence type (preferences use visual), and can require both technical and visual verification. Preferences are project direction, not a global taste file. Roles and references are caller-attributed, never authenticated identities.

Author the native revision with the existing `begin-edit` / `finish-edit`, or explicitly accept an external revision. Publishing the native checkpoint does not resolve its notes. Record a separate response:

```powershell
python -m dcc_harness feedback-respond PROJECT --response INPUT/response.json --expected-revision REVISION --request-id UUID
python -m dcc_harness feedback-verify PROJECT --verification INPUT/verification.json --expected-revision NEW_REVISION --request-id NEW_UUID
```

Response schema `dcc.feedback.response.v1` requires `note_id`, `author`, `disposition`, `change`, `result` and `evidence`. `result` is `{checkpoint_id, checkpoint_sha256}` for the current native checkpoint. Dispositions: `implemented`, `partial`, `deferred`, `not_applicable`. The latter two are requests for a disposition, not automatic closure.

Verification schema `dcc.feedback.verification.v1` requires `note_id`, `response_id` (the response event's revision), `reviewer: {role, author, reference}`, `finding`, `verdict: pass|fail|uncertain` and `views: [view_id...]`. Technical contracts are recomputed from the retained inputs. Visual verification requires declared inspection of bound views; if the original note has a view, its settings digest must match. Partial work cannot be verified as resolved. Missing anchored targets require an explicit disposition instead of silently rebinding names. Same-author review is disclosed. Agent review never becomes artist acceptance.

Use `feedback-decide --decision FILE` for `reopen`, `reassign`, `deferred` or `not_applicable`. Its schema is `dcc.feedback.decision.v1` with `note_id`, `action`, `reason`, `authority: {role, author, reference}`, and current `result`; reassignment also needs `stage_id`. Blocking deferral/non-applicability requires an attributed artist decision in this first release. Historical notes are never deleted or rewritten. Supersession is represented by a new note plus an explicit disposition of the old one, not an implicit replacement.

A resolved note is current only at its verified checkpoint. After another native publication, it remains historically resolved but becomes `needs_recheck`. Repeat the response/verification against the new evidence. No field-dependency guessing or automatic carry-forward waiver is performed.

## Evidence entries

| `kind` | Additional fields and behavior |
|---|---|
| `native_contract` | `before: {checkpoint_id, checkpoint_sha256}`, `contract: {path, sha256}`. Recomputes the supported continuity contract against the result observation. Feedback target IDs must be covered. |
| `whole_scene_render`, `detail_render` | `render: {receipt: {path, sha256}, settings: {path, sha256}, view_id}`. Binds image bytes, native hash and reproducible view settings. |
| `visual_review` | `reviewer`, `verdict`, `finding`, `views`. Every inspected view must have a render entry in the same evidence list. This is an attributed assessment, not machine vision. |
| `native_reopen` | `observation: {path, sha256}`, `producer: {role, author, reference}`. Checks clean saved/native binding and preservation against the committed observation. Process independence remains a producer claim. |
| `direction_record`, `handoff` | `file: {path, sha256}` containing nonempty UTF-8 text. Content quality needs review. |
| `shared_user_report` | No additional fields; derives measured material users. |
| `dependency_report` | No additional fields; returns observed issues/coverage. It does not certify unmeasured caches, fonts or complete portability. |
| `feedback_reconciliation` | No additional fields; derives applicable unresolved blockers in a stage context. |

## Pin an environment workflow

```powershell
python -m dcc_harness workflow-template --out INPUT/environment.json
python -m dcc_harness workflow-bind PROJECT --binding INPUT/binding.json --expected-revision REVISION --request-id UUID --evidence-root INPUT
```

The built-in template covers direction, blockout, assets, materials, assembly, lighting and delivery. `--manifest FILE` permits an explicitly validated variation. Evidence names are a small fixed registry; unknown checks and cyclic/disconnected dependencies are rejected.

Binding schema `dcc.environment.binding.v1` has:

- `checkpoint`: current checkpoint identity pair.
- `authority`: attributed source of the project direction/permissions.
- `review_policies`: stage-ID mapping to `agent_within_brief` or `artist_required`; `{}` uses stage defaults.
- `inherited`: `{}` for a new sequence, or stage-ID mapping to `{reason, gaps: [...], evidence: [...]}` for existing work. Inherited predecessors must also be declared. Missing required evidence becomes an automatic gap. Delivery cannot be inherited.
- `skill_files`: every skill named by the manifest mapped to a list of `{path, sha256}` files, including its matching `SKILL.md`.
- `references`: explicit `{path, sha256}` references for required supporting documents. Preserve their relative folder layout with the skills when preparing input.

Binding freezes selected files and records the runtime version/source digest. Repository updates do not change this snapshot. Resume exposes `pinned_files_root`; read the pinned files from there. Supply supporting references deliberately; the current binder does not crawl all Markdown links or package native runtimes. A runtime digest mismatch prevents workflow mutations. There is no in-place upgrade command yet: use the matching runtime or a separately reviewed new coordination project, preserving old history.

The default allows routine agent review within the brief. It does not require the artist to approve every stage. A stage explicitly marked `artist_required` retains that requirement. Neither policy overrides failed technical checks.

## Submit, review and continue a stage

```powershell
python -m dcc_harness stage-submit PROJECT --submission INPUT/stage.json --expected-revision REVISION --request-id UUID
python -m dcc_harness stage-complete PROJECT --submission-id SUBMISSION_REVISION --review INPUT/review.json --expected-revision SUBMISSION_REVISION --request-id NEW_UUID
```

Submission schema `dcc.environment.submission.v1` contains `stage_id`, current `checkpoint`, `deliverables` (each manifest deliverable mapped to a concrete description), typed `evidence`, `feedback_ids`, and `note`. Include every applicable note, including advisory and already-resolved notes; delivery includes all notes. Incomplete submissions are retained with missing-evidence and unresolved-note lists, but cannot complete.

Completion review has `reviewer: {role, author, reference}`, `verdict: pass`, and `finding`. Completion recomputes validators, checks current feedback and enforces the retained review policy. Any intervening coordination event or native publication makes a pending submission stale. Refresh it instead of overwriting the old submission. Pending native operations prevent completion.

Use `stage-reopen --decision FILE` with schema `dcc.environment.reopen.v1`, `stage_id`, `reason` and `authority` to revisit an earlier stage. Its descendants need review again. New blocking feedback on a completed stage also reopens readiness. Historical completion receipts remain intact. Normal next-stage work does not erase them; delivery still requires current evidence and no inherited evidence gaps.

Native publication and coordination commits are separate. If Blender work is published but feedback recording fails, resume and reference that existing checkpoint. Never rebuild the edit merely to get a feedback receipt. Direct/older writers can bypass coordination; use the compatible runtime and preserve single-writer ownership.

The [implementation plan](../archive/plans/STRUCTURED_FEEDBACK_ENVIRONMENT_WORKFLOW.md) remains the design record. Its draft JSON examples are historical sketches; use this document and the packaged template for the implemented payloads.
