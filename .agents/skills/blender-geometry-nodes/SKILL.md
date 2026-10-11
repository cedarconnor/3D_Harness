---
name: blender-geometry-nodes
description: Design, script and verify Geometry Nodes in Blender 5.x for scattering, procedural modeling, instancing, motion graphics and simulations. Covers fields and domains, building trees from Python with the interface API and socket identifiers, modifier inputs, zones (repeat, simulation, for-each, closures), instancing and realizing, seeds, menus, organization, baking, and checking the evaluated result instead of the graph.
---

# Geometry Nodes

A node tree is code. Expose its parameters, make its randomness seeded, keep it readable, and judge it by the geometry it produces, not by how many nodes it has.

## Choose what to build

- **Built-in modifiers first.** Do not rebuild Mirror, Bevel, Array or Subdivision in nodes unless the procedural system needs them inside.
- **Plain fields over zones.** Field nodes evaluate in parallel and are fastest.
  - The **Repeat** zone is for iterations that depend on each other: growth, erosion, iterative subdivision. It is feedback within one evaluation, not a simulation.
  - The **For Each Element** zone (4.3+) generates something per element when no field form exists. It is much slower than fields.
  - The **Simulation** zone is for state that carries from frame to frame. If a value can be computed from Scene Time alone, it is not a simulation.
  - **Closures and bundles** (5.0+) inject behaviour into reusable groups and pass many values as one. Use them only in 5.0+ files.
- **Menus.** Offer user-facing modes through a Menu Switch fed by a `NodeSocketMenu` group input, not an integer switch.

## Fields and domains

- **Fields.** A field (Position, Index, Normal, a Random Value) is a function. It is evaluated on the domain of the node that consumes it, for that node's geometry. The same field means different things on points, edges, faces and corners.
- **Moving between domains.** Use Evaluate on Domain, or Capture Attribute, which freezes values at a moment. Put Capture **before** topology changes such as extrusion, subdivision or realizing, and capture coupled values (position and velocity) in one Capture node.
- **Named attributes.** Store Named Attribute only data that must leave the tree: data for shaders through an Attribute node, for export, or for another modifier. Keep everything else anonymous.
- **Missing attributes.** A missing attribute reads as zero or false, with no error. An all-false selection deletes everything. Unsupported domain and component combinations pass through silently.
- **Units.** Angles are in radians. Positions are object-local. For world directions such as gravity or "up in the world", use Self Object → Object Info, Invert Matrix and Transform Direction.

## Instancing

- **Default pattern.** Distribute Points on Faces → Instance on Points → (Realize Instances only if needed). Instances share data: a million instances of one rock cost one rock plus a transform each.
  - Realize only when a later mesh operation needs real topology: a boolean, a merge, per-vertex displacement.
  - Set Position on instances moves only their origins.
- **Seeds.** Seed every Random Value and distribution, and expose the seed. Two Random Value nodes with the same seed and ID are perfectly correlated, so offset their seeds. Inside For Each, feed the zone's Index as the ID.
- **Masks.** Scatter with masks: a slope mask (`Normal.z > 0.7` for grass), a painted vertex group or attribute, and distance from paths. Poisson-disk distribution (`distribute_method='POISSON'`, Distance Min) avoids clumping.
- **Rotation.** Align Rotation to Vector plus Rotate Rotation, using rotation sockets rather than Euler vectors. Random yaw is a rotation about the aligned axis.

## Build trees from Python

- **Create the tree.** `tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')`, then use the object returned; the name may gain `.001`. Get or rebuild an existing tree by clearing its nodes rather than creating duplicates.
- **Interface.**
  - Add sockets with `tree.interface.new_socket(name, in_out='INPUT', socket_type='NodeSocketFloat')`, using base type names, then set `default_value`, `min_value`, `max_value`, `subtype` and `description` on the returned item.
  - Group sockets with `new_panel`.
  - Put the Geometry socket first on both input and output, the modifier convention.
  - Check `tree.interface.items_tree` before adding sockets, so a rerun does not duplicate them.
- **Nodes and links.**
  - Set mode properties (`data_type`, `domain`, `operation`) **before** linking, because they change which sockets exist.
  - Link by socket name only when the name is unique among *available* sockets, and never by index on dynamically typed nodes (Mix, Switch, Compare, Store Named Attribute).
  - Confirm `link.is_valid` after linking.
- **Zones.** Create the input and output nodes, then call `input.pair_with_output(output)` and check it returns `True`. Add items on the **output** node: `repeat_items`, `state_items`, `main_items`.
- **Modifier inputs.** These are keyed by the interface item's **identifier**, not its name. Read identifiers from `items_tree`; never hard-code `Socket_2`: in a tree built from Python the first float input was `Socket_1`.
  - On 5.1 write `mod[item.identifier] = value`.
  - On 5.2 that raises TypeError; write `getattr(mod.properties.inputs, item.identifier).value = value` instead, with `.type` and `.attribute_name` for attribute inputs. Both were measured.
  - Gate on `hasattr(mod, 'properties')`.
  - Since 4.2 the values are typed, so a float into an int input fails.
- **After changing an input,** call `obj.update_tag()` and get a fresh depsgraph before measuring.
- **Organization.** Lay out left to right, with one titled Frame per functional block. Keep default node names and use labels for meaning. Nest reusable logic as subgroups. Give library groups a fake user (`use_fake_user = True`). Mark modifier assets with `tree.is_modifier = True` and `tree.asset_mark()`.

## Verify the evaluated result

- **Outcome checks.** Use the outcomes the request implies: point and instance counts (density × area; floor(length / spacing) for curve arrays), bounds, attribute presence per domain, no NaNs.
- **Instances.** `to_mesh()` and `bound_box` **ignore instances**. Count them through `obj.evaluated_get(depsgraph).evaluated_geometry()` (a GeometrySet, 4.5+), or iterate `depsgraph.object_instances`.
- **Robustness.** Rotate the object 90°, change the resolution and push every exposed input to its extremes; test seeds such as 0, 42 and 9999. World-space logic that breaks under rotation is a bug.
- **Debugging.** In the UI, use the Viewer node with the Spreadsheet, and Ctrl+F to search warnings (5.1). Headless, read evaluated attributes and `node.warnings`, and mute nodes to bisect.
- **Performance.** Realize late, cap densities, use Is Viewport to lower preview density, avoid nested zones, and bake static expensive results with the Bake node.

## Simulation and baking

Simulation state lives in the zone's state items. Results are correct only when stepped frame by frame from the start, or baked: a jump to frame 200 of an unbaked simulation is not the stepped result. Bake with `bpy.ops.object.simulation_nodes_cache_bake(selected=False)`, or `geometry_node_bake_single(session_uid=..., modifier_name=..., bake_id=...)`. `NodesModifier.bake_target` is `'PACKED'` (inside the .blend) or `'DISK'` (with `bake_directory`). See [simulation](../blender-simulation/SKILL.md) for general cache practice.

```python verify
import bpy

def build_scatter():
    tree = bpy.data.node_groups.get('GN-scatter') or bpy.data.node_groups.new('GN-scatter', 'GeometryNodeTree')
    tree.nodes.clear()
    if not tree.interface.items_tree:
        tree.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        density = tree.interface.new_socket('Density', in_out='INPUT', socket_type='NodeSocketFloat')
        density.default_value, density.min_value = 10.0, 0.0
        tree.interface.new_socket('Seed', in_out='INPUT', socket_type='NodeSocketInt')
        tree.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n, l = tree.nodes, tree.links
    group_in, group_out = n.new('NodeGroupInput'), n.new('NodeGroupOutput')
    distribute = n.new('GeometryNodeDistributePointsOnFaces')
    rock = n.new('GeometryNodeMeshIcoSphere'); rock.inputs['Radius'].default_value = 0.05
    instance = n.new('GeometryNodeInstanceOnPoints')
    join = n.new('GeometryNodeJoinGeometry')
    l.new(group_in.outputs['Geometry'], distribute.inputs['Mesh'])
    l.new(group_in.outputs['Density'], distribute.inputs['Density'])
    l.new(group_in.outputs['Seed'], distribute.inputs['Seed'])
    l.new(distribute.outputs['Points'], instance.inputs['Points'])
    l.new(rock.outputs['Mesh'], instance.inputs['Instance'])
    l.new(group_in.outputs['Geometry'], join.inputs['Geometry'])
    l.new(instance.outputs['Instances'], join.inputs['Geometry'])
    l.new(join.outputs['Geometry'], group_out.inputs['Geometry'])
    assert all(link.is_valid for link in l)
    return tree

tree = build_scatter()
tree = build_scatter()                      # idempotent: no duplicate tree or sockets on rerun
assert len([g for g in bpy.data.node_groups if g.name.startswith('GN-scatter')]) == 1
sockets = lambda side: [i.name for i in tree.interface.items_tree if i.in_out == side]
assert sockets('INPUT') == ['Geometry', 'Density', 'Seed'] and sockets('OUTPUT') == ['Geometry']

bpy.ops.mesh.primitive_plane_add(size=4); ground = bpy.context.object   # 16 square metres
mod = ground.modifiers.new('scatter', 'NODES'); mod.node_group = tree
ident = {i.name: i.identifier for i in tree.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}
def set_input(modifier, identifier, value):
    """By identifier, never by display name or a guessed Socket_N; 5.2 moved inputs under modifier.properties."""
    if hasattr(modifier, 'properties'):
        getattr(modifier.properties.inputs, identifier).value = value
    else:
        modifier[identifier] = value

set_input(mod, ident['Density'], 25.0)
set_input(mod, ident['Seed'], 42)
ground.update_tag()

def instance_count():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    geometry = ground.evaluated_get(depsgraph).evaluated_geometry()
    return len(geometry.instances_pointcloud().points) if geometry.instances_pointcloud() else 0

count = instance_count()
assert 300 < count < 500, count             # density x area = 400, random distribution
# The evaluated mesh ignores instances: only the plane's 4 vertices are there.
depsgraph = bpy.context.evaluated_depsgraph_get()
assert len(ground.evaluated_get(depsgraph).to_mesh().vertices) == 4
ground.evaluated_get(depsgraph).to_mesh_clear()
# Rotating the object must not change a surface scatter's count.
ground.rotation_euler.x = 1.5708; ground.update_tag()
assert instance_count() == count

# Zones are pairs: pair the input with the output and add items on the output.
repeat_in, repeat_out = tree.nodes.new('GeometryNodeRepeatInput'), tree.nodes.new('GeometryNodeRepeatOutput')
assert repeat_in.pair_with_output(repeat_out)
repeat_out.repeat_items.new('FLOAT', 'Height')
assert 'Height' in [s.name for s in repeat_in.outputs]
sim_in, sim_out = tree.nodes.new('GeometryNodeSimulationInput'), tree.nodes.new('GeometryNodeSimulationOutput')
assert sim_in.pair_with_output(sim_out)
sim_out.state_items.new('VECTOR', 'Velocity')
```
