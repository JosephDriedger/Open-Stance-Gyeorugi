"""Renders the key phases of every placeholder technique for review: the start, half way through startup, the strike
fully out, half way through recovery. Side view (the opponent is off to the left) and a three-quarter view, Workbench.

    blender.exe -b <PlaceholderTechniques.blend> -P render_placeholder_review.py -- <out folder>

Writes <out folder>/<Technique>_<phase>_<view>.png and, if Pillow is importable, one contact sheet per view.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(sys.argv[sys.argv.index('--') + 1])
OUT.mkdir(parents=True, exist_ok=True)
FPS = 30
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
made = json.loads((Path(bpy.data.filepath).parent / 'techniques.json').read_text())

scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.render.resolution_x, scene.render.resolution_y = 420, 520
scene.render.film_transparent = False
scene.world = scene.world or bpy.data.worlds.new('Review')

camera_data = bpy.data.cameras.new('ReviewCamera')
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 2.6
camera = bpy.data.objects.new('ReviewCamera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera

VIEWS = {
    # The fighter faces -Y; from +X the opponent is on the left, as on a broadcast.
    'side': (Vector((5.0, -0.35, 1.0)), Vector((0.0, -0.35, 0.95))),
    'front': (Vector((3.0, -4.0, 1.4)), Vector((0.0, -0.3, 0.95))),
}


def aim(eye, target):
    camera.location = eye
    camera.rotation_euler = (target - eye).to_track_quat('-Z', 'Y').to_euler()


def phase_frames(info):
    s, a, rec = info['startup_s'], info['active_s'], info['recovery_s']
    named = {'start': 0, 'chamber': s / 2, 'strike': s, 'rechamber': s + a + rec / 2}
    return {k: 1 + round(v * FPS) for k, v in named.items()}


done = []
for name, info in made.items():
    if name.endswith('_Mirror') or 'startup_s' not in info:
        continue
    rig.animation_data.action = bpy.data.actions[info['action']]
    for phase, frame in phase_frames(info).items():
        scene.frame_set(frame)
        for view, (eye, target) in VIEWS.items():
            aim(eye, target)
            path = OUT / f'{name}_{phase}_{view}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            done.append(path)

try:
    from PIL import Image, ImageDraw
    names = [n for n, i in made.items() if not n.endswith('_Mirror') and 'startup_s' in i]
    phases = ['start', 'chamber', 'strike', 'rechamber']
    for view in VIEWS:
        w, h = scene.render.resolution_x // 2, scene.render.resolution_y // 2
        sheet = Image.new('RGB', (w * len(phases), h * len(names)), 'white')
        for row, name in enumerate(names):
            for col, phase in enumerate(phases):
                image = Image.open(OUT / f'{name}_{phase}_{view}.png').convert('RGB').resize((w, h))
                sheet.paste(image, (col * w, row * h))
                ImageDraw.Draw(sheet).text((col * w + 4, row * h + 4), f'{name} {phase}', fill='black')
        sheet.save(OUT / f'sheet_{view}.png')
except ImportError:
    pass
print('PLACEHOLDER REVIEW DONE', len(done), flush=True)
