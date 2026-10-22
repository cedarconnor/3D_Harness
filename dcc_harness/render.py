"""Render a project's fixed review views of a saved .blend in fresh background Blender; never saves.

Renders run one at a time per machine under an operating-system file lock, which a crashed
process releases. Each job keeps its state in status.json inside its own output folder, so
a detached job can be awaited by folder. Images are evidence for review, not a quality verdict.
"""
from __future__ import annotations

from contextlib import contextmanager
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

from .continuity import _plain
from .evidence import digest, file_hash, read_json, write_json
from .native import run_worker
from .project import now

WORKER = Path(__file__).with_name('_render_blender.py')
SCHEMA = 'dcc.review.views.v1'
ENGINES = ('CYCLES', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH')  # names Blender 5.1 accepts
RENDER_KEYS = {'engine', 'resolution', 'samples', 'seed', 'view_transform', 'look', 'exposure'}
VIEW_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
EVIDENCE_KIND = {'whole': 'whole_scene_render', 'detail': 'detail_render'}


def _number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _vector(value):
    return isinstance(value, list) and len(value) == 3 and all(_number(v) for v in value)


def validate_views(definition):
    """Check a dcc.review.views.v1 definition and return it unchanged."""
    if not isinstance(definition, dict) or set(definition) != {'schema', 'render', 'views'} or definition['schema'] != SCHEMA:
        raise ValueError('Review views need schema dcc.review.views.v1 with render and views')
    settings = definition['render']
    if not isinstance(settings, dict) or not {'engine', 'resolution', 'samples', 'seed'} <= set(settings) <= RENDER_KEYS:
        raise ValueError('Render settings need engine, resolution, samples and seed, and only known keys')
    if settings['engine'] not in ENGINES:
        raise ValueError('Unsupported render engine')
    resolution = settings['resolution']
    if (not isinstance(resolution, list) or len(resolution) != 2 or
            any(isinstance(v, bool) or not isinstance(v, int) or not 0 < v <= 16384 for v in resolution)):
        raise ValueError('Resolution must be two positive integers')
    for key in ('samples', 'seed'):
        if isinstance(settings[key], bool) or not isinstance(settings[key], int) or settings[key] < (1 if key == 'samples' else 0):
            raise ValueError('Samples and seed must be integers')
    if 'exposure' in settings and not _number(settings['exposure']):
        raise ValueError('Exposure must be a finite number')
    for key in ('view_transform', 'look'):
        if key in settings and (not isinstance(settings[key], str) or not settings[key]):
            raise ValueError('Colour settings must be names')
    views = definition['views']
    if not isinstance(views, list) or not views:
        raise ValueError('Review views need at least one view')
    seen = set()
    for view in views:
        if not isinstance(view, dict) or not {'id', 'purpose', 'camera'} <= set(view) <= {'id', 'purpose', 'camera', 'border'}:
            raise ValueError('A view needs id, purpose and camera, and optionally border')
        if not isinstance(view['id'], str) or not VIEW_ID.fullmatch(view['id']) or view['id'] in seen:
            raise ValueError('View IDs must be unique letters, digits, dots, dashes or underscores')
        seen.add(view['id'])
        if view['purpose'] not in EVIDENCE_KIND:
            raise ValueError('View purpose must be whole or detail')
        camera = view['camera']
        if not isinstance(camera, dict) or not (
                (set(camera) == {'object_id'} and isinstance(camera['object_id'], str) and camera['object_id']) or
                (set(camera) == {'lens', 'location', 'target'} and _number(camera['lens']) and camera['lens'] > 0
                 and _vector(camera['location']) and _vector(camera['target']) and camera['location'] != camera['target'])):
            raise ValueError('A camera is either {object_id} or {lens, location, target}')
        if 'border' in view:
            border = view['border']
            if (not isinstance(border, list) or len(border) != 4 or any(not _number(v) or not 0 <= v <= 1 for v in border)
                    or border[0] >= border[1] or border[2] >= border[3]):
                raise ValueError('Border is [min_x, max_x, min_y, max_y] as increasing fractions')
    return definition


def strip_png_text(path):
    """Remove PNG text chunks in place: Cycles writes render timings there, so identical renders would differ."""
    data = Path(path).read_bytes()
    signature = b'\x89PNG\r\n\x1a\n'
    if not data.startswith(signature):
        raise ValueError(f'Not a PNG image: {path}')
    kept, position = [signature], len(signature)
    while position < len(data):
        length = int.from_bytes(data[position:position + 4], 'big')
        end = position + 12 + length
        if end > len(data):
            raise ValueError(f'Truncated PNG image: {path}')
        if data[position + 4:position + 8] not in (b'tEXt', b'zTXt', b'iTXt'):
            kept.append(data[position:end])
        position = end
    Path(path).write_bytes(b''.join(kept))


def _definition(project, views):
    if (project is None) == (views is None):
        raise ValueError('Give exactly one of a project or a views file')
    if views is not None:
        return validate_views(read_json(_plain(views)))
    from .workflow import resume
    decisions = resume(project)['decisions']
    if 'review_views' not in decisions:
        raise ValueError('The project has no review_views decision; record one or pass a views file')
    return validate_views(decisions['review_views'])


def _prepare(source, out, project, views):
    source = _plain(source)
    if source.suffix.lower() != '.blend' or not source.is_file():
        raise ValueError('Source must be an existing saved .blend file')
    definition = _definition(project, views)
    folder = _plain(out)
    folder.mkdir(parents=True, exist_ok=False)
    descriptor = {'path': str(source.resolve(strict=True)), 'sha256': file_hash(source)}
    return folder.resolve(), {'source': descriptor, 'out': str(folder.resolve()), 'definition': definition}


def _status(folder, state, **extra):
    path = folder / 'status.json'
    temporary = folder / 'status.json.tmp'
    temporary.unlink(missing_ok=True)
    write_json(temporary, {'schema': 'dcc.render.status.v1', 'state': state, **extra})
    os.replace(temporary, path)


def _lock_path():
    return Path(os.environ.get('DCC_HARNESS_RENDER_LOCK') or Path(tempfile.gettempdir()) / 'dcc_harness-render.lock')


@contextmanager
def render_lock():
    """Hold the machine-wide render lock; the operating system releases it if the process dies."""
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            while True:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.2)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _run(folder, blender, request):
    _status(folder, 'waiting')
    started_at = None
    try:
        with render_lock():
            started_at = now()
            _status(folder, 'running', started_at=started_at)
            started = time.monotonic()
            options = {'timeout': 120} if 'preview' in request else {}
            run_worker(blender, folder, WORKER, 'render', request, **options)
            seconds = round(time.monotonic() - started, 3)
        source = request['source']
        if file_hash(source['path']) != source['sha256']:
            raise RuntimeError('Source changed during rendering; inspect retained outputs')
        receipt = read_json(folder / 'receipt.json')
        if receipt.get('schema') != 'dcc.quality.renders.v1' or receipt.get('checkpoint_sha256') != source['sha256']:
            raise RuntimeError('Render receipt is not bound to the source bytes')
        if receipt.get('views_digest') != digest(read_json(folder / 'views.json')):
            raise RuntimeError('Render settings digest differs from the receipt')
        views = request['definition']['views']
        if set(receipt['images']) != {v['id'] for v in views}:
            raise RuntimeError('Render receipt does not cover every view')
        for image in receipt['images'].values():
            if file_hash(_plain(folder / image['path'])) != image['sha256']:
                raise RuntimeError('Rendered image changed after its receipt')
        prefix = folder.name + '/'
        result = {'schema': 'dcc.render.v1', 'status': 'RENDERED', 'passed': True, 'source': source, 'source_unchanged': True,
                  'receipt': str(folder / 'receipt.json'), 'settings': str(folder / 'views.json'),
                  'images': {vid: str(folder / image['path']) for vid, image in receipt['images'].items()},
                  'views_digest': receipt['views_digest'], 'seconds': seconds, 'evidence_root': str(folder.parent),
                  'evidence': [{'kind': EVIDENCE_KIND[v['purpose']], 'render': {
                      'receipt': {'path': prefix + 'receipt.json'}, 'settings': {'path': prefix + 'views.json'}, 'view_id': v['id']}}
                      for v in views],
                  'artistic_acceptance': 'not_assessed'}
    except BaseException as exc:
        _status(folder, 'failed', error=f'{type(exc).__name__}: {exc}', started_at=started_at, finished_at=now())
        raise
    _status(folder, 'done', result=result, started_at=started_at, finished_at=now())
    return result


def render_file(source, out, blender, *, project=None, views=None, preview=None):
    folder, request = _prepare(source, out, project, views)
    if preview is not None:
        request['preview'] = preview
    return _run(folder, blender, request)


def start_detached(source, out, blender, *, project=None, views=None):
    """Validate and queue a render in a separate process; the output folder is the job's ID."""
    folder, request = _prepare(source, out, project, views)
    write_json(folder / 'job.json', {'schema': 'dcc.render.job.v1', 'blender': str(blender), 'request': request})
    _status(folder, 'queued')
    options = ({'creationflags': subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt'
               else {'start_new_session': True})
    root = str(Path(__file__).resolve().parent.parent)
    environment = {**os.environ, 'PYTHONPATH': root + os.pathsep + os.environ.get('PYTHONPATH', '')}
    with (folder / 'job.log').open('x', encoding='utf-8') as log:
        subprocess.Popen([sys.executable, '-m', 'dcc_harness', 'render-job', str(folder)], stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT, cwd=root, env=environment, close_fds=True, **options)
    return {'schema': 'dcc.render.queued.v1', 'status': 'QUEUED', 'job': str(folder),
            'next_action': f'python -m dcc_harness render-wait "{folder}"'}


def run_job(folder):
    folder = _plain(folder).resolve()
    job = read_json(folder / 'job.json')
    return _run(folder, job['blender'], job['request'])


def wait(folder, timeout=100):
    """Wait up to timeout seconds for a job to finish, then return its current status."""
    path = Path(folder) / 'status.json'
    if not path.is_file():
        raise ValueError(f'No render job in {folder}')
    deadline = time.monotonic() + max(0, timeout)
    while True:
        status = read_json(path)
        if status['state'] in ('done', 'failed') or time.monotonic() >= deadline:
            return {**status, 'job': str(Path(folder).resolve())}
        time.sleep(0.25)
