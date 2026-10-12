"""Portable checks for the GLB delivery receipt: comparison, checkpoint binding and the CLI."""
import copy
import json
import subprocess
import sys
import unittest
from unittest import mock

from coordination_helpers import Fixture
from dcc_harness import delivery
from dcc_harness.continuity import Continuity


def record(iid, triangles=12, low=(0, 0, 0), high=(1, 1, 1), materials=('timber',), kind='MESH'):
    return {'id': iid, 'type': kind, 'triangles': triangles, 'bounds': [list(low), list(high)], 'materials': list(materials)}


EXPORTED = {'objects': [record('bench.top'), record('ground', 2, (-5, -5, 0), (5, 5, 0), ('stone',))],
            'not_exported': [{'id': 'review.camera', 'type': 'CAMERA', 'reason': 'cameras are not delivered'}]}


def imported(objects):
    return {'objects': objects}


class CompareTests(unittest.TestCase):
    def test_a_faithful_import_passes(self):
        result = delivery.compare(EXPORTED, imported(copy.deepcopy(EXPORTED['objects'])))
        self.assertTrue(result['passed'])
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['not_exported'], EXPORTED['not_exported'])
        self.assertEqual(result['matched'], 2)

    def test_each_finding(self):
        changed = [record('bench.top', triangles=10, high=(1, 1, 1.5), materials=('oak',)), record('stray')]
        result = delivery.compare(EXPORTED, imported(changed))
        self.assertFalse(result['passed'])
        codes = sorted((f['id'], f['code']) for f in result['findings'])
        self.assertEqual(codes, [('bench.top', 'BOUNDS'), ('bench.top', 'MATERIALS'), ('bench.top', 'TRIANGLES'),
                                 ('ground', 'MISSING'), ('stray', 'EXTRA')])

    def test_bounds_tolerance_allows_float32_storage(self):
        near = [record('bench.top', high=(1, 1, 1.0008)), record('ground', 2, (-5, -5, 0), (5, 5, 0.0004), ('stone',))]
        self.assertTrue(delivery.compare(EXPORTED, imported(near))['passed'])
        far = [record('bench.top', high=(1, 1, 1.004)), copy.deepcopy(EXPORTED['objects'][1])]
        self.assertFalse(delivery.compare(EXPORTED, imported(far))['passed'])

    def test_duplicate_stable_ids_after_import_are_findings(self):
        doubled = copy.deepcopy(EXPORTED['objects']) + [record('ground', 2, (-5, -5, 0), (5, 5, 0), ('stone',))]
        result = delivery.compare(EXPORTED, imported(doubled))
        self.assertEqual([(f['id'], f['code']) for f in result['findings']], [('ground', 'DUPLICATE')])

    def test_collection_instance_contents_are_set_aside_on_both_sides(self):
        """The exporter writes an instance as its root with the members beneath; neither is compared."""
        def under(item, *ancestors):
            return {**item, 'parent': ancestors[0] if ancestors else None, 'ancestors': list(ancestors)}
        exported = {'objects': [under(record('bench.top')), under(record('ground', 2, (-5, -5, 0), (5, 5, 0), ('stone',))),
                                under(record('ext.instance.label'), 'ext.instance')],
                    'not_exported': [{'id': 'ext.instance', 'type': 'EMPTY', 'reason': 'collection instance', 'instance': True}]}
        arrived = copy.deepcopy(exported['objects']) + [
            under(record('ext.instance', 0, kind='EMPTY')), under(record('bench.top'), 'ext.instance'),
            under(record('name:leg', 4), 'bench.top', 'ext.instance')]
        result = delivery.compare(exported, imported(arrived))
        self.assertTrue(result['passed'], result['findings'])
        self.assertEqual((result['matched'], result['instance_content']), (3, ['bench.top', 'ext.instance', 'name:leg']))
        # The source's own child of the instance is still compared.
        lost = [item for item in arrived if item['id'] != 'ext.instance.label']
        self.assertEqual([(f['id'], f['code']) for f in delivery.compare(exported, imported(lost))['findings']],
                         [('ext.instance.label', 'MISSING')])


class BindingTests(Fixture):
    def test_only_a_checkpoint_of_the_project_is_delivered_for_it(self):
        status = Continuity(self.root).status()
        bound = delivery.checkpoint_for(self.root, status['active']['checkpoint'])
        self.assertEqual(bound['checkpoint_id'], status['active']['id'])
        other = self.base / 'other.blend'
        other.write_bytes(b'not a checkpoint')
        with self.assertRaisesRegex(ValueError, 'not a checkpoint of this project'):
            delivery.checkpoint_for(self.root, other)

    def test_deliver_records_the_receipt_and_fails_on_findings(self):
        status = Continuity(self.root).status()

        def fake_worker(blender, folder, worker, action, request):
            if action == 'export':
                (folder / 'delivery.glb').write_bytes(b'glTF synthetic')
                (folder / 'export.json').write_text(json.dumps({**EXPORTED, 'blender': '5.1.1', 'exporter': '5.1.0',
                                                                'source_sha256': request['source']['sha256']}))
            else:
                (folder / 'import.json').write_text(json.dumps(imported(copy.deepcopy(EXPORTED['objects'][:1]))))
        with mock.patch.object(delivery, 'run_worker', fake_worker):
            result = delivery.deliver(status['active']['checkpoint'], self.base / 'out', 'blender', project=self.root)
        self.assertFalse(result['passed'])
        self.assertEqual(result['checkpoint']['checkpoint_id'], status['active']['id'])
        receipt = json.loads((self.base / 'out/receipt.json').read_text())
        self.assertEqual(receipt['schema'], 'dcc.delivery.glb.v1')
        self.assertEqual(receipt['glb']['bytes'], len(b'glTF synthetic'))
        self.assertEqual([f['code'] for f in receipt['comparison']['findings']], ['MISSING'])

    def test_cli_parses(self):
        proc = subprocess.run([sys.executable, '-m', 'dcc_harness', 'deliver-glb', '--help'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('--project', proc.stdout)


if __name__ == '__main__':
    unittest.main()
