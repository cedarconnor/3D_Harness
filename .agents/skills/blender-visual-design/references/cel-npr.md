# Cel and graphic NPR

Start with a reference frame and choose the number of value bands, shadow-edge
softness, line treatment and palette. Large tonal regions need clean geometry and
deliberate normals; noisy roughness and microdetail can break the graphic read.
Keep palette and proportions tied to this project's direction rather than a
universal rule about anime faces or painted highlights.

## Pick the renderer before building shaders

- **EEVEE:** Diffuse BSDF → Shader to RGB → ColorRamp with Constant interpolation
  → Emission → Material Output is a light-responsive banded route. Tune ramp
  thresholds with the intended key light; changing light energy changes the bands.
- **Cycles:** Toon BSDF offers a light-dependent toon response; tune Size and
  Smooth. Shader to RGB does not work in Cycles. A Fresnel or Layer Weight ramp
  responds to view angle and is useful for rims, but is not a shadow-band substitute.
- **Engine delivery:** Blender-specific shader graphs do not transfer through
  ordinary glTF PBR export. Recreate the look in the destination shader or deliver
  an explicitly unlit/baked look. A baked lit image will not relight like a toon shader.

These renderer boundaries are documented in the Blender manuals for
[Shader to RGB](https://docs.blender.org/manual/en/5.1/render/shader_nodes/color/shader_to_rgb.html)
and [Toon BSDF](https://docs.blender.org/manual/en/5.1/render/shader_nodes/shader/toon.html).

For outlines, choose Grease Pencil Line Art, Freestyle in a supported renderer,
or a separately tested inverted hull. Hull thickness follows subject scale;
check culling and normals rather than copying a fixed Solidify distance. Render
contours over concavities, detached parts and the face before accepting the setup.

Review silhouette at thumbnail size, shadow shapes on the face, band stability
through camera/light motion, and outline thickness at final resolution. Inspect
the Combined beauty output for Shader to RGB work; other passes need their own
validation. A still render does not qualify temporal stability or exported shaders.
