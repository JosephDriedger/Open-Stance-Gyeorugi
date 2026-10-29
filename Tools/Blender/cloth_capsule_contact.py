import bpy,math
from mathutils import Vector

def capsules(s,r,radius_scale=1.0):
 scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578;coll=bpy.data.collections.new('SIM_Limb_Contact');s.collection.children.link(coll)
 for side in 'lr':
  for bone,end,radius in [('thigh','calf',.065),('calf','foot',.043),('upperarm','lowerarm',.045),('lowerarm','hand',.032)]:
   name=bone+'_'+side;a=r.matrix_world@r.data.bones[name].head_local;b=r.matrix_world@r.data.bones[end+'_'+side].head_local;axis=(b-a).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u);rad=radius*scale*radius_scale;verts=[];faces=[];rings=[]
   for j in range(6):
    angle=-math.pi/2+(math.pi/2)*j/5;rings.append((a+axis*rad*math.sin(angle),max(rad*math.cos(angle),.00001)))
   for j in range(6):
    angle=(math.pi/2)*j/5;rings.append((b+axis*rad*math.sin(angle),max(rad*math.cos(angle),.00001)))
   for c,rr in rings:
    for i in range(16):verts.append(c+rr*(u*math.cos(math.tau*i/16)+v*math.sin(math.tau*i/16)))
   for j in range(len(rings)-1):
    for i in range(16):faces.append((j*16+i,j*16+(i+1)%16,(j+1)*16+(i+1)%16,(j+1)*16+i))
   me=bpy.data.meshes.new('Contact_'+name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('SIM_Capsule_'+name,me);coll.objects.link(o);o.vertex_groups.new(name=name).add(list(range(len(verts))),1,'REPLACE');mod=o.modifiers.new('Follow limb','ARMATURE');mod.object=r;o.modifiers.new('Cloth contact','COLLISION');o.collision.thickness_outer=.001;o.collision.thickness_inner=.001;o.collision.cloth_friction=3;o.hide_render=True;o.display_type='WIRE';o['SimulationOnly']=True
 return coll
