"""Release launches must isolate native user paths before any native fixture."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_release.py'
spec = importlib.util.spec_from_file_location('release_runner', SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseContainmentTests(unittest.TestCase):
    def test_owned_paths_exist_and_reach_child_and_descendant_with_overrides(self):
        self.assertTrue(callable(getattr(release, 'release_environment', None)),
                        'Release runner lacks owned native environment setup')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            env = release.release_environment(out, {**os.environ, 'BLENDER_USER_CONFIG': 'artist-config'})
            expected = {f'BLENDER_USER_{name.upper()}': str(out / 'native-user' / name)
                        for name in ('config', 'scripts', 'datafiles', 'extensions')}
            for key, value in expected.items():
                self.assertEqual(env[key], value)
                self.assertTrue(Path(value).is_dir())
            code = "import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith('BLENDER_USER_') or k=='QUALIFIER_OVERRIDE'}))"
            child = "import subprocess,sys; subprocess.run([sys.executable,'-c',sys.argv[1]],check=True)"
            results = []
            release.run_check('descendant', [sys.executable, '-c', child, code],
                              out=out, results=results, cwd=out, base_env=env,
                              env={'QUALIFIER_OVERRIDE': 'retained'})
            observed = json.loads((out / 'descendant.log').read_text())
            self.assertEqual({k: observed[k] for k in expected}, expected)
            self.assertEqual(observed['QUALIFIER_OVERRIDE'], 'retained')
            self.assertEqual(results[0]['exit_code'], 0)

    def test_read_only_probe_records_mismatch_and_refuses(self):
        self.assertTrue(callable(getattr(release, 'native_config_probe', None)),
                        'Release runner lacks read-only exact CONFIG preflight')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            expected = out / 'expected'; expected.mkdir()
            fake = out / 'bpy.py'
            fake.write_text("class utils:\n @staticmethod\n def user_resource(name): return " + repr(str(out / 'artist')) + "\n")
            probe = out / 'probe.py'; record = out / 'probe.json'
            probe.write_text(release.native_config_probe(expected, record))
            result = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Owned CONFIG mismatch', result.stderr)
            proof = json.loads(record.read_text())
            self.assertFalse(proof['matched'])
            self.assertFalse(proof['preference_writes'])
            fake.write_text("class utils:\n @staticmethod\n def user_resource(name): return " + repr(str(expected)) + "\n")
            # Keep the fake source size different so timestamp pyc cannot mask the corrected path.
            fake.write_text(fake.read_text() + '# corrected effective CONFIG\n')
            result = subprocess.run([sys.executable, str(probe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(record.read_text())['matched'])
