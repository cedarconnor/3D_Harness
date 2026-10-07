"""Run code against an isolated copy of selected dcc_harness modules.

Trial packets ship only a listed subset of the runtime. These helpers prove
that the subset imports and works without the rest of the package.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import dcc_harness

PACKAGE = Path(dcc_harness.__file__).parent


def run_isolated(helper_files, code):
    with tempfile.TemporaryDirectory() as temp:
        package = Path(temp) / 'dcc_harness'
        package.mkdir()
        for name in helper_files:
            shutil.copyfile(PACKAGE / name, package / name)
        (Path(temp) / 'value.json').write_text('{"value": 1}\n', encoding='utf-8')
        guard = ('import sys, pathlib, dcc_harness\n'
                 'assert pathlib.Path(dcc_harness.__file__).resolve().parents[1] == '
                 'pathlib.Path(sys.argv[1]).resolve(), dcc_harness.__file__\n')
        env = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
        return subprocess.run([sys.executable, '-c', guard + code, temp], cwd=temp, env=env,
                              capture_output=True, text=True)
