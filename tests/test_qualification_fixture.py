"""The synthetic lifecycle provider responds to its declared mesh/material inputs."""
from pathlib import Path
import runpy
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch


class Modifiers(dict):
    def new(self, name, kind):
        self[name] = NS(name=name, type=kind)
        return self[name]


class LifecycleFixtureTests(unittest.TestCase):
    def setUp(self):
        bpy = ModuleType('bpy')
        bpy.types = NS(Operator=object)
        bpy.props = NS(FloatProperty=lambda **kw: None, StringProperty=lambda **kw: None)
        handlers = ModuleType('bpy.app.handlers'); handlers.persistent = lambda fn: fn
        with patch.dict(sys.modules, {'bpy': bpy, 'bpy.app.handlers': handlers}):
            self.provider = runpy.run_path(str(Path(__file__).parent / 'fixtures/addons/legacy/capability_fixture/__init__.py'))
        self.roughness = NS(default_value=.5)
        material = NS(node_tree=NS(nodes={'Principled BSDF': NS(inputs={'Roughness': self.roughness})}))
        self.obj = NS(data=NS(vertices=[NS(co=NS(length=1.0)), NS(co=NS(length=3.0))]),
                      active_material=material, modifiers=Modifiers())

    def apply(self, name):
        result = self.provider[name]({'target': self.obj}, {'amount': .1, 'behavior': 'normal'}, 'test-effect')
        self.assertEqual(result, {'status': 'FINISHED'})
        self.assertEqual(len(self.obj.modifiers), 1)
        return self.obj.modifiers['DCC::test-effect'].width

    def test_adaptive_effect_responds_to_geometry_and_material_but_is_repeatable(self):
        initial = self.apply('mark_adaptive')
        self.assertEqual(self.apply('mark_adaptive'), initial)
        self.obj.data.vertices[0].co.length = 2.0
        geometry = self.apply('mark_adaptive')
        self.assertGreater(geometry, initial)
        self.roughness.default_value = .72
        material = self.apply('mark_adaptive')
        self.assertGreater(material, geometry)
        self.assertEqual(self.apply('mark_adaptive'), material)
        self.assertEqual(self.obj.data.vertices[0].co.length, 2.0)
        self.assertEqual(self.roughness.default_value, .72)

    def test_constant_provider_stays_constant_after_dependency_changes(self):
        initial = self.apply('mark')
        self.obj.data.vertices[0].co.length = 2.0
        self.roughness.default_value = .72
        self.assertEqual(self.apply('mark'), initial)


if __name__ == '__main__':
    unittest.main()
