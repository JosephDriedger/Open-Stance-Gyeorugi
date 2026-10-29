import bpy,sys,time,json,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import repair_garment_openings as fix
import audit_fighter_range as audit
import rebuild_updated_characters as build
OUT=fix.OUT
try:
 rows=[]
 for kind in ['Medium','Stocky','Female_Strong']:
  d=OUT/kind;deadline=time.monotonic()+3600
  while not (d/'Gameplay_High_validation.json').exists():
   if time.monotonic()>deadline:raise RuntimeError('Missing '+kind)
   time.sleep(5)
  bpy.ops.wm.open_mainfile(filepath=str(d/'Gameplay_High.blend'));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
  r.animation_data.action=None
  for tr in r.animation_data.nla_tracks:tr.mute=True
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  s.cycles.samples=16;s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100
  for style in [0,1]:
   r['JacketStyle']=style;build.refresh(r)
   for pose in ['Wrists_Flexed','Wrists_Extended','Ankle_Flexed','Ankle_Extended']:
    audit.pose(r,pose,scale);bpy.context.view_layer.update()
    wrist=pose.startswith('Wrists');center=r.matrix_world@r.pose.bones['hand_l' if wrist else 'foot_l'].head
    target=center+Vector((0,0,0 if wrist else .06))*scale
    build.view.camera(s,tuple(target+Vector((.30,-.5,.08))*scale),tuple(target),(.38 if wrist else .48)*scale)
    path=d/f'Close_{style}_{pose}.png';s.render.filepath=str(path);bpy.ops.render.render(write_still=True);rows.append(str(path.relative_to(OUT)))
 (OUT/'closeup_validation.json').write_text(json.dumps({'rendered':rows},indent=2))
except:(OUT/'closeup_error.log').write_text(traceback.format_exc());raise
