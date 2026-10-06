import copy
import struct
import unittest

from dcc_harness.uv_guard import evaluated_uv_noise_only


class UVGuardTests(unittest.TestCase):
    def setUp(self):
        self.a = dict(source_mesh_hash="mesh", source_uv_hash="uv", modifier_settings=[],
                      geometry_hash="evaluated", uv_layers=["UVMap"],
                      evaluated_uv_values={"UVMap": [0.50000001, 0.75]})

    def test_native_low_bit_noise_and_rounding_boundary(self):
        for drift in (5.960464477539063e-8, 1.1920928955078125e-7):
            b = copy.deepcopy(self.a)
            b["evaluated_uv_values"]["UVMap"][0] += drift
            with self.subTest(drift=drift):
                self.assertTrue(evaluated_uv_noise_only(self.a, b))
        b["evaluated_uv_values"]["UVMap"][0] = self.a["evaluated_uv_values"]["UVMap"][0] + 2.1e-7
        self.assertFalse(evaluated_uv_noise_only(self.a, b))

    def test_authored_uv_geometry_or_modifier_change_never_waived(self):
        for key in ("source_mesh_hash", "source_uv_hash", "modifier_settings", "geometry_hash", "uv_layers"):
            b = copy.deepcopy(self.a)
            b[key] = "changed"
            with self.subTest(key=key):
                self.assertFalse(evaluated_uv_noise_only(self.a, b))

    def test_meaningful_evaluated_change_nonfinite_or_missing_data_rejected(self):
        for val in (0.5001, float("nan"), float("inf")):
            b = copy.deepcopy(self.a)
            b["evaluated_uv_values"]["UVMap"][0] = val
            self.assertFalse(evaluated_uv_noise_only(self.a, b))
        b = copy.deepcopy(self.a)
        b["evaluated_uv_values"]["UVMap"].append(0.0)
        self.assertFalse(evaluated_uv_noise_only(self.a, b))
        self.assertFalse(evaluated_uv_noise_only({}, {}))

    def test_tiled_adjacent_native_float32_values(self):
        for first, second in ((9.774999618530273, 9.77500057220459),
                              (-9.774999618530273, -9.77500057220459)):
            a = copy.deepcopy(self.a); b = copy.deepcopy(self.a)
            a['evaluated_uv_values']['UVMap'][0] = first
            b['evaluated_uv_values']['UVMap'][0] = second
            self.assertTrue(evaluated_uv_noise_only(a, b))
            b['source_uv_hash'] = 'authored tiny change'
            self.assertFalse(evaluated_uv_noise_only(a, b))

    def test_multiple_steps_non_native_doubles_and_large_steps_rejected(self):
        def next_float(value, steps):
            bits = struct.unpack('!I', struct.pack('!f', value))[0]
            return struct.unpack('!f', struct.pack('!I', bits + steps))[0]
        for first, second in ((4.0, next_float(4.0, 2)),
                              (32.0, next_float(32.0, 1)),
                              (9.77500001, 9.77500061)):
            a = copy.deepcopy(self.a); b = copy.deepcopy(self.a)
            a['evaluated_uv_values']['UVMap'][0] = first
            b['evaluated_uv_values']['UVMap'][0] = second
            self.assertFalse(evaluated_uv_noise_only(a, b))


if __name__ == "__main__":
    unittest.main()
