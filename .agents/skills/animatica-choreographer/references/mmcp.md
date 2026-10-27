# MMCP connection and adapter reference

Use this for Choreographer self-hosting or explicit adapter work. [MMCP](https://animatica.ai/mmcp) means Motion Model Context Protocol: an HTTP motion-generation contract. It is not an agent MCP server and does not itself expose Blender scene-editing tools. Do not register its generation URL as an agent MCP transport.

Documentation checked 2026-10-27. The landing page labels itself v1.0-rc1 while reference pages describe 1.2 features. Read the connected server's capabilities and matching schema; do not infer installed support from either page alone.

## Discover before constructing requests

Read [capabilities](https://animatica.ai/mmcp/docs/reference/capabilities) with `GET /capabilities`. Retain the response with the endpoint and model identity. Check native FPS, supported segments/constraints, loop, sample and duration limits, async and batch support. If `supports_retargeting` is false, send `canonical_skeleton` verbatim. When true, the request may carry the user's skeleton; that does not prove compatibility with a particular control rig. Motion/video reference segments require explicit advertised support.

Follow the [client quickstart](https://animatica.ai/mmcp/docs/get-started/quickstart-client) for a first request against an authorized endpoint. The SDK is optional; installing it is not required to use Choreographer's UI. Preserve requests and responses as evidence without retaining credentials.

## Request, timing and coordinates

The [request schema](https://animatica.ai/mmcp/docs/reference/generate-request) requires `protocol_version`, a discovered `model` and `skeleton`. Supply segments and/or constraints. Top-level `duration_frames` is required for constraints-only requests and forbidden with nonempty segments. Reproducing a selected variation requires the same seed, sample count and sample index; a derived single-sample seed is not guaranteed equivalent.

Per [timing](https://animatica.ai/mmcp/docs/concepts/timing), frame counts use `timing.fps` when supplied, otherwise the model FPS. Convert seconds explicitly; preserve the scene's effective FPS and record any resampling. Review stitched chunk boundaries on long takes.

The [coordinate contract](https://animatica.ai/mmcp/docs/concepts/coordinates) is right-handed Y-up, metres, with XYZW quaternions. Convert Blender Z-up at the boundary: position `(x,y,z)` becomes `(x,z,-y)` and the inverse is `(x,-z,y)`. Account for Blender's quaternion component order when using its math types. Convert once; do not re-convert data already handled by a glTF importer. Verify a known rest pose and root displacement before processing a full shot.

## Response and uncertain outcomes

`POST /generate` can complete synchronously or return an [async job](https://animatica.ai/mmcp/docs/reference/async). For `202`, retain `Location` and honor the latest `Retry-After` while polling that job. Bound waiting to the task budget. Cancellation is optional server behavior. A timeout or expired job is not proof that generation never ran; reconcile rather than silently submitting again.

Decode the [response](https://animatica.ai/mmcp/docs/reference/response) according to its content type: glTF JSON or binary GLB. Each sample is an animation; `MMCP_motion` supplies FPS, frame counts, contacts and chunk boundaries when available. Validate joint mapping, sample count and duration before applying it to an owned action. Preserve extra rig controls, face and finger channels through explicit client-side rig handling. In-place conversion must separate travel from body sway; simply zeroing pelvis translation removes intended movement.

No network client, server installation or native adapter is implemented by this reference. Qualify any future implementation on an owned fixture through the harness before claiming managed Animatica execution.
