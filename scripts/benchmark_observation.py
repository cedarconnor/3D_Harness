"""Fresh-process observation read+validation and optional lossless packing.

File hashing warms filesystem caches before timing. This measures storage
transport on one observation, not full history resume or Blender observation.
"""
import argparse
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--pack', action='store_true')
    args = parser.parse_args()
    runtime = Path(args.runtime).resolve()
    sys.path.insert(0, str(runtime))
    import dcc_harness
    from dcc_harness.evidence import digest, file_hash, read_json, validate_observation, write_json
    assert Path(dcc_harness.__file__).resolve().is_relative_to(runtime)
    source = Path(args.source).resolve()
    output = Path(args.out).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_sha = file_hash(source)
    start = time.perf_counter()
    observation = read_json(source)
    read_seconds = time.perf_counter() - start
    validate_observation(observation)
    total_seconds = time.perf_counter() - start
    logical_digest = digest(observation)
    result = {'version': dcc_harness.__version__, 'runtime': dcc_harness.__file__,
              'source': str(source), 'source_bytes': source.stat().st_size,
              'read_seconds': read_seconds, 'read_validate_seconds': total_seconds,
              'revision': observation['revision'], 'logical_digest': logical_digest,
              'conditions': 'Fresh process; source hashing warms filesystem cache outside timing.'}
    if args.pack:
        destination = output/'observation.json'
        start = time.perf_counter()
        write_json(destination, observation, compact_observation=True)
        result['pack_seconds'] = time.perf_counter() - start
        result['compact_bytes'] = destination.stat().st_size
        result['compact_sha256'] = file_hash(destination)
        restored = read_json(destination)
        validate_observation(restored)
        assert digest(restored) == logical_digest, 'Expanded values or metadata differ'
        result['logical_digest_identical'] = True
    assert file_hash(source) == source_sha, 'Source changed during benchmark'
    result.update(source_unchanged=True, source_sha256=source_sha)
    write_json(output/'result.json', result)
    print(f"{source.name}: read+validate {total_seconds:.3f}s; {result.get('compact_bytes', source.stat().st_size)} bytes")


if __name__ == '__main__':
    main()
