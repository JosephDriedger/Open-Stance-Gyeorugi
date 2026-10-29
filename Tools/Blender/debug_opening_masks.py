import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_fighter_range as audit
import rebuild_updated_characters as build
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/OpeningRepair')
bpy.ops.wm.open_mainfile(filepath=str(out/'Medium/Gameplay_High.blend'))
r=bpy.data.objects['RIG_Body_Medium'];s=bpy.context.scene;r.animation_data.action=None
for tr in r.animation_data.nla_tracks:tr.mute=True
for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
build.refresh(r);audit.pose(r,'Wrists_Flexed',1)
o=bpy.data.objects['Body'];rows=[]
for m in o.modifiers:
 if m.type=='MASK':
  rows.append({'name':m.name,'visible':m.show_render,'group':m.vertex_group,'smooth':m.use_smooth})
  if o.animation_data:
   for d in list(o.animation_data.drivers):
    if m.name in d.data_path:o.driver_remove(d.data_path)
  m.show_render=m.name=='Coverage_Jacket';m.show_viewport=m.show_render;m.use_smooth=False
(out/'mask_debug.json').write_text(json.dumps(rows,indent=2))
w=r.matrix_world@r.pose.bones['hand_l'].head
build.view.camera(s,tuple(w+Vector((.30,-.5,.08))),tuple(w),.38)
s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100;s.cycles.samples=12
s.render.filepath=str(out/'Debug_JacketOnly.png');bpy.ops.render.render(write_still=True)
