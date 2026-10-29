import bpy, sys, json, traceback
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path('D:/Open-Stance-Gyeorugi')
OUT=ROOT/'Resources/Models/TPose'; OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
KINDS=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
def log(s):
 with (OUT/'build.log').open('a') as f:f.write(str(s)+'\n')
try:
 rows=[]
 for kind in KINDS:
  bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/Animation'/('OpenStance_'+kind+'_Animation.blend')))
  bpy.context.preferences.filepaths.save_version=0
  s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
  for o in s.objects:
   if o.type=='ARMATURE':
    if o.animation_data:
     o.animation_data.action=None
     for tr in o.animation_data.nla_tracks:tr.mute=True
    for pb in o.pose.bones:pb.matrix_basis=Matrix.Identity(4)
   if o.get('MarkerLabel'):o.hide_set(True);o.hide_render=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=False
  r['Wear_Jacket']=True;r['Wear_Pants']=True
  r.update_tag();bpy.context.view_layer.update()
  for side,sign in [('l',1),('r',-1)]:
   for name,child in [('upperarm','lowerarm'),('lowerarm','hand')]:
    pb=r.pose.bones[name+'_'+side];bpy.context.view_layer.update()
    direction=r.pose.bones[child+'_'+side].head-pb.head;target=(r.matrix_world.to_3x3().inverted()@Vector((sign,0,0))).normalized()
    q=direction.normalized().rotation_difference(target)
    m=pb.matrix.copy();h=m.translation.copy()
    pb.matrix=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@m
  bpy.context.view_layer.update()
  for side in ['l','r']:
   for n,child in [('upperarm','lowerarm'),('lowerarm','hand')]:
    pb=r.pose.bones[n+'_'+side];assert abs((r.matrix_world.to_3x3()@(r.pose.bones[child+'_'+side].head-pb.head)).normalized().x)>.999
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  view.camera(s,(0,-4*scale,1.0*scale),(0,0,1.0*scale),2.4*scale)
  for screen in bpy.data.screens:
   for area in screen.areas:
    if area.type=='VIEW_3D':
     sp=area.spaces.active;sp.overlay.show_overlays=False
     sp.region_3d.view_rotation=Vector((0,1,0)).to_track_quat('-Z','Y')
     sp.region_3d.view_location=Vector((0,0,.95*scale));sp.region_3d.view_distance=3*scale;sp.region_3d.view_perspective='ORTHO'
  for o in s.objects:o.select_set(False)
  r.select_set(True);bpy.context.view_layer.objects.active=r
  t=bpy.data.texts.get('T_POSE_README') or bpy.data.texts.new('T_POSE_README')
  t.write('Full character inspection copy. Body rig is posed in T, rest skeleton unchanged. Actions retained but inactive. Overlays off for clear inspection; Shift Alt Z / Viewport Overlays restores rig display. Select body rig custom properties to change clothing and gear. Wear_Jacket and Wear_Pants off reveals the underlying body through existing mask drivers. Cuff and ankle opening defects are not repaired in this inspection copy.\n')
  s.render.resolution_x=900;s.render.resolution_y=900;s.render.resolution_percentage=100
  s.render.engine='CYCLES';s.cycles.samples=8
  dest=OUT/('OpenStance_'+kind+'_Tpose.blend');bpy.ops.wm.save_as_mainfile(filepath=str(dest),compress=True)
  row={'preset':kind,'file':dest.name,'body_bones':len(r.data.bones),'masks':[]}
  for o in s.objects:
   if o.type=='MESH':
    for m in o.modifiers:
     if m.type=='MASK':row['masks'].append({'object':o.name,'modifier':m.name,'group':m.vertex_group,'invert':m.invert_vertex_group})
  rows.append(row);log(kind+' SAVED')
  if kind=='Medium':
   s.render.filepath=str(OUT/'Medium_Tpose.png');bpy.ops.render.render(write_still=True)
 (OUT/'validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2));log('COMPLETE')
except:log(traceback.format_exc());raise
