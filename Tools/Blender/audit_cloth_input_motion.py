"""Separate animation input movement from cloth-generated movement."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
bpy.ops.wm.open_mainfile(filepath=str(root/'KnotBeltPresets/Medium/Candidate.blend'))
s=bpy.context.scene
def clone(name,label):
    source=bpy.data.objects[name];o=source.copy();o.data=source.data.copy();o.name=label;s.collection.objects.link(o)
    o.animation_data_clear();o.hide_viewport=False;o.hide_render=True;o.hide_set(False)
    for m in list(o.modifiers):
        if m.type in ['CLOTH','COLLISION','SOLIDIFY']:o.modifiers.remove(m)
    return o.name
names=['Pants','SIM_Shared_Belt_Tails',clone('Pants','AUDIT_Kinematic_Pants'),clone('SIM_Shared_Belt_Tails','AUDIT_Belt_Input')]
previous={};rows=[]
for frame in range(1,289):
    s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
    for name in names:
        o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh();pts=[o.matrix_world@v.co for v in me.vertices];ev.to_mesh_clear()
        speed=max((a-b).length for a,b in zip(pts,previous[name]))*s.render.fps/s.render.fps_base if name in previous else 0
        if frame in [72,144,216,288]:rows.append({'frame':frame,'object':name,'maximum_speed_m_per_s':speed})
        previous[name]=pts
(root/'cloth_input_motion.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
