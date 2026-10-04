"""Replace only the four preview presets' eyebrows, preserving existing assets."""
import bpy,sys,json,shutil,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import build_character_variations as lib
from mathutils import Vector

OUT=lib.OUT
LOG=OUT/'eyebrow_refinement.log'
def log(message):
 with LOG.open('a') as handle:handle.write(message+'\n')

def run(name):
 path=OUT/name/'Character.blend'
 backup=lib.base.ROOT/'Resources/Models/Archive/Before_Eyebrow_Refinement'/name/'Character.blend'
 backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(path,backup)
 bpy.ops.wm.open_mainfile(filepath=str(path))
 scene=bpy.context.scene;head=bpy.data.objects['Head'];rig=bpy.data.objects['RIG_Body_Medium']
 old=[o for o in bpy.data.objects if o.type=='MESH' and 'eyebrow' in o.name.lower()]
 mat=next(o for o in bpy.data.objects if o.name.startswith('Hair_') and len(o.data.materials)).data.materials[0]
 collections=list(old[0].users_collection) if old else []
 for o in old:bpy.data.objects.remove(o,do_unlink=True)
 brow=lib.eyebrows(lib.Hair(head),mat,name.startswith('Male'));lib.bind_eyebrows(brow,head)
 if collections:
  for coll in list(brow.users_collection):coll.objects.unlink(brow)
  for coll in collections:coll.objects.link(brow)
 assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in brow.data.vertices)
 assert len([o for o in bpy.data.objects if o.type=='MESH' and 'eyebrow' in o.name.lower()])==1
 bpy.context.view_layer.update()
 deform=next(m.object for m in brow.modifiers if m.type=='ARMATURE');deform_name=deform.name
 used={brow.vertex_groups[g.group].name for v in brow.data.vertices for g in v.groups}
 totals={}
 for v in brow.data.vertices:
  for g in v.groups:
   n=brow.vertex_groups[g.group].name
   if n.startswith('FACIAL_') and n in deform.pose.bones:totals[n]=totals.get(n,0)+g.weight
 browbones=sorted(totals,key=totals.get,reverse=True)
 assert browbones,'Expected facial skin weights'
 bone=deform.pose.bones[browbones[0]];saved=bone.location.copy()
 hidden=deform.hide_viewport;hidden_set=deform.hide_get();deform.hide_viewport=False
 deform.hide_set(False);bpy.context.view_layer.update()
 def points():
  evaluated=brow.evaluated_get(bpy.context.evaluated_depsgraph_get())
  return [evaluated.matrix_world@v.co for v in evaluated.data.vertices]
 before=points();bone.location+=Vector((.002/max(abs(deform.matrix_world.to_scale().x),1e-6),0,0));bpy.context.view_layer.update();after=points()
 delta=max((a-b).length for a,b in zip(before,after));bone.location=saved;bpy.context.view_layer.update()
 log(f'{name}: tested {bone.name}, delta {delta}, deform enabled {bone.bone.use_deform}, previous rig visibility {hidden}')
 assert delta>.00001,'Facial brow bone did not move the eyebrow'
 deform.hide_viewport=hidden;deform.hide_set(hidden_set)
 lib.base.camera(scene,(.43,-1,1.77),(0,-.003,1.57),.52)
 scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
 bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(path));scene=bpy.context.scene
 scene.render.filepath=str(OUT/name/'Portrait.png');bpy.ops.render.render(write_still=True)
 lib.base.camera(scene,(0,-1,1.69),(0,-.065,1.635),.20)
 scene.render.resolution_x=1200;scene.render.resolution_y=850
 scene.render.filepath=str(OUT/name/'Eyebrows_Closeup.png');bpy.ops.render.render(write_still=True)
 lib.base.camera(scene,(.75,-2,1.50),(0,0,.91),2.06)
 scene.render.resolution_x=1000;scene.render.resolution_y=1100
 scene.render.filepath=str(OUT/name/'Full_Body.png');bpy.ops.render.render(write_still=True)
 report={'preset':name,'groom_version':2,'fibers':int(bpy.data.objects['Eyebrows']['FiberCount']),'facial_rig':deform_name, 'facial_bone_test':browbones[0], 'facial_movement_meters':delta,'normalized_weights':True,'saved_file_reopened':True}
 (OUT/name/'eyebrow_validation.json').write_text(json.dumps(report,indent=2));log('COMPLETE '+name)

if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
  for preset in lib.PRESETS:
   if not args or preset[0] in args:run(preset[0])
 except:log(traceback.format_exc());raise

