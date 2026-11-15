# Live scene

Read this when the work happens in an open Blender scene. [Live Blender operation](../../../../docs/guides/LIVE_BLENDER.md) has the procedure and [combined MCP operation](../../../../docs/guides/COMBINED_MCP.md) has the setup.

- Discover the explicit session, select its scene, and inspect stable target IDs before editing.
- Attach into a new live project.
- Never infer a target from the selection, and never reuse a preparation across file reloads.
- A lost reply requires status inspection. An external edit requires an explicit refresh.
- Preview renders are evidence to inspect, not approval.
- Unsupported contexts and unqualified add-ons remain explicit stops.
- Readiness to inspect is not permission to mutate an unknown live editor. Preserve the artist's current document, and use an owned background file when live editing is unnecessary.
- An interactive session observes `native_dirty: true`, because Blender does not mark edits made from Python as modified.
