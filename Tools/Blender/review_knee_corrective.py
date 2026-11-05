"""Reports how far each knee corrective moves the trousers and renders the knee transition frames.

    blender.exe -b <Candidate.blend> -P review_knee_corrective.py -- <out folder> [r] <frame> [<frame> ...]

With `r` the left leg's pose is copied onto the right bones, to review the right knee (the animation only bends the left).
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from audit_sparring_styles import render

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
MIRROR = args[1:2] == ['r']
frames = [int(a) for a in args[2 if MIRROR else 1:]]
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Stocky']
pants = bpy.data.objects['Pants']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
for modifier in pants.modifiers:
    if modifier.type != 'ARMATURE':
        modifier.show_viewport = False
        modifier.show_render = False

keys = pants.data.shape_keys.key_blocks
basis = keys['Basis']
report = {}
for key in keys:
    if key.name == 'Basis' or 'Knee' not in key.name:
        continue
    offsets = [(a.co - b.co).length for a, b in zip(key.data, basis.data)]
    report[key.name] = {'moved_vertices': sum(o > 1e-6 for o in offsets),
                        'max_offset_mm': round(max(offsets) * 1000, 2),
                        'mean_moved_offset_mm': round(1000 * sum(o for o in offsets if o > 1e-6) / max(1, sum(o > 1e-6 for o in offsets)), 2)}
(out / 'corrective_offsets.json').write_text(json.dumps(report, indent=1))
print('OFFSETS', json.dumps(report), flush=True)

for frame in frames:
    scene.frame_set(frame)
    if MIRROR:
        # Rendering re-applies the action, so detach it and hold the copied pose by hand.
        pose = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
        for name in list(pose):
            if name.endswith('_l') and name[:-1] + 'r' in pose:
                pose[name[:-1] + 'r'] = pose[name]
        action = rig.animation_data.action
        rig.animation_data.action = None
        for name, matrix in pose.items():
            rig.pose.bones[name].matrix_basis = matrix
    bpy.context.view_layer.update()
    render(scene, rig, scale, out, 'Side_%d' % frame, (4, -.8, 1.65), (0, -.25, .95), 2.25, 480, 600)
    render(scene, rig, scale, out, 'Back_%d' % frame, (-1.2, 2.6, 1.0), (0, -.25, .75), 1.8, 480, 600)
    if MIRROR:
        rig.animation_data.action = action
print('REVIEW DONE', flush=True)
