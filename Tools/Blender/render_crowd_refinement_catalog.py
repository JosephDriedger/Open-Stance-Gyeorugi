import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import refine_crowd_faces as fix
import audit_sparring_styles as a
for kind in sys.argv[sys.argv.index('--')+1:]:
 for level in ['Crowd_Near','Crowd_Far']:
  bpy.ops.wm.open_mainfile(filepath=str(fix.OUT/kind/(level+'.blend')))
  s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.animation_data_create();r.animation_data.action=None
  for t in r.animation_data.nla_tracks:t.mute=True
  for o in s.objects:
   if o.get('MarkerLabel'):o.hide_render=True
  for prop in ['Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','BlenderCloth']:r[prop]=False
  scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
  s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True
  for style in [0,1]:
   r['JacketStyle']=style;a.build.refresh(r)
   assert len(r.data.bones)==25
   head=bpy.data.objects['Head'];assert len({p.material_index for p in head.data.polygons})>=3
   for o in s.objects:
    if o.animation_data:assert all(d.is_valid for d in o.animation_data.drivers)
   deps=bpy.context.evaluated_depsgraph_get();total=0
   for o in a.build.meshes():
    if not o.hide_render:
     ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();total+=len(me.loop_triangles);ev.to_mesh_clear()
   (fix.OUT/kind/(level+'_'+str(style)+'_count.json')).write_text(json.dumps({'triangles':total,'drivers_valid':True}))
   label='Crowd_StandingIdle' if level.startswith('Crowd') else 'Neutral'
   if level.startswith('Crowd'):r.animation_data.action=bpy.data.actions['Crowd_StandingIdle'];s.frame_set(16)
   else:a.audit.pose(r,'Neutral',scale)
   a.render(s,r,scale,fix.OUT/kind,f'{level}_{style}_{label}',(.8,-4,1.7),(0,0,.96),2.35,480,540)
