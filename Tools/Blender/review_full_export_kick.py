"""Bake the corrected dummy pose onto the staged full FBX rig for visual review."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT=review.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyFullKickReview';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardSmoothKickReview/Animation_Test.blend'))
s=bpy.context.scene;native=bpy.data.objects['RIG_Body_Stocky']
source_meshes=[o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
before=set(s.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Resources/Models/FinalRefinement/StockyGuardIntegration/Stocky_Sparring_Padded.fbx'),use_anim=False)
rig=next(o for o in s.objects if o not in before and o.type=='ARMATURE')
source_by_name={o.name:o for o in source_meshes}
corrective_pairs=[]
for obj in s.objects:
 if obj in before or obj.type!='MESH' or not obj.data.shape_keys:continue
 source=source_by_name.get(obj.name.rsplit('.',1)[0])
 if source and source.data.shape_keys:corrective_pairs.append((source,obj))
ordered=sorted(rig.pose.bones,key=lambda p:len(p.parent_recursive))
for p in ordered:p.rotation_mode='QUATERNION'
for frame in range(1,145):
 s.frame_set(frame)
 for source,obj in corrective_pairs:
  for key in obj.data.shape_keys.key_blocks:
   if key.name!='Basis' and key.name in source.data.shape_keys.key_blocks:
    key.value=source.data.shape_keys.key_blocks[key.name].value;key.keyframe_insert('value',frame=frame)
 for p in ordered:
  p.matrix=rig.matrix_world.inverted()@native.matrix_world@native.pose.bones[p.name].matrix
  bpy.context.view_layer.update()
 for p in ordered:
  for prop in ('location','rotation_quaternion','scale'):p.keyframe_insert(prop,frame=frame,group=p.name)
 if frame%24==0:print('BAKED',frame,flush=True)
rig.animation_data.action.name='Review_Corrected_Front_Kick'
for o in source_meshes:bpy.data.objects.remove(o,do_unlink=True)
bpy.data.objects.remove(native,do_unlink=True)
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.fps=30
scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
for frame in (1,26,35,54):
 s.frame_set(frame)
 review.render(s,rig,scale,OUT,f'Full_{frame}',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
 if frame in (26,35):review.render(s,rig,scale,OUT,f'Hip_{frame}',(2,-.7,1.25),(0,-.1,.95),.85,800,800)
s.frame_set(1)
review.render(s,rig,scale,OUT,'Start',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Full_Export_Kick.blend'),compress=True)
(OUT/'scope.json').write_text(json.dumps({'production_installed':False,'frames':144,'scope':'Full imported FBX with global bone poses and existing native corrective shape values baked from corrected dummy action. No cloth simulation. Visual inspection required; not automatic collision acceptance.'},indent=2))
