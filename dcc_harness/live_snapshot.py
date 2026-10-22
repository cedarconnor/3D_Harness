"""Live equivalence: exact fields except the existing narrowly gated evaluated UV noise."""
import hashlib
import json
from .uv_guard import evaluated_uv_noise_only


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


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
