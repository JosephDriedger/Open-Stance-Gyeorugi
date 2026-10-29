"""Review the candidate from original studies, preserving all source files."""
import bpy,sys,json,hashlib,math,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
import extend_garment_repairs as base
from linear_belt_physics_candidate import configure
root=a.ROOT/'Resources/Models'
args=sys.argv[sys.argv.index('--')+1:]
modes={
    'linear':(False,False,False,0.0,'LinearBeltPresets'),
    'anchor-fit':(True,False,False,0.0,'AnchorBeltPresets'),
    'center-fit':(True,True,False,0.0,'CenterBeltPresets'),
    'render-clearance':(True,True,True,0.0,'ClearanceBeltPresets'),
    'full-clearance':(True,True,True,.005,'ThicknessBeltPresets'),
    'balanced-clearance':(True,True,True,.003,'BalancedBeltPresets'),
    'knot-clearance':(True,True,True,.003,'KnotBeltPresets'),
    'stable-contact':(True,True,True,.003,'StableBeltPresets'),
    'mass-contact':(True,True,True,.003,'MassBeltPresets'),
    'mass-verified':(True,True,True,.003,'MassVerifiedBeltPresets'),
    'soft-world':(True,True,True,.003,'SoftWorldBeltPresets'),
}
mode=args.pop(0) if args[0] in modes else 'linear'
anchor_fit,center_anchor,render_clearance,self_clearance,folder=modes[mode]
for kind in args:
    source=root/'Animation/Physics/Body_Type_Studies'/('SecondaryCloth_'+kind+'_Wrap.blend')
    out=root/'FinalRefinement'/folder/kind;out.mkdir(parents=True,exist_ok=True)
    assert not (out/'validation.json').exists(),'Do not overwrite reviewed output'
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
    rig_kind=kind.replace('_Straight_Punches','');r=bpy.data.objects['RIG_Body_'+rig_kind]
    signature,actions=base.signature(r),base.actions()
    original={name:([tuple(v.co) for v in bpy.data.objects[name].data.vertices],
        {k.name:[tuple(v.co) for v in k.data] for k in bpy.data.objects[name].data.shape_keys.key_blocks} if bpy.data.objects[name].data.shape_keys else {})
        for name in ['Belt_Tail_Left','Belt_Tail_Right']}
    report=configure(s,r,anchor_fit,center_anchor,render_clearance,self_clearance);scale=report['scale'];s.cycles.samples=8
    end_frame=288 if mode in ['knot-clearance','stable-contact','mass-contact','mass-verified','soft-world'] else 144
    s.frame_end=end_frame
    if mode in ['knot-clearance','stable-contact','mass-contact','mass-verified','soft-world']:
        proxy=bpy.data.objects['SIM_Shared_Belt_Tails'];cloth=next(m for m in proxy.modifiers if m.type=='CLOTH')
        group=proxy.vertex_groups.new(name='KnotInterior_NoSelfContact')
        group.add([v.index for v in proxy.data.vertices if v.index%125<5],1,'REPLACE')
        cloth.collision_settings.vertex_group_self_collisions=group.name
        report['knot_interior_excluded_from_self_collision']=True
        if mode in ['stable-contact','mass-contact','mass-verified','soft-world']:
            from stable_garment_collision import replace_pants
            report['stable_collision_surface']=replace_pants(s,cloth)
        if mode in ['mass-contact','mass-verified','soft-world']:
            from normalize_uniform_cloth_mass import configure as mass
            report['uniform_mass']=mass(s)
        if mode=='soft-world':
            contacts=cloth.collision_settings.collection
            for prop in ['show_viewport','show_render']:cloth.driver_remove(prop)
            proxy.modifiers.remove(cloth)
            modifier=proxy.modifiers.new('Physical woven belt springs','SOFT_BODY');settings=proxy.soft_body
            settings.use_goal=True;settings.vertex_group_goal='LiveCloth_Pin';settings.goal_min=0;settings.goal_max=1;settings.goal_default=0
            settings.goal_spring=.999;settings.goal_friction=8;settings.mass=.001;settings.friction=6
            settings.use_edges=True;settings.pull=.9;settings.push=.9;settings.damping=8;settings.bend=5;settings.use_stiff_quads=True
            settings.use_self_collision=True;settings.ball_size=.45;settings.ball_stiff=.8;settings.ball_damp=.5
            settings.collision_collection=contacts;settings.use_edge_collision=True;settings.use_face_collision=True;settings.step_min=20;settings.step_max=200
            modifier.point_cache.frame_start=1;modifier.point_cache.frame_end=end_frame
            for prop in ['show_viewport','show_render']:
                driver=modifier.driver_add(prop).driver;v=driver.variables.new();v.name='live';v.targets[0].id=r;v.targets[0].data_path='["BlenderCloth"]';driver.expression='live'
            report['belt_solver']='Blender Soft Body on world-space simulation mesh'
    for o in s.objects:
        for modifier in o.modifiers:
            if modifier.type=='CLOTH':modifier.point_cache.frame_end=end_frame
    for name,(coords,keys) in original.items():
        o=bpy.data.objects[name];assert [tuple(v.co) for v in o.data.vertices]==coords
        if keys:assert {k.name:[tuple(v.co) for v in k.data] for k in o.data.shape_keys.key_blocks}==keys
    started=time.monotonic()
    for frame in range(1,end_frame+1):
        s.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get()
        for name in ['Belt_Tail_Left','Belt_Tail_Right','Pants','Jacket_Front_Left','Jacket_Front_Right']:
            o=bpy.data.objects[name];ev=o.evaluated_get(deps);me=ev.to_mesh()
            assert all(math.isfinite(x) and abs(x)<5 for v in me.vertices for x in o.matrix_world@v.co),(kind,name,frame)
            ev.to_mesh_clear()
        if frame%24==0:print('PRESET',kind,frame,round(time.monotonic()-started,1),flush=True)
        if frame in [26,35,144,end_frame]:
            a.render(s,r,scale,out,'Front_'+str(frame),(.2,-4,1.3),(0,0,.96),1.25,480,540)
            a.render(s,r,scale,out,'Side_'+str(frame),(4,-.8,1.65),(0,-.3,.95),2.25,480,540)
    assert base.signature(r)==signature and base.actions()==actions
    assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
    s.frame_set(1);s['ValidationStatus']='Experimental linear-bending belt candidate; not production approved.'
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True)
    report.update(source=str(source),source_sha256=sha,frames=end_frame,original_belt_geometry_preserved=True,rig_actions_preserved=True,production_installed=False)
    (out/'validation.json').write_text(json.dumps(report,indent=2))
