"""Read identities without modifying native datablocks."""
import bpy


def inventory(scene=None):
    scene = scene or bpy.context.scene
    active = set(scene.objects)
    used_materials = {slot.material for o in active for slot in o.material_slots if slot.material}
    material_users = bpy.data.user_map(subset=list(bpy.data.materials))

    def scoped_object(obj):
        return obj in active and set(obj.users_scene) == {scene}

    def outside_material_users(mat):
        outside = []
        for user in material_users.get(mat, set()):
            if isinstance(user, bpy.types.Object):
                allowed = scoped_object(user)
            elif hasattr(user, 'materials'):
                owners = [o for o in bpy.data.objects if o.data == user]
                allowed = bool(owners) and all(scoped_object(o) for o in owners)
            else:
                # Node groups and other indirect users need a deliberate ownership decision.
                allowed = False
            if not allowed:
                outside.append(type(user).__name__ + ':' + user.name_full)
        return sorted(outside)

    def properties(item, names):
        # Preserve invalid types as diagnostics without serializing arbitrary IDProperty groups.
        return {p: item[p] if isinstance(item[p], str) else {'invalid_type': type(item[p]).__name__}
                for p in names if p in item}

    def base(item, scope, props):
        return {'name': item.name_full, 'scope': scope, 'properties': properties(item, props),
                'read_only': bool(item.library or item.override_library)}

    objects = []
    for obj in sorted(bpy.data.objects, key=lambda o: o.name_full):
        record = base(obj, obj in active, ('dcc_instance_id', 'dcc_asset_id'))
        record.update(type=obj.type, mesh=obj.data.name_full if obj.type == 'MESH' else None,
                      scenes=sorted(s.name for s in obj.users_scene))
        objects.append(record)
    materials = []
    for mat in sorted(bpy.data.materials, key=lambda m: m.name_full):
        record = base(mat, mat in used_materials, ('dcc_material_id',))
        record['outside_users'] = outside_material_users(mat)
        materials.append(record)
    instanced = {o.instance_collection for o in active if o.instance_type == 'COLLECTION' and o.instance_collection}
    collections = [base(c, c in instanced, ('dcc_asset_id',)) for c in sorted(bpy.data.collections, key=lambda c: c.name_full)]
    return {'scene': scene.name, 'objects': objects, 'materials': materials, 'collections': collections}
