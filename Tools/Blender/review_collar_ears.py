import bpy,sys,json,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_collar_ears as fix
import audit_sparring_styles as a
OUT=fix.OUT
try:
 rows=[]
 for kind in a.build.PRESETS:
  for level in ['Gameplay_High','Gameplay_Mid','Gameplay_Far','Preview']:
   check=OUT/kind/(level+'_validation.json')
   while not check.exists():time.sleep(5)
   report=json.loads(check.read_text());bpy.ops.wm.open_mainfile(filepath=str(OUT/kind/report['file']))
   s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];assert s['CollarEarRepair']=='2026-10-20'
   r.animation_data_create();r.animation_data.action=None
   for tr in r.animation_data.nla_tracks:tr.mute=True
   for o in s.objects:
    if o.get('MarkerLabel'):o.hide_render=True
   z=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;s.cycles.samples=12
   d=OUT/'QA'/kind;d.mkdir(parents=True,exist_ok=True)
   a.audit.pose(r,'Neutral',z);r['HairStyle']=0
   if level in ['Gameplay_High','Preview']:
    for j in range(2):
     r['JacketStyle']=j;r['Wear_Helmet']=False;r['Wear_Protector']=False;a.build.refresh(r)
     for pose in ['Neutral','Arms_Overhead']:
      a.audit.pose(r,pose,z)
      a.render(s,r,z,d,f'{level}_J{j}_{pose}',(.5,.8,1.83),(0,0,1.47),.46,480,480)
   a.audit.pose(r,'Neutral',z);r['Wear_Helmet']=True;r['Wear_Protector']=True
   for helmet in range(3):
    r['HelmetDesign']=helmet;a.build.refresh(r)
    a.render(s,r,z,d,f'{level}_H{helmet}',(.9,.25,1.72),(0,0,1.65),.44,480,480)
   rows.append({'preset':kind,'level':level,'scene_revision_checked':True})
  with (OUT/'qa.log').open('a') as f:f.write(kind+' COMPLETE\n')
 (OUT/'qa_completed.json').write_text(json.dumps(rows,indent=2))
except:(OUT/'qa_error.log').write_text(traceback.format_exc());raise
