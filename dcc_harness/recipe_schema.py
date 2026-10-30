"""Closed portable recipe and parameter contracts, identical in host and Blender."""
import json
import math
import re

ID = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
FIELDS = {'schema','id','version','capabilities','provider','parameters','compatibility',
          'coverage','invocation','update','validators','cases'}
MEASUREMENTS = {'geometry','transform','materials','modifiers','nodes','properties'}


def identifier(value):
    if (not isinstance(value, str) or not ID.fullmatch(value) or value.endswith('.')
            or value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',
                *('COM' + str(i) for i in range(10)), *('LPT' + str(i) for i in range(10))}):
        raise ValueError('Invalid portable identifier')
    return value


def sha(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError('Expected SHA-256')
    return value


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('Invalid closed schema fields')


def strings(value, allowed=None):
    if (not isinstance(value, list) or not value or any(not isinstance(v, str) or not v for v in value)
            or len(set(value)) != len(value) or (allowed is not None and set(value) - allowed)):
        raise ValueError('Expected distinct supported strings')


def parameter_schema(value, depth=0):
    if depth > 12 or not isinstance(value, dict):
        raise ValueError('Parameter schema exceeds supported depth')
    kind = value.get('type')
    common = {'type','description','enum'}
    extras = {'object':{'properties','required','additionalProperties'}, 'array':{'items','minItems','maxItems'},
              'number':{'minimum','maximum'}, 'integer':{'minimum','maximum'},
              'string':{'minLength','maxLength'}, 'boolean':set()}
    if kind not in extras or set(value) - common - extras[kind]:
        raise ValueError('Unsupported parameter schema keyword or type')
    if 'description' in value and not isinstance(value['description'], str):
        raise ValueError('Invalid schema description')
    if kind == 'object':
        if (not isinstance(value.get('properties'), dict) or value.get('additionalProperties') is not False
                or not isinstance(value.get('required'), list)
                or any(not isinstance(v, str) for v in value['required'])
                or len(set(value['required'])) != len(value['required'])
                or set(value['required']) - value['properties'].keys()):
            raise ValueError('Closed object properties and required list are mandatory')
        for key, child in value['properties'].items():
            identifier(key); parameter_schema(child, depth + 1)
    if kind == 'array': parameter_schema(value.get('items'), depth + 1)
    for low, high in (('minimum','maximum'), ('minItems','maxItems'), ('minLength','maxLength')):
        for key in (low, high):
            if key in value:
                item = value[key]
                if type(item) not in (int,float) or not math.isfinite(item):
                    raise ValueError('Finite schema bounds required')
                if key not in ('minimum','maximum') and (type(item) is not int or item < 0):
                    raise ValueError('Nonnegative integer length bound required')
        if low in value and high in value and value[low] > value[high]:
            raise ValueError('Reversed parameter bounds')
    if 'enum' in value:
        if not isinstance(value['enum'], list) or not value['enum']:
            raise ValueError('Nonempty enum required')
        for item in value['enum']:
            parameter_value({k:v for k,v in value.items() if k != 'enum'}, item)
    json.dumps(value, allow_nan=False)
    return value


def parameter_value(schema, value):
    kind = schema['type']
    valid = {'object':isinstance(value,dict), 'array':isinstance(value,list), 'string':isinstance(value,str),
             'integer':type(value) is int, 'number':type(value) in (int,float), 'boolean':type(value) is bool}
    if not valid[kind]: raise ValueError('Wrong parameter type')
    if kind == 'object':
        if set(value) - schema['properties'].keys() or set(schema['required']) - value.keys():
            raise ValueError('Missing or unknown parameter')
        for key, item in value.items(): parameter_value(schema['properties'][key], item)
    if kind == 'array':
        for item in value: parameter_value(schema['items'], item)
    if kind in ('number','integer'):
        if not math.isfinite(value) or value < schema.get('minimum',-math.inf) or value > schema.get('maximum',math.inf):
            raise ValueError('Parameter outside finite numeric bounds')
    if kind in ('string','array'):
        low,high = ('minLength','maxLength') if kind == 'string' else ('minItems','maxItems')
        if not schema.get(low,0) <= len(value) <= schema.get(high,65536):
            raise ValueError('Parameter outside length bounds')
    if 'enum' in schema and not any(type(value) is type(v) and value == v for v in schema['enum']):
        raise ValueError('Parameter outside enum')
    return value


def callable_entry(value):
    if (not isinstance(value,str) or len(value) > 128
            or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+',value) is None):
        raise ValueError('Invalid bounded lifecycle callable entry')


def effect_schema(value):
    if not isinstance(value,dict) or value.get('kind') not in ('modifier','material','shader_nodes'):
        raise ValueError('Unsupported native effect kind')
    kind = value['kind']
    exact(value, {'kind'} | ({'material_id','slot'} if kind != 'modifier' else set())
          | ({'nodes'} if kind == 'shader_nodes' else set()))
    if kind == 'modifier': return
    if type(value['slot']) is not int or not 0 <= value['slot'] <= 1023:
        raise ValueError('Native material slot must be an integer from zero to 1023')
    material_id = value['material_id']
    if kind == 'material' and material_id != '{effect_name}':
        raise ValueError('Owned material requires the deterministic effect_name selector')
    if material_id != '{effect_name}': identifier(material_id)
    if kind == 'shader_nodes':
        nodes = value['nodes']; strings(nodes)
        if len(nodes) > 256: raise ValueError('Too many owned native node selectors')
        for name in nodes:
            if (not name.startswith('{effect_name}') or any(ord(ch)<32 or ord(ch)==127 for ch in name)
                    or any(not 32 <= ord(ch) <= 126 or ch in '{}' for ch in name[13:])
                    or len(name[13:].encode('utf-8')) > 10):
                raise ValueError('Owned node selectors require effect_name and a bounded native suffix')


def validate(value):
    if not isinstance(value, dict) or value.get('schema') not in ('dcc.capability.recipe.v1','dcc.capability.recipe.v2'):
        raise ValueError('Unknown recipe schema')
    v2 = value['schema'] == 'dcc.capability.recipe.v2'
    exact(value, FIELDS | ({'effect'} if v2 else set()))
    if v2: effect_schema(value['effect'])
    identifier(value['id'])
    if type(value['version']) is not int or value['version'] < 1: raise ValueError('Positive recipe version required')
    strings(value['capabilities'])
    for name in value['capabilities']: identifier(name)
    exact(value['provider'], {'id','source_digest'}); identifier(value['provider']['id']); sha(value['provider']['source_digest'])
    parameter_schema(value['parameters'])
    if value['parameters']['type'] != 'object': raise ValueError('Recipe parameters must be an object')
    compat = value['compatibility']; exact(compat, {'blender_min','blender_max','engines','target_types','contexts'})
    for key in ('blender_min','blender_max'):
        if not isinstance(compat[key],list) or len(compat[key]) != 3 or any(type(v) is not int or v < 0 for v in compat[key]):
            raise ValueError('Blender version triple required')
    if compat['blender_min'] >= compat['blender_max']: raise ValueError('Empty Blender compatibility range')
    strings(compat['engines']); strings(compat['target_types'], {'MESH','EMPTY','CAMERA','LIGHT'})
    strings(compat['contexts'], {'background','live'})
    exact(value['coverage'], {'reads','writes','dependencies'})
    for fields in value['coverage'].values(): strings(fields, MEASUREMENTS)
    if (not v2 or value['effect']['kind'] == 'modifier') and 'modifiers' not in value['coverage']['writes']:
        raise ValueError('Supported claimed output requires a native modifier effect: include modifiers in coverage.writes and create or update the owned modifier; standalone geometry/material/node effects are unsupported')
    if v2 and value['effect']['kind'] != 'modifier' and not {'materials','nodes'}.intersection(value['coverage']['writes']):
        raise ValueError('Material and shader effects require materials or nodes in coverage.writes')
    invocation = value['invocation']
    if not isinstance(invocation,dict): raise ValueError('Invalid invocation object')
    asynchronous = v2 and invocation.get('completion') == 'asynchronous'
    lifecycle = {'poll','cancel','collect','poll_interval','timeout','cancel_grace'} if asynchronous else set()
    exact(invocation, {'kind','entry','completion','cancellation'} | lifecycle | ({'arguments'} if 'arguments' in invocation else set()))
    if 'arguments' in invocation:
        if invocation['kind']!='python_function' or not isinstance(invocation['arguments'],dict):
            raise ValueError('Argument mapping requires a Python function')
        for name,source in invocation['arguments'].items():
            if not isinstance(name,str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name) is None:
                raise ValueError('Invalid Python argument name')
            if not isinstance(source,str) or (source not in ('target','effect_name','effect_id','parameters','context') and source not in {
                    'parameter:'+key for key in value['parameters']['properties']}):
                raise ValueError('Unknown invocation argument source')
    if asynchronous:
        if invocation['kind'] != 'python_function' or invocation['cancellation'] != 'cooperative':
            raise ValueError('Asynchronous invocation requires cooperative Python lifecycle wrappers')
        for key in ('poll','cancel','collect'): callable_entry(invocation[key])
        for key, low, high in (('poll_interval',.05,5), ('timeout',.1,3600), ('cancel_grace',.1,60)):
            item = invocation[key]
            if type(item) not in (int,float) or not math.isfinite(item) or not low <= item <= high:
                raise ValueError('Invalid bounded asynchronous timing: ' + key)
    elif (invocation['kind'] not in ('python_function','operator','node_asset') or invocation['completion'] != 'synchronous'
            or invocation['cancellation'] != 'between_calls'):
        raise ValueError('Unsupported invocation or completion protocol')
    entry=invocation['entry']
    if invocation['kind']=='node_asset':
        if not isinstance(entry,str) or not 1<=len(entry)<=255 or any(ord(ch)<32 or ord(ch)==127 for ch in entry):
            raise ValueError('Node asset entry must be bounded native text without control characters')
    else:
        segments=1 if invocation['kind']=='operator' else None
        if (not isinstance(entry,str) or len(entry)>128
                or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+',entry) is None
                or (segments is not None and entry.count('.')!=segments)):
            raise ValueError('Invalid callable or operator entry syntax')
    exact(value['update'], {'identity','shared_materials'})
    if value['update']['identity'] != 'effect_key' or value['update']['shared_materials'] not in ('none','all_users','single_user_copy'):
        raise ValueError('Explicit effect identity and material scope required')
    if v2 and {'materials','nodes'}.intersection(value['coverage']['writes']) and value['update']['shared_materials'] == 'none':
        raise ValueError('Material and node writes require an explicit shared material policy')
    if value['validators'] != ['inspect_output','verify_saved']: raise ValueError('Both independent validators required')
    if not isinstance(value['cases'],list) or not value['cases']: raise ValueError('Qualification cases required')
    names = set()
    for case in value['cases']:
        exact(case, {'name','parameters','context','expect'} | ({'failure_contains'} if case.get('expect') == 'fail' else set()))
        identifier(case['name'])
        if case['expect'] == 'fail' and (not isinstance(case['failure_contains'],str) or len(case['failure_contains']) < 8):
            raise ValueError('Negative cases require a specific failure reason')
        if case['name'] in names: raise ValueError('Duplicate qualification case')
        names.add(case['name'])
        if case['context'] not in compat['contexts'] or case['expect'] not in ('pass','fail'):
            raise ValueError('Unsupported qualification case')
        parameter_value(value['parameters'], case['parameters'])
    json.dumps(value, allow_nan=False)
    return json.loads(json.dumps(value))


def validate_parameters(recipe, parameters):
    validate(recipe)
    return parameter_value(recipe['parameters'], parameters)
