# Review sheet

Version 0.25.0, build-plan item G4. `review-sheet` renders one image that shows chosen objects from all sides, four ways. The project's fixed review views show the scene as composed; this shows a single asset's shape, topology and face direction. It needs no project and no stable IDs, and it never saves the file.

```powershell
python -m dcc_harness review-sheet "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/sheet-1" --targets "ext.bench.*"
python -m dcc_harness review-sheet "<saved .blend>" --blender "<BLENDER>" --output-dir "<work>/sheet-2" --views 6 --color random --width 1200
```

The result names the image, `sheet.png` in the output folder. Read that one image.

## What the sheet shows

Columns are views; rows are passes.

| Row | What it shows | Look for |
|---|---|---|
| `silhouette` | Black shape on white | Proportions, outline, parts that have come away |
| `clay` | Even grey with cavity shading and an outline | Surface form without materials; missing bevels, dents |
| `wireframe` | Edges of the evaluated mesh on a white surface | Topology and density; a part that turns black is very dense |
| `backface` | Faces pointing at the viewer in grey, faces pointing away in red | Flipped faces, and whole parts built inside out |

- **`--views 4`** (the default) gives four orbit views at azimuths 30°, 120°, 210° and 300°, 25° above the horizon. **`--views 6`** adds top and bottom.
- **`--targets`** takes ID globs, or names for objects without an ID. Without it, everything render-visible is drawn. The camera frames the targets, so naming one asset fills the tiles.
- **`--color random`** gives each object its own colour in the clay row, so a duplicated or stray object stands out. The other rows are unchanged.
- **`--width`** is the sheet's width in pixels, from 400 to 1600. Tiles are 4:3.

The printed result lists the rows and columns in order, so a tile can be named by row and view. An open sheet seen from behind is red in the backface row; that is correct, not a defect.

## How it renders

A fresh background Blender opens the file and copies each target's evaluated geometry, in world space, into a temporary scene. Modifiers are applied in the copy. Curves, text, surfaces and metaballs are converted to meshes. The sheet is rendered with Workbench through an orthographic camera, tile by tile, and joined into one PNG.

- **Wireframe** is a Wireframe modifier on a copy, since Workbench renders no overlays in the background.
- **Backface** draws each part twice with backface culling on: once as built, in grey, and once with its faces reversed, in red. Whichever copy faces the viewer is the one seen.
- **Backgrounds** are composited by the runtime, because Blender 5.1 and 5.2 take a Workbench background from different places.
- **The receipt** (`receipt.json`) binds the image's SHA-256 to the file's SHA-256, the settings and the layout. The command refuses to report if the file changed while it rendered.
- **Repeat renders are byte-identical.** The PNG carries no metadata. In qualification the same sheet had the same bytes on Blender 5.1.1 and 5.2.1.
- Renders wait for the same machine-wide lock as `render`.

## Limits

- **One image per call.** The size limit protects the agent's context; render two sheets to compare two assets.
- **Over 300,000 faces** the wireframe row is left out and the result says so. Name fewer targets.
- **Geometry that modifiers instance is not drawn,** as in `audit`.
- **No materials, textures or lighting.** Use `render` for the scene as it will look.
- **It shows; it does not judge.** Pair it with [`audit`](AUDIT.md), which measures the same defects and names the objects.

## Qualification

`scripts/qualify_review_sheet.py` builds a crate beside a post, the same scene with one crate face flipped and a detached block inside the crate's object, and a grid over the wireframe budget. It reads the sheet's pixels: the flipped face is red from the two views that see it and nothing is red in the control; the detached block is a third shape in the silhouette row; repeat renders are byte-identical; the source hash is unchanged. It passed from source on Blender 5.1.1 and 5.2.1.

On the production garden, a sheet of the potting bench and its pots took a few seconds and shows the bench red in every view of the backface row, which is the inside-out geometry that `audit` reports as `NORMALS_INWARD`.
