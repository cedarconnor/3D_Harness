"""Copy only matched images and an neutral brief into a fresh review packet."""
import argparse
from pathlib import Path
import random
import shutil
import sys
repo=Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo))
from dcc_harness.evidence import file_hash,read_json,write_json
p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage');p.add_argument('packet');p.add_argument('--focus',required=True)
a=p.parse_args();stage=Path(a.stage).resolve();packet=Path(a.packet).resolve()
round_doc=read_json(stage/'round.json'); names=[c['id'] for c in round_doc['candidates']]
assert len(names)==3
random.SystemRandom().shuffle(names);mapping=dict(zip(['V-184','V-527','V-936'],names))
packet.mkdir(exist_ok=False);(packet/'images').mkdir();(packet/'review-output').mkdir()
manifest={}
for label,name in mapping.items():
    for view in ('overview','garden','worktop'):
        dest=packet/'images'/f'{label}-{view}.png';shutil.copyfile(stage/name/f'{view}.png',dest)
        manifest[dest.relative_to(packet).as_posix()]=file_hash(dest)
write_json(packet.parent/(packet.name+'-mapping.json'),mapping)
write_json(packet/'manifest.json',manifest)
(packet/'PROMPT.md').write_text('''# Anonymous courtyard quality review

Inspect all nine images in images/ at full resolution. This is a warm stylized courtyard with a primary arched entry, coherent garden structures and a believable working area. Cameras, lighting and render settings match. Worktop uses a fixed camera offset relative to the table.

Specific review focus: '''+a.focus+'''

Rank V-184, V-527 and V-936 for visual quality; ties are allowed. Do not assume more objects means improvement. Explain what changes are visible and whether they improve the brief, and identify the two highest-value remaining revisions. Give each a coarse score using 1 unusable, 2 rough blockout, 3 coherent draft requiring substantial refinement, 4 usable with minor cleanup, 5 finished for the supplied brief. Separate whole-scene and task-detail assessments if they differ. Do not infer hidden topology, editability, technical validity or method, and do not grant artist acceptance.

Read only this packet. Do not inspect other runs, mappings, logs, other agents' output or conversation history. Do not open or mutate Blender. You own only review-output/; you are not alone in the repository and must preserve everyone else's work. Write review-output/REVIEW.md and review-output/review.json, including inspected paths and concrete visible evidence. Return the ranking and compact findings. No Git operations or messages to other chats.
''',encoding='utf-8')
print(packet)
