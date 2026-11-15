"""Every bundled skill stays within its word budget, links only to files that exist and names real commands.

The entry skill is read at the start of every session, so its budget is the tightest. Rules for
managed, live, new-project, external-revision, review and add-on work live in its `references/`
folder, each behind one row that says when to read it.
"""
import argparse
from pathlib import Path
import re
import unittest

from dcc_harness.__main__ import build_parser

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / '.agents/skills'
ENTRY = SKILLS / 'dcc-harness'
LINK = re.compile(r'\]\(([^)\s]+)\)')
SPAN = re.compile(r'`([^`\n]+)`')
HYPHENATED = re.compile(r'[a-z][a-z0-9]*(-[a-z0-9]+)+$')

# Words per SKILL.md, counted as whitespace-separated tokens including frontmatter.
DEFAULT_BUDGET = 1800
BUDGETS = {'dcc-harness': 550}
# Hyphenated code spans in the entry skill that are not CLI commands.
NOT_COMMANDS = {'dcc-harness', 'dcc-harness-mcp'}


def subcommands():
    parser = build_parser()
    return set(next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices)


def skill_names():
    return sorted(p.parent.name for p in SKILLS.glob('*/SKILL.md'))


@unittest.skipUnless(SKILLS.exists(), 'skills are checked from the source tree, not an installed runtime')
class SkillLintTests(unittest.TestCase):
    def test_every_skill_is_within_its_word_budget(self):
        for name in skill_names():
            with self.subTest(name):
                words = len((SKILLS / name / 'SKILL.md').read_text(encoding='utf-8').split())
                self.assertLessEqual(words, BUDGETS.get(name, DEFAULT_BUDGET))

    def test_every_relative_link_resolves(self):
        for path in SKILLS.rglob('*.md'):
            for target in LINK.findall(path.read_text(encoding='utf-8')):
                if re.match(r'[a-z]+:', target) or target.startswith('#'):
                    continue
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    self.assertTrue((path.parent / target.split('#')[0]).resolve().exists())

    def test_entry_skill_commands_exist(self):
        known = subcommands() | set(skill_names()) | NOT_COMMANDS
        named = set()
        for path in [ENTRY / 'SKILL.md', *sorted((ENTRY / 'references').glob('*.md'))]:
            for span in SPAN.findall(path.read_text(encoding='utf-8')):
                first = span.split()[0]
                if first in subcommands():
                    named.add(first)
                if HYPHENATED.match(first):
                    with self.subTest(path=path.name, span=span):
                        self.assertIn(first, known)
        # The loop itself must stay in the entry skill and its references.
        self.assertLessEqual({'brief', 'next', 'resume', 'begin-edit', 'observe', 'render', 'relations', 'finish-edit'}, named)

    def test_every_entry_reference_is_routed_once_with_a_condition(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        rows = dict((target, when) for when, target in re.findall(r'^\| (.+?) \| \[[^\]]+\]\((references/[^)]+)\) \|$', text, re.M))
        self.assertEqual(sorted(rows), sorted(p.relative_to(ENTRY).as_posix() for p in (ENTRY / 'references').glob('*.md')))
        for target in rows:
            with self.subTest(target):
                self.assertEqual(text.count('(' + target + ')'), 1)
                self.assertGreater(len(rows[target].split()), 3)

    def test_entry_skill_keeps_the_rules_the_p5_situations_depend_on(self):
        text = (ENTRY / 'SKILL.md').read_text(encoding='utf-8')
        for phrase in ('finish-edit --reconciled', 'Never run the script again', 'shared material', 'recorded decision',
                       'Only the artist approves', 'never as cameras saved into the scene', 'never earlier renders'):
            with self.subTest(phrase):
                self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
