import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Resources/Models/FinalRefinement'
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_LinearBelt/Candidate.blend'))
s=bpy.context.scene;s.frame_set(1);deps=bpy.context.evaluated_depsgraph_get();rows=[]
for o in s.objects:
    if o.type!='MESH' or not any(x in o.name.lower() for x in ['belt','knot']):continue
    ev=o.evaluated_get(deps);me=ev.to_mesh();pts=[o.matrix_world@v.co for v in me.vertices]
    if pts:rows.append({'name':o.name,'bounds':[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)]})
    ev.to_mesh_clear()
(root/'belt_attachment_audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
