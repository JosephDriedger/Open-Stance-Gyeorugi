"""Push trouser cloth back out of the leg after the cloth step, then render review poses.

    blender.exe -b <TrouserKneeRelax/Trouser_Test.blend> -P test_trouser_knee_shrinkwrap.py -- <out folder> <wrap type> <offset mm>

The Shrinkwrap runs after the cloth and the knee smoothing, so folds that sink into the leg are corrected without
changing the cloth setup. Re-run check_trouser_leg_clearance.py on the saved file for the numbers.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from audit_sparring_styles import render

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
wrap_type = args[1] if len(args) > 1 else 'OUTSIDE_SURFACE'
offset = float(args[2]) / 1000 if len(args) > 2 else 0.004
out.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
pants = bpy.data.objects['Pants']
rig = bpy.data.objects['RIG_Body_Stocky']
body = bpy.data.objects['Body']
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578

# The body as the pants see it: same pose, but without the coverage mask that hides skin under clothing.
leg_surface = body.copy()
leg_surface.data = body.data.copy()
leg_surface.name = 'SIM_leg_surface'
scene.collection.objects.link(leg_surface)
for modifier in list(leg_surface.modifiers):
    if modifier.type == 'MASK':
        leg_surface.modifiers.remove(modifier)
leg_surface.hide_render = True
leg_surface.hide_viewport = True

wrap = pants.modifiers.new('Keep fabric outside the leg', 'SHRINKWRAP')
wrap.target = leg_surface
wrap.wrap_method = 'NEAREST_SURFACEPOINT'
wrap.wrap_mode = wrap_type
wrap.offset = offset
wrap.use_negative_direction = True
wrap.use_positive_direction = True
smooth = pants.modifiers.get('Relax compressed knee folds')
if smooth is not None:
    # Smooth once more after the correction so the push-out does not leave a hard ridge.
    again = pants.modifiers.new('Relax after leg clearance', 'CORRECTIVE_SMOOTH')
    again.vertex_group = smooth.vertex_group
    again.use_only_smooth = True
    again.smooth_type = 'LENGTH_WEIGHTED'
    again.factor = 0.5
    again.iterations = 4

bpy.context.preferences.filepaths.save_version = 0
scene.frame_set(scene.frame_start)
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    bpy.context.evaluated_depsgraph_get().update()
    if frame in (86, 95, 101, 110, 120, 144):
        render(scene, rig, scale, out, 'Review_' + str(frame), (4, -.8, 1.65), (0, -.25, .95), 2.25, 480, 600)
        render(scene, rig, scale, out, 'Back_' + str(frame), (-1.2, 2.6, 1.0), (0, -.25, .75), 1.8, 480, 600)
scene.frame_set(scene.frame_start)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Trouser_Test.blend'), compress=True)
print('SHRINKWRAP DONE', wrap_type, offset, flush=True)
