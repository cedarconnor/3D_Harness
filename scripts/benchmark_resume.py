"""Measure one fresh-process resume, retaining output and source-store integrity.

Run baseline and candidate in alternating processes against the same project.
File hashing outside the timed region warms filesystem caches equally; this is
not a cold-disk or native-authoring benchmark.
"""
import argparse
import cProfile
import io
from pathlib import Path
import pstats
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    runtime = Path(args.runtime).resolve()
    sys.path.insert(0, str(runtime))
    import dcc_harness
    from dcc_harness.evidence import digest, file_hash, write_json
    from dcc_harness.workflow import resume

    assert Path(dcc_harness.__file__).resolve().is_relative_to(runtime)
    project = Path(args.project).resolve()
    output = Path(args.out).resolve()
    if output.is_relative_to(project):
        raise ValueError('Benchmark outputs must be outside the retained project')
    output.mkdir(parents=True, exist_ok=False)
    inventory = lambda: {str(p.relative_to(project)): file_hash(p)
                         for p in sorted(project.rglob('*')) if p.is_file()}
    before = inventory()
    profiler = cProfile.Profile() if args.profile else None
    if profiler:
        profiler.enable()
    started = time.perf_counter()
    packet = resume(project)
    seconds = time.perf_counter() - started
    if profiler:
        profiler.disable()
        profiler.dump_stats(str(output / 'resume.prof'))
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(25)
        (output / 'profile.txt').write_text(stream.getvalue(), encoding='utf-8')
    assert before == inventory(), 'Read-only benchmark changed the source project'
    write_json(output / 'packet.json', packet)
    result = {'version': dcc_harness.__version__, 'runtime': dcc_harness.__file__,
              'seconds': seconds, 'profiled': args.profile, 'packet_digest': digest(packet),
              'project_inventory_digest': digest(before), 'project_unchanged': True,
              'retained_files': len(before), 'checkpoints': packet['active']['sequence'],
              'status': packet['status'], 'pending': len(packet['pending']),
              'unresolved_edits': len(packet['unresolved_edits']),
              'conditions': 'Fresh Python process; source hashing warms filesystem cache outside timing.'}
    write_json(output / 'result.json', result)
    print(f"{result['version']}: {seconds:.3f}s; {result['status']}; {result['packet_digest']}")


if __name__ == '__main__':
    main()
