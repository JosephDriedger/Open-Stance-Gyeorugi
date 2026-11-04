"""Renders the lower jacket and hip at chosen frames with the cloth simulation off (the skinned pose the game would show).

    blender.exe -b <Candidate.blend> -P review_jacket_hip.py -- <out folder> <frame> [<frame> ...]
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
rig = bpy.data.objects['RIG_Body_Stocky']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
for obj in scene.objects:
    for modifier in obj.modifiers:
        if modifier.type == 'CLOTH':
            modifier.show_viewport = False
            modifier.show_render = False
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    render(scene, rig, scale, out, 'Hip_Side_%d' % frame, (2, -.7, 1.25), (0, -.1, .95), .85, 800, 800)
    render(scene, rig, scale, out, 'Hip_Front_%d' % frame, (.6, -2.5, 1.2), (0, -.1, .95), .85, 800, 800)
    render(scene, rig, scale, out, 'Hip_Back_%d' % frame, (-1.2, 2.5, 1.2), (0, -.1, .95), .85, 800, 800)
print('REVIEW DONE', flush=True)
