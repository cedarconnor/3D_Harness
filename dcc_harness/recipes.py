"""Public recipe drafts and qualification registry. Inspection never imports adapters."""
from pathlib import Path
import uuid
from .recipe_schema import validate, validate_parameters, sha
from .recipe_store import draft, load
from .evidence import digest, read_json, write_json, file_hash
from .files import reject_links


def applicable(recipe, version, engine, target_type, context):
    validate(recipe); c = recipe['compatibility']
    return c['blender_min'] <= version < c['blender_max'] and engine in c['engines'] and target_type in c['target_types'] and context in c['contexts']


def qualifiable_contexts(recipe):
    validate(recipe)
    return sorted({case['context'] for case in recipe['cases'] if case['expect'] == 'pass'})


def profile_reference(root, identity):
    path = reject_links(Path(root) / 'capabilities/profiles' / sha(identity) / 'profile.json')
    return {'path':str(path.resolve()),'sha256':file_hash(path),'digest':identity}


def current_profile(root, identity):
    from .environments import load_profile, validate_profile
    from .provider_sources import scan
    ref = profile_reference(root,identity); profile = load_profile(ref)
    roots = [{'path':str(Path(p['path']).parent),'namespace':p['module'].rpartition('.')[0]} for p in profile['providers']]
    validate_profile(profile,scan(roots,profile['blender']))
    return ref,profile


def qualify(root, recipe_id, recipe_digest, profile_digest, *, blender, out):
    from .native import run_worker
    from .environment_workflow import runtime_stamp
    runtime = runtime_stamp()
    bundle = load(root,recipe_id,recipe_digest); ref,profile = current_profile(root,profile_digest)
    recipe = bundle['recipe']; contexts = qualifiable_contexts(recipe)
    if not contexts: raise ValueError('Qualification requires a positive case')
    if not any(p['id'] == recipe['provider']['id'] and p['source_digest'] == recipe['provider']['source_digest'] for p in profile['providers']):
        raise ValueError('STALE recipe provider source')
    folder = reject_links(out).resolve(); base = reject_links(Path(root) / 'capabilities/qualifications').resolve()
    if not folder.is_relative_to(base) or folder == base:
        raise ValueError('Qualification output must be a fresh retained project qualification directory')
    folder.mkdir(parents=True,exist_ok=False)
    intent = {'schema':'dcc.capability.qualification.request.v1','id':recipe_id,'recipe_digest':recipe_digest,
              'profile_digest':profile_digest,'qualification_id':str(uuid.uuid4()),'blender':str(blender)}
    write_json(folder / 'request.json',intent)
    results = []
    for case in recipe['cases']:
        case_folder = folder / case['name']; case_folder.mkdir()
        params = {'root':str(Path(root).resolve()),'id':recipe_id,'digest':recipe_digest,'case':case,
                  'effect_id':digest({'recipe':recipe_id,'target':'Cube','slot':case['name']}),
                  'engine':recipe['compatibility']['engines'][0]}
        entry = {'name':case['name'],'context':case['context'],'expect':case['expect']}
        try:
            run_worker(blender,case_folder,Path(__file__).with_name('_recipe_blender.py'),'recipe_apply',params,
                       profile=ref,gui=case['context']=='live',timeout=120)
            applied = read_json(case_folder / 'recipe_apply-result.json')
            entry['applied'] = applied
            if applied['passed']:
                verify_folder = case_folder / 'verify'; verify_folder.mkdir()
                run_worker(blender,verify_folder,Path(__file__).with_name('_recipe_blender.py'),'recipe_verify',
                           {**params,'applied':applied},profile=ref,gui=case['context']=='live',timeout=120)
                entry['verified'] = read_json(verify_folder / 'recipe_verify-result.json')
                if case['context']=='live' and entry['verified']['passed']:
                    background_folder=case_folder / 'background-verify'; background_folder.mkdir()
                    run_worker(blender,background_folder,Path(__file__).with_name('_recipe_blender.py'),'recipe_verify',
                               {**params,'applied':applied},profile=ref,timeout=120)
                    entry['background_verified']=read_json(background_folder / 'recipe_verify-result.json')
            entry['actual_passed'] = applied['passed'] and entry.get('verified',{}).get('passed',False)
            if case['context']=='live': entry['actual_passed'] &= entry.get('background_verified',{}).get('passed',False)
        except (ValueError,RuntimeError,TimeoutError) as exc:
            entry.update(actual_passed=False,error=str(exc),error_type=type(exc).__name__)
        failure = entry.get('background_verified',entry.get('verified',entry.get('applied',entry))).get('error',entry.get('error',''))
        entry['expected_result'] = (entry['actual_passed'] if case['expect']=='pass' else
                                    not entry['actual_passed'] and case['failure_contains'] in failure)
        results.append(entry)
    load(root,recipe_id,recipe_digest); current_profile(root,profile_digest)
    artifacts = {path.relative_to(folder).as_posix():file_hash(reject_links(path)) for path in sorted(folder.rglob('*')) if path.is_file()}
    if runtime_stamp() != runtime: raise ValueError('Qualification runtime changed during native work')
    report = {'schema':'dcc.capability.qualification.v1','runtime':runtime,**{k:intent[k] for k in ('id','recipe_digest','profile_digest','qualification_id')},
              'blender':profile['blender'],'contexts':contexts,'results':results,'artifacts':artifacts,
              'passed':all(r['expected_result'] for r in results),
              'limits':'Owned synthetic scenes; technical results only; offline auditing is not an OS sandbox'}
    write_json(folder / 'report.json',report)
    return {'state':'QUALIFIED' if report['passed'] else 'FAILED','report':str(folder / 'report.json'), 'sha256':file_hash(folder / 'report.json')}


def check_report(root, report_path):
    from .environment_workflow import runtime_stamp
    path = reject_links(report_path).resolve(); base = reject_links(Path(root) / 'capabilities/qualifications').resolve()
    if not path.is_relative_to(base) or path.name != 'report.json': raise ValueError('Expected retained qualification report')
    report = read_json(path)
    if report.get('schema') != 'dcc.capability.qualification.v1' or report.get('passed') is not True:
        raise ValueError('Failed or invalid qualification report')
    if report.get('runtime') != runtime_stamp(): raise ValueError('STALE qualification runtime')
    bundle = load(root,report['id'],report['recipe_digest']); current_profile(root,report['profile_digest'])
    request = read_json(path.parent / 'request.json')
    if any(request[k] != report[k] for k in ('id','recipe_digest','profile_digest','qualification_id')):
        raise ValueError('Qualification identity changed')
    if report['contexts'] != qualifiable_contexts(bundle['recipe']): raise ValueError('Qualification context changed')
    if [r['name'] for r in report['results']] != [c['name'] for c in bundle['recipe']['cases']]: raise ValueError('Qualification cases changed')
    for result,case in zip(report['results'],bundle['recipe']['cases']):
        if result['context']!=case['context'] or result['expect']!=case['expect']:
            raise ValueError('Qualification case semantics changed')
        if case['expect']=='pass' and case['context']=='live' and not result.get('background_verified',{}).get('passed'):
            raise ValueError('Managed live qualification requires background reopen proof')
    if not all(r['expected_result'] and (r['expect'] == 'fail' or
                (r['applied']['passed'] and r['verified']['passed'] and r['applied']['repeat']['output']['effect_count']==1))
               for r in report['results']): raise ValueError('Qualification measurements failed')
    actual = {p.relative_to(path.parent).as_posix() for p in path.parent.rglob('*') if p.is_file() and p != path}
    if actual != set(report['artifacts']): raise ValueError('Qualification artifact members changed')
    for name,wanted in report['artifacts'].items():
        member = reject_links(path.parent / name).resolve()
        if not member.is_relative_to(path.parent) or file_hash(member) != sha(wanted): raise ValueError('Qualification artifact changed')
    return report


def register_qualified(root, report_path):
    report = check_report(root,report_path); path = Path(report_path).resolve(); identity = file_hash(path)
    record = {'schema':'dcc.capability.registration.v1','report':str(path),'sha256':identity,
              'recipe_digest':report['recipe_digest'],'profile_digest':report['profile_digest']}
    target = reject_links(Path(root) / 'capabilities/registered' / (identity + '.json'))
    if target.exists():
        if read_json(target) != record: raise ValueError('Registration changed')
    else: write_json(target,record)
    return {**record,'state':'QUALIFIED','contexts':report['contexts']}


def registrations(root, identity):
    result=[]
    for path in sorted((Path(root) / 'capabilities/registered').glob('*.json')):
        record=read_json(reject_links(path))
        if record.get('recipe_digest')!=identity: continue
        if path.stem!=sha(record['sha256']): raise ValueError('Registration filename changed')
        result.append(record)
    return result


def require_qualified(root, recipe_id, identity, *, context=None, profile_digest=None):
    bundle = load(root,recipe_id,identity)
    records = registrations(root,identity)
    if not records: raise ValueError('DRAFT recipe has no qualified registration')
    for record in records:
        if profile_digest is not None and record['profile_digest'] != profile_digest: continue
        try:
            if file_hash(reject_links(record['report'])) != record['sha256']: raise ValueError('STALE qualification report')
            report = check_report(root,record['report'])
            if report['recipe_digest'] != identity: raise ValueError('Qualification belongs to another recipe')
        except (ValueError,OSError,KeyError):
            continue  # Every selected report still receives full fresh byte validation.
        if context is not None and context not in report['contexts']: continue
        return {**bundle,'state':'QUALIFIED','qualification':record,'report':report}
    raise ValueError('UNQUALIFIED in this profile/context')


def inspect(root, recipe_id, identity):
    bundle = load(root,recipe_id,identity)
    if registrations(root,identity):
        try:
            return require_qualified(root,recipe_id,identity)
        except ValueError as exc:
            return {**bundle,'state':'STALE','reason':str(exc)}
    for path in sorted((Path(root) / 'capabilities/qualifications').glob('*/report.json')):
        report = read_json(reject_links(path))
        if report.get('recipe_digest') == identity and report.get('passed') is False:
            return {**bundle,'state':'FAILED','report':str(path)}
    return bundle


def scaffold(value):
    validate(value)
    return '''"""Implement and qualify this adapter before use. No mutation during preflight."""
def preflight(context, parameters):
    raise NotImplementedError("Declare context, poll, dependency and shared-user checks")

def apply(context, parameters, effect_id):
    raise NotImplementedError("Update the same owned effect using the declared provider")

def inspect_output(context, effect_id):
    raise NotImplementedError("Measure actual output and effect_count")

def verify_saved(observation, output):
    raise NotImplementedError("Validate independently reopened measured output")
'''
