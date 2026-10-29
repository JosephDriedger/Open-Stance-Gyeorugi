"""Reimport staged FBX deliveries and check skeletons, weights and materials."""
import bpy,sys,json,traceback,hashlib
from pathlib import Path
from mathutils import Vector,Quaternion
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
ROOT=view.ROOT;OUT=ROOT/'Resources/Models/UpdatedBuild'
def run(kind,quick=False):
 results=[];directory=OUT/kind
 files=[directory/'Gameplay_High_Sparring.fbx'] if quick else sorted(directory.glob('*.fbx'))
 for path in files:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True)
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1,(path,len(rigs))
  rig=rigs[0];expected=26 if path.stem.startswith('Crowd') else 341
  # Current reduced rig uses the declared keep set (25 bones in these sources).
  if expected==26:assert len(rig.data.bones) in [25,26]
  else:assert len(rig.data.bones)==expected
  objects=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert objects
  for o in objects:
   assert any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers),o.name
   assert all(0<len(v.groups)<=4 and abs(sum(g.weight for g in v.groups)-1)<.002 for v in o.data.vertices),o.name
  skin=[m for m in bpy.data.materials if 'Skin_Head' in m.name];assert skin
  images=[n.image for m in skin if m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
  assert images and all(i.size[0]>0 for i in images),'Missing skin albedo'
  body_images=[n.image for m in bpy.data.materials if 'Skin_Body' in m.name and m.use_nodes for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
  assert body_images
  import numpy as np
  px=np.empty(len(body_images[0].pixels),dtype=np.float32);body_images[0].pixels.foreach_get(px)
  assert float(px.reshape(-1,4)[:,:3].max())>.05,'Empty body albedo'
  for o in objects:
   if o.name.startswith('Body'):
    assert all(-.001<=d.uv.x<=1.001 and -.001<=d.uv.y<=1.001 for d in o.data.uv_layers.active.data),'Body UV tile not normalized'
  if path.stem.startswith('Crowd_') and path.stem not in ['Crowd_Near','Crowd_Far']:
   assert rig.animation_data and rig.animation_data.action,'Missing crowd animation'
  row={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bones':len(rig.data.bones),'meshes':len(objects),'weights_passed':True,'skin_albedo_loaded':True}
  results.append(row)
  if path.name=='Gameplay_High_Sparring.fbx':
   scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=900;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
   scene.world=bpy.data.worlds.new('Export Studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1)
   for location,power,size in [((2,-3,4),550,4),((-3,-1,2),350,3),((0,3,3),450,3)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(o);o.location=location;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
   head=rig.matrix_world@rig.data.bones['head'].head_local;scale=head.z/1.578
   cam=bpy.data.objects.new('Export Camera',bpy.data.cameras.new('Export Camera'));scene.collection.objects.link(cam);scene.camera=cam
   view.camera(scene,(.8*scale,-2*scale,1.55*scale),(0,0,.91*scale),2.06*scale)
   scene.render.filepath=str(directory/'FBX_Reimport_Sparring.png');bpy.ops.render.render(write_still=True)
  (directory/('export_smoke.json' if quick else 'export_validation.json')).write_text(json.dumps({'passed':True,'files':results},indent=2))
if __name__=='__main__':
 try:
  args=sys.argv[sys.argv.index('--')+1:]
  for kind in [a for a in args if not a.startswith('--')]:run(kind,'--quick' in args)
 except:(OUT/'export_errors.log').open('a').write(traceback.format_exc());raise
