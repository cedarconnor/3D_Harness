import copy
from pathlib import Path
import re
import unittest
import uuid

import test_workflow as existing
from dcc_harness import checks, coordination as c, feedback, environment_workflow as ew, owner, workflow
from dcc_harness.evidence import digest, file_hash, write_json


class Console:
    """A scripted stand-in for the owner's terminal; 'code' types the code the prompt shows."""

    def __init__(self, answer='code', tty=True, environ=None):
        self.answer, self.tty, self.environ, self.shown = answer, tty, environ or {}, []

    def isatty(self):
        return self.tty

    def ask(self, text):
        self.shown.append(text)
        if self.answer == 'code':
            return re.search(r'Type ([A-Z0-9]{4})', text).group(1)
        return self.answer


class Fixture(unittest.TestCase):
    setUp = existing.WorkflowTests.setUp
    save_observation = existing.WorkflowTests.save_observation
    begin = existing.WorkflowTests.begin
    candidate = existing.WorkflowTests.candidate

    def ref(self, path):
        return {'path': Path(path).relative_to(self.base).as_posix(), 'sha256': file_hash(path)}

    def actor(self, role='agent'):
        return {'role': role, 'author': 'test-reviewer', 'reference': 'Synthetic fixture, no actual artist review'}

    def revision(self):
        events = c.read(self.root)
        return events[-1]['id'] if events else 'none'

    def apply(self, kind, value, **kwargs):
        module = feedback if kind.startswith('feedback.') else checks if kind.startswith('check.') else ew
        approval = owner.confirm(kind, value, Console()) if kwargs.get('owner') else kwargs.get('approval')
        return module.apply(self.root, kind, value, kwargs.get('expected', self.revision()),
                            kwargs.get('request', str(uuid.uuid4())), self.base, approval=approval)

    def cp(self):
        return c.checkpoint_ref(workflow.resume(self.root)['active'])

    def note(self, **updates):
        value = {'schema': 'dcc.feedback.note.v1', 'source': self.actor(), 'stage_id': 'direction',
                 'category': 'technical', 'priority': 'blocking', 'text': 'Preserve the table dimensions',
                 'acceptance': 'Measured dimensions match the declared contract',
                 'anchor': {**self.cp(), 'instance_ids': ['ext.table.top']}}
        value.update(updates)
        return value

    def add(self, **updates):
        return self.apply('feedback.add', self.note(**updates))['result']['note']['id']

    def respond(self, nid, **updates):
        value = {'schema': 'dcc.feedback.response.v1', 'note_id': nid, 'author': 'test-builder',
                 'disposition': 'implemented', 'change': 'Inspected retained dimension baseline', 'result': self.cp(),
                 'evidence': [{'kind': 'native_contract', 'before': self.cp(), 'contract': self.ref(self.contract)}]}
        value.update(updates)
        return self.apply('feedback.respond', value)

    def verify(self, nid, response, **updates):
        value = {'schema': 'dcc.feedback.verification.v1', 'note_id': nid, 'response_id': response['revision'],
                 'reviewer': self.actor(), 'finding': 'Measured the intended table', 'verdict': 'pass', 'views': []}
        value.update(updates)
        return self.apply('feedback.verify', value)

    def manifest(self):
        return {'schema': 'dcc.environment.workflow.v1', 'id': 'environment', 'version': 1,
                'description': 'Small test workflow', 'default_review_policy': 'agent_within_brief', 'stages': [
                    {'id': 'direction', 'after': [], 'skills': ['dcc-plan-environment'], 'deliverables': ['brief'],
                     'evidence': ['direction_record'], 'review': 'agent_within_brief'},
                    {'id': 'delivery', 'after': ['direction'], 'skills': ['dcc-review-continue'], 'deliverables': ['native'],
                     'evidence': ['native_reopen', 'native_contract', 'feedback_reconciliation', 'handoff'], 'review': 'agent_within_brief'}]}

    def bind(self, manifest=None, owner=False, **updates):
        manifest = manifest or self.manifest()
        skill_files = {}
        for name in {n for s in manifest['stages'] for n in s['skills']}:
            path = self.base / 'skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('---\nname: ' + name + '\ndescription: test\n---\nSynthetic skill.\n')
            skill_files[name] = [self.ref(path)]
        binding = {'schema': 'dcc.environment.binding.v1', 'checkpoint': self.cp(), 'authority': self.actor(),
                   'review_policies': {}, 'inherited': {}, 'skill_files': skill_files, 'references': []}
        binding.update(updates)
        return self.apply('workflow.bind', {'manifest': manifest, 'binding': binding}, owner=owner)

    def submit(self, **updates):
        notes = feedback.state(c.read(self.root), c.Continuity(self.root).status())
        value = {'schema': 'dcc.environment.submission.v1', 'stage_id': 'direction', 'checkpoint': self.cp(),
                 'deliverables': {'brief': 'Fixture description'}, 'evidence': [{'kind': 'direction_record', 'file': self.ref(self.handoff)}],
                 'feedback_ids': list(notes), 'note': 'Direction ready for review'}
        value.update(updates)
        return self.apply('stage.submit', value)

    def complete(self, submitted, owner=False, **updates):
        review = {'reviewer': self.actor(), 'verdict': 'pass', 'finding': 'Reviewed the stated direction'}
        review.update(updates)
        return self.apply('stage.complete', {'submission_id': submitted['revision'], 'review': review}, owner=owner)

    def render(self, checkpoint=None, view='DETAIL'):
        folder = self.base / ('render-' + uuid.uuid4().hex)
        folder.mkdir()
        image = folder / 'image.png'; image.write_bytes(b'Synthetic image, not visual qualification')
        receipt = folder / 'receipt.json'
        settings = folder / 'views.json'
        values = {'camera': 'synthetic-fixed', 'frame': 1}
        write_json(settings, values)
        write_json(receipt, {'schema': 'dcc.quality.renders.v1', 'checkpoint_sha256': (checkpoint or self.cp())['checkpoint_sha256'],
                            'views_digest': digest(values), 'images': {view: {'path': 'image.png', 'sha256': file_hash(image)}}})
        return {'receipt': self.ref(receipt), 'view_id': view, 'settings': self.ref(settings)}
