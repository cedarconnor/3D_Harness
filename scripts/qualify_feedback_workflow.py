"""Prepare native evidence, then finish only with an explicit image-review record."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

p = argparse.ArgumentParser()
p.add_argument('phase', choices=['prepare', 'finish'])
p.add_argument('--blender', required=True); p.add_argument('--out', required=True)
p.add_argument('--runtime', help='Source checkout; omit to test installed runtime')
p.add_argument('--skills-root', required=True, help='Repository holding the actual project skills and docs')
p.add_argument('--review', help='Actual image inspection record required by finish')
a = p.parse_args()
if a.runtime:
    sys.path.insert(0, a.runtime)
from dcc_harness import coordination as c, feedback, environment_workflow as ew, revisions, workflow
from dcc_harness.evidence import file_hash, read_json, write_json

runtime = Path(workflow.__file__).resolve().parent.parent
out = Path(a.out).resolve(); root = out / 'project'
probe = Path(__file__).with_name('feedback_native_probe.py')
reviewer = {'role': 'agent', 'author': 'qualification-script', 'reference': 'Synthetic technical fixture; no artist acceptance'}


def native(action, target, source=None):
    command = [a.blender, '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1',
               '--python', str(probe), '--', action, '--runtime', str(runtime), '--out', str(target)]
    if source: command += ['--source', str(source)]
    with (out / (target.name + '.log')).open('x', encoding='utf-8') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True)


def ref(path):
    return {'path': Path(path).relative_to(out).as_posix(), 'sha256': file_hash(path)}


def cp():
    return c.checkpoint_ref(c.Continuity(root).status()['active'])


def apply(kind, payload, request=None, expected=None):
    events = c.read(root)
    revision = events[-1]['id'] if events else 'none'
    module = feedback if kind.startswith('feedback.') else ew
    return module.apply(root, kind, payload, revision if expected is None else expected, request or str(uuid.uuid4()), out)


def render_ref(name, view):
    return {'receipt': ref(out / name / 'receipt.json'), 'view_id': view,
            'settings': ref(out / name / 'views.json')}


def native_evidence(parent):
    return {'kind': 'native_contract', 'before': parent, 'contract': ref(out / 'contract.json')}


def fresh_packet(name):
    proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'resume', str(root)],
                          cwd=runtime, capture_output=True, text=True, check=True)
    packet = json.loads(proc.stdout); write_json(out / name, packet)
    return packet


if a.phase == 'prepare':
    out.mkdir(parents=True, exist_ok=False)
    native('fixtures', out / 'fixtures')
    for name in ('baseline', 'revised', 'bad-light'):
        native('observe', out / (name + '.json'), out / 'fixtures' / (name + '.blend'))
    native('render', out / 'before-views', out / 'fixtures/baseline.blend')
    native('render', out / 'after-views', out / 'fixtures/revised.blend')
    handoff = out / 'CONTINUE.md'
    handoff.write_text('Synthetic micro-environment qualification: preserve camera, lighting, wall, ground and all placements. '
                       'Extend only the bench top to 2 m and change shared timber roughness to 0.65. '
                       'Review images before verifying the appearance note. This is not a production scene.', encoding='utf-8')
    initial = workflow.start(root, out / 'fixtures/baseline.blend', out / 'baseline.json', handoff.read_text(), {}, handoff)
    before = read_json(out / 'baseline.json'); after = read_json(out / 'revised.json')
    parent = cp()
    rules = {'schema': 'dcc.continuity.contract.v1', 'spec': {'schema': 'dcc.spec.v1',
             'required': {iid: {'type': obj['type']} for iid, obj in before['objects'].items()},
             'required_materials': ['timber'], 'material_nodes': {'timber': {'Principled BSDF': {'Roughness': .65}}}},
             'allowed_new_prefixes': [], 'allowed_object_prefixes': {'bench.top': ['dimensions', 'bounds', 'matrix_world']},
             'allowed_material_inputs': {'timber': {'Principled BSDF': {'Roughness': .65}}}}
    rules['spec']['required']['bench.top']['dimensions'] = [2.0, .65, .09]
    write_json(out / 'contract.json', rules)
    ids = []
    for category, target, text in [('technical', 'bench.top', 'Extend the bench top to 2 m without moving the legs'),
                                  ('visual', 'bench.top', 'Reduce the glossy timber response while preserving the lighting'),
                                  ('technical', 'light.key', 'Keep the established camera, lighting and unrelated geometry')]:
        anchor = {**parent, 'instance_ids': [target]}
        if category == 'visual': anchor['render'] = render_ref('before-views', 'REVIEW_DETAIL')
        note = {'schema': 'dcc.feedback.note.v1', 'source': reviewer, 'stage_id': 'materials',
                'category': category, 'priority': 'blocking', 'text': 'SYNTHETIC TEST: ' + text,
                'acceptance': text + '; check the scoped contract and relevant fixed view.', 'anchor': anchor,
                'requires': ['technical', 'visual'] if category == 'visual' else ['technical']}
        ids.append(apply('feedback.add', note)['result']['note']['id'])
    bad = revisions.preview_revision(root, initial['active']['id'], out / 'fixtures/bad-light.blend', out / 'bad-light.json',
        out / 'contract.json', handoff, {}, 'bad-light', 'Synthetic preservation fault', out / 'bad-preview')
    assert bad['status'] == 'REJECTED_CONTRACT', bad
    good = revisions.preview_revision(root, initial['active']['id'], out / 'fixtures/revised.blend', out / 'revised.json',
        out / 'contract.json', handoff, {}, 'scoped-revision', 'Synthetic dimension and roughness edit', out / 'good-preview')
    assert good['passed'], good
    accepted = revisions.accept_revision(root, good['preview'], good['preview_sha256'], 'Native contract checked; visual feedback remains unresolved')
    assert accepted['status'] == 'PUBLISHED'
    native('observe', out / 'reopened.json', accepted['active']['checkpoint'])
    for nid in (ids[0], ids[2]):
        response = apply('feedback.respond', {'schema': 'dcc.feedback.response.v1', 'note_id': nid, 'author': 'qualification-script',
            'disposition': 'implemented', 'change': 'Scoped native revision saved and independently reopened',
            'result': cp(), 'evidence': [native_evidence(parent)]})
        verified = apply('feedback.verify', {'schema': 'dcc.feedback.verification.v1', 'note_id': nid,
            'response_id': response['revision'], 'reviewer': reviewer, 'finding': 'Recomputed native target and preservation checks',
            'verdict': 'pass', 'views': []})
        assert verified['result']['passed']
    packet = fresh_packet('fresh-resume-before-review.json')
    assert packet['coordination']['unresolved_blockers'] == [ids[1]]
    write_json(out / 'prepared.json', {'parent': parent, 'note_ids': ids, 'checkpoint': cp(),
               'baseline_sha256': file_hash(out / 'fixtures/baseline.blend'), 'runtime': ew.runtime_stamp()})
    print('PREPARED: inspect before-views and after-views; visual note remains open')
else:
    if not a.review:
        raise ValueError('Finish requires an actual --review inspection record')
    prepared = read_json(out / 'prepared.json'); parent = prepared['parent']; ids = prepared['note_ids']
    if prepared['runtime'] != ew.runtime_stamp():
        raise ValueError('Runtime changed since prepare; preserve this run and qualify a new one')
    review = read_json(a.review)
    response_payload = {'schema': 'dcc.feedback.response.v1', 'note_id': ids[1], 'author': 'qualification-script',
        'disposition': 'implemented', 'change': 'Timber roughness changed to 0.65; fixed lighting and camera retained',
        'result': cp(), 'evidence': [native_evidence(parent), {'kind': 'detail_render', 'render': render_ref('before-views', 'REVIEW_DETAIL')}]}
    try:
        apply('feedback.respond', response_payload)
        raise AssertionError('Stale render accepted')
    except ValueError as exc:
        assert 'Stale or invalid render' in str(exc)
    response_payload['evidence'][1]['render'] = render_ref('after-views', 'REVIEW_DETAIL')
    response_payload['evidence'].append({'kind': 'whole_scene_render', 'render': render_ref('after-views', 'REVIEW_WHOLE')})
    response = apply('feedback.respond', response_payload)
    verification = {'schema': 'dcc.feedback.verification.v1', 'note_id': ids[1], 'response_id': response['revision'], **review}
    assert apply('feedback.verify', verification)['result']['passed']
    manifest = ew.default_manifest()
    # Preserve relative repository paths so selected skill documentation links still resolve.
    inputs = out / 'inputs'; repo = Path(a.skills_root).resolve()
    skill_files = {}
    for skill in {name for stage in manifest['stages'] for name in stage['skills']}:
        relative = Path('.agents/skills') / skill / 'SKILL.md'
        target = inputs / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / relative, target); skill_files[skill] = [ref(target)]
    references = []
    for directory in ('docs',):
        for source in sorted((repo / directory).rglob('*.md')):
            target = inputs / source.relative_to(repo); target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target); references.append(ref(target))
    for source in sorted(repo.glob('*.md')):
        target = inputs / source.name; shutil.copyfile(source, target); references.append(ref(target))
    apply('workflow.bind', {'manifest': manifest, 'binding': {'schema': 'dcc.environment.binding.v1', 'checkpoint': cp(),
        'authority': review['reviewer'], 'review_policies': {}, 'inherited': {}, 'skill_files': skill_files, 'references': references}})
    all_evidence = [native_evidence(parent), {'kind': 'whole_scene_render', 'render': render_ref('after-views', 'REVIEW_WHOLE')},
        {'kind': 'detail_render', 'render': render_ref('after-views', 'REVIEW_DETAIL')},
        {'kind': 'visual_review', **review}, {'kind': 'native_reopen', 'observation': ref(out / 'reopened.json'), 'producer': reviewer},
        {'kind': 'direction_record', 'file': ref(out / 'CONTINUE.md')}, {'kind': 'handoff', 'file': ref(out / 'CONTINUE.md')},
        {'kind': 'shared_user_report'}, {'kind': 'dependency_report'}, {'kind': 'feedback_reconciliation'}]
    completed = []
    for stage in manifest['stages']:
        applicable = ids if stage['id'] in ('materials', 'delivery') else []
        payload = {'schema': 'dcc.environment.submission.v1', 'stage_id': stage['id'], 'checkpoint': cp(),
            'deliverables': {key: 'Synthetic fixture evidence for ' + key for key in stage['deliverables']},
            'evidence': all_evidence, 'feedback_ids': applicable, 'note': 'Engineering template exercise; no production art claim'}
        if stage['id'] == 'materials':
            try:
                apply('stage.submit', {**payload, 'feedback_ids': ids[:1]})
                raise AssertionError('Forgotten feedback accepted')
            except ValueError as exc:
                assert 'every applicable' in str(exc)
        submission = apply('stage.submit', payload)
        completed.append(apply('stage.complete', {'submission_id': submission['revision'],
            'review': {key: review[key] for key in ('reviewer', 'verdict', 'finding')}}))
    # Real metadata publication followed by simulated acknowledgement loss: retry the exact request.
    decision = {'schema': 'dcc.feedback.decision.v1', 'note_id': ids[1], 'action': 'reopen', 'reason': 'Acknowledgement recovery fixture',
                'authority': review['reviewer'], 'result': cp()}
    request = str(uuid.uuid4()); expected = c.read(root)[-1]['id']
    committed = apply('feedback.decide', decision, request=request, expected=expected)
    recovery = apply('feedback.decide', decision, request=request, expected=expected)
    assert recovery['status'] == 'ALREADY_COMMITTED' and recovery['revision'] == committed['revision']
    packet = fresh_packet('fresh-resume-after-review.json')
    assert packet['coordination']['unresolved_blockers'] == [ids[1]]
    assert file_hash(out / 'fixtures/baseline.blend') == prepared['baseline_sha256']
    write_json(out / 'RESULTS.json', {'technical_pass': True, 'stages_completed_before_reopen': len(completed),
        'stale_image_rejected': True, 'forgotten_note_rejected': True, 'protected_light_fault_rejected': True,
        'acknowledgement_recovered': True, 'reopened_note_survives_fresh_process': True,
        'artistic_acceptance': 'not_evaluated', 'review': review, 'runtime': ew.runtime_stamp()})
    print('PASSED: native preservation, feedback, seven stages and fresh-process recovery; reopened note retained')
