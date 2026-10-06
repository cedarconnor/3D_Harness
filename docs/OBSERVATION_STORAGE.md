# Compact observation storage

Version 0.4.6 can pool repeated evaluated UV arrays inside a single JSON file. This is useful for environments with many instances of plants, tiles or other shared meshes. It changes storage only: the expanded `dcc.observation.v1` content, logical revision, tolerances and native binding remain the same.

## Write new evidence

Inside the supported Blender Python runtime, after saving an owned native file:

```python
from dcc_harness.continuity_blender import observe
from dcc_harness.evidence import write_json

write_json("C:/project/new-observation.json", observe(), compact_observation=True)
```

Opt in only when every consumer uses harness 0.4.6 or later. Default `write_json` behavior remains plain JSON. Both formats work with `start`, `begin-edit`, `finish-edit`, `resume`, `review` and the existing checks. Publication retains the supplied observation bytes; a history can contain both formats.

To make a compact copy of an existing observation:

```powershell
python -m dcc_harness pack-observation C:/project/input.json C:/project/new-compact.json
```

The destination must not exist. Never replace an observation already retained in a checkpoint or edit reservation; manifests bind its exact file hash. Conversion verifies logical integrity and unchanged source bytes. It does not reopen Blender, refresh stale evidence, adopt edits or establish native correctness.

## Read and verify

```python
from dcc_harness.evidence import read_json, validate_observation

observation = read_json("C:/project/new-compact.json")
validate_observation(observation)
```

Use `read_json`, not a bare `json.load`: the latter returns the storage envelope. The reader checks pooled block hashes and structure, then restores independent lists. `validate_observation` checks the original logical revision; workflow consumers additionally verify native binding and the full retained history. Reading does not cache a verification result.

The storage envelope has schema `dcc.observation.storage.v1`, an `observation` payload and `uv_blocks` keyed by SHA-256 of each array's canonical JSON. Only `objects.*.evaluated_uv_values.*` is pooled. Arrays below 256 values stay inline; if none qualify, the file remains an ordinary observation with compact whitespace. No quantization, external sidecars or binary decoder is involved. Float precision, signed zero and integer versus float representation survive encoding.

The decoder rejects missing, unused or modified blocks, malformed references, unsupported storage versions, nonnumeric/nonfinite UV data and more than 50 million expanded UV scalar values. This bounds reference expansion, not total JSON file size or all process memory. Large inputs still require memory for the decoded observation and canonical validation. Choose ordinary storage if the observation exceeds that limit.

## Qualification boundaries

Use [the measurements](OBSERVATION_0_4_6_RESULTS.md) for actual savings and timings. Compact transport does not reduce native observation work, geometry, renders, the logical UV arrays held in memory, or mandatory full-history validation. Old retained files are not migrated. Large histories will still accumulate cost; do not drop measured fields or skip verification to make resume faster.
