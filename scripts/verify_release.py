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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, help='Fresh evidence directory')
    parser.add_argument('--blender', help='Run maintained native qualifications against the installed wheel')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    results = []

    def run(name, command, *, cwd=repo, env=None):
        with (out / (name + '.log')).open('x', encoding='utf-8') as log:
            completed = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        results.append({'name': name, 'exit_code': completed.returncode, 'log': str(out / (name + '.log'))})
        (out / 'progress.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(name, 'PASS' if completed.returncode == 0 else 'FAIL', flush=True)
        if completed.returncode:
            raise SystemExit(completed.returncode)

    run('source-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run('wheel-build', [sys.executable, '-m', 'pip', 'wheel', '.', '--no-deps', '--no-build-isolation', '--wheel-dir', str(out / 'wheels')])
    wheel, = (out / 'wheels').glob('*.whl')
    run('sdist-build', [sys.executable, '-c', f"from setuptools.build_meta import build_sdist; build_sdist({str(out / 'sdist')!r})"])
    sdist, = (out / 'sdist').glob('*.tar.gz')
    run('sdist-wheel', [sys.executable, '-m', 'pip', 'wheel', str(sdist), '--no-deps', '--no-build-isolation', '--wheel-dir', str(out / 'sdist-wheels')])
    rebuilt, = (out / 'sdist-wheels').glob('*.whl')
    with zipfile.ZipFile(wheel) as first, zipfile.ZipFile(rebuilt) as second:
        assert first.read('dcc_harness/data/rules.zip') == second.read('dcc_harness/data/rules.zip'), 'sdist rules differ'
    clean = out / 'venv'
    venv.EnvBuilder(with_pip=True).create(clean)
    python = str(clean / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
    run('wheel-install', [python, '-m', 'pip', 'install', str(wheel)])
    target = Path(subprocess.check_output([python, '-c', 'import sysconfig; print(sysconfig.get_paths()["purelib"])'], text=True).strip())
    env = dict(os.environ, PYTHONPATH=str(target))
    code = ("from pathlib import Path; import dcc_harness; import unittest; "
            f"assert Path(dcc_harness.__file__).resolve().is_relative_to(Path({str(target)!r})); "
            "print(dcc_harness.__file__, flush=True); "
            f"suite=unittest.defaultTestLoader.discover({str(repo / 'tests')!r}); "
            "result=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(not result.wasSuccessful())")
    run('installed-tests', [python, '-c', code], cwd=out, env=env)
    run('installed-cli', [python, '-m', 'dcc_harness', '--help'], cwd=out, env=env)
    run('installed-mcp-cli', [str(clean / ('Scripts/dcc-harness-mcp.exe' if os.name == 'nt' else 'bin/dcc-harness-mcp')), '--help'], cwd=out, env=env)
    if args.blender:
        for name in ('units', 'adoption', 'execution', 'mcp'):
            run('native-' + name, [python, str(repo / 'scripts' / ('qualify_' + name + '.py')),
                                  '--blender', str(Path(args.blender).resolve()), '--runtime', str(target),
                                  '--out', str(out / ('native-' + name))], cwd=out, env=env)
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
