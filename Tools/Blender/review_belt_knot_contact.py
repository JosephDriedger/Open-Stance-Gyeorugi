"""Inspect the one remaining root contact at its actual animated frame."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/ClearanceBeltPresets/Medium'
bpy.ops.wm.open_mainfile(filepath=str(out/'Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];s.cycles.samples=24
for frame in range(1,21):
    s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
    for name in ['Belt_Tail_Left','Belt_Tail_Right','Pants']:
        ev=bpy.data.objects[name].evaluated_get(deps);ev.to_mesh();ev.to_mesh_clear()
for label,pos in [('Contact_Front',(-.1,-3,1.1)),('Contact_Side',(-3,-1,1.1))]:
    a.render(s,r,1,out,label,pos,(-.11,-.14,.94),.42,600,600)
