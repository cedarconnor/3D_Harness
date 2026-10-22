# Combined harness MCP implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver one installable package and one stdio endpoint with build rules, managed construction, evidence and a pinned Blender observation bridge.

**Architecture:** The MCP adapter calls the existing CLI/service, preserving its durable execution and owner authority. A bundled, unmodified upstream add-on is loaded behind a small allowlist adapter; its raw execution, providers, telemetry registration and upstream UI are not exposed. Rules are built from repository sources into a hash-indexed resource bundle rather than maintained as duplicate copies.

**Tech stack:** Python 3.11+, MCP Python SDK 1.26.0, setuptools, Blender 5.1; upstream mcp-for-blender 2.2.2 at 5a3618fccb2d982d0dd61e7a1879912c3100073b (protocol 14).

**Spec:** User-authorized P20 in docs/BUILD_PLAN.md; docs/guides/MANAGED_EXECUTION.md defines mutation and approval semantics.

## Constraints and rulings

- One client endpoint; stdio only. No user-wide configuration changes or automatic installation into an artist's Blender.
- Managed execution is the sole edit path exposed by MCP. Owner decisions remain in the owner's terminal; MCP always carries the agent marker.
- Agent supplies scripts and judgment. This is a trusted local tool, not an arbitrary-Python security sandbox.
- Live bridge observations are advisory and never replace independent saved-checkpoint evidence.
- Keep upstream source and MIT notice intact. No claim about licensing of owner-authored repository code.
- Ruling: retain all provider code only inside the pinned upstream source, unreachable through the adapter. This preserves upstream provenance without importing its server/telemetry dependencies or exposing bypasses.
- Ruling: keep changes on the existing codex branch, uncommitted alongside the authorized overhaul; preserve evidence and user changes.

## Review focus

Wrong bridge/protocol; split Unicode/oversized socket responses; attempted raw mutation/artist authority; wheel resources drifting from source; MCP cancellation during native work.

## Tasks

- [x] Bundle resources and provenance: build-time skill/reference closure, index verification, exclusive export; tests for traversal, tampering and installed resources.
- [x] Restricted upstream bridge: pinned source plus wrapper, bounded socket adapter, test real fragmentation/errors and disallowed commands; native proof in an owned Blender process.
- [x] Stdio harness: allowlisted CLI adapter, managed commands, input/evidence files, bundled rules/resources, default binding helper. Test cancellation and authority with real child processes and an MCP client handshake.
- [x] Release qualification: source + installed tests, native managed modes and bridge, wheel/sdist resource proof; independent final review and fixes; document exact scope and limits.

## Ledger

- 2026-10-22: P19 verified; user said "Good continue". Refreshed upstream commit through GitHub connector; pin unchanged. Integration starts here.
- Ruling: historical `runs/`, `dist/` and `build/` references are enumerated in EXTERNAL_EVIDENCE.json rather than copied into the reusable rules. Skills and maintained local reference files are shipped.
- Ruling: a blank managed project contains one non-rendering root Empty because the existing continuity contract deliberately rejects object-free observations. New authored objects still require scoped `ext.*` identities and explicit contract permissions.
- Source qualification: real stdio drove both modes, saved/reopened native cube builds, identical replay, unapproved successor refusal and a read-only GUI bridge. A protocol cancellation stopped native execution and retained the prior checkpoint. Evidence: runs/overhaul/mcp-native-cancel.
- Independent reviewer found P2 nested resource URLs broken by FastMCP's single-segment template matcher. Added a failing nested-resource protocol test, registered explicit resource URIs, and observed it pass. Reviewer established no other actionable integration defect.
- Fixed PEP 517 root imports and Windows inherited-stdin startup; retained red and green evidence. Clean release qualification is in progress.

- Final release checks: source and clean-installed suites each ran 480 tests (478 passed, two permission skips); wheel/sdist rules match; installed entry points and native units/adoption/execution/MCP all passed. Documentation-only final packaging is checked separately with unchanged runtime hashes.

- 2026-10-22 user override: remove all telemetry code. Version 0.21.1 supersedes the original unmodified-source architecture above with an observation-only derivative, preserving MIT attribution and original/modified hashes. Remove activity capture, consent/UI, trajectory snapshots, tracking links and unused provider/account/update code; require bridge protocol 2 and requalify built artifacts plus native operation.

- 0.21.1 qualification: source and clean-installed suites each ran 481 tests (479 passed, two permission skips). All 12 release checks passed, including native units/adoption/execution/MCP; the installed bridge audit recorded no outbound Python socket attempts or activity-handler changes. Final documentation packaging retains exact qualified runtime bytes.
