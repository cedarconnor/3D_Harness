"""Portable request validation shared by managed execution backends."""
from typing import TypedDict

from . import coordination as c
from .evidence import canonical, finite_number
from .live_recipes import validate as validate_live_recipe


class OperationRequest(TypedDict):
    schema: str
    backend: str
    operation_id: str
    stage: str
    script: str
    contract: str
    handoff: str
    blender: str
    expected_parent: str
    timeout: float


def validate_operation(value: dict) -> dict:
    required = set(OperationRequest.__annotations__)
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - {'live', 'profile'}:
        raise ValueError('Invalid managed operation fields')
    if value['schema'] != 'dcc.execution.operation.v2' or value['backend'] not in ('background', 'live'):
        raise ValueError('Invalid operation schema or backend')
    c.identifier(value['operation_id'])
    for field in required - {'timeout'}:
        c.text(value[field])
    finite_number(value['timeout'])
    if value['timeout'] <= 0:
        raise ValueError('Operation timeout must be positive')
    if 'live' in value and (value['backend'] != 'live' or not isinstance(value['live'], dict)):
        raise ValueError('Live payload requires the live backend')
    if 'profile' in value and not isinstance(value['profile'], dict):
        raise ValueError('An explicit profile reference is required')
    canonical(value)  # Reject nonfinite or unserializable nested values before reserving.
    return value.copy()
