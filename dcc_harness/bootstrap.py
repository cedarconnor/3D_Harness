"""Initialize only a new, owned baseline; failure retains files for inspection."""
from pathlib import Path
import uuid

from . import distribution, execution, workflow
from .evidence import finite_number, read_json, write_json
from .files import reject_links, write_exclusive
from .native import run_worker


def create(destination, brief_file, blender, mode, *, max_operations=20, seconds=3600):
    if mode not in ('autonomous', 'approval_gated') or type(max_operations) is not int or max_operations < 1:
        raise ValueError('Valid execution mode and positive operation budget required')
    finite_number(seconds)
    if seconds <= 0:
        raise ValueError('Time budget must be positive')
    brief = Path(brief_file).read_text(encoding='utf-8')
    if not brief.strip():
        raise ValueError('A project brief is required')
    folder = reject_links(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    write_exclusive(folder / 'brief.md', brief.encode('utf-8'))
    source = folder / 'baseline.blend'
    run_worker(blender, folder, Path(__file__).with_name('_bootstrap_blender.py'), 'initialize',
               {'output': str(source)}, timeout=60)
    from .evidence import file_hash
    observed = folder / 'observation'
    observed.mkdir()
    run_worker(blender, observed, execution.OBSERVER, 'observe',
               {'source': {'path': str(source), 'sha256': file_hash(source)}, 'out': str(observed), 'compact': True}, timeout=60)
    handoff = folder / 'handoff.md'
    write_exclusive(handoff, b'Empty owned baseline. Establish direction, then build and review the requested scene.\n')
    root = folder / 'state'
    workflow.start(root, source, observed / 'observation.json', brief, {}, handoff)
    bind_rules(str(root), folder, 'none', str(uuid.uuid4()))
    result = execution.create(root, mode, max_operations=max_operations, seconds=seconds)
    result.update(project=str(root), baseline=str(source))
    write_json(folder / 'created.json', result)
    return result


def bind_rules(project, workspace, expected_revision, request_id):
    from . import environment_workflow as ew, coordination as c, workflow
    root = Path(project)
    if not root.is_absolute():
        root = Path(workspace) / root
    # Stable export path allows an identical request to replay after lost acknowledgement.
    request = str(uuid.UUID(request_id))
    target = reject_links(Path(workspace) / '.harness-mcp' / 'rules' / request)
    if not target.exists():
        distribution.export_rules(target)
    index = distribution.verify_rules(target)
    manifest = ew.default_manifest()
    skills = {s for stage in manifest['stages'] for s in stage['skills']}
    refs = lambda names: [{'path': name, 'sha256': index['files'][name]} for name in names]
    skill_files = {skill: refs([n for n in index['files'] if n.startswith('.agents/skills/' + skill + '/')]) for skill in skills}
    selected = {r['path'] for files in skill_files.values() for r in files}
    binding = {'schema': 'dcc.environment.binding.v1', 'checkpoint': c.checkpoint_ref(workflow.resume(root)['active']),
               'authority': {'role': 'agent', 'author': 'combined harness MCP', 'reference': 'User requested project setup'},
               'review_policies': {}, 'inherited': {}, 'skill_files': skill_files,
               'references': refs([n for n in index['files'] if n not in selected])}
    return ew.apply(root, 'workflow.bind', {'manifest': manifest, 'binding': binding},
                    expected_revision, request, target)

