import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import build_single_helmet_study as view
OUT=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(OUT/'Front_Kick.fbx'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=640;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1)
for loc,power,size in [((2,-3,4),550,4),((-3,-1,2),350,3),((0,3,3),450,3)]:
 d=bpy.data.lights.new('Softbox','AREA');d.energy=power;d.size=size;o=bpy.data.objects.new('Softbox',d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Review Camera',bpy.data.cameras.new('Review Camera'));scene.collection.objects.link(cam);scene.camera=cam
view.camera(scene,(4,-.8,1.65),(0,-.3,.95),2.25)
for f in [26,35]:
 scene.frame_set(f);scene.render.filepath=str(OUT/f'Clothing_FBX_{f}.png');bpy.ops.render.render(write_still=True)
