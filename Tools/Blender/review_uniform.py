"""Renders the whole fighter at chosen frames with the Blender cloth off (the skinned pose the game starts from).

    blender.exe -b <Candidate.blend> -P review_uniform.py -- <out folder> <frame> [<frame> ...]
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from audit_sparring_styles import render

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
frames = [int(a) for a in args[1:]]
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
for obj in scene.objects:
    for modifier in obj.modifiers:
        if modifier.type == 'CLOTH':
            for prop in ('show_viewport', 'show_render'):
                modifier.driver_remove(prop)
            modifier.show_viewport = modifier.show_render = False
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    render(scene, rig, scale, out, 'Front_%d' % frame, (.4, -4.2, 1.0), (0, 0, .85), .85, 600, 900)
    render(scene, rig, scale, out, 'Side_%d' % frame, (4.2, -.4, 1.0), (0, 0, .85), .85, 600, 900)
print('REVIEW DONE', flush=True)
