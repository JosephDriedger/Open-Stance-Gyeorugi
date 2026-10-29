import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_crew_surface_finish as f
for kind in f.f.review.build.PRESETS:
 bpy.ops.wm.open_mainfile(filepath=str(f.f.ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'));o=bpy.data.objects['Head'];uv=o.data.uv_layers['DiffuseUV'];r=bpy.data.objects['RIG_Body_'+kind];scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;o.data.calc_loop_triangles();rows=[]
 for t in o.data.loop_triangles:
  pts=[o.matrix_world@o.data.vertices[i].co for i in t.vertices]
  if min(v.z for v in pts)>1.69*scale and t.material_index==0:rows.append({'points':[list(v) for v in pts],'uv':[list(uv.data[i].uv) for i in t.loops]})
 (f.OUT/(kind+'_CrownUV.json')).write_text(json.dumps(rows))
