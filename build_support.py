"""Build rules from their single repository source; included in the sdist."""
from pathlib import Path
import sys
import zipfile
from setuptools.command.build_py import build_py


class BundleBuild(build_py):
    def run(self):
        super().run()
        # PEP 517 loaders do not guarantee that the project root is on sys.path.
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from dcc_harness.distribution import source_rules
        finally:
            sys.path.pop(0)
        target = Path(self.build_lib) / 'dcc_harness/data/rules.zip'
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in source_rules(Path(__file__).parent).items():
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content)
