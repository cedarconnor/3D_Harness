"""Public recipe drafts and qualification registry. Inspection never imports adapters."""
from .recipe_schema import validate, validate_parameters
from .recipe_store import draft, load


def require_qualified(root, recipe_id, identity):
    load(root, recipe_id, identity)
    raise ValueError('DRAFT recipe has no qualified registration')


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
