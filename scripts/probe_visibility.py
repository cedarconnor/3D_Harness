"""Read saved native visibility without saving the source. Disposable process."""
import argparse
from pathlib import Path
import sys
import bpy

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True); p.add_argument('--queries', required=True)
p.add_argument('--out', required=True); p.add_argument('--repo', required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
assert bpy.app.background
sys.path.insert(0, a.repo)
from dcc_harness.evidence import read_json, write_json, file_hash
from dcc_harness.continuity_blender import observe
from dcc_harness.visibility_blender import observe_visibility

out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
source = file_hash(a.source)
bpy.ops.wm.open_mainfile(filepath=a.source, load_ui=False)
obs = observe()
write_json(out / 'observation.json', obs)
report = observe_visibility(read_json(a.queries), obs)
assert file_hash(a.source) == source
write_json(out / 'visibility.json', report)
print({k: {'fraction': v['visible_fraction'], 'samples': v['target_samples'], 'blockers': v['blockers']} for k,v in report['queries'].items()})
