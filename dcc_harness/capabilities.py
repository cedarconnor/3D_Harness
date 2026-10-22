"""Explicit provider policy and checkpoint-bound use; execution remains one service."""
from pathlib import Path

from . import coordination as c, recipes
from .evidence import digest, read_json, write_json, file_hash
from .files import reject_links, write_exclusive
from .recipe_schema import identifier, sha, strings, exact, MEASUREMENTS


def validate_policy(value):
    exact(value,{'schema','id','version','rules'})
    if value['schema']!='dcc.capability.policy.v1' or type(value['version']) is not int or value['version']<1:
        raise ValueError('Invalid capability policy version')
    identifier(value['id'])
    if not isinstance(value['rules'],list): raise ValueError('Explicit capability rules required')
    ids=set()
    for rule in value['rules']:
        exact(rule,{'id','capability','mode','providers','fallback_providers','allow_manual','candidates',
                    'selectors','stages','slot','parameters','dependencies','benchmark'})
        identifier(rule['id']); identifier(rule['capability']); identifier(rule['slot'])
        if rule['id'] in ids: raise ValueError('Duplicate capability rule')
        ids.add(rule['id'])
        if rule['mode'] not in ('require','prefer','best_qualified') or type(rule['allow_manual']) is not bool:
            raise ValueError('Invalid provider mode/fallback')
        strings(rule['providers'])
        if rule['fallback_providers']: strings(rule['fallback_providers'])
        elif rule['fallback_providers']!=[]: raise ValueError('Explicit fallback list required')
        if rule['mode']=='require' and (rule['allow_manual'] or rule['fallback_providers']):
            raise ValueError('Required providers cannot use fallback')
        if not isinstance(rule['candidates'],list) or not rule['candidates']: raise ValueError('Pinned candidate recipes required')
        seen=set()
        for candidate in rule['candidates']:
            exact(candidate,{'provider','recipe_id','recipe_digest','profile_digest'})
            identifier(candidate['provider']); identifier(candidate['recipe_id'])
            sha(candidate['recipe_digest']); sha(candidate['profile_digest'])
            key=digest(candidate)
            if key in seen: raise ValueError('Duplicate candidate')
            seen.add(key)
        selectors=rule['selectors']; exact(selectors,{'instance_ids','prefixes','types'})
        for selected in selectors.values():
            if selected: strings(selected)
            elif selected!=[]: raise ValueError('Explicit selectors required')
        if not any(selectors.values()): raise ValueError('No implicit all-object capability requirement')
        strings(rule['stages']); strings(rule['dependencies'],MEASUREMENTS)
        if not isinstance(rule['parameters'],dict): raise ValueError('Explicit capability parameters required')
        if rule['benchmark'] is not None:
            exact(rule['benchmark'],{'metric','direction','case'})
            if rule['benchmark']['metric']!='elapsed_seconds' or rule['benchmark']['direction']!='minimize':
                raise ValueError('Only measured qualification timing is a built-in comparison metric')
            identifier(rule['benchmark']['case'])
    digest(value)
    return value


def bound_policy(events):
    event=next((e for e in reversed(events) if e['kind']=='capability.bind'),None)
    if event is None: return None
    value=event['result']['policy']; validate_policy(value)
    if digest(value)!=event['result']['policy_digest']: raise ValueError('Capability policy changed')
    return event['result']


def bind_policy(root, value, *, expected_revision, request_id, authority, approval=None):
    from . import environment_workflow as ew
    from .coordination_evidence import actor
    validate_policy(value); actor(authority)
    def build(ctx,payload):
        ctx.quiet(); binding=ew._binding(ctx)
        stages={s['id'] for s in binding['result']['manifest']['stages']}
        wanted={s for r in value['rules'] for s in r['stages']}
        if wanted-stages: raise ValueError('Capability policy names unknown stages')
        previous=bound_policy(ctx.events)
        if previous:
            old=previous['policy']
            if old['id']!=value['id'] or value['version']<=old['version']: raise ValueError('Policy changes require a new version')
            wanted.update(s for r in old['rules'] for s in r['stages'])
        return {'policy':value,'policy_digest':digest(value),'affected_stages':sorted(wanted),'authority':authority}
    return c.transact(root,'capability.bind',{'policy':value,'authority':authority},expected_revision,request_id,
                      Path(root),build,approval)


def effect_key(capability,target_id,slot):
    return digest({'capability':capability,'target_id':target_id,'slot':slot})


def dependency_state(observation,target_id,fields):
    obj=observation['objects'].get(target_id)
    if obj is None: return {'missing_target':target_id}
    result={}
    for field in fields:
        if field=='geometry':
            names=('source_mesh_hash','source_uv_hash','source_attribute_hash') if 'source_mesh_hash' in obj else ('geometry_hash','dimensions')
            result[field]={k:obj[k] for k in names if k in obj}
        elif field=='transform':
            result[field]={k:obj[k] for k in ('transform','matrix_world','location','rotation','scale','bounds') if k in obj}
        elif field in ('materials','nodes'):
            result[field]={mid:observation['materials'].get(mid) for mid in obj.get('material_ids',[]) if mid is not None}
            result['material_users']={mid:sorted(oid for oid,o in observation['objects'].items() if mid in o.get('material_ids',[])) for mid in result[field]}
        elif field=='modifiers': result[field]=obj.get('modifier_settings')
        elif field=='properties': result[field]=obj.get('custom_properties')
    return result


def comparison_input(measured):
    return digest({'geometry':measured.get('geometry'), 'modifiers':measured.get('modifiers'),
        'materials':sorted(({'material':material,'users':len(measured.get('material_users',{}).get(mid,[]))}
                            for mid,material in measured.get('materials',{}).items()),key=digest)})


def benchmark_input(observation,target):
    obj=observation['objects'].get(target,{})
    measured=dependency_state(observation,target,['materials','modifiers'])
    measured['geometry']={k:obj[k] for k in ('source_mesh_hash','source_uv_hash','source_attribute_hash','geometry_hash') if k in obj}
    return comparison_input(measured)


def requirements(root,stage_id,observation):
    from .execution import configuration
    bound=bound_policy(c.read(root))
    if bound is None: return []
    result=[]; config=configuration(root) or {}
    for rule in bound['policy']['rules']:
        if stage_id not in rule['stages']: continue
        selectors=rule['selectors']; targets=set(selectors['instance_ids'])
        targets.update(oid for oid,obj in observation['objects'].items()
                       if any(oid.startswith(p) for p in selectors['prefixes']) or obj['type'] in selectors['types'])
        for target in sorted(targets):
            obj=observation['objects'].get(target,{})
            result.append({'schema':'dcc.capability.requirement.v1','policy_digest':bound['policy_digest'],'rule':rule,
                'target_id':target,'target_type':obj.get('type','MISSING'),'stage':stage_id,
                'engine':observation['scene'].get('render',{}).get('engine','UNKNOWN'),
                'context':config.get('backend','background'),'blender_version':None,
                'benchmark_input':benchmark_input(observation,target),
                'dependency_fingerprint':digest(dependency_state(observation,target,rule['dependencies']))})
    return result


def candidate_evidence(root,ref,requirement):
    try:
        bundle=recipes.require_qualified(root,ref['recipe_id'],ref['recipe_digest'],
                    context=requirement['context'],profile_digest=ref['profile_digest'])
        recipe=bundle['recipe']; report=bundle['report']
        if requirement['context']=='live' and not any(r.get('actual_passed') and r['context']=='live'
                and r.get('background_verified',{}).get('passed') for r in report['results']):
            return {'qualified':False,'reason':'UNSUPPORTED_CONTEXT: managed background reopen is not qualified'}
        version=requirement.get('blender_version') or report['blender']['version']
        if (recipe['provider']['id']!=ref['provider'] or requirement['rule']['capability'] not in recipe['capabilities']
                or not recipes.applicable(recipe,version,requirement['engine'],requirement['target_type'],requirement['context'])
                or requirement['target_type']!='MESH' or requirement['engine']!=recipe['compatibility']['engines'][0]):
            return {'qualified':False,'reason':'UNSUPPORTED_CONTEXT: no matching native case'}
        recipes.validate_parameters(recipe,requirement['rule']['parameters'])
        result={'candidate':ref,'qualified':True,'qualification':bundle['qualification'],'score':None,'comparison':None}
        benchmark=requirement['rule']['benchmark']
        if benchmark:
            case=next((r for r in report['results'] if r['name']==benchmark['case'] and r['actual_passed']
                       and r['context']==requirement['context']),None)
            spec=next((r for r in recipe['cases'] if r['name']==benchmark['case']),None)
            if case and spec and spec['parameters']==requirement['rule']['parameters']:
                # A fixture speed test is comparable only on its measured input scope.
                before=case['applied']['result']['before']
                if requirement.get('benchmark_input')==comparison_input(before):
                    result.update(score=case['applied']['elapsed_seconds'],comparison=digest({
                        'input':comparison_input(before),'parameters':spec['parameters'],'build':report['blender'],
                        'engine':requirement['engine'],'context':requirement['context']}))
        return result
    except (ValueError,OSError,KeyError) as exc:
        return {'qualified':False,'reason':str(exc)}


def resolve(root,requirement,inventory):
    rule=requirement['rule']; validate_policy({'schema':'dcc.capability.policy.v1','id':'resolution','version':1,'rules':[rule]})
    evidence=[]; rejected=[]; available={p['id']:p for p in inventory['providers']}
    for ref in rule['candidates']:
        provider=available.get(ref['provider'])
        if not provider or provider['availability']!='AVAILABLE' or provider['compatible'] is not True:
            rejected.append({'provider':ref['provider'],'state':'UNAVAILABLE'}); continue
        row=candidate_evidence(root,ref,requirement)
        if row['qualified']: evidence.append(row)
        else: rejected.append({'provider':ref['provider'],'state':'UNQUALIFIED','reason':row.get('reason')})
    def ordered(names):
        return sorted((e for e in evidence if e['candidate']['provider'] in names),
                      key=lambda e:(names.index(e['candidate']['provider']),e['candidate']['provider'],e['candidate']['recipe_id'],e['candidate']['recipe_digest']))
    preferred=ordered(rule['providers']); selected=None; fallback=None
    state='UNQUALIFIED' if any(r['state']=='UNQUALIFIED' and r['provider'] in rule['providers'] for r in rejected) else 'UNAVAILABLE'
    if rule['mode']=='best_qualified' and preferred:
        if (any(e['score'] is None or e['comparison'] is None for e in preferred)
                or len({e['comparison'] for e in preferred})!=1): state='NO_COMPARABLE_EVIDENCE'
        else: selected=min(preferred,key=lambda e:e['score'])
    elif preferred: selected=preferred[0]
    if selected is None and rule['mode']!='require':
        choices=ordered(rule['fallback_providers'])
        if choices: selected=choices[0]; fallback=state + ': explicit fallback provider'
        elif rule['allow_manual']: fallback=state + ': explicit manual fallback'
    return {'schema':'dcc.capability.resolution.v1','state':'RESOLVED' if selected or fallback else state,
            'requirement_digest':digest(requirement),'selected':selected['candidate'] if selected else None,
            'qualification':selected.get('qualification') if selected else None,'fallback_reason':fallback,
            'comparison':selected.get('comparison') if selected else None,'rejected':rejected}


def verify_receipts(root,stage_id,checkpoint):
    native=c.Continuity(root).status(); active=native['active']
    if c.checkpoint_ref(active)!=checkpoint: raise ValueError('Capability checkpoint is stale')
    needed=requirements(root,stage_id,read_json(active['observation']))
    rows=[]
    for req in needed:
        satisfied=False; reasons=[]
        for folder in sorted((Path(root) / 'execution/operations').glob('*')):
            receipt=folder / 'capability-receipt.json'
            if not receipt.is_file(): continue
            try:
                result=verify_operation_receipt(root,folder,req,checkpoint)
                if result: satisfied=True; break
            except (ValueError,OSError,KeyError) as exc: reasons.append(str(exc))
        fallback=None
        if not satisfied and req['rule']['allow_manual']:
            decision=resolve(root,req,inventory_for_requirement(root,req))
            if decision['state']=='RESOLVED' and decision['selected'] is None:
                satisfied=True; fallback=decision['fallback_reason']
        rows.append({'requirement':req,'passed':satisfied,'reason':None if satisfied else 'Missing or stale required capability receipt',
                     'details':reasons,'fallback_reason':fallback})
    return {'passed':all(r['passed'] for r in rows),'requirements':rows}


def verify_operation_receipt(root,folder,requirement,checkpoint):
    from .execution import _outcome
    receipt=validate_receipt(read_json(reject_links(folder / 'capability-receipt.json')))
    outcome=_outcome(folder)
    request=read_json(reject_links(folder / 'request.json'))
    if ('capability' not in request or outcome['status']!='PUBLISHED'
            or receipt.get('checkpoint')!=checkpoint or receipt.get('current_requirement_digest')!=digest(requirement)):
        return False
    if (receipt['operation_id']!=folder.name or receipt['request_sha256']!=digest(request)
            or receipt['checkpoint']!=c.checkpoint_ref(outcome['outcome']['active'])
            or outcome.get('capability_receipt',{}).get('sha256')!=file_hash(folder / 'capability-receipt.json')):
        raise ValueError('Capability receipt does not match service publication')
    cap=request['capability']; selected=cap['resolution']['selected']
    if receipt['requirement_digest']!=digest(cap['requirement']) or receipt['effect_id']!=cap['effect_id']:
        raise ValueError('Capability request identity changed')
    expected={'target_id':cap['requirement']['target_id'],'capability':cap['requirement']['rule']['capability'],
        'slot':cap['requirement']['rule']['slot'],'policy_digest':cap['requirement']['policy_digest'],
        'provider':selected['provider'],'recipe_digest':selected['recipe_digest'],'profile_digest':selected['profile_digest'],
        'parameters_digest':digest(cap['parameters']),'input_dependency_fingerprint':cap['requirement']['dependency_fingerprint'],
        'dependency_fingerprint':requirement['dependency_fingerprint']}
    if any(receipt[k]!=v for k,v in expected.items()): raise ValueError('Capability receipt bindings changed')
    recipes.require_qualified(root,selected['recipe_id'],selected['recipe_digest'],
                              profile_digest=selected['profile_digest'],context=request['backend'])
    for name,wanted in receipt['evidence'].items():
        if name not in ('capability-output.json','capability-verified.json','observation.json'):
            raise ValueError('Unexpected capability receipt artifact')
        if file_hash(reject_links(folder / name))!=wanted: raise ValueError('Capability evidence changed')
    verified=read_json(folder / 'capability-verified.json')
    if verified.get('passed') is not True or verified['output_fingerprint']!=receipt['output_fingerprint']:
        raise ValueError('Capability independent output validation failed')
    return True


def validate_receipt(value):
    hashes={'request_sha256','requirement_digest','current_requirement_digest','effect_id','policy_digest',
            'recipe_digest','profile_digest','parameters_digest','input_dependency_fingerprint',
            'dependency_fingerprint','output_fingerprint'}
    exact(value,hashes | {'schema','operation_id','target_id','capability','slot','provider','checkpoint','evidence'})
    if value['schema']!='dcc.capability.receipt.v1': raise ValueError('Unsupported capability receipt')
    c.identifier(value['operation_id'])
    for key in hashes: sha(value[key])
    for key in ('target_id','capability','slot','provider'): identifier(value[key])
    exact(value['checkpoint'],{'checkpoint_id','checkpoint_sha256'})
    for item in value['checkpoint'].values(): sha(item)
    exact(value['evidence'],{'capability-output.json','capability-verified.json','observation.json'})
    for item in value['evidence'].values(): sha(item)
    return value


def status(root,stage_id,checkpoint):
    result=verify_receipts(root,stage_id,checkpoint)
    for row in result['requirements']:
        row['resolution']=resolve(root,row['requirement'],inventory_for_requirement(root,row['requirement']))
    return result


def inventory_for_requirement(root,requirement):
    providers={}
    for ref in requirement['rule']['candidates']:
        try:
            _,profile=recipes.current_profile(root,ref['profile_digest'])
            provider=next(p for p in profile['providers'] if p['id']==ref['provider'])
            providers[ref['provider']]={**provider,'availability':'AVAILABLE','compatible':True}
        except (ValueError,OSError,StopIteration): continue
    return {'providers':list(providers.values())}


def admit(root,value):
    cap=value['capability']; exact(cap,{'root','requirement','resolution','parameters','effect_id'})
    if Path(cap['root']).resolve()!=Path(root).resolve(): raise ValueError('Capability project mismatch')
    req=cap['requirement']; active=c.Continuity(root).status()['active']
    current=requirements(root,value['stage'],read_json(active['observation']))
    if req not in current or req['context']!=value['backend']: raise ValueError('Stale or unrelated capability requirement')
    decision=resolve(root,req,inventory_for_requirement(root,req))
    if decision!=cap['resolution'] or decision['state']!='RESOLVED' or decision['selected'] is None:
        raise ValueError('Capability resolution is unavailable or changed')
    if cap['parameters']!=req['rule']['parameters'] or cap['effect_id']!=effect_key(req['rule']['capability'],req['target_id'],req['rule']['slot']):
        raise ValueError('Capability parameters/effect differ from policy')
    ref=decision['selected']; profile=recipes.profile_reference(root,ref['profile_digest'])
    if value.get('profile')!=profile: raise ValueError('Capability profile differs from qualification')
    if value['backend']=='live' and value.get('live')!={'recipe':'capability.recipe','target':req['target_id'],
                                                     'parameters':{'operation_id':value['operation_id']}}:
        raise ValueError('Live capability payload mismatch')
    return cap


def execute(root,requirement,resolution,parameters,operation_id,*,blender,contract,handoff,timeout=300):
    from . import execution
    c.identifier(operation_id)
    if resolution.get('selected') is None: raise ValueError('No qualified provider selected for execution')
    root=reject_links(root).resolve(); folder=reject_links(root / 'capabilities/inputs' / operation_id)
    folder.mkdir(parents=True,exist_ok=True)
    script=folder / 'script.py'
    content=b'# Qualified capability invocation; dispatched by the shared execution service.\n'
    if script.exists():
        if script.read_bytes()!=content: raise ValueError('Capability retained input changed')
    else: write_exclusive(script,content)
    cap={'root':str(root),'requirement':requirement,'resolution':resolution,'parameters':parameters,
         'effect_id':effect_key(requirement['rule']['capability'],requirement['target_id'],requirement['rule']['slot'])}
    existing=root / 'execution/operations' / operation_id / 'request.json'
    parent=(read_json(existing)['expected_parent'] if existing.exists() else c.Continuity(root).status()['active']['id'])
    value={'schema':'dcc.execution.operation.v2','backend':requirement['context'],'stage':requirement['stage'],
           'operation_id':operation_id,'script':str(script),'contract':str(contract),'handoff':str(handoff),
           'blender':str(blender),'expected_parent':parent,'timeout':timeout,'capability':cap,
           'profile':recipes.profile_reference(root,resolution['selected']['profile_digest'])}
    if value['backend']=='live':
        value['live']={'recipe':'capability.recipe','target':requirement['target_id'],'parameters':{'operation_id':operation_id}}
    return execution.execute_operation(root,value)


def record_operation(root,folder,result,request):
    if result['status']!='PUBLISHED' or result.get('live_state','READY')!='READY': return None
    cap=request['capability']; req=cap['requirement']; active=result['outcome']['active']
    current=next((r for r in requirements(root,req['stage'],read_json(active['observation']))
                  if r['target_id']==req['target_id'] and r['rule']['id']==req['rule']['id']
                  and r['policy_digest']==req['policy_digest']),None)
    if current is None: raise ValueError('Capability policy changed before receipt')
    verified=read_json(folder / 'capability-verified.json')
    if verified.get('passed') is not True: raise ValueError('Missing independent capability verification')
    selected=cap['resolution']['selected']
    receipt={'schema':'dcc.capability.receipt.v1','operation_id':folder.name,'request_sha256':digest(request),
        'requirement_digest':digest(req),'current_requirement_digest':digest(current), 'effect_id':cap['effect_id'],
        'target_id':req['target_id'],'capability':req['rule']['capability'],'slot':req['rule']['slot'],
        'policy_digest':req['policy_digest'],'provider':selected['provider'],'recipe_digest':selected['recipe_digest'],
        'profile_digest':selected['profile_digest'],'parameters_digest':digest(cap['parameters']),
        'input_dependency_fingerprint':req['dependency_fingerprint'],'dependency_fingerprint':current['dependency_fingerprint'],
        'output_fingerprint':verified['output_fingerprint'],'checkpoint':c.checkpoint_ref(active),
        'evidence':{name:file_hash(folder / name) for name in ('capability-output.json','capability-verified.json','observation.json')}}
    validate_receipt(receipt)
    path=folder / 'capability-receipt.json'; write_json(path,receipt)
    return {'path':str(path),'sha256':file_hash(path)}
