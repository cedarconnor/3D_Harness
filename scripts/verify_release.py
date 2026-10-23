"""Repeatable source/wheel qualification. No installer or user configuration changes."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import hashlib
import zipfile
import venv


def release_environment(out, parent=None):
    """Precreate native user directories; descendants inherit these owned paths."""
    env = dict(os.environ if parent is None else parent)
    for name in ('config', 'scripts', 'datafiles', 'extensions'):
        directory = out / 'native-user' / name
        directory.mkdir(parents=True, exist_ok=False)
        env['BLENDER_USER_' + name.upper()] = str(directory)
    return env


def run_check(name, command, *, out, results, cwd, base_env, env=None):
    # Specific qualifiers may supply overrides without dropping release containment.
    child_env = {**base_env, **(env or {})}
    with (out / (name + '.log')).open('x', encoding='utf-8') as log:
        completed = subprocess.run(command, cwd=cwd, env=child_env, stdout=log, stderr=subprocess.STDOUT)
    results.append({'name': name, 'exit_code': completed.returncode, 'log': str(out / (name + '.log'))})
    (out / 'progress.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(name, 'PASS' if completed.returncode == 0 else 'FAIL', flush=True)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def native_config_probe(expected, record):
    """A self-contained Blender probe: read CONFIG and abort before native fixtures."""
    return ("import bpy, json\nfrom pathlib import Path\n"
            f"expected = Path({str(expected)!r}).resolve()\n"
            "actual = Path(bpy.utils.user_resource('CONFIG')).resolve()\n"
            "proof = {'expected_config': str(expected), 'effective_config': str(actual), "
            "'matched': actual == expected, 'preference_writes': False}\n"
            f"Path({str(record)!r}).write_text(json.dumps(proof, indent=2), encoding='utf-8')\n"
            "print(json.dumps(proof), flush=True)\n"
            "if actual != expected: raise RuntimeError('Owned CONFIG mismatch; refusing native fixtures')\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, help='Fresh evidence directory')
    parser.add_argument('--blender', help='Run maintained native qualifications against the installed wheel')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    results = []
    base_env = release_environment(out)

    def run(name, command, *, cwd=repo, env=None):
        run_check(name, command, out=out, results=results, cwd=cwd, base_env=base_env, env=env)

    run('source-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run('wheel-build', [sys.executable, '-m', 'pip', 'wheel', '.', '--no-deps', '--no-build-isolation', '--wheel-dir', str(out / 'wheels')])
    wheel, = (out / 'wheels').glob('*.whl')
    run('sdist-build', [sys.executable, '-c', f"from setuptools.build_meta import build_sdist; build_sdist({str(out / 'sdist')!r})"])
    sdist, = (out / 'sdist').glob('*.tar.gz')
    run('sdist-wheel', [sys.executable, '-m', 'pip', 'wheel', str(sdist), '--no-deps', '--no-build-isolation', '--wheel-dir', str(out / 'sdist-wheels')])
    rebuilt, = (out / 'sdist-wheels').glob('*.whl')
    with zipfile.ZipFile(wheel) as first, zipfile.ZipFile(rebuilt) as second:
        assert first.read('dcc_harness/data/rules.zip') == second.read('dcc_harness/data/rules.zip'), 'sdist rules differ'
        expected = {name: hashlib.sha256(first.read(name)).hexdigest() for name in first.namelist() if name.startswith('dcc_harness/')}
        actual = {name: hashlib.sha256(second.read(name)).hexdigest() for name in second.namelist() if name.startswith('dcc_harness/')}
        assert actual == expected, 'sdist-rebuilt runtime or bridge members differ'
    clean = out / 'venv'
    venv.EnvBuilder(with_pip=True).create(clean)
    python = str(clean / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
    run('wheel-install', [python, '-m', 'pip', 'install', str(wheel)])
    target = Path(subprocess.check_output([python, '-c', 'import sysconfig; print(sysconfig.get_paths()["purelib"])'], text=True).strip())
    env = dict(base_env, PYTHONPATH=str(target))
    code = ("from pathlib import Path; import dcc_harness; import unittest; "
            f"assert Path(dcc_harness.__file__).resolve().is_relative_to(Path({str(target)!r})); "
            "print(dcc_harness.__file__, flush=True); "
            f"suite=unittest.defaultTestLoader.discover({str(repo / 'tests')!r}); "
            "result=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(not result.wasSuccessful())")
    run('installed-tests', [python, '-c', code], cwd=out, env=env)
    run('installed-cli', [python, '-m', 'dcc_harness', '--help'], cwd=out, env=env)
    run('installed-mcp-cli', [str(clean / ('Scripts/dcc-harness-mcp.exe' if os.name == 'nt' else 'bin/dcc-harness-mcp')), '--help'], cwd=out, env=env)
    export_code = ("from dcc_harness.distribution import export_addon, verify_addon; "
                   "import sys,json; export_addon(sys.argv[1]); print(json.dumps(verify_addon(sys.argv[1])))")
    run('source-bridge-export', [sys.executable, '-c', export_code, str(out / 'source-bridge.zip')])
    run('installed-bridge-export', [python, '-c', export_code, str(out / 'installed-bridge.zip')], cwd=out, env=env)
    with zipfile.ZipFile(out / 'source-bridge.zip') as first, zipfile.ZipFile(out / 'installed-bridge.zip') as second:
        assert {n: first.read(n) for n in first.namelist()} == {n: second.read(n) for n in second.namelist()}, 'source/installed bridge mismatch'
    if args.blender:
        probe = out / 'native-config-preflight.py'
        probe.write_text(native_config_probe(Path(base_env['BLENDER_USER_CONFIG']),
                                            out / 'native-config-preflight.json'), encoding='utf-8')
        run('native-config-preflight', [str(Path(args.blender).resolve()), '--background', '--offline-mode',
            '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', str(probe)],
            cwd=out, env=env)
        run('native-paths', [python, str(repo / 'scripts/qualify_native_paths.py'),
            '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
            '--out', str(out / 'native-paths')], cwd=out, env=env)
        for name in ('units', 'adoption', 'execution', 'mcp'):
            run('native-' + name, [python, str(repo / 'scripts' / ('qualify_' + name + '.py')),
                                  '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
                                  '--out', str(out / ('native-' + name))], cwd=out, env=env)
        run('native-live', [python, str(repo / 'scripts/qualify_live.py'), '--blender', str(Path(args.blender).resolve()),
                           '--runtime', str(target), '--out', str(out / 'native-live'), '--case', 'all'], cwd=out, env=env)
        run('native-live-preservation', [python, str(repo / 'scripts/qualify_live_preservation.py'),
            '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
            '--out', str(out / 'native-live-preservation')], cwd=out, env=env)
        run('native-live-transport', [python, str(repo / 'scripts/qualify_live_transport.py'),
            '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
            '--out', str(out / 'native-live-transport')], cwd=out, env=env)
        run('native-review-capabilities', [python, str(repo / 'scripts/qualify_review_capabilities.py'),
            '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
            '--out', str(out / 'native-review-capabilities')], cwd=out, env=env)
        run('native-capabilities',[python,str(repo/'scripts/qualify_capabilities.py'),'--blender',str(Path(args.blender).resolve()),
            '--runtime',str(target),'--out',str(out/'native-capabilities'),'--case','all'],cwd=out,env=env)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert 'dcc_harness/execution.py' in names and 'dcc_harness/_execution_blender.py' in names
        assert 'dcc_harness/data/rules.zip' in names and 'dcc_harness/data/bridge/LICENSE.upstream' in names
    (out / 'VERIFICATION.json').write_text(json.dumps({'passed': True, 'checks': results,
        'wheel': str(wheel), 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(), 'wheel_files': names,
        'native_qualified': bool(args.blender), 'installed_runtime': str(target),
        'limits': 'Clean Python environment on this host, source test fixtures available. Owned Blender fixtures; no user registration or artist production qualification.'}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
