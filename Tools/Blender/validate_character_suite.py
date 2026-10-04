"""Reopen suite outputs, check skinning and render representative assets headlessly."""
import bpy,json,sys,traceback
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/CharacterSuite'
def run(kind):
 report={}
 catalog=json.loads((OUT/kind/'catalog.json').read_text())
 for path in sorted((OUT/kind).glob('*.blend')):
  bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['RIG_Body_'+kind]
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
  errors=[];maxweights=0
  for o in meshes:
   arm=next(m.object for m in o.modifiers if m.type=='ARMATURE');names={g.index:g.name for g in o.vertex_groups};bones=set(arm.data.bones.keys())
   for v in o.data.vertices:
    w=[g.weight for g in v.groups if names[g.group] in bones and g.weight>1e-6];maxweights=max(maxweights,len(w))
    if not w or abs(sum(w)-1)>.002:errors.append((o.name,v.index,sum(w)))
  assert not errors,errors[:10]
  if path.stem!='Preview':assert maxweights <= (2 if path.stem.startswith('Crowd') else 4),maxweights
  drivers=[d for o in meshes for d in (o.animation_data.drivers if o.animation_data else [])]
  assert all(d.driver.is_valid for d in drivers),'Invalid visibility driver'
  report[path.stem]={'weighted_meshes':len(meshes),'max_influences':maxweights,'skin_weights_passed':True,'body_bones':len(rig.data.bones),'visibility_drivers_valid':True}
  if path.stem!='Preview':
   counts={}
   for o in meshes:o.data.calc_loop_triangles();counts[o.name]=len(o.data.loop_triangles)
   catalog['profiles'][path.stem]['base_triangles']=counts
  if path.stem.startswith('Crowd'):
   import numpy as np
   checks={};rest=(rig.matrix_world@rig.pose.bones['head'].matrix.translation).z
   for label in ['StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave']:
    rig.animation_data.action=bpy.data.actions['Crowd_'+label]
    samples=[]
    for frame in [1,16,61]:
     bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
     samples.append(np.array([list(rig.matrix_world@p.matrix.translation) for p in rig.pose.bones]))
    loop_error=float(np.max(np.abs(samples[0]-samples[2])));assert loop_error<.0001,(label,loop_error)
    checks[label]={'loop_error_m':loop_error,'joint_motion_m':float(np.max(np.abs(samples[0]-samples[1])))}
    if label=='SeatedIdle':
     drop=rest-(rig.matrix_world@rig.pose.bones['head'].matrix.translation).z;assert .3<drop<.6,drop;checks[label]['pelvis_drop_m']=drop
    if label=='SeatedClap':
     distance=(rig.matrix_world@rig.pose.bones['hand_l'].matrix.translation-rig.matrix_world@rig.pose.bones['hand_r'].matrix.translation).length
     assert distance<.15,distance;checks[label]['hands_distance_m']=distance
   report[path.stem]['animation_checks']=checks
   rig.animation_data.action=None
   for p in rig.pose.bones:p.matrix_basis=Matrix()
   bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
  if kind=='Medium' and path.stem in ['Preview','Gameplay_High','Crowd_Near','Crowd_Far']:
   scene=bpy.context.scene;scene.render.resolution_percentage=55
   if scene.render.engine=='CYCLES':scene.cycles.samples=20
   scene.render.filepath=str(OUT/kind/(path.stem+'.png'));bpy.ops.render.render(write_still=True)
   if path.stem=='Crowd_Near':
    for label in ['SeatedIdle','SeatedClap','Cheer','Wave']:
     action=bpy.data.actions['Crowd_'+label];rig.animation_data.action=action;scene.frame_set(16)
     scene.render.filepath=str(OUT/kind/('Crowd_'+label+'.png'));bpy.ops.render.render(write_still=True)
 (OUT/kind/'validation.json').write_text(json.dumps(report,indent=2))
 (OUT/kind/'catalog.json').write_text(json.dumps(catalog,indent=2))
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Medium','Compact','Stocky','LeanTall','Tall']
  for kind in args:run(kind)
 except:
  (OUT/'validation_error.log').write_text(traceback.format_exc());raise
