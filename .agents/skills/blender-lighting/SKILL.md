---
name: blender-lighting
description: Light Blender scenes deliberately for product, character, interior and exterior work in Cycles and EEVEE. Covers motivated key/fill/rim structure, light size and softness, physical units and scaling rigs to subject size, HDRI and sky worlds, reflections for metal and glass, light linking, EEVEE light probes, and one-variable lighting diagnosis.
---

# Light with intent

Before placing a light, decide what it is for: the story's motivation (sun, window, practical lamp), the focal hierarchy, and the shape of the form. Adding lights until nothing is dark is not a lighting method. Check exposure and colour management first (see [rendering](../blender-rendering/SKILL.md)). Many "lighting" problems are a wrong view transform or exposure.

In a harness project, the approved lights and cameras are protected. Read [lighting review](../dcc-lighting-review/SKILL.md) before changing them, and change lighting only when the task includes it.

## Structure

- **Key.** One dominant direction sets the shadow shape. A key 30–45° to the side and above reads form; frontal light flattens it.
- **Fill.** Fill sets the contrast ratio, not the visibility. Key-to-fill around 2:1 is soft and commercial, 4:1 is dramatic, 8:1 or more is low-key. Soft light can still be high-contrast.
- **Rim or kick.** A rim from behind separates the silhouette from the background. Keep it narrow and check it does not flare the edges.
- **Practicals and motivation.** In environments, every visible source should explain some light, and every strong light should have a plausible source.
- **Source size.** Apparent size, not power, controls shadow softness. Use `shadow_soft_size` for point and spot lights, `size` for area lights, and `angle` for the sun: about 0.5° for clear sun, larger for haze.

## Units and scale

- **Power units.** Point, spot and area lights are in watts of emitted power; the sun is in irradiance (W/m²).
  - For a believable sun in Blender's standard pipeline, start around 3–5 W/m² with exposure 0. Physical values near 1000 need matching exposure changes.
  - A 100 W bulb in Blender is not a 100 W household bulb. Judge by the render, with exposure fixed.
- **Scale rigs to the subject.** Derive light distances and sizes from the subject's bounding box. When you move a rig to a subject k times larger, multiply distances and sizes by k and the energy of point, spot and area lights by k². Sun strength does not scale with size.
- **Colour temperature.** Set it on the light (`light.use_temperature`, `light.temperature` in kelvin, 5.0+), not by tinting the world or the albedo. Rough values: 1900 K candle, 2700 K tungsten, 4000 K neutral, 5500 K daylight, 6500–8000 K overcast and shade.

## Worlds

- **HDRI.** An HDRI gives both lighting and reflections. Match its sun direction to any sun light you add, and rotate it with a Mapping node rather than rotating the scene.
- **Several jobs at once.** When one HDRI cannot do every job (background, light and reflections), split them with a Light Path node (`Is Camera Ray`) in Cycles. Do this for a specific reason, because it breaks physical consistency.
- **Sky texture (5.1).** The types are `SINGLE_SCATTERING`, `MULTIPLE_SCATTERING`, `PREETHAM` and `HOSEK_WILKIE`; `NISHITA` is gone.
  - The sky's sun disc renders only in Cycles. For the same sun in both engines, add a real Sun light, turn the sky's `sun_disc` off, and set `world.sun_threshold = 0` in EEVEE so it does not extract a second sun.
- **Neutral world for products.** A low-strength neutral world (about 0.1–0.4) gives subtle reflections without flattening the shot.

## Metal, glass and product shots

- **Metals and chrome** show the shape of what they reflect. Shape their highlights with large area strips and cards, and darken their edges with black flags (black emissive or diffuse planes). Move a strip to reshape a highlight; do not just add power.
- **Clear and translucent objects** need something bright behind or beside them to read. Black flags behind glass turn it grey and dirty. In Cycles, give them 12–16 transmission bounces, and enable caustics only where they matter.
- **A camera-locked rig.** Parent the product lights to an empty that rotates with the camera, so every angle of a turntable or product set keeps the same light-to-camera relationship.
- **Contact shadow.** A product or character must sit on something. A soft contact shadow under it does more for realism than another light.

## Light linking and EEVEE specifics

- **Light linking** (Cycles, and EEVEE with limits) is `obj.light_linking.receiver_collection` and `blocker_collection`. An *include* set with one object means only that object receives the light (or casts its shadow), not "the defaults plus one". Check receivers and shadows in separate renders.
- **EEVEE bounce.** EEVEE gets bounce light from baked **volume light probes**. Ray tracing alone gave no bounce from a white reflector card in tests. Add a `VOLUME` probe covering the scene and bake it, and re-bake after moving lights or reflectors. Sphere and plane probes provide reflections.
- **EEVEE shadows.** Raise `shadow_ray_count` and `shadow_step_count` for soft, contact-correct shadows on hero shots.

## Diagnose one variable at a time

Lock the camera, exposure, view transform, samples and seed. Change one light. Render before and after at the same settings, and compare. For a gray-shaded readability pass, use the view layer's `material_override` with a mid-gray diffuse material, keeping the colour pipeline unchanged. Remove the override before final renders. Name lights for their role (`key`, `fill`, `rim_left`, `practical_desk`) so a later session can reason about them.

```python verify
import bpy, math
from mathutils import Vector

scene = bpy.context.scene
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0.5)); subject = bpy.context.object

def three_point(target, scale=1.0, base_energy=200.0):
    """Key, fill and rim sized to the subject's bounds; energy scales with the square of rig size."""
    corners = [target.matrix_world @ Vector(c) for c in target.bound_box]
    centre = sum(corners, Vector()) / 8
    extent = max((corners[6] - corners[0])) * scale
    rig = {}
    for role, azimuth, elevation, ratio, size in (('key', -40, 40, 1.0, 1.0), ('fill', 50, 15, 0.25, 2.0), ('rim', 160, 35, 0.6, 0.5)):
        data = bpy.data.lights.new(role, 'AREA'); data.size = extent * size
        data.energy = base_energy * ratio * (extent / 1.0) ** 2
        light = bpy.data.objects.new(role, data); scene.collection.objects.link(light)
        a, e, d = math.radians(azimuth), math.radians(elevation), extent * 3
        light.location = centre + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
        light.rotation_euler = (centre - light.location).to_track_quat('-Z', 'Y').to_euler()
        rig[role] = light
    return rig

rig = three_point(subject)
assert abs(rig['fill'].data.energy / rig['key'].data.energy - 0.25) < 1e-6      # 4:1 key to fill
# Each light points at the subject: its -Z axis passes through the centre (update matrices first).
bpy.context.view_layer.update()
for light in rig.values():
    aim = light.matrix_world.to_3x3() @ Vector((0, 0, -1))
    to_centre = (Vector((0, 0, 0.5)) - light.location).normalized()
    assert aim.dot(to_centre) > 0.999, light.name

# Scaling the subject 2x scales distances by 2 and area-light energy by 4.
key_energy = rig['key'].data.energy
subject.scale = (2, 2, 2); bpy.context.view_layer.update()
big = three_point(subject)
assert abs(big['key'].data.energy / key_energy - 4.0) < 1e-6

# Colour temperature lives on the light (5.0+); the sun is irradiance, not watts.
rig['key'].data.use_temperature, rig['key'].data.temperature = True, 3200
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy, sun.angle = 4.0, math.radians(0.53)
assert rig['key'].data.temperature == 3200 and sun.energy == 4.0

# Light linking: the rim lights only the subject.
receivers = bpy.data.collections.new('rim_receivers'); receivers.objects.link(subject)
rig['rim'].light_linking.receiver_collection = receivers
assert rig['rim'].light_linking.receiver_collection == receivers

# Sky types in 5.1, and a volume probe for EEVEE bounce.
world = bpy.data.worlds.new('w'); scene.world = world
sky = world.node_tree.nodes.new('ShaderNodeTexSky')
assert {i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items} >= {'MULTIPLE_SCATTERING', 'HOSEK_WILKIE'}
assert 'NISHITA' not in {i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items}
probe = bpy.data.objects.new('bounce', bpy.data.lightprobes.new('bounce', 'VOLUME'))
assert probe.data.type == 'VOLUME' and hasattr(world, 'sun_threshold')
```
