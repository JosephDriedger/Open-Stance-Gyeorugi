from pathlib import Path
p=Path(__file__).with_name('refine_belt_render_surface.py');code=p.read_text()
code=code.replace("'Resources/Models/FinalRefinement/BeltSurface'","'Resources/Models/FinalRefinement/BeltEnvelope'")
code=code.replace("for name in ['Belt_Tail_Left','Belt_Tail_Right']:\n o=", """from cloth_capsule_contact import capsules
from mathutils import Vector
outer=capsules(s,r,1.7);outer.name='SIM_Belt_Outer_Envelope'
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
center=r.matrix_world@r.data.bones['pelvis'].head_local+Vector((0,0,-.015*scale))
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=center)
proxy=bpy.context.object;proxy.name='SIM_Belt_Pelvis_Envelope'
for v in proxy.data.vertices:v.co.x*=.19*scale;v.co.y*=.23*scale;v.co.z*=.13*scale
for collection in list(proxy.users_collection):collection.objects.unlink(proxy)
outer.objects.link(proxy)
proxy.vertex_groups.new(name='pelvis').add(list(range(len(proxy.data.vertices))),1,'REPLACE')
proxy.modifiers.new('Follow pelvis','ARMATURE').object=r;proxy.modifiers.new('Cloth contact','COLLISION')
proxy.collision.thickness_outer=.001;proxy.collision.cloth_friction=3;proxy.hide_render=True;proxy.display_type='WIRE';proxy['SimulationOnly']=True
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=""",1)
code=code.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
 cloth=next(m for m in o.modifiers if m.type=='CLOTH');cs=cloth.settings
 cs.quality=25;cs.mass=.02;cs.use_dynamic_mesh=False;cs.tension_stiffness=500;cs.compression_stiffness=500;cs.shear_stiffness=100;cs.bending_stiffness=100
 cc=cloth.collision_settings;cc.collection=outer;cc.use_self_collision=True;cc.self_distance_min=.0015;cc.self_friction=3;cc.collision_quality=12""")
exec(compile(code,str(p),'exec'))
