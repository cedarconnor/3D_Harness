import importlib.util
from pathlib import Path
import sys
import socket
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from dcc_harness import offline


class Entries(list):
    def get(self, name):
        return next((e for e in self if e.module == name), None)

    def new(self, **kwargs):
        item = NS(module=kwargs.get('module', ''), preferences=NS(strength=1.0),
                  directory=kwargs.get('custom_directory', ''))
        self.append(item)
        return item


class AsyncProfileTests(unittest.TestCase):
    def setUp(self):
        self.prefs = NS(use_preferences_save=True, addons=Entries(),
                        extensions=NS(repos=Entries()))
        self.artist = self.prefs.addons.new(module='artist')
        self.provider = self.prefs.addons.new(module='provider')
        self.profile = {'providers': [], 'preferences': {'provider': {'strength': 2.0}}}
        path = Path(__file__).parents[1] / 'dcc_harness/data/bridge/addons.py'
        spec = importlib.util.spec_from_file_location('async_test_addons', path)
        self.addons = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {'bpy': NS(context=NS(preferences=self.prefs)),
                                          'addon_utils': NS()}):
            spec.loader.exec_module(self.addons)
        self.stack = mock.patch.object(self.addons.provider_sources, 'validate_profile')
        self.stack.start()
        self.addons.inventory = lambda roots=None: {}

    def tearDown(self):
        lease = getattr(self.addons, 'ACTIVE_LEASE', None)
        if lease:
            lease.close()
        offline.LEASES.clear()
        self.stack.stop()

    def test_preferences_remain_active_until_explicit_close(self):
        lease = self.addons.AsyncProfileLease(self.profile, 'operation')
        self.assertFalse(self.prefs.use_preferences_save)
        self.assertEqual(self.provider.preferences.strength, 2.0)
        self.assertRaises(ValueError, self.addons.AsyncProfileLease, self.profile, 'other')
        lease.close()
        lease.close()
        self.assertTrue(lease.closed)
        self.assertTrue(self.prefs.use_preferences_save)
        self.assertEqual(self.provider.preferences.strength, 1.0)
        self.assertIn(self.artist, self.prefs.addons)

    def test_new_preferences_and_repos_are_restored(self):
        self.profile['preferences']['new_provider'] = {'strength': 3.0}
        lease = self.addons.AsyncProfileLease(self.profile, 'operation')
        self.prefs.extensions.repos.new(module='temporary')
        self.assertIsNotNone(self.prefs.addons.get('new_provider'))
        lease.close()
        self.assertIsNone(self.prefs.addons.get('new_provider'))
        self.assertEqual(self.prefs.extensions.repos, [])

    def test_constructor_failure_rolls_back(self):
        self.profile['preferences']['provider']['missing'] = 1
        self.assertRaises(AttributeError, self.addons.AsyncProfileLease, self.profile, 'operation')
        self.assertEqual(self.provider.preferences.strength, 1.0)
        self.assertTrue(self.prefs.use_preferences_save)
        self.assertIsNone(self.addons.ACTIVE_LEASE)
        self.assertFalse(offline.LEASES)

    def test_restore_failure_keeps_guard_and_can_retry(self):
        lease = self.addons.AsyncProfileLease(self.profile, 'operation')
        original = self.prefs.addons.remove
        self.prefs.addons.new(module='temporary')
        self.prefs.addons.remove = lambda item: (_ for _ in ()).throw(RuntimeError('restore denied'))
        self.assertRaises(RuntimeError, lease.close)
        self.assertFalse(lease.closed)
        self.assertIs(self.addons.ACTIVE_LEASE, lease)
        self.assertTrue(offline.LEASES)
        self.assertFalse(self.prefs.use_preferences_save)
        self.prefs.addons.remove = original
        lease.close()
        self.assertTrue(lease.closed)

    def test_offline_lease_survives_nested_scopes(self):
        attempts, nested = [], []
        offline.begin_lease(attempts, 'owner')
        with offline.scope(nested):
            self.assertRaises(RuntimeError, offline.audit, 'socket.connect', (None, ('host', 443)))
        self.assertFalse(offline.ACTIVE)
        self.assertRaises(RuntimeError, offline.audit, 'socket.connect', (None, ('later', 443)))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(len(nested), 1)
        offline.end_lease('owner')
        offline.end_lease('owner')
        offline.audit('socket.connect', (None, ('allowed', 443)))

    def test_real_socket_audit_denies_between_callbacks(self):
        attempts = []
        original_connect = socket.socket.connect
        offline.begin_lease(attempts, 'owner')
        with socket.socket() as connection:
            self.assertRaises(RuntimeError, connection.connect, ('127.0.0.1', 9))
        self.assertIs(socket.socket.connect, original_connect)
        self.assertEqual(len(attempts), 1)
        offline.end_lease('owner')

    def test_extension_activation_survives_ticks_then_repository_restores(self):
        with tempfile.TemporaryDirectory() as folder:
            name = 'bl_ext.owned.provider'
            pin = {'module': name, 'path': str(Path(folder) / 'provider')}
            self.profile['providers'] = [pin]
            self.addons.PINS[name] = pin
            calls = []
            self.addons.addon_utils.enable = lambda *args, **kwargs: calls.append((args, kwargs)) or NS()
            lease = self.addons.AsyncProfileLease(self.profile, 'operation')
            self.assertEqual(self.prefs.extensions.repos[0].module, 'owned')
            self.assertEqual(len(calls), 1)
            self.assertFalse(calls[0][1]['default_set'])
            with self.addons.session_preferences(self.profile, activate=False):
                self.assertEqual(self.provider.preferences.strength, 2.0)
            self.assertEqual(self.provider.preferences.strength, 2.0)
            self.assertFalse(self.prefs.use_preferences_save)
            lease.close()
            self.assertEqual(self.prefs.extensions.repos, [])
            self.assertEqual(self.provider.preferences.strength, 1.0)

    def test_unpinned_extension_rolls_back_and_preserves_artist_provider(self):
        self.profile['providers'] = [{'module': 'bl_ext.owned.provider', 'path': '/unused/provider'}]
        self.assertRaises(ValueError, self.addons.AsyncProfileLease, self.profile, 'operation')
        self.assertIn(self.artist, self.prefs.addons)
        self.assertTrue(self.prefs.use_preferences_save)
        self.assertFalse(offline.LEASES)


if __name__ == '__main__':
    unittest.main()
