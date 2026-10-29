"""Retain skin overlap inside sleeve and trouser openings without altering bodies."""
import bpy,sys,json,traceback
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
ROOT=Path('D:/Open-Stance-Gyeorugi');OUT=ROOT/'Resources/Models/OpeningRepair';OUT.mkdir(exist_ok=True)
def repair(scene):
 r=next(o for o in scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'))
 body=next(o for o in scene.objects if o.type=='MESH' and (o.name=='Body' or o.name.endswith('_Body')))
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
 pts=[body.matrix_world@v.co for v in body.data.vertices]
 rows={}
 for garment,bone,child,depth,radius in [('Jacket','lowerarm','hand',.22,.11),('Pants','calf','foot',.12,.14)]:
  group=body.vertex_groups.get('CoveredBy_'+garment)
  if not group:continue
  keep=set()
  for side in ['l','r']:
   a=r.matrix_world@r.data.bones[bone+'_'+side].head_local;b=r.matrix_world@r.data.bones[child+'_'+side].head_local;axis=(b-a).normalized()
   for i,p in enumerate(pts):
    t=(p-b).dot(axis);rad=(p-b-axis*t).length
    if -.001-depth*scale<t<.30*scale and rad<radius*scale:keep.add(i)
  covered=[i for i in keep if any(g.group==group.index and g.weight>.5 for g in body.data.vertices[i].groups)]
  # LOD interpolation can leave another garment's coverage on exposed limbs.
  # Neither jacket nor trousers should remove these distal overlap regions.
  for other in ['CoveredBy_Jacket','CoveredBy_Pants']:
   g=body.vertex_groups.get(other)
   if g and keep:g.remove(list(keep))
  rows[garment]={'restored_vertices':len(covered),'overlap_depth_m':depth*scale}
 scene['OpeningRepair']='2026-10-15: skin extends inside cuffs and trouser hems'
 for text in bpy.data.texts:
  if text.name.startswith('T_POSE_README'):
   content=text.as_string().replace('Cuff and ankle opening defects are not repaired in this inspection copy.','Wrist and ankle coverage masks are repaired in this inspection copy.')
   text.clear();text.write(content)
 return rows
if __name__=='__main__':
 try:
  bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/TPose/OpenStance_Medium_Tpose.blend'))
  s=bpy.context.scene;rows=repair(s);bpy.context.view_layer.update()
  bpy.context.preferences.filepaths.save_version=0
  bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Medium_Pilot.blend'),compress=True)
  r=bpy.data.objects['RIG_Body_Medium'];w=r.matrix_world@r.pose.bones['hand_l'].head
  s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100;s.cycles.samples=24
  view.camera(s,tuple(w+Vector((.20,-.42,-.10))),tuple(w+Vector((-.035,0,0))),.31)
  s.render.filepath=str(OUT/'Wrist.png');bpy.ops.render.render(write_still=True)
  view.camera(s,(.4,-.65,.10),(0,0,.20),.52)
  s.render.filepath=str(OUT/'Ankles.png');bpy.ops.render.render(write_still=True)
  (OUT/'pilot.json').write_text(json.dumps(rows,indent=2))
 except:(OUT/'error.log').write_text(traceback.format_exc());raise
