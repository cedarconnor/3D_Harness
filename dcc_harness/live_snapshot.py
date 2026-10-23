"""Live equivalence: exact fields except the existing narrowly gated evaluated UV noise."""
import hashlib
import json
from .uv_guard import evaluated_uv_noise_only


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def retain(root, observation):
    """Keep exact content-addressed observations for explicitly chosen recovery."""
    from pathlib import Path
    from .files import io_path, reject_links, write_exclusive, json_bytes
    identity=fingerprint(observation)
    path=reject_links(Path(root)/'live/observations'/(identity+'.json'))
    io_path(path.parent).mkdir(parents=True,exist_ok=True)
    if not io_path(path).exists(): write_exclusive(path,json_bytes(observation))
    if json.loads(io_path(path).read_text(encoding='utf-8'))!=observation: raise ValueError('Retained observation changed')
    return identity


def matches_retained(root, identity, current):
    from pathlib import Path
    from .files import io_path, reject_links
    if not isinstance(identity,str) or len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):
        raise ValueError('Invalid retained fingerprint')
    path=reject_links(Path(root)/'live/observations'/(identity+'.json'))
    if not io_path(path).exists(): return fingerprint(current)==identity
    expected=json.loads(io_path(path).read_text(encoding='utf-8'))
    if fingerprint(expected)!=identity: raise ValueError('Retained observation changed')
    return equivalent(expected,current)


def equivalent(before, after):
    if before == after:
        return True
    a, b = dict(before), dict(after)
    objects_a, objects_b = a.pop('objects', {}), b.pop('objects', {})
    if a != b or objects_a.keys() != objects_b.keys():
        return False
    for identifier, old in objects_a.items():
        new = objects_b[identifier]
        if old == new:
            continue
        ignore = ('uv_hash', 'evaluated_uv_values')
        if ({k: v for k, v in old.items() if k not in ignore} != {k: v for k, v in new.items() if k not in ignore}
                or not evaluated_uv_noise_only(old, new)):
            return False
    return True
