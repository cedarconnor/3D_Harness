---
name: blender-shading
description: Build physically plausible Blender 5.x materials and procedural textures. Covers Principled BSDF v2 socket names and value ranges, measured base colours and IORs, colour spaces, normal maps (OpenGL and DirectX), bump and displacement, metres-based procedural coordinates, box mapping, reusable node groups, glass and liquids, layered wear, EEVEE material settings, and controlled lookdev.
---

# Materials and procedural textures

Build the clean base response first: colour, roughness, metalness and normal. Judge it in neutral, consistent light. Add variation and wear only after the clean material reads correctly. In a harness project, read [materials](../dcc-materials/SKILL.md) for shared-material users, then edit through a reservation.

## Principled BSDF v2 (4.0+): sockets by name

The inputs are `Base Color`, `Metallic`, `Roughness`, `IOR`, `Alpha`, `Normal`, `Weight`, `Diffuse Roughness`, `Subsurface Weight`, `Subsurface Radius`, `Subsurface Scale`, `Subsurface IOR`, `Subsurface Anisotropy`, `Specular IOR Level`, `Specular Tint`, `Anisotropic`, `Anisotropic Rotation`, `Tangent`, `Transmission Weight`, `Coat Weight`, `Coat Roughness`, `Coat IOR`, `Coat Tint`, `Coat Normal`, `Sheen Weight`, `Sheen Roughness`, `Sheen Tint`, `Emission Color`, `Emission Strength`, `Thin Film Thickness` and `Thin Film IOR`.

Always index sockets by name. Old names such as `Specular`, `Transmission`, `Clearcoat` and `Emission` raise KeyError, and indices changed in 4.0.

- **Metallic** is 0 or 1 for real materials; in-between values are only for transitions in masks such as rust over steel. A metal's colour goes in Base Color.
- **IOR** sets dielectric reflectance. Leave `Specular IOR Level` at 0.5 (neutral) unless you want an artistic change; set the physical IOR instead.
- **Emission Strength** defaults to 0, so emission is invisible until you raise it. A small mesh emitter needs a large strength: a 1–2 cm bulb takes hundreds to thousands.
- **Coat** is a clear layer over the base (car paint, varnish, glossy plastic product shots): `Coat Weight` 1 with `Coat Roughness` 0–0.05.
- **Sheen** is for fabric and velvet. **Subsurface** is for skin, wax, marble and leaves; `Subsurface Scale` is in metres.
- **Thin Film** is iridescence (soap, oil). It is not thin-wall transparency.

## Plausible values

| Material | Base colour (linear) | Roughness | Other |
|---|---|---|---|
| Gold | 1.0, 0.77, 0.31 | 0.1–0.4 | Metallic 1 |
| Copper | 0.93, 0.62, 0.52 | 0.15–0.5 | Metallic 1 |
| Aluminium | 0.92, 0.92, 0.92 | 0.2–0.5 | Metallic 1 |
| Iron or steel | 0.53, 0.51, 0.49 | 0.3–0.7 | Metallic 1 |
| Chrome | 0.65, 0.69, 0.70 | 0.02–0.1 | Metallic 1 |
| Concrete | about 0.25–0.5 | 0.7–0.95 | IOR 1.5 |
| Charcoal or tyre rubber | 0.02 | 0.7–0.9 | |
| Fresh snow | about 0.85 | 0.4–0.7 | IOR 1.31 |
| Water, glass, acrylic | — | 0–0.05 | IOR 1.333, 1.52, 1.49 |

- **Albedo range.** Keep dielectric albedo roughly between 0.02 and 0.9 in linear values; never exactly 0 or 1. Most real surfaces are darker than people expect.
- **Roughness floor.** About 0.02; perfectly smooth surfaces look CG.
- **Dirt and wear.** They raise roughness as well as darkening colour.
- **Sources.** The physicallybased.info database collects measured values. Check its colour space before copying numbers.

## Colour spaces and maps

- **Colour space.** Colour and emission textures are `sRGB`. Roughness, metallic, normal, height, AO and masks are `Non-Color` (`image.colorspace_settings.name = 'Non-Color'`). Check the actual connected image, not its filename.
- **Normal maps.** Use them through a Normal Map node. Its `convention` is `'OPENGL'` (+Y, Blender's native) or `'DIRECTX'`; set it to match the map instead of inverting green by hand. Keep Strength at 1. Never feed the same detail into both a normal map and bump.
- **Bump and displacement.** Bump is a shading-only fake and is cheap. True displacement (`material.displacement_method = 'DISPLACEMENT'` or `'BOTH'`) needs dense geometry or adaptive subdivision, and the Displacement node's `Scale` in metres.
- **Sizes.** Use power-of-two textures and pack or relocate them consistently. Packed images survive moving the .blend; external paths should be relative (`//textures/...`).

## Procedural textures at physical scale

- **Coordinates.**
  - `Generated` coordinates run 0–1 over each object's undeformed bounds, so they stretch on non-cubic objects and change when an object is resized.
  - `Object` coordinates are in local metres once scale is applied: Noise or Voronoi `Scale` then means features per metre, consistent across objects.
  - For bricks, tiles and planks, drive the scale from metres (Object coordinates or a Mapping node scaled by 1/tile size), never from a scaled UV.
- **Box mapping.** An Image Texture with `projection='BOX'`, `projection_blend` 0.1–0.3, fed Object coordinates, textures kitbash and architecture without UVs.
- **Variation.** Per-object variation comes from Object Info `Random` driving small hue (±5%) and value (±10%) shifts. Per-instance variation in Geometry Nodes comes from a stored attribute read with an Attribute node.
- **Reuse.** Get or create node groups by name. A material library of node groups beats copying node trees between materials.
- **Export.** Procedural textures do not export to glTF, FBX or engines. [Bake](../blender-baking/SKILL.md) them.

## Glass, liquids and translucency

- **Glass.** `Transmission Weight` 1, `Roughness` 0–0.05, IOR 1.45–1.52, and real thickness: a single plane refracts wrongly. In Cycles, raise the transmission bounces to 12–16 for stacks.
- **Coloured glass and liquid.** A near-white surface plus Volume Absorption inside (density in the tens to hundreds, depending on thickness), not a tinted surface colour.
- **Liquid in a container.** Model the liquid slightly larger than the inner wall, overlapping the glass, so there is no air gap. An air gap of a fraction of a millimetre turns the liquid grey.
- **Thin shells** (bubbles, bottle walls seen through): mix toward a Transparent BSDF instead of refracting twice.
- **EEVEE.** Set `material.surface_render_method` (`'DITHERED'` default, or `'BLENDED'`), `use_raytrace_refraction` and `thickness_mode` (`'SLAB'` for thin, `'SPHERE'` for solid). `blend_method` is legacy; do not use it.

## Wear and lookdev

- **Motivated wear.** Edge wear comes from contact (an Ambient Occlusion or Bevel-node mask, or a curvature bake). Grime goes in crevices and under drips (gravity: a gradient on world Z). Damp collects at the base and at joints. Avoid uniform grunge across unrelated materials.
- **Lookdev in three passes.** First a neutral studio, then a moving area light that reveals roughness and normals, then the production lighting. Compare a whole-scene view and a close-up with the camera, the light and the view transform locked. Change one parameter at a time.
- **Animating materials.** Never animate a value on a shared material, or every user changes. Use object-level attributes (Object Info, an Attribute node reading a custom property), or a per-object material copy.

```python verify
import bpy

def material(name):
    """Get or create: re-running does not leave name.001 duplicates."""
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)

steel = material('MAT-steel')
nodes, links = steel.node_tree.nodes, steel.node_tree.links
bsdf = nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (0.53, 0.51, 0.49, 1)
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.4
assert material('MAT-steel') is steel and len([m for m in bpy.data.materials if m.name.startswith('MAT-steel')]) == 1

# v2 names exist and the old ones are gone.
for name in ('Specular IOR Level', 'Transmission Weight', 'Coat Weight', 'Emission Color', 'Thin Film Thickness'):
    assert name in bsdf.inputs, name
for old in ('Specular', 'Transmission', 'Clearcoat', 'Emission'):
    assert old not in bsdf.inputs, old

# Data maps are Non-Color; DirectX normal maps use the node's convention instead of a green flip.
rough = bpy.data.images.new('T_steel_R', 64, 64); rough.colorspace_settings.name = 'Non-Color'
assert rough.colorspace_settings.is_data
normal_map = nodes.new('ShaderNodeNormalMap'); normal_map.convention = 'DIRECTX'
links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

# Procedural noise in metres: Object coordinates, so scale = features per metre on any object.
coords = nodes.new('ShaderNodeTexCoord')
noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 4.0
ramp = nodes.new('ShaderNodeMapRange')
ramp.inputs['To Min'].default_value, ramp.inputs['To Max'].default_value = 0.35, 0.5
links.new(coords.outputs['Object'], noise.inputs['Vector'])
links.new(noise.outputs['Fac'], ramp.inputs['Value'])
links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
assert bsdf.inputs['Roughness'].is_linked and all(l.is_valid for l in links)

# Glass: transmission, low roughness, physical IOR; EEVEE settings on the material.
glass = material('MAT-glass'); g = glass.node_tree.nodes['Principled BSDF']
g.inputs['Transmission Weight'].default_value, g.inputs['Roughness'].default_value, g.inputs['IOR'].default_value = 1.0, 0.02, 1.52
glass.surface_render_method, glass.use_raytrace_refraction, glass.thickness_mode = 'DITHERED', True, 'SLAB'

# A reusable node group, got or created by name.
group = bpy.data.node_groups.get('NG-edge-wear') or bpy.data.node_groups.new('NG-edge-wear', 'ShaderNodeTree')
group.interface.new_socket('Mask', in_out='OUTPUT', socket_type='NodeSocketFloat')
assert bpy.data.node_groups['NG-edge-wear'].interface.items_tree['Mask'].in_out == 'OUTPUT'
```
