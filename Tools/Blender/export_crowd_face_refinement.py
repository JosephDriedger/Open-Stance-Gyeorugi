import bpy,sys,json,hashlib,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import refine_crowd_faces as fix
import rebuild_updated_characters as build
OUT=fix.OUT
try:
 for kind in build.PRESETS:
  for level in ['Crowd_Near','Crowd_Far']:
   deadline=time.monotonic()+1800
   while not (OUT/kind/(level+'_validation.json')).exists():
    assert time.monotonic()<deadline
    time.sleep(3)
  rows=[]
  for style in [0,1]:
   d=OUT/kind/('WhiteVNeck' if style else 'WhiteWrap');d.mkdir(exist_ok=True);paths=[]
   for level in ['Crowd_Near','Crowd_Far']:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/kind/(level+'.blend')));r=bpy.data.objects['RIG_Body_'+kind];s=bpy.context.scene
    r.animation_data.action=None;r['JacketStyle']=style
    for t in r.animation_data.nla_tracks:t.mute=True
    build.refresh(r);p=d/(level+'.fbx');build.export(r,p);paths.append(p)
    if level=='Crowd_Near':
     for clip in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
      r.animation_data.action=bpy.data.actions['Crowd_'+clip];s.frame_start=1;s.frame_end=61;s.frame_set(1)
      p=d/('Crowd_'+clip+'.fbx');build.export(r,p,True);paths.append(p)
   for p in paths:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p))
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones)==25
    head=next(o for o in bpy.context.scene.objects if o.name.split('.')[0]=='Head');head.data.calc_loop_triangles()
    assert len(head.data.loop_triangles)==(2400 if p.stem=='Crowd_Far' else 6000)
    assert len(set(poly.material_index for poly in head.data.polygons))>=3
    for o in bpy.context.scene.objects:
     if o.type=='MESH':assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.003 for v in o.data.vertices),o.name
    if p.stem not in ['Crowd_Near','Crowd_Far']:assert rigs[0].animation_data.action and rigs[0].animation_data.action.frame_range[1]>=60
    rows.append({'file':p.relative_to(OUT).as_posix(),'sha256':fix.sha(p),'rig_bones':25,'head_triangles':len(head.data.loop_triangles),'reimport_passed':True})
  (OUT/kind/'exports.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
  with (OUT/'export.log').open('a') as log:log.write(kind+' COMPLETE\n')
except:(OUT/'export_error.log').write_text(traceback.format_exc());raise
