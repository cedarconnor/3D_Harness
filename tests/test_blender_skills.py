"""The Blender craft skill library must stay navigable and its code runnable.

Every `blender-*` skill has valid frontmatter, appears in the `blender-craft` index, links only to
files that exist, and carries at least one `python verify` block that parses. The blocks themselves
run in Blender through `scripts/qualify_blender_skills.py`.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.agents/skills'
INDEX = SKILLS / 'blender-craft/SKILL.md'
LINK = re.compile(r'\]\(([^)\s]+)\)')
VERIFY = re.compile(r'^```python verify\n(.*?)^```', re.M | re.S)

# The areas the library must cover; the index may add more but not drop these.
REQUIRED = {
    'blender-python', 'blender-reference-modeling', 'blender-hard-surface', 'blender-sculpt-retopo',
    'blender-precision-cad', 'blender-uv', 'blender-shading', 'blender-baking', 'blender-geometry-nodes',
    'blender-lighting', 'blender-rendering', 'blender-compositing', 'blender-camera', 'blender-animation',
    'blender-motion-design', 'blender-rigging', 'blender-skinning', 'blender-mocap', 'blender-matchmove',
    'blender-simulation', 'blender-hair', 'blender-grease-pencil', 'blender-realtime-assets',
    'blender-pipeline', 'blender-visual-design', 'blender-vegetation',
}


def frontmatter(path):
    text = path.read_text(encoding='utf-8')
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not match:
        return None
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(':')
        fields[key.strip()] = value.strip()
    return fields


def library():
    return sorted(p.parent.name for p in SKILLS.glob('blender-*/SKILL.md') if p.parent.name != 'blender-craft')


def verify_blocks(name):
    return VERIFY.findall((SKILLS / name / 'SKILL.md').read_text(encoding='utf-8'))


@unittest.skipUnless(SKILLS.exists(), 'skills are checked from the source tree, not an installed runtime')
class BlenderSkillLibraryTests(unittest.TestCase):
    def test_the_library_covers_every_required_area(self):
        self.assertEqual(sorted(REQUIRED - set(library())), [])

    def test_the_index_links_every_skill_and_nothing_else(self):
        linked = set(re.findall(r'\]\(\.\./(blender-[a-z-]+)/SKILL\.md\)', INDEX.read_text(encoding='utf-8')))
        self.assertEqual(sorted(linked ^ set(library())), [])

    def test_frontmatter_names_match_folders(self):
        for name in library() + ['blender-craft']:
            with self.subTest(name):
                fields = frontmatter(SKILLS / name / 'SKILL.md') or {}
                self.assertEqual(set(fields), {'name', 'description'})
                self.assertEqual(fields['name'], name)
                self.assertTrue(40 <= len(fields['description']) <= 1024, fields['description'])

    def test_skills_stay_short_enough_to_load_selectively(self):
        for name in library() + ['blender-craft']:
            with self.subTest(name):
                self.assertLessEqual(len((SKILLS / name / 'SKILL.md').read_text(encoding='utf-8').splitlines()), 260)

    def test_relative_links_resolve(self):
        for path in SKILLS.glob('blender-*/**/*.md'):
            for target in LINK.findall(path.read_text(encoding='utf-8')):
                if re.match(r'[a-z]+:', target):
                    continue
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    self.assertTrue((path.parent / target.split('#')[0]).resolve().exists())

    def test_every_skill_has_a_verify_block_that_parses(self):
        for name in library():
            blocks = verify_blocks(name)
            with self.subTest(name):
                self.assertTrue(blocks, 'no python verify block')
            for index, block in enumerate(blocks):
                with self.subTest(name, block=index):
                    ast.parse(block)
                    self.assertIn('assert', block, 'a verify block must check its own result')

    def test_the_harness_entry_skill_routes_to_the_index(self):
        self.assertIn('../blender-craft/SKILL.md', (SKILLS / 'dcc-harness/SKILL.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
