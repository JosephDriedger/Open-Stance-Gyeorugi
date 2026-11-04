"""Layer 10 of the traditional dobok: hang the belt tails on bone chains so the engine's physics can swing them.

Engine cloth only collides with body capsules, never with another garment, so cloth tails sank behind the jacket skirt or
slid into the gap between the legs. A chain of bones per tail (belt_l_01..08, belt_r_01..08 under the pelvis, the tails
skinned to them; Tools/Blender/belt_bone_chain.py) is driven in Unreal by a physics asset whose kinematic leg capsules
the links collide with, so a rising knee and thigh push the tails up while the band and knot stay cinched.

    blender.exe -b <Candidate.blend> -P add_belt_chain_layer.py -- <out folder>
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import belt_bone_chain as chain

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
rig = chain.rig_object()
if any(b.name.startswith('belt_') for b in rig.data.bones):
    raise RuntimeError('the rig already has belt chain bones')
rig.hide_viewport = False
rig.hide_set(False)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
points = chain.convert()
# The tails are single-sided strips whose faces point at the body; their thickness came from a Solidify modifier, which
# the export copies dropped, so in Unreal the strips were back-face culled from the front and vanished. Bake the
# thickness into the mesh (both faces and the rims), so no export path can lose it.
for name in ('Belt_Tail_Left', 'Belt_Tail_Right'):
    tail = bpy.data.objects[name]
    solidify = next((m for m in tail.modifiers if m.type == 'SOLIDIFY'), None)
    if solidify is None:
        continue
    with bpy.context.temp_override(object=tail, active_object=tail):
        bpy.ops.object.modifier_apply(modifier=solidify.name)
rig.data.pose_position = pose_position
report = {side: {'links': len(pts) - 1, 'top_z': round(pts[0][2], 3), 'tip_z': round(pts[-1][2], 3)} for side, pts in points.items()}
print('BELT CHAIN DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'belt_chain_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
