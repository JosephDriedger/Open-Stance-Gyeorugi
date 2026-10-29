"""Review a clean belt simulation grid against the existing kick animation."""
import bpy, sys, json, math, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import extend_garment_repairs as base
from rebuild_belt_solver_mesh import rebuild, garment_contact, normalize_world_mesh
root = a.ROOT/'Resources/Models/FinalRefinement'
clamped = sys.argv[-1]=='Clamped'
soft = sys.argv[-1]=='SoftBody'
guided = sys.argv[-1]=='GuidedHem'
center_anchor = sys.argv[-1]=='CenterAnchor'
anchor_fit = sys.argv[-1] in ['AnchorFit','CenterAnchor']
no_self = sys.argv[-1]=='NoSelfWorld'
linear = sys.argv[-1] in ['LinearBelt','AnchorFit','CenterAnchor']
normal_contact = sys.argv[-1] in ['NormalContact','LinearBelt','NoSelfWorld','AnchorFit','CenterAnchor']
if normal_contact: sys.argv[-1]='StiffSingleSurface'
stiff = sys.argv[-1]=='StiffSingleSurface'
single = sys.argv[-1] in ['SingleSurface','StiffSingleSurface']
freehem = sys.argv[-1] in ['FreeHem','GuidedHem']
actualpants = sys.argv[-1] in ['ActualPants','GuidedHem','SingleSurface','StiffSingleSurface']
worldspace = sys.argv[-1] in ['WorldSpace','FreeHem','ActualPants','GuidedHem','SingleSurface','StiffSingleSurface']
fitted = sys.argv[-1] in ['Fitted','Clamped','SoftBody','WorldSpace','FreeHem','ActualPants','GuidedHem','SingleSurface','StiffSingleSurface']
out = root/('ClothRefinement_SingleSurface' if single else 'ClothRefinement_GuidedHem' if guided else 'ClothRefinement_ActualPants' if actualpants else 'ClothRefinement_FreeLowerHem' if freehem else 'ClothRefinement_RebuiltWorldSpace' if worldspace else 'ClothRefinement_RebuiltSoftBody' if soft else 'ClothRefinement_RebuiltClamped' if clamped else 'ClothRefinement_RebuiltFitted' if fitted else 'ClothRefinement_RebuiltGrid'); out.mkdir(exist_ok=True)
if stiff: out=root/'ClothRefinement_StiffSingleSurface';out.mkdir(exist_ok=True)
if normal_contact: out=root/'ClothRefinement_NormalContact';out.mkdir(exist_ok=True)
if linear: out=root/'ClothRefinement_LinearBelt';out.mkdir(exist_ok=True)
if no_self: out=root/'ClothRefinement_NoSelfWorld';out.mkdir(exist_ok=True)
if anchor_fit: out=root/'ClothRefinement_AnchorFit';out.mkdir(exist_ok=True)
if center_anchor: out=root/'ClothRefinement_CenterAnchor';out.mkdir(exist_ok=True)
assert not (out/'validation.json').exists(), 'Do not overwrite a reviewed candidate'
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_SharedAppliedScale/Candidate.blend'))
s = bpy.context.scene; r = bpy.data.objects['RIG_Body_Medium']
signature, actions = base.signature(r), base.actions()
s.frame_set(1); r['BlenderCloth']=False; r.update_tag(); bpy.context.view_layer.update()
proxy=bpy.data.objects['SIM_Shared_Belt_Tails']
report = rebuild(proxy,r,fitted,anchor_fit)
if center_anchor:
    pin=proxy.vertex_groups['LiveCloth_Pin']
    for v in proxy.data.vertices:pin.add([v.index],1 if v.index%125==2 else 0,'REPLACE')
    report['center_knot_anchor']=True
if fitted: report['contact_collection']=garment_contact(s,next(m for m in proxy.modifiers if m.type=='CLOTH'))
if worldspace:
    report['world_scales']={o.name:normalize_world_mesh(o) for o in [proxy]+list(bpy.data.collections[report['contact_collection']].objects)}
if actualpants:
    if single:
        from single_surface_cloth_contact import separate_render_thickness
        report['render_surface']=separate_render_thickness(s,bpy.data.objects['Pants'],r)
        r['BlenderCloth']=True;r.update_tag();bpy.context.view_layer.update()
    from visible_garment_contact import configure as actual_contact
    cloth=next(m for m in proxy.modifiers if m.type=='CLOTH')
    old=cloth.collision_settings.collection
    report['evaluated_contact']=actual_contact(s,cloth,['Pants'])
    for o in old.objects:
        if o.name!='SIM_LowRes_Pants':cloth.collision_settings.collection.objects.link(o)
if stiff:
    cloth=next(m for m in proxy.modifiers if m.type=='CLOTH')
    cs=cloth.settings;cs.quality=60;cs.mass=.001;cs.bending_stiffness=30;cs.bending_damping=10;cs.air_damping=3
    cs.tension_stiffness=80;cs.compression_stiffness=80;cs.shear_stiffness=40
    cloth.collision_settings.collision_quality=8
    cloth.collision_settings.distance_min=.002
    report['stiff_belt_material']=True
    if normal_contact:
        for obj in cloth.collision_settings.collection.objects:
            obj.collision.use_normal=True
            obj.collision.use_culling=False
        report['outward_two_sided_contact']=True
    if linear:
        cs.bending_model='LINEAR';cs.bending_stiffness=5;cs.bending_damping=2
        report['linear_bending_model']=True
    if no_self:
        cloth.collision_settings.use_self_collision=False
        report['diagnostic_self_collision_disabled']=True
if freehem:
    contacts=bpy.data.collections.new('SIM_FreeHem_Pants_Contact');s.collection.children.link(contacts)
    contacts.objects.link(bpy.data.objects['SIM_Contact_Pants' if guided else 'SIM_LowRes_Pants'])
    for name in ['Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
        o=bpy.data.objects[name];normalize_world_mesh(o)
        pin=o.vertex_groups['LiveCloth_Pin'];top=max(v.co.z for v in o.data.vertices)
        for v in o.data.vertices:
            weight=max(0,min(1,(v.co.z-top+.065)/.03))
            pin.add([v.index],.35+.65*weight if guided else weight,'REPLACE')
        cloth=next(m for m in o.modifiers if m.type=='CLOTH');cs=cloth.settings
        cs.use_dynamic_mesh=False;cs.mass=.002;cs.quality=30;cs.bending_stiffness=2 if guided else .3;cs.bending_damping=2;cs.air_damping=3
        cloth.collision_settings.collection=contacts;cloth.collision_settings.use_self_collision=True;cloth.collision_settings.self_distance_min=.001
    report['free_lower_hem']=True
if clamped:
    cloth=next(m for m in proxy.modifiers if m.type=='CLOTH')
    cloth.collision_settings.self_impulse_clamp=.1
    cloth.collision_settings.impulse_clamp=.1
    pin=proxy.vertex_groups['LiveCloth_Pin'];exclude=proxy.vertex_groups.new(name='FixedRootContactExclusion')
    exclude.add([v.index for v in proxy.data.vertices if pin.weight(v.index)>0],1,'REPLACE')
    cloth.collision_settings.vertex_group_self_collisions=exclude.name
if soft:
    cloth=next(m for m in proxy.modifiers if m.type=='CLOTH');collection=cloth.collision_settings.collection
    for prop in ['show_viewport','show_render']:cloth.driver_remove(prop)
    proxy.modifiers.remove(cloth)
    mod=proxy.modifiers.new('Physical belt spring surface','SOFT_BODY');settings=proxy.soft_body
    settings.use_goal=True;settings.vertex_group_goal='LiveCloth_Pin';settings.goal_min=0;settings.goal_max=1;settings.goal_default=0;settings.goal_spring=.999;settings.goal_friction=5
    settings.mass=.002;settings.friction=2;settings.use_edges=True;settings.pull=.9;settings.push=.9;settings.damping=5;settings.bend=5;settings.use_stiff_quads=True
    settings.use_self_collision=True;settings.ball_size=.15;settings.ball_stiff=.8;settings.ball_damp=.5
    settings.collision_collection=collection;settings.use_edge_collision=True;settings.use_face_collision=True;settings.step_min=10;settings.step_max=100
    mod.point_cache.frame_start=1;mod.point_cache.frame_end=144
    for prop in ['show_viewport','show_render']:
        driver=mod.driver_add(prop).driver;v=driver.variables.new();v.name='live';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';driver.expression='live'
r['BlenderCloth']=True; r.update_tag(); bpy.context.view_layer.update()
s.cycles.samples=12
started=time.monotonic()
for frame in range(1,145):
    s.frame_set(frame); deps=bpy.context.evaluated_depsgraph_get()
    for name in ['Belt_Tail_Left','Belt_Tail_Right','Pants','Jacket_Front_Left','Jacket_Front_Right']:
        o=bpy.data.objects[name]; ev=o.evaluated_get(deps); mesh=ev.to_mesh()
        assert all(math.isfinite(c) and abs(c)<5 for v in mesh.vertices for c in o.matrix_world@v.co),(name,frame)
        ev.to_mesh_clear()
    if frame%12==0: print('FRAME',frame,round(time.monotonic()-started,1),flush=True)
    if frame in [1,26,35,72,144]:
        a.render(s,r,1,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,640,720)
        a.render(s,r,1,out,'Side_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,640,720)
assert base.signature(r)==signature and base.actions()==actions
s.frame_set(1); bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True)
report.update(frames=144,rig_actions_preserved=True,production_installed=False)
(out/'validation.json').write_text(json.dumps(report,indent=2))
