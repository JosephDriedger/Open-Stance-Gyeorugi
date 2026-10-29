import bpy,sys,time,json,traceback,runpy,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import repair_collar_ears as fix
import rebuild_updated_characters as build
OUT=fix.OUT
try:
 rows=[]
 for kind in build.PRESETS:
  d=OUT/kind
  while not (d/'Gameplay_High_validation.json').exists():time.sleep(5)
  for gear in [False,True]:
   bpy.ops.wm.open_mainfile(filepath=str(d/'Gameplay_High.blend'));r=bpy.data.objects['RIG_Body_'+kind]
   r.animation_data_create();r.animation_data.action=None
   for tr in r.animation_data.nla_tracks:tr.mute=True
   r['HairStyle']=5;r['Wear_Hair']=True
   for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=gear
   build.refresh(r);name='CompactBun_'+('Sparring' if gear else 'Dobok')+'.fbx';path=d/name;build.export(r,path)
   bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path))
   rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
   core=next(o for o in bpy.context.scene.objects if o.name.split('.')[0]=='Hair_Compact_Bun__Coiled_Bun_Core')
   assert all(len(v.groups)>0 and abs(sum(g.weight for g in v.groups)-1)<.002 for v in core.data.vertices)
   rows.append({'file':str(path.relative_to(OUT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'passed':True})
 (OUT/'exports_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))

except:(OUT/'bun_export_error.log').write_text(traceback.format_exc());raise
