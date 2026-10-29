import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/HairExportFinish'
for name in ['Crowd_Near_Pilot']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(out/(name+'.fbx')));s=bpy.context.scene;s.frame_set(1);s.world=bpy.data.worlds.new('ReviewWorld');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.22,.22,1)
 for pos,power,size in [((1,-3,3),350,3),((-2,-1,2),200,2),((0,2,3),450,2)]:
  dat=bpy.data.lights.new('Review','AREA');dat.energy=power;dat.shape='DISK';dat.size=size;o=bpy.data.objects.new('Review',dat);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
 cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));s.collection.objects.link(cam);s.camera=cam
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_percentage=100
 print('MESHES',[(o.name,len(o.data.vertices)) for o in s.objects if o.type=='MESH'])
 for o in s.objects:
  if 'Hair_Crew' in o.name:o.hide_render=True
 a.render(s,None,1,out,name+'_NoHair',(.4,-1,1.9),(0,0,1.65),.52,600,600)



