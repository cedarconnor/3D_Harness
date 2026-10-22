"""Only retained, qualified bundles may reach invocation. Discovery stays import-free."""
try:
    from .recipe_store import load
    from .recipe_schema import validate_parameters
except ModuleNotFoundError:
    from dcc_harness.recipe_store import load
    from dcc_harness.recipe_schema import validate_parameters


def inspect_bundle(root, recipe_id, identity):
    return load(root, recipe_id, identity)
