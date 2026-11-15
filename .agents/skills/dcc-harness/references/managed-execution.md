# Managed execution

Read this when `brief` shows a managed project, a capability policy or a pending managed job. The [managed execution guide](../../../../docs/guides/MANAGED_EXECUTION.md) has the full procedure and takes precedence over the advisory loop in the entry skill.

## Submitting and running

- Follow `brief` and `next`, submit with `run-submit`, and execute and reconcile through the project's backend.
- Background runs use `run-execute` and `run-reconcile`. Paired open scenes use `blender_execute` and `blender_job`, or `live-execute` and `live-reconcile`.
- Do not call `begin-edit` or `finish-edit`, or an unrelated live-write MCP, for a managed project.
- Autonomous mode advances evidence-backed stages within the brief. Approval-gated mode waits for the artist's own terminal. Never manufacture artist approval.

## Capability policy

When a project has capability policy, inspect `requirements PROJECT STAGE` before choosing a manual approach.

- Resolve qualified providers against the target and engine, and obey explicit require, prefer and fallback policy.
- Reuse a fresh service receipt instead of dispatching again.
- A missing required provider or qualification is an actionable stop. It is not a permission prompt, and manual work does not satisfy the policy.

## Lost replies and pending jobs

- On a lost acknowledgement or quota interruption, keep the operation unresolved and use the backend's status and reconciliation routes. Do not redispatch because no reply arrived.
- After a lost reply, inspect the existing managed operation UUID without resubmitting.
- Pending work or a provider handle cannot satisfy a stage.
- Uncertain termination retains the reservation and profile lease. Confirm the provider stopped and the lease was restored before restoring a precopy or releasing recovery.
- Partial metadata or stale locks require diagnosis.
- Carry unresolved jobs into the handoff.

Recurring scheduling, external-write interception and automatic mutation replay are outside this workflow.
