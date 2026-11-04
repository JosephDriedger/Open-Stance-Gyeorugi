"""Render a built traditional-dobok fighter at stance and the front-kick peak with the scene's camera setup and renderer
(Blender cloth off), full body, orthographic. Replaces earlier renders in the folder.

    blender.exe -b <Kind>/Candidate.blend -P review_traditional_dobok.py -- <out folder>
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from audit_sparring_styles import render

out = Path(sys.argv[sys.argv.index('--') + 1])
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
rig.update_tag()
for frame, name in ((1, 'Stance'), (30, 'KickPeak')):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    eye = (1.2, -3.4, 1.1) if name == 'Stance' else (3.0, -2.2, 1.1)
    (out / (name + '.png')).unlink(missing_ok=True)  # the shared helper skips existing files
    render(scene, rig, scale, out, name, eye, (0, 0, .9), 2.2, 700, 900)
print('REVIEW DONE', out, flush=True)
