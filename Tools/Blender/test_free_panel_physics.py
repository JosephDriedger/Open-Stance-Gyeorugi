"""Free woven panels with waist-only attachment and a stationary settling period."""
import bpy, sys, json, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
diagnostic='--no-contact' in sys.argv
conditioning='--conditioning' in sys.argv
physical='--physical-mass' in sys.argv
rest_start='--rest-start' in sys.argv
sewn='--sewn' in sys.argv
full_pants='--full-pants' in sys.argv
OUT=review.ROOT/'Resources/Models/FinalRefinement'/('FreeUniformCoupled' if full_pants else 'FreePanelSewn' if sewn else 'FreePanelRestStart' if rest_start else 'FreePanelLinearMass' if physical else 'FreePanelConditioning' if conditioning else 'FreePanelNoContact' if diagnostic else 'FreePanelPhysicsV2'); OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(review.ROOT/'Resources/Models/FinalRefinement/FootguardSmoothKickReview/Animation_Test.blend'))
s=bpy.context.scene; r=bpy.data.objects['RIG_Body_Stocky']; scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
parts=['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back','Belt_Tail_Left','Belt_Tail_Right']
poses=[]
for frame in range(1,145):
    s.frame_set(frame); poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
r.animation_data.action=None
for track in r.animation_data.nla_tracks: track.mute=True
preroll=60 if rest_start else 30
for frame in range(1,145+preroll):
    for name,matrix in poses[max(0,frame-preroll-1)].items():
        if rest_start and frame<=preroll:
            blend=max(0,min(1,(frame-30)/30)); blend=blend*blend*(3-2*blend)
            matrix=Matrix.Identity(4).lerp(matrix,blend)
        b=r.pose.bones[name]; b.matrix_basis=matrix
        b.keyframe_insert('location',frame=frame); b.keyframe_insert('rotation_quaternion' if b.rotation_mode=='QUATERNION' else 'rotation_euler',frame=frame); b.keyframe_insert('scale',frame=frame)
s.frame_end=144+preroll; s.frame_set(1)
for obj in list(s.objects):
    if obj.get('SimulationOnly'): bpy.data.objects.remove(obj,do_unlink=True)
for obj in s.objects:
    if obj.type=='MESH':
        for mod in list(obj.modifiers):
            if mod.type=='CLOTH':
                for prop in ('show_viewport','show_render'):mod.driver_remove(prop)
                obj.modifiers.remove(mod)
contact=bpy.data.collections.new('FreePanel_PantsContact'); s.collection.children.link(contact)
pants=bpy.data.objects['Pants'] if full_pants else bpy.data.objects['Pants'].copy()
if not full_pants:
    pants.data=pants.data.copy(); pants.name='SIM_SingleSurface_Pants'; pants['SimulationOnly']=True
    for prop in ('visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow'):setattr(pants,prop,False)
contact.objects.link(pants)
for mod in list(pants.modifiers):
    if mod.type!='ARMATURE':pants.modifiers.remove(mod)
if full_pants:
    pants.shape_key_clear()
    bodycontact=bpy.data.collections.new('FreeUniform_BodyContact');s.collection.children.link(bodycontact)
    body=bpy.data.objects['Body'].copy();body.data=body.data.copy();body.name='SIM_FullBody_Contact';body['SimulationOnly']=True;bodycontact.objects.link(body)
    for mod in list(body.modifiers):
        if mod.type!='ARMATURE':body.modifiers.remove(mod)
    for prop in ('visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow'):setattr(body,prop,False)
    body.modifiers.new('Body contact','COLLISION');body.collision.thickness_outer=.002*scale;body.collision.cloth_friction=1
    top=max((pants.matrix_world@v.co).z for v in pants.data.vertices)
    pin=pants.vertex_groups.new(name='WaistOnly_PhysicalPants')
    for v in pants.data.vertices:pin.add([v.index],1 if (pants.matrix_world@v.co).z>top-.035*scale else 0,'REPLACE')
    cloth=pants.modifiers.new('Free trouser physics','CLOTH');c=cloth.settings
    c.quality=32;c.mass=.55/len(pants.data.vertices);c.vertex_group_mass=pin.name;c.pin_stiffness=1;c.use_dynamic_mesh=False
    c.tension_stiffness=100;c.compression_stiffness=100;c.shear_stiffness=60;c.bending_model='LINEAR';c.bending_stiffness=5
    c.tension_damping=.5;c.compression_damping=.5;c.shear_damping=.5;c.bending_damping=.5;c.air_damping=2
    cc=cloth.collision_settings;cc.use_collision=True;cc.collection=bodycontact;cc.distance_min=.003*scale;cc.collision_quality=8;cc.use_self_collision=True;cc.self_distance_min=.001*scale
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=s.frame_end
pants.modifiers.new('Outer trouser contact','COLLISION'); pants.collision.thickness_outer=.002*scale; pants.collision.cloth_friction=1
bpy.context.view_layer.update()
ev=pants.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh(); mesh.calc_loop_triangles()
rest_tree=BVHTree.FromPolygons([pants.matrix_world@v.co for v in mesh.vertices],[tuple(t.vertices) for t in mesh.loop_triangles],all_triangles=True); ev.to_mesh_clear()
beltcontact=bpy.data.collections.new('FreePanel_BeltContact'); s.collection.children.link(beltcontact); beltcontact.objects.link(pants)
for name in parts:
    obj=bpy.data.objects[name]; belt=name.startswith('Belt')
    if obj.data.shape_keys:obj.shape_key_clear()
    # Contact uses the single fabric surface, with an initial clearance margin.
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        if belt:p.y-=.02*scale
        else:
            outward=Vector((p.x,p.y,0)).normalized(); p+=outward*.006*scale
            if rest_start:
                for iteration in range(6):
                    hit,normal,_,_=rest_tree.find_nearest(p); distance=(p-hit).dot(normal)
                    if distance>=.006*scale:break
                    p+=normal*min(.004*scale,.006*scale-distance)
        v.co=obj.matrix_world.inverted()@p
    # Free panels inherit only the waist motion; no leg-driven rest-shape changes.
    for v in obj.data.vertices:
        for g in list(v.groups):
            if obj.vertex_groups[g.group].name in r.data.bones:obj.vertex_groups[g.group].remove([v.index])
    vg=obj.vertex_groups.get('pelvis') or obj.vertex_groups.new(name='pelvis'); vg.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    top=max((obj.matrix_world@v.co).z for v in obj.data.vertices)
    pin=obj.vertex_groups.new(name='WaistOnly_Pin')
    for v in obj.data.vertices:
        depth=top-(obj.matrix_world@v.co).z
        pin.add([v.index],1 if depth<.012*scale else 0,'REPLACE')
    for mod in list(obj.modifiers):
        if mod.type=='SOLIDIFY':obj.modifiers.remove(mod)
    cloth=obj.modifiers.new('Free woven physics','CLOTH'); c=cloth.settings
    c.quality=16; c.mass=(.035 if belt else .09)/len(obj.data.vertices)
    c.vertex_group_mass=pin.name; c.pin_stiffness=1; c.use_dynamic_mesh=False
    c.tension_stiffness=100; c.compression_stiffness=100; c.shear_stiffness=60; c.bending_stiffness=2 if belt else .5
    c.tension_damping=8; c.compression_damping=8; c.shear_damping=8; c.bending_damping=3; c.air_damping=2
    if conditioning:
        c.mass=.01; c.quality=40; c.bending_model='LINEAR'; c.bending_stiffness=5
        c.tension_damping=.5; c.compression_damping=.5; c.shear_damping=.5; c.bending_damping=.5
        if physical:c.mass=(.035 if belt else .09)/len(obj.data.vertices)
    cc=cloth.collision_settings; cc.use_collision=True; cc.collection=beltcontact if belt else contact
    cc.distance_min=.003*scale; cc.collision_quality=8; cc.use_self_collision=True; cc.self_distance_min=.001*scale
    if diagnostic:cc.use_collision=False;cc.use_self_collision=False
    cloth.point_cache.frame_start=1; cloth.point_cache.frame_end=s.frame_end
    if not belt:
        obj.modifiers.new('Simulated panel contact','COLLISION'); obj.collision.thickness_outer=.002*scale; obj.collision.cloth_friction=1; beltcontact.objects.link(obj)
    thick=obj.modifiers.new('Fabric thickness','SOLIDIFY'); thick.thickness=(.002 if belt else .001)*scale; thick.offset=0
if sewn:
    import bmesh
    panels=[bpy.data.objects[n] for n in parts[:3]]
    for index,obj in enumerate(panels):
        attr=obj.data.attributes.new('SourcePanel','INT','POINT')
        for datum in attr.data:datum.value=index
    bpy.ops.object.select_all(action='DESELECT')
    for obj in panels:obj.select_set(True)
    bpy.context.view_layer.objects.active=panels[0]; bpy.ops.object.join()
    skirt=bpy.context.object; skirt.name='Jacket_Skirt_Physics'
    bm=bmesh.new();bm.from_mesh(skirt.data);layer=bm.verts.layers.int['SourcePanel'];bm.verts.ensure_lookup_table()
    top=max((skirt.matrix_world@v.co).z for v in bm.verts)
    boundary=[v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    fronts=[v for v in boundary if v[layer]<2 and abs((skirt.matrix_world@v.co).y)<.02*scale and abs((skirt.matrix_world@v.co).x)>.17*scale and (skirt.matrix_world@v.co).z>top-.14*scale]
    backs=[v for v in boundary if v[layer]==2];count=0
    for front in fronts:
        if not front.is_valid:continue
        choices=[v for v in backs if v.is_valid and abs(v.co.z-front.co.z)<.001*scale and (v.co-front.co).length<.025*scale]
        if choices:
            back=min(choices,key=lambda v:(v.co-front.co).length)
            bmesh.ops.pointmerge(bm,verts=[front,back],merge_co=(front.co+back.co)*.5);count+=1
    bm.to_mesh(skirt.data);bm.free();skirt.data.update();assert count>20,count
    cloth=next(m for m in skirt.modifiers if m.type=='CLOTH');cloth.settings.mass=.27/len(skirt.data.vertices)
    parts=[skirt.name]+parts[3:]
    (OUT/'seams.json').write_text(json.dumps(dict(merged_pairs=count,side_slit_m=.06*scale,production_installed=False),indent=2))
if full_pants:
    thick=pants.modifiers.new('Fabric thickness','SOLIDIFY');thick.thickness=.001*scale;thick.offset=0
    parts.append(pants.name)
s.render.engine='CYCLES'; s.cycles.samples=16; s.cycles.use_denoising=True
bpy.context.preferences.filepaths.save_version=0; bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
for frame in range(1,31 if diagnostic else preroll+73):
    s.frame_set(frame); dg=bpy.context.evaluated_depsgraph_get()
    for name in parts:
        ev=bpy.data.objects[name].evaluated_get(dg); mesh=ev.to_mesh()
        assert all(math.isfinite(x) and abs(x)<5 for v in mesh.vertices for x in v.co),(name,frame)
        ev.to_mesh_clear()
    print('SIM_FRAME',frame,flush=True)
    if frame in (preroll,preroll+26,preroll+35,preroll+72):review.render(s,r,scale,OUT,'Full_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
(OUT/'report.json').write_text(json.dumps(dict(simulated_frames=frame,preroll=preroll,production_installed=False,contact_disabled=diagnostic,conditioning_test=conditioning,rest_start=rest_start,scope='Finite geometry only; requires visual acceptance and cache baking'),indent=2))
