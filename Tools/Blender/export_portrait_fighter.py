"""Export a menu portrait fighter (prepare_portrait_fighter.py, then build_traditional_dobok.py --upto=5) for Unreal.

    blender.exe -b <Portrait/<Kind>_<Sex>/Candidate.blend> -P export_portrait_fighter.py -- <out.fbx>

Body, head, hair, eyebrows and the dobok with its belt; no sparring gear and no animation. The belt tails' Solidify is
baked into the mesh first (single-sided strips are back-face culled in Unreal, see add_belt_chain_layer.py). The
armature is exported as `root` for import onto the production fighter skeleton, which the placeholder clips use.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import rebuild_updated_characters as build

out = Path(sys.argv[sys.argv.index('--') + 1])
out.parent.mkdir(parents=True, exist_ok=True)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
for key in ('Wear_Helmet', 'Wear_Protector', 'Wear_Gloves', 'Wear_FootGuards'):
    rig[key] = False
rig['BlenderCloth'] = False
build.refresh(rig)
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    tail = bpy.data.objects.get(name)
    solidify = next((m for m in tail.modifiers if m.type == 'SOLIDIFY'), None) if tail else None
    if solidify is not None:
        with bpy.context.temp_override(object=tail, active_object=tail):
            bpy.ops.object.modifier_apply(modifier=solidify.name)
# The jacket is one garment: its lower part (built as Jacket_Skirt so the game can simulate it as cloth) joins the
# jacket body here, where nothing simulates it.
jacket, skirt = bpy.data.objects.get('Jacket'), bpy.data.objects.get('Jacket_Skirt')
if jacket and skirt:
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (jacket, skirt))
    bpy.context.view_layer.objects.active = jacket
    with bpy.context.temp_override(active_object=jacket, selected_editable_objects=[jacket, skirt]):
        bpy.ops.object.join()
# The belt tails hang from the knot: skinned partly to the thighs they swung out sideways in the stance. With no chain
# physics here, they follow the pelvis alone.
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    tail = bpy.data.objects.get(name)
    if tail is None:
        continue
    tail.vertex_groups.clear()
    group = tail.vertex_groups.new(name='pelvis')
    group.add([v.index for v in tail.data.vertices], 1.0, 'REPLACE')
rig.data.pose_position = pose_position
rig.name = 'root'
build.export(rig, out, False)
print('PORTRAIT EXPORTED', out, [o.name for o in build.meshes() if not o.hide_render], flush=True)
