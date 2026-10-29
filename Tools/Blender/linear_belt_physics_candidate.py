"""Candidate physical belt setup; intentionally not a production installer."""
import bpy
from shared_belt_simulation import configure as shared
from rebuild_belt_solver_mesh import rebuild,garment_contact,normalize_world_mesh
from single_surface_cloth_contact import separate_render_thickness
from visible_garment_contact import configure as contact

def configure(scene,rig,anchor_fit=False,center_anchor=False,render_clearance=False,self_clearance=0.0):
    scene.frame_set(1);rig['BlenderCloth']=False;rig.update_tag();bpy.context.view_layer.update()
    assert 'SIM_Shared_Belt_Tails' not in bpy.data.objects,'Start from an unmodified study'
    proxy=bpy.data.objects[shared(scene,rig)]
    report=rebuild(proxy,rig,True,anchor_fit)
    if center_anchor:
        pin=proxy.vertex_groups['LiveCloth_Pin']
        for v in proxy.data.vertices:pin.add([v.index],1 if v.index%125==2 else 0,'REPLACE')
        report['center_knot_anchor']=True
    cloth=next(m for m in proxy.modifiers if m.type=='CLOTH')
    collection=bpy.data.collections[garment_contact(scene,cloth)]
    for o in [proxy]+list(collection.objects):normalize_world_mesh(o)
    report['render_surface']=separate_render_thickness(scene,bpy.data.objects['Pants'],rig)
    rig['BlenderCloth']=True;rig.update_tag();bpy.context.view_layer.update()
    contact(scene,cloth,['Pants'])
    for o in collection.objects:
        if o.name!='SIM_LowRes_Pants':cloth.collision_settings.collection.objects.link(o)
    cs=cloth.settings
    cs.quality=60;cs.mass=.001;cs.bending_model='LINEAR';cs.bending_stiffness=5;cs.bending_damping=2;cs.air_damping=3
    cs.tension_stiffness=80;cs.compression_stiffness=80;cs.shear_stiffness=40
    cloth.collision_settings.collision_quality=8;cloth.collision_settings.distance_min=.002
    if render_clearance:
        cloth.collision_settings.distance_min=.005*report['scale']
        cloth.collision_settings.collision_quality=12
        cs.quality=80
        report['render_contact_clearance_m']=cloth.collision_settings.distance_min
    if self_clearance:
        cloth.collision_settings.self_distance_min=float(self_clearance)*report['scale']
        report['render_self_clearance_m']=cloth.collision_settings.self_distance_min
    for o in cloth.collision_settings.collection.objects:
        o.collision.use_normal=True;o.collision.use_culling=False
        if render_clearance:o.collision.thickness_outer=max(o.collision.thickness_outer,.002*report['scale'])
    report['self_collision']=cloth.collision_settings.use_self_collision
    report['bending_model']=cs.bending_model
    return report
