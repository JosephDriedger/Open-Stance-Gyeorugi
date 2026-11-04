"""Low-resolution simulation cages drive the existing detailed garment surfaces."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
from rebuild_belt_solver_mesh import normalize_world_mesh
OUT=review.ROOT/'Resources/Models/FinalRefinement/UniformSimulationCages';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(review.ROOT/'Resources/Models/FinalRefinement/FreeUniformCoupled/Candidate.blend'))
s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Stocky'];s.frame_set(1);r.data.pose_position='REST'
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
for obj in list(s.objects):
    if any(m.type=='COLLISION' for m in obj.modifiers):
        normalize_world_mesh(obj);obj.collision.thickness_inner=.001*scale;obj.collision.thickness_outer=.002*scale;obj.collision.use_normal=True;obj.collision.use_culling=False
rows=[]
for name in ('Belt_Tail_Left','Belt_Tail_Right'):
    for mod in bpy.data.objects[name].modifiers:
        if mod.type=='CLOTH':mod.show_viewport=False;mod.show_render=False
for name,total,budget in [('Pants',.55,350),('Jacket_Skirt_Physics',.27,240)]:
    high=bpy.data.objects[name];old=next(m for m in high.modifiers if m.type=='CLOTH')
    pin=old.settings.vertex_group_mass;contact=old.collision_settings.collection
    proxy=high.copy();proxy.data=high.data.copy();proxy.animation_data_clear();proxy.name='SIM_Cage_'+name;s.collection.objects.link(proxy);proxy['SimulationOnly']=True
    for prop in ('visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow'):setattr(proxy,prop,False)
    proxy.hide_render=False;proxy.hide_viewport=False;proxy.hide_set(False);proxy.display_type='WIRE'
    for mod in list(proxy.modifiers):
        if mod.type!='ARMATURE':proxy.modifiers.remove(mod)
    dec=proxy.modifiers.new('Simulation mesh reduction','DECIMATE');dec.ratio=min(1,budget/len(proxy.data.vertices));dec.use_collapse_triangulate=True
    bpy.ops.object.select_all(action='DESELECT');proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
    bpy.ops.object.modifier_apply(modifier=dec.name)
    triangulate=proxy.modifiers.new('Simulation triangles','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    import bmesh
    bm=bmesh.new();bm.from_mesh(proxy.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    bad=[face for face in bm.faces if face.calc_area()<1e-12]
    if bad:bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
    bm.to_mesh(proxy.data);bm.free();proxy.data.update()
    cloth=proxy.modifiers.new('Cage cloth','CLOTH');c=cloth.settings
    c.mass=total/len(proxy.data.vertices);c.quality=24;c.vertex_group_mass=pin;c.pin_stiffness=1;c.use_dynamic_mesh=False
    c.tension_stiffness=20;c.compression_stiffness=20;c.shear_stiffness=10;c.bending_model='LINEAR';c.bending_stiffness=.5
    c.tension_damping=.1;c.compression_damping=.1;c.shear_damping=.1;c.bending_damping=.1;c.air_damping=.1
    cc=cloth.collision_settings;cc.use_collision=True;cc.collection=contact;cc.distance_min=.003*scale;cc.collision_quality=8;cc.use_self_collision=True;cc.self_distance_min=.001*scale
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=s.frame_end
    had_collision=any(m.type=='COLLISION' for m in high.modifiers)
    for mod in list(high.modifiers):
        if mod.type=='ARMATURE':mod.show_viewport=False;mod.show_render=False
        else:high.modifiers.remove(mod)
    surface=high.modifiers.new('Physical cage deformation','SURFACE_DEFORM');surface.target=proxy
    bpy.ops.object.select_all(action='DESELECT');high.select_set(True);bpy.context.view_layer.objects.active=high
    bpy.context.view_layer.update();bpy.ops.object.surfacedeform_bind(modifier=surface.name);assert surface.is_bound,name
    if had_collision:
        high.modifiers.new('Outer fabric contact','COLLISION');high.collision.thickness_inner=.001*scale;high.collision.thickness_outer=.002*scale;high.collision.use_normal=True;high.collision.use_culling=False
    thick=high.modifiers.new('Fabric thickness','SOLIDIFY');thick.thickness=(.002 if name.startswith('Belt') else .001)*scale;thick.offset=0
    rows.append(dict(part=name,render_vertices=len(high.data.vertices),solver_vertices=len(proxy.data.vertices),vertex_mass=c.mass))
r.data.pose_position='POSE';s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
for frame in range(1,31):
    s.frame_set(frame);dg=bpy.context.evaluated_depsgraph_get()
    for row in rows:
        ev=bpy.data.objects[row['part']].evaluated_get(dg);m=ev.to_mesh();ev.to_mesh_clear()
    print('CAGE_FRAME',frame,flush=True)
review.render(s,r,scale,OUT,'Rest_30',(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
(OUT/'report.json').write_text(json.dumps(dict(production_installed=False,frames=30,parts=rows,scope='Stationary cage deformation trial; not export-ready or animation accepted'),indent=2))
