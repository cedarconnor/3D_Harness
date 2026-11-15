"""Native qualification of review-sheet (build-plan item G4).

Builds a clean crate beside a post, the same scene with one face of the crate flipped and a small
detached block inside the crate's object, and a dense grid over the wireframe budget. Checks, by
reading the sheet's pixels: the flipped face is red in the backface row and nothing is red in the
control; the detached block is a second shape in the silhouette row; the wireframe row has lines;
`--color random` colours the two objects differently; a repeat render is byte-identical; the
source hash is unchanged; and the receipt binds the image to the file.
"""
from _launcher import Qualification
q = Qualification(__doc__)
a, out = q.args, q.out
from dcc_harness.evidence import file_hash, read_json
from dcc_harness.review_sheet import decode_png

builder = out / 'build.py'
builder.write_text(
    "import bpy, sys\n"
    "folder = sys.argv[sys.argv.index('--') + 1]\n"
    "FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]\n"
    "def corners(lo, hi):\n"
    "    (a, b, c), (d, e, f) = lo, hi\n"
    "    return [(a, b, c), (d, b, c), (d, e, c), (a, e, c), (a, b, f), (d, b, f), (d, e, f), (a, e, f)]\n"
    "def add(name, vertices, faces):\n"
    "    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces)\n"
    "    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj)\n"
    "    obj['dcc_instance_id'] = name.lower()\n"
    "def scene(defect):\n"
    "    bpy.ops.wm.read_factory_settings(use_empty=True)\n"
    "    vertices, faces = corners((0, 0, 0), (1.2, 0.8, 0.6)), list(FACES)\n"
    "    if defect:\n"
    "        faces[3] = tuple(reversed(faces[3]))\n"
    "        vertices += corners((0.4, 0.2, 1.0), (0.7, 0.5, 1.3)); faces += [tuple(i + 8 for i in f) for f in FACES]\n"
    "    add('Crate', vertices, faces)\n"
    "    add('Post', corners((-0.5, 0, 0), (-0.3, 0.2, 0.6)), FACES)\n"
    "    bpy.ops.wm.save_as_mainfile(filepath=folder + ('/defect.blend' if defect else '/control.blend'))\n"
    "scene(False); scene(True)\n"
    "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
    "bpy.ops.mesh.primitive_grid_add(x_subdivisions=560, y_subdivisions=560, size=2)\n"
    "bpy.context.object['dcc_instance_id'] = 'dense'\n"
    "bpy.ops.wm.save_as_mainfile(filepath=folder + '/dense.blend')\n", encoding='utf-8')
q.blender('build.log', '--python', builder, '--', out)


def sheet(name, key, *extra):
    source = out / f'{name}.blend'
    before = file_hash(source)
    result = q.cli('review-sheet', source, '--blender', a.blender, '--output-dir', out / key, *extra)
    receipt = read_json(result['receipt'])
    assert file_hash(source) == before == result['source']['sha256'] == receipt['checkpoint_sha256'] and result['source_unchanged']
    assert file_hash(result['image']) == receipt['image']['sha256'] and sorted(p.name for p in (out / key).iterdir() if p.suffix == '.png') == ['sheet.png']
    width, height, pixels = decode_png((out / key / 'sheet.png').read_bytes())
    assert [width, height] == result['size'] == receipt['layout']['size'] and width <= 1600
    return result, receipt, (width, pixels)


def tile(receipt, image, row, column):
    """Pixels of one tile as rows of (r, g, b)."""
    layout, (width, pixels) = receipt['layout'], image
    tw, th, gap = *layout['tile'], layout['gap']
    x0, y0 = column * (tw + gap), layout['rows'].index(row) * (th + gap)
    return [[tuple(pixels[((y0 + y) * width + x0 + x) * 3:((y0 + y) * width + x0 + x) * 3 + 3]) for x in range(tw)] for y in range(th)]


def count(rows, test):
    return sum(test(*pixel) for line in rows for pixel in line)


def shapes(rows):
    """Connected dark regions of at least 20 pixels."""
    height, width = len(rows), len(rows[0])
    dark = [[sum(pixel) < 200 for pixel in line] for line in rows]
    found = 0
    for y in range(height):
        for x in range(width):
            if not dark[y][x]:
                continue
            stack, size = [(x, y)], 0
            dark[y][x] = False
            while stack:
                px, py = stack.pop()
                size += 1
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if 0 <= nx < width and 0 <= ny < height and dark[ny][nx]:
                        dark[ny][nx] = False
                        stack.append((nx, ny))
            found += size >= 20
    return found


def red(r, g, b):
    return r > 150 and g < 90 and b < 90


control, control_receipt, control_image = sheet('control', 'control')
defect, defect_receipt, defect_image = sheet('defect', 'defect')
assert control['size'] == [1598, 1198] and [r['row'] for r in control['rows']] == ['silhouette', 'clay', 'wireframe', 'backface']
assert [c['id'] for c in control['columns']] == ['orbit-030', 'orbit-120', 'orbit-210', 'orbit-300'] and control['targets'] == ['crate', 'post']
columns = range(4)
# The flipped face is red from the two sides that see it; nothing is red in the control.
red_control = [count(tile(control_receipt, control_image, 'backface', c), red) for c in columns]
red_defect = [count(tile(defect_receipt, defect_image, 'backface', c), red) for c in columns]
assert red_control == [0, 0, 0, 0] and sum(n > 500 for n in red_defect) >= 2, (red_control, red_defect)
# The crate and the post are two shapes; the detached block is a third wherever it does not overlap them.
shapes_control = [shapes(tile(control_receipt, control_image, 'silhouette', c)) for c in columns]
shapes_defect = [shapes(tile(defect_receipt, defect_image, 'silhouette', c)) for c in columns]
assert max(shapes_control) <= 2 and max(shapes_defect) == 3, (shapes_control, shapes_defect)
# The wireframe row has dark lines on its white surfaces.
lines = count(tile(control_receipt, control_image, 'wireframe', 0), lambda r, g, b: r + g + b < 150)
assert lines > 100, lines

# A repeat render is byte-identical.
again, _, _ = sheet('defect', 'defect-again')
assert file_hash(again['image']) == file_hash(defect['image'])

# Random colours: the two objects differ in the clay row, and only that row changes.
random, random_receipt, random_image = sheet('control', 'random', '--color', 'random')
hues = {pixel for line in tile(random_receipt, random_image, 'clay', 0) for pixel in line if max(pixel) - min(pixel) > 60}
spread = max(p[0] - p[2] for p in hues) - min(p[0] - p[2] for p in hues)
assert spread > 60, spread
assert count(tile(control_receipt, control_image, 'clay', 0), lambda r, g, b: max(r, g, b) - min(r, g, b) > 60) == 0
for row in ('silhouette', 'wireframe', 'backface'):
    assert tile(random_receipt, random_image, row, 0) == tile(control_receipt, control_image, row, 0), row

# Targets, six views and a narrower sheet.
one, one_receipt, _ = sheet('control', 'one', '--targets', 'cr*', '--views', '6', '--width', '800')
assert one['targets'] == ['crate'] and [c['id'] for c in one['columns']][4:] == ['top', 'bottom'] and one['size'][0] <= 800
q.refused(['review-sheet', out / 'control.blend', '--blender', a.blender, '--output-dir', out / 'none', '--targets', 'absent*'], 'Native process failed')
assert 'absent*' in (out / 'none/sheet.log').read_text(encoding='utf-8')

# Over the wireframe budget the row is left out and the result says so.
dense, dense_receipt, _ = sheet('dense', 'dense')
assert [r['row'] for r in dense['rows']] == ['silhouette', 'clay', 'backface'] and 'Wireframe row left out' in dense['notes'][0]
q.finish({'blender': a.blender, 'size': control['size'], 'red_pixels': {'control': red_control, 'defect': red_defect},
          'silhouette_shapes': {'control': shapes_control, 'defect': shapes_defect}, 'wireframe_line_pixels': lines,
          'repeat_identical': True, 'random_colour_spread': spread, 'dense_faces': dense_receipt['faces'], 'sheet_sha256': defect_receipt['image']['sha256']})
