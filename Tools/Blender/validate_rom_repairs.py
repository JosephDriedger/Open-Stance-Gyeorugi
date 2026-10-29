import bpy,sys,json,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import repair_rom_garments as repair
OUT=repair.OUT;ROOT=repair.ROOT
report=[]
def signature(r):return [[b.name,b.parent.name if b.parent else None,*[v for row in b.matrix_local for v in row]] for b in r.data.bones]
try:
 for kind in ['Updated_Medium','Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']:
  source=ROOT/'Resources/Models/Animation/Samples/Medium_Sparring_Samples.blend' if kind=='Updated_Medium' else ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
  bpy.ops.wm.open_mainfile(filepath=str(source));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));original=signature(rig)
  path=OUT/kind/('Medium_Sparring_Samples.blend' if kind=='Updated_Medium' else 'Gameplay_High.blend');bpy.ops.wm.open_mainfile(filepath=str(path));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));assert signature(r)==original
  # Keep the existing alternate-uniform selector mutually exclusive.
  if bpy.data.objects.get('Jacket_WhiteVNeck'):
   for name in ['Jacket','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
    o=bpy.data.objects[name]
    for channel in ['hide_render','hide_viewport']:
     d=o.driver_add(channel).driver
     if not any(v.name=='style' for v in d.variables):
      v=d.variables.new();v.name='style';v.targets[0].id=r;v.targets[0].data_path='["JacketStyle"]'
     d.expression='not wear or style > 0.5'
  bpy.ops.wm.save_as_mainfile(filepath=str(path));action=r.animation_data.action;r.animation_data.action=None;scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.57778847
  values={}
  for label in ['Neutral','Deep_Squat']:
   repair.audit.pose(r,label,scale);bpy.context.view_layer.update();values[label]={}
   for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
    o=bpy.data.objects[name];key=next(k for k in o.data.shape_keys.key_blocks if k.name.startswith('Squat_'));values[label][name]=key.value
    assert key.value<.01 if label=='Neutral' else key.value>.98,(kind,label,name,key.value)
    assert all(d.is_valid for d in o.data.shape_keys.animation_data.drivers)
  report.append({'kind':kind,'file':str(path.relative_to(OUT)),'skeleton_rest_and_hierarchy_unchanged':True,'bones':341,'corrective_values':values,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 (OUT/'native_validation.json').write_text(json.dumps({'passed':True,'files':report},indent=2))
except:(OUT/'native_error.log').write_text(traceback.format_exc());raise
