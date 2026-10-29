"""Install selectable facially skinned eyebrow styles into existing preview files."""
import bpy,sys,json,shutil,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import build_character_variations as lib
OUT=lib.OUT
def log(s):
 with (OUT/'eyebrow_styles.log').open('a') as f:f.write(s+'\n')
def refresh(rig):
 rig.update_tag();bpy.context.scene.frame_set(2);bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
def run(name):
 path=OUT/name/'Character.blend';backup=lib.base.ROOT/'Resources/Models/Archive/Before_Eyebrow_Styles'/name/'Character.blend'
 backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(path,backup)
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));head=bpy.data.objects['Head']
 mat=next(o for o in bpy.data.objects if o.name.startswith('Hair_') and len(o.data.materials)).data.materials[0]
 lib.add_eyebrow_styles(head,mat,rig,name.startswith('Male'))
 bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'));scene=bpy.context.scene
 brows=[bpy.data.objects['Eyebrows_'+s] for s in lib.EYEBROW_STYLES];checks=[]
 for index,o in enumerate(brows):
  rig['EyebrowStyle']=index;refresh(rig)
  assert [not b.hide_render for b in brows]==[i==index for i in range(6)]
  assert [not b.hide_viewport for b in brows]==[i==index for i in range(6)]
  assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in o.data.vertices)
  deform=next(m.object for m in o.modifiers if m.type=='ARMATURE');totals={}
  for v in o.data.vertices:
   for g in v.groups:
    n=o.vertex_groups[g.group].name
    if n.startswith('FACIAL_') and n in deform.pose.bones:totals[n]=totals.get(n,0)+g.weight
  bone=deform.pose.bones[max(totals,key=totals.get)];original=bone.location.copy()
  def points():return [v.co.copy() for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
  before=points();bone.location+=Vector((.002/max(abs(deform.matrix_world.to_scale().x),1e-6),0,0));bpy.context.view_layer.update()
  delta=max((a-b).length for a,b in zip(points(),before));bone.location=original;bpy.context.view_layer.update();assert delta>.00001
  checks.append({'style':lib.EYEBROW_STYLES[index],'fibers':o['FiberCount'],'visibility_passed':True,'weights_passed':True,'facial_movement_meters':delta})
  if name=='Female_Athletic':
   lib.base.camera(scene,(0,-1,1.69),(0,-.065,1.655),.15);scene.render.resolution_x=900;scene.render.resolution_y=440;scene.render.resolution_percentage=100
   scene.render.filepath=str(OUT/('Eyebrow_Style_'+lib.EYEBROW_STYLES[index]+'.png'));bpy.ops.render.render(write_still=True)
 rig['Wear_Eyebrows']=False;refresh(rig);assert all(o.hide_render and o.hide_viewport for o in brows)
 rig['Wear_Eyebrows']=True;rig['EyebrowStyle']=0;refresh(rig)
 (OUT/name/'eyebrow_styles_validation.json').write_text(json.dumps({'preset':name,'saved_file_reopened':True,'none_toggle_passed':True,'styles':checks},indent=2))
 log('COMPLETE '+name)
if __name__=='__main__':
 try:
  for preset in lib.PRESETS:run(preset[0])
 except:log(traceback.format_exc());raise
