"""Disposable native probe for qualify_native_paths; launched only after CONFIG preflight."""
from pathlib import Path
import hashlib
import runpy
import sys

mode, runtime, out, deep = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, runtime)
out, deep = Path(out), Path(deep)
import bpy
from dcc_harness import evidence, files, live_snapshot


if mode == 'io':
    results = {}
    def check(name, action):
        try:
            action()
            results[name] = {'passed': True}
        except Exception as exc:
            results[name] = {'passed': False, 'error': type(exc).__name__ + ': ' + str(exc)}

    path = deep / 'verify-request.json'
    expected = {'path': str(path), 'unicode': '\u96ea', 'number': 7}
    def read():
        assert evidence.read_json(path) == expected
        assert files.file_hash(path) == evidence.read_json(out / 'input-hash.json')['sha256']
    check('read_and_hash', read)

    def write():
        target = deep / 'new-child/output-evidence.json'
        evidence.write_json(target, expected)
        assert evidence.read_json(target) == expected
        before = files.file_hash(target)
        try:
            evidence.write_json(target, {'overwritten': True})
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing evidence was replaced')
        assert files.file_hash(target) == before
        copied = deep / 'new-copy/output-evidence.json'
        assert files.copy_verified(target, copied, before, 'copy changed') == copied
        assert evidence.read_json(copied) == expected
        binary = deep / 'new-child/exclusive-bytes.bin'
        data = b'\x00exact evidence\xff\n'
        files.write_exclusive(binary, data)
        try:
            files.write_exclusive(binary, b'changed')
        except FileExistsError:
            pass
        else:
            raise AssertionError('Existing byte evidence was replaced')
        assert files.file_hash(binary) == hashlib.sha256(data).hexdigest()
    check('exclusive_write_and_copy', write)

    def retention():
        assert files.reject_links(path) == path
        identity = live_snapshot.retain(deep, expected)
        assert identity == live_snapshot.fingerprint(expected)
        assert live_snapshot.retain(deep, expected) == identity
        assert live_snapshot.matches_retained(deep, identity, expected)
        assert not str(path).startswith('\\\\?\\')
    check('logical_identity_and_retention', retention)

    junction = evidence.read_json(out / 'junction.json')
    if junction['created']:
        def refuse_junction():
            for candidate in (Path(junction['path']), Path(junction['path']) / 'marker.json',
                              Path(junction['path']) / 'absent/child.json'):
                try:
                    files.reject_links(candidate)
                except ValueError as exc:
                    assert 'reparse' in str(exc)
                else:
                    raise AssertionError('Junction accepted: ' + str(candidate))
        check('long_junction_refused', refuse_junction)
    else:
        results['long_junction_refused'] = {'passed': None, 'reason': junction['reason']}
    evidence.write_json(out / 'io-proof.json', results)
    assert all(item['passed'] is not False for item in results.values()), results
elif mode == 'fixture':
    from dcc_harness.data.bridge.attachment import snapshot
    from dcc_harness.adoption_inventory_blender import inventory
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    root = bpy.data.objects.new('HarnessRoot', None)
    bpy.context.scene.collection.objects.link(root)
    root['dcc_instance_id'] = 'harness.root'; root['dcc_asset_id'] = 'harness.root'
    bpy.data.orphans_purge(do_recursive=True)
    source = out / 'source.blend'
    assert not source.exists()
    assert bpy.ops.wm.save_as_mainfile(filepath=str(source), check_existing=False) == {'FINISHED'}
    value = snapshot(bpy.context.scene)
    retained = deep / 'fixture-snapshot.json'
    evidence.write_json(retained, value)
    evidence.write_json(out / 'fixture.json', {'source': {'path': str(source), 'sha256': files.file_hash(source)},
        'scene': bpy.context.scene.name, 'snapshot': str(retained), 'fingerprint': live_snapshot.fingerprint(value),
        'inventory': inventory(bpy.context.scene),
        'blender': {'version': bpy.app.version_string, 'build_hash': bpy.app.build_hash.decode()}})
    # bpy/native library path support is measured separately from Python I/O.
    results = {}
    for spelling in ('ordinary', 'extended'):
        native = deep / ('native-save-' + spelling + '.blend')
        argument = str(native) if spelling == 'ordinary' else str(files.io_path(native))
        try:
            result = bpy.ops.wm.save_as_mainfile(filepath=argument, copy=True, check_existing=False)
            proof = {'path': str(native), 'argument': argument, 'characters': len(str(native)), 'result': sorted(result),
                     'sha256': files.file_hash(native), 'logical_source_unchanged': bpy.data.filepath == str(source)}
        except Exception as exc:
            proof = {'path': str(native), 'argument': argument, 'characters': len(str(native)),
                     'error': type(exc).__name__ + ': ' + str(exc)}
        results[spelling] = proof
    evidence.write_json(out / 'native-save.json', results)
elif mode == 'verify':
    sys.argv = [sys.argv[0], '--', 'verify', str(deep / 'independent/verify-request.json')]
    runpy.run_module('dcc_harness._live_verify_blender', run_name='__main__')
elif mode == 'profile-refusal':
    # Expected CONFIG is intentionally different from the proven owned CONFIG.
    # An invalid profile makes reaching activation an independent test failure.
    sys.argv = [sys.argv[0], '--', 'verify', str(deep / 'profile/verify-request.json'), 'unused-worker.py']
    try:
        runpy.run_module('dcc_harness._profile_blender', run_name='__main__')
    except ValueError as exc:
        assert 'Owned worker configuration was not selected' in str(exc), str(exc)
        evidence.write_json(out / 'profile-refusal.json', {'refused_before_activation': True, 'error': str(exc)})
    else:
        raise AssertionError('Mismatched CONFIG accepted')
elif mode in ('native-open-ordinary', 'native-open-extended'):
    source = deep / (mode + '.blend')
    before = files.file_hash(source)
    argument = str(source) if mode.endswith('ordinary') else str(files.io_path(source))
    try:
        result = bpy.ops.wm.open_mainfile(filepath=argument, load_ui=False)
        proof = {'path': str(source), 'argument': argument, 'result': sorted(result),
                 'filepath': bpy.data.filepath, 'canonical_filepath': bpy.data.filepath == str(source),
                 'source_unchanged': files.file_hash(source) == before}
    except Exception as exc:
        proof = {'path': str(source), 'argument': argument, 'error': type(exc).__name__ + ': ' + str(exc)}
    evidence.write_json(out / (mode + '.json'), proof)
else:
    raise ValueError('Unknown probe action')
