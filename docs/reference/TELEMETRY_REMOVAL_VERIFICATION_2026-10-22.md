# MCP telemetry removal — October 22, 2026

Version **0.21.1** supersedes the 0.21.0 full-source add-on bundle. The user's
explicit request to remove telemetry supersedes the original decision to wrap
unmodified upstream source. This is a modified MIT-licensed derivative of
MCP for Blender 2.2.2, commit `5a3618fccb2d982d0dd61e7a1879912c3100073b`.

## Removed code

The bundled `upstream.py` now contains eight server methods and one object-label
helper. The retained transport lifecycle and three scene readers preserve upstream
implementation, except for removal of the activity-capture hooks in start/stop.
The harness adapter still supplies the bounded, observation-only dispatcher.

Removed from shipped executable source:

- Manual operator and undo/redo recording, buffers and activity drain commands.
- Activity handlers, consent preferences, consent commands and telemetry UI.
- Trajectory/world-state capture and unused screenshot/viewport capture code.
- Tracking URL parameters, provider/account/device activation code and update checks.
- Unused upstream UI, automatic startup and raw Python execution.

The original MIT license remains. [upstream.json](../../dcc_harness/data/upstream.json)
records the original SHA-256 and a separate modified SHA-256, plus the modification
description. Harness bridge protocol 2 requires the reduced export; the MCP client
refuses protocol 1 before requesting scene data. Replace earlier bridge exports
when installing 0.21.1.

Local execution receipts, request logs, checkpoint observations and explicitly
requested scene replies remain necessary workflow records. This endpoint does not
upload them to a telemetry service.

## Verification

The new export-surface test first failed against the original bundle. It now passes
and checks the shipped Python imports, retained methods, attribution hashes and
absence of recording/telemetry/tracking symbols. All nine focused MCP/socket/stdio
tests also pass, including rejection of the older bridge protocol.

The owned Blender 5.1.1 source fixture passed all five observation commands,
raw socket mutation refusal, saved construction in autonomous and approval-gated
modes, replay and actual MCP cancellation. Its Python audit hook recorded zero
outbound socket connection attempts during bridge import/start/reads/stop. Undo,
redo and dependency-graph activity handlers were unchanged, and the bridge stopped
cleanly. Evidence: [source native report](../../runs/overhaul/mcp-no-telemetry-source/VERIFICATION.json).

Full release qualification passed all 12 checks:

| Check | Result |
| --- | --- |
| Source suite | 481 run: 479 passed, 2 Windows permission skips |
| Clean-installed suite | 481 run: 479 passed, 2 Windows permission skips |
| Wheel, source archive, rebuilt wheel | Built; bundled rule bytes match |
| Installed CLI and MCP entry points | Passed |
| Native units, adoption and managed execution | Passed |
| Installed stdio MCP and live bridge | Passed, including both modes and cancellation |
| Installed bridge audit | Zero outbound Python socket attempts; activity handlers unchanged; clean stop |

Full evidence: [release verification](../../runs/overhaul/release-0211-verified/VERIFICATION.json)
and [installed MCP report](../../runs/overhaul/release-0211-verified/native-mcp/VERIFICATION.json).
The source suite emitted the previously recorded detached-process ResourceWarning;
MCP tests emitted the existing SDK/settings forward-reference warning. Neither
failed a test or protocol/native check.

Final documentation packaging is checked against the qualified wheel for identical
runtime and bridge bytes. Its source-archive rebuild must match those bytes and
the rules archive. Installed resource/protocol tests and a scan of executable code
in all three delivery formats are recorded in RELEASE.json.

## Limits and delivery

These are owned test fixtures, not artist production acceptance or a whole-system
network packet capture. The network audit covers Python socket connection attempts
in the bridge process; static inspection also removes unused network/provider code.
No global MCP registration or artist Blender configuration was changed.

Historical 0.21.0 archives and diagnostic snapshots remain as earlier evidence;
they are excluded from the current rules bundle and are superseded by 0.21.1.
Current delivery is recorded at [RELEASE.json](../../dist/0.21.1/RELEASE.json).
