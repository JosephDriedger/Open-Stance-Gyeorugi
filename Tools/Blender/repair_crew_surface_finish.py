import bpy,sys,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import refine_crowd_faces as f
OUT=f.ROOT/'Resources/Models/HairExportFinish';OUT.mkdir(exist_ok=True)
def repair(s):
 if s.get("HairExportFinish"):return {"already_repaired":True}
 r=next(o for o in s.objects if o.name.startswith('RIG_Body_'));states={o:o.data.pose_position for o in s.objects if o.type=='ARMATURE'}
 for o in states:o.data.pose_position='REST'
 bpy.context.view_layer.update();surface=f.fit.tree(bpy.data.objects['Head'],True);scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;center=Vector((0,.002,1.65))*scale
 for o in s.objects:
  if o.type!='MESH' or not o.name.startswith('Hair_Crew_Cut') or len(r.data.bones)==25:continue
  keys=o.data.shape_keys;inv=o.matrix_world.inverted()
  for block in (keys.key_blocks if keys else [o.data]):
   for v in (block.data if keys else block.vertices):
    p=o.matrix_world@v.co;axis=(p-center).normalized();hit=surface.ray_cast(center+axis*.35*scale,-axis,.35*scale)[0]
    if hit is not None:
     clearance=.0009*scale if 'Scalp_Coverage' in o.name else max(.001*scale,min(.0025*scale,(p-hit).dot(axis)))
     v.co=inv@(hit+axis*clearance)
  if keys:
   for v,k in zip(o.data.vertices,keys.key_blocks[0].data):v.co=k.co
 # Keep the coarse crown UVs inside the padded scalp texture region.
 head=bpy.data.objects['Head'];uv=head.data.uv_layers.get('DiffuseUV')
 if uv and len(head.data.polygons)<10000:
  for poly in head.data.polygons:
   if poly.material_index!=0 or min((head.matrix_world@head.data.vertices[i].co).z for i in poly.vertices)<1.72*scale:continue
   for li in poly.loop_indices:
    v=uv.data[li].uv.y
    if v>.92:uv.data[li].uv.y=.92+(v-.92)*.25
 for o,state in states.items():o.data.pose_position=state
 bpy.context.view_layer.update();s["HairExportFinish"]="2026-10-22"
 return {"crew_surface_fitted":len(r.data.bones)!=25,"coarse_crown_uv_padded":len(head.data.polygons)<10000}
if __name__=='__main__':
 for level in ['Gameplay_High','Crowd_Near']:
  bpy.ops.wm.open_mainfile(filepath=str(f.ROOT/'Resources/Models/CharacterSuite/Medium'/(level+'.blend')));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium'];repair(s)
  r.animation_data.action=None
  for t in r.animation_data.nla_tracks:t.mute=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  f.review.build.refresh(r);s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
  f.review.render(s,r,1,OUT,level+'_NativeV3',(.4,-1,1.9),(0,0,1.65),.52,600,600)
  f.review.build.export(r,OUT/(level+'_Pilot.fbx'))
