# Combined harness MCP verification — October 22, 2026

Historical 0.21.0 report. Its full-source add-on bundle is superseded by the
[0.21.1 telemetry-removal derivative](TELEMETRY_REMOVAL_VERIFICATION_2026-10-22.md).

Version **0.21.0**, on `codex/managed-execution-overhaul`. This follows the
[verified managed-execution overhaul](MANAGED_EXECUTION_VERIFICATION_2026-10-22.md).
The main branch and client configuration were not changed. No artist scene was
opened; qualification used owned fixtures. Changes remain uncommitted.

## Delivered behavior

- One Python distribution provides `dcc-harness`, `dcc-harness-mcp`, the build-rule
  reference bundle and an exportable observation add-on.
- `new-project` creates an owned baseline with a non-rendering root Empty, independently
  observes it, binds the packaged rules and chooses autonomous or approval-gated mode.
- MCP construction goes through the existing managed execution service. Legacy edit
  and artist-approval commands are not exposed. The owner still approves from their
  own terminal; agent markers are forced on child commands.
- The optional live bridge wraps the unmodified MIT-licensed upstream add-on at
  `5a3618fccb2d982d0dd61e7a1879912c3100073b`, version 2.2.2, protocol 14. Its Git blob
  is `9ffe9d84a031b43151d9a18d86e6972d3f704946`; SHA-256 is
  `229ee114f0504b486bdd24bbc8b08fa9b22112f5e831ef8b2e9cc507e9ccbbfe`.
  Both adapter and socket restrict commands to observation. Upstream UI, raw live
  execution, providers and telemetry are not registered by this adapter.

## Qualification

The maintained release command ran against the checkout, built wheel and a newly
created Python environment with normally resolved dependencies:

| Gate | Result |
|---|---|
| Source suite | 480 tests: 478 passed, 2 Windows symlink-permission skips; 222.871 seconds |
| Wheel and source archive | Both build; their bundled rule archives are byte-identical |
| Clean Python environment | Wheel and MCP SDK 1.26.0 installed successfully |
| Installed suite | 480 tests: 478 passed, same 2 skips; 214.410 seconds |
| Installed CLI entry points | Both pass |
| Native units | Physical support units across scales; conservative non-unit GLB refusal; source preserved |
| Native adoption | Supported collection instances succeed; unsupported vertex instancing refuses; identities and preservation checked |
| Native execution | Both modes publish twice; replay, timeout, cancellation and synthetic owner-authority path checked |
| Installed MCP | Actual stdio initialize/list/call/resource reads; owned Blender GUI bridge; default project initialization and managed builds in both modes |

The installed MCP fixture built and independently observed a one-metre cube.
Autonomous mode completed direction and published a successor edit. Gated mode
returned `AWAITING_APPROVAL` and refused the successor. Identical operation requests
returned retained results. A real MCP cancellation notification stopped a sleeping
native script, retained the accepted checkpoint and left explicit cancellation and
failure records. The original live scene and both initialization baselines stayed
unchanged. A direct raw socket `execute_code` probe was refused.

Evidence: `runs/overhaul/release-021-verified/VERIFICATION.json`, its per-check logs,
and the native subdirectories. Dependency versions are recorded in `wheel-install.log`.
The final distributable's hashes and documentation-only packaging checks are in
[RELEASE.json](../../dist/0.21.0/RELEASE.json). The wheel is
[dcc_harness-0.21.0-py3-none-any.whl](../../dist/0.21.0/dcc_harness-0.21.0-py3-none-any.whl).

## Review and corrections

An independent reviewer established one P2 defect: FastMCP's resource template could
not match nested skill/guide paths. A real protocol regression failed, explicit
resource registration replaced the template, and the regression passed. No other
actionable integration defect was established in that review.

Qualification also corrected Windows inherited-stdin startup, PEP 517 source imports,
a missing source-archive changelog dependency, and environment-dependent enumeration
of excluded historical directories. Regression and failed qualification logs remain
as diagnostics; they are not the final result. Historical run/build outputs are
explicitly listed in `EXTERNAL_EVIDENCE.json` instead of bundled.

## Limits

This is Windows/Python 3.11/Blender 5.1.1 qualification with disposable fixtures,
not artist acceptance or a full production environment comparison. The agent still
supplies reasoning, scripts and visual review. The server is trusted local automation,
not a Python or filesystem sandbox. Abruptly killing the entire MCP controller can
leave a native child requiring inspection before reconciliation.

The live surface is intentionally smaller than upstream: no paid generation,
downloads or arbitrary live Python. The package includes Blender's add-on, not Blender
itself. No user-level client registration or Blender installation was performed.
The original artistic-quality comparison gate remains open.

Early GUI debugging used Blender's default temporary recovery directory; the
maintained qualifier redirects recovery into its own output folder.

The source suite emitted the previously recorded detached-render `ResourceWarning`;
tests still passed. The SDK/settings dependency combination emits a forward-reference
warning on startup; real protocol calls passed in both source and clean installation.
Neither warning is counted as native or artistic qualification.

See [combined MCP setup and operation](../guides/COMBINED_MCP.md).
