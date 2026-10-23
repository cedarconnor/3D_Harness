# Third-party notices

The combined distribution contains an observation-only derivative of the Blender add-on from
[ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender/tree/5a3618fccb2d982d0dd61e7a1879912c3100073b),
version 2.2.2, commit `5a3618fccb2d982d0dd61e7a1879912c3100073b`.
Its MIT license is retained at `dcc_harness/data/bridge/LICENSE.upstream` and
inside every exported add-on zip. Copyright (c) 2025 Siddharth Ahuja.

The adjacent `__init__.py` is a 3D Harness adapter, not an upstream file. It
supplies observation tools, its own start/stop panel, and the paired attachment,
job submission/cancellation/acknowledgment and recovery surface. The reduced
upstream derivative supplies observation/transport code; paired execution is
separately authored harness adapter code. The upstream dispatcher is replaced.
Activity recording, telemetry consent/UI, trajectory capture,
tracking links, provider/account/update code, raw execution and upstream UI have been
removed from the upstream derivative. Only transport lifecycle, three scene readers
and their object-label helper remain in that reduced upstream code. `dcc_harness/data/upstream.json` records both the
original upstream SHA-256 and the modified bundled SHA-256, plus modification details.
The MCP Python SDK is a separately installed dependency, pinned in pyproject.toml;
its own distribution contains its license. These notices do not select a license
for owner-authored 3D Harness code.
