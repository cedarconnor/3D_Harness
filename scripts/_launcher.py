"""Shared launcher for the qualify_* orchestrators.

Parses the common arguments, puts a source checkout first on the path when --runtime is given (so
the same script qualifies the source tree or an installed wheel), creates the new output folder, and
runs `python -m dcc_harness` and background Blender the same way every time. Evaluators that are
copied into frozen packets do not import this; they stay self-contained.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
BLENDER_FLAGS = ('--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1')


class Qualification:
    def __init__(self, description=None, arguments=()):
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument('--blender', required=True)
        parser.add_argument('--out', required=True)
        parser.add_argument('--runtime', help='Source checkout; omit for installed package testing')
        for name, options in arguments:
            parser.add_argument(name, **options)
        self.args = parser.parse_args()
        if self.args.runtime:
            sys.path.insert(0, self.args.runtime)
        import dcc_harness
        self.runtime = Path(dcc_harness.__file__).resolve().parent.parent
        self.version = dcc_harness.__version__
        self.out = Path(self.args.out).resolve()
        self.out.mkdir(parents=True, exist_ok=False)

    def run(self, *args, env=None, input=None, cwd=None):
        """Run `python -m dcc_harness` from the runtime under test; stdin is closed unless input is given."""
        options = {'input': input} if input is not None else {'stdin': subprocess.DEVNULL}
        return subprocess.run([sys.executable, '-m', 'dcc_harness', *map(str, args)], cwd=cwd or self.runtime,
                              capture_output=True, text=True, env=env or os.environ, **options)

    def call(self, *args, expect=0, cwd=None, env=None):
        """Run and check the exit code (None: any failure), returning the parsed output and stderr."""
        proc = self.run(*args, cwd=cwd, env=env)
        ok = proc.returncode == expect if expect is not None else proc.returncode != 0
        assert ok, (args, proc.returncode, proc.stderr[-2000:])
        text = proc.stdout.strip()
        return (json.loads(text) if text.startswith('{') else text or None), proc.stderr

    def cli(self, *args, expect=0, cwd=None, env=None):
        return self.call(*args, expect=expect, cwd=cwd, env=env)[0]

    def refused(self, args, message, **options):
        """Require a failure whose stderr contains message; return the last line's message."""
        proc = self.run(*args, **options)
        assert proc.returncode != 0 and message in proc.stderr, (args, proc.stderr[-1500:])
        return proc.stderr.strip().splitlines()[-1].split(': ', 1)[-1]

    def blender(self, log_name, *arguments):
        """Run background Blender with the qualification flags, logging to a new file in the output folder."""
        with (self.out / log_name).open('x', encoding='utf-8') as log:
            subprocess.run([self.args.blender, *BLENDER_FLAGS, *map(str, arguments)], stdout=log, stderr=subprocess.STDOUT, check=True)

    def finish(self, summary):
        from dcc_harness.evidence import write_json
        summary = {'runtime': str(self.runtime), 'version': self.version, **summary, 'passed': True}
        write_json(self.out / 'summary.json', summary)
        print(json.dumps(summary, indent=2))
        return summary


class ScriptedOwner:
    """Stands in for the owner's terminal: an interactive input outside any agent session, typing the shown code."""

    def __init__(self):
        self.environ, self.shown = {}, []

    def isatty(self):
        return True

    def ask(self, text):
        self.shown.append(text)
        return re.search(r'Type ([A-Z0-9]{4})', text).group(1)
