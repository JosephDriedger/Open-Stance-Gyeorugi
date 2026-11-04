from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).parent))
from audit_sparring_styles import render

scene = bpy.context.scene
pants = bpy.data.objects['Pants']
rig = bpy.data.objects['RIG_Body_Stocky']
out = Path(bpy.path.abspath('//')).parent / 'TrouserKneeRelax'
out.mkdir(exist_ok=True)
scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z / 1.578
cloth = next(mod for mod in pants.modifiers if mod.type == 'CLOTH')
def picture(frame, label):
    render(scene, rig, scale, out, label, (4,-.8,1.65), (0,-.25,.95), 2.25, 480, 600)

cloth.show_viewport = cloth.show_render = False
scene.frame_set(110)
picture(110, 'Armature_110')
scene.frame_set(1)
cloth.show_viewport = cloth.show_render = True
group = pants.vertex_groups.new(name='Knee fabric smoothing')
knees = [rig.matrix_world @ rig.data.bones['calf_'+side].head_local for side in ('l','r')]
for vertex in pants.data.vertices:
    pos = pants.matrix_world @ vertex.co
    distance = min((pos-knee).length for knee in knees)
    weight = max(0, min(1, (.22-distance)/.10))
    if weight:
        group.add([vertex.index], weight*weight*(3-2*weight), 'REPLACE')
smooth = pants.modifiers.new('Relax compressed knee folds', 'CORRECTIVE_SMOOTH')
smooth.vertex_group = group.name
smooth.use_only_smooth = True
smooth.smooth_type = 'LENGTH_WEIGHTED'
smooth.factor = .75
smooth.iterations = 8
pants.modifiers.move(len(pants.modifiers)-1, pants.modifiers.find(cloth.name)+1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Trouser_Test.blend'), compress=True)
for frame in range(1, scene.frame_end+1):
    scene.frame_set(frame)
    bpy.context.evaluated_depsgraph_get().update()
    if frame in (86,95,110,144,scene.frame_end):
        picture(frame, 'Review_'+str(frame))
