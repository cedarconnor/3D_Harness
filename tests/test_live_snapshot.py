import copy
import unittest


class SnapshotTests(unittest.TestCase):
    def snapshot(self):
        return {'objects': {'cube': {'source_mesh_hash': 'mesh', 'source_uv_hash': 'uv', 'source_attribute_hash': 'attrs',
                'geometry_hash': 'geo', 'modifier_settings': [], 'uv_layers': ['UVMap'], 'matrix_world': [1, 0, 0],
                'uv_hash': 'old', 'evaluated_uv_values': {'UVMap': [.4937499761581421]}}}, 'scene': {'frame': 1}}

    def compare(self, before, after):
        from dcc_harness import live_snapshot
        return live_snapshot.equivalent(before, after)

    def test_only_qualified_evaluated_uv_noise_is_accepted(self):
        before = self.snapshot(); after = copy.deepcopy(before)
        after['objects']['cube']['evaluated_uv_values']['UVMap'] = [.4937500059604645]
        after['objects']['cube']['uv_hash'] = 'different extraction'
        self.assertTrue(self.compare(before, after))
        after['objects']['cube']['matrix_world'] = [2, 0, 0]
        self.assertFalse(self.compare(before, after))

    def test_authored_uv_geometry_and_context_remain_exact(self):
        before = self.snapshot()
        for key in ('source_mesh_hash', 'source_uv_hash', 'source_attribute_hash', 'geometry_hash'):
            after = copy.deepcopy(before); after['objects']['cube'][key] = 'changed'
            self.assertFalse(self.compare(before, after))
        after = copy.deepcopy(before); after['scene']['frame'] = 2
        self.assertFalse(self.compare(before, after))
        after = copy.deepcopy(before); after['objects']['cube']['evaluated_uv_values']['UVMap'] = [.6]
        self.assertFalse(self.compare(before, after))
