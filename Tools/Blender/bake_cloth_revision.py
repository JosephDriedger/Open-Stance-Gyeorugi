import bpy,sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples/ClothRevision')
def log(s):
 with (OUT/'bake.log').open('a') as f:f.write(str(s)+'\n')
try:
 bpy.ops.wm.open_mainfile(filepath=str(OUT/'Medium_Cloth_Physics_Test.blend'))
 scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];names=['Uniform_Wrap_Skirt','Belt_Tail_Left','Belt_Tail_Right'];snapshots={n:[] for n in names}
 frames=OUT/'Frames';frames.mkdir(exist_ok=True)
 for f in range(1,73):
  scene.frame_set(f);bpy.context.view_layer.update()
  for name in names:
   o=bpy.data.objects[name];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
   deform=r.matrix_world@r.pose.bones['pelvis'].matrix@r.data.bones['pelvis'].matrix_local.inverted()@r.matrix_world.inverted()@o.matrix_world
   inverse=deform.inverted();snapshots[name].append([inverse@(o.matrix_world@v.co) for v in list(m.vertices)[:len(o.data.vertices)]]);ev.to_mesh_clear()
  if f%2==1:
   scene.render.filepath=str(frames/f'{(f-1)//2:04d}.png');bpy.ops.render.render(write_still=True)
  if f%12==0:log('FRAME '+str(f))
 for name in names:
  o=bpy.data.objects[name]
  for m in list(o.modifiers):
   if m.type in ['CLOTH','COLLISION']:o.modifiers.remove(m)
  o.shape_key_add(name='Basis')
  for i,coords in enumerate(snapshots[name]):
   key=o.shape_key_add(name=f'ClothBake_{i+1:02d}')
   for v,p in zip(key.data,coords):v.co=p
   for f,value in [(0,0),(i,0),(i+1,1),(i+2,0),(74,0)]:key.value=value;key.keyframe_insert('value',frame=f)
   key.value=0
  o['PreserveExportShapeKeys']=True
 for name in ['Jacket','Belt','Pants']:
  o=bpy.data.objects[name];o['FabricRevision']='Matte cotton, corrected world thickness'
 scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Front_Kick_Cloth_Baked.blend'))
 build.export(r,OUT/'Front_Kick_Cloth_Baked.fbx',True)
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/'Front_Kick_Cloth_Baked.fbx'))
 rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==341
 report={'body_bones':341,'cloth_objects':{},'source':'Blender cloth simulation baked to animated shape keys','live_physics_in_fbx':False}
 for name in names:
  o=next(o for o in bpy.context.scene.objects if o.name.startswith(name));keys=o.data.shape_keys;assert keys and len(keys.key_blocks)==73
  vals=[]
  for f in [1,26,35,72]:
   bpy.context.scene.frame_set(f);bpy.context.view_layer.update();vals.append(sum(k.value for k in keys.key_blocks if k.name.startswith('ClothBake_')))
  assert all(abs(v-1)<.01 for v in vals),vals
  report['cloth_objects'][name]={'shapes':72,'animation_reimport_passed':True}
 (OUT/'validation.json').write_text(json.dumps(report,indent=2));log('COMPLETE')
except:log(traceback.format_exc());raise
