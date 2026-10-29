"""Replace the Blender-cloth belt tails with a skinned bone chain driven by a verlet simulation.

Why: Blender cloth left the two tails curled, twisted or clipped through the pants in every
configuration tried (see Resources/Models/FinalRefinement/REMAINING_WORK.md). A chain of bones is
deterministic, exports to FBX as ordinary skeleton data and maps onto an Unreal AnimDynamics /
physics-asset chain at runtime. The verlet bake here is the Blender-side preview of that motion.

Usage (inside Blender, with a Body_Type_Studies .blend open):
    import belt_bone_chain as b; b.convert(); b.simulate(); b.bake()
"""
import bpy,math,time
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

SEGMENTS=8
COLLIDERS=['Pants','Jacket','Belt_Waistband','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']
TAILS=(('l','Belt_Tail_Left'),('r','Belt_Tail_Right'))
RAY_REACH=.3        # m: forward ray start in front of each particle
CLEARANCE=.012      # m: particle-centre offset from the garment surface
TAIL_HALF_WIDTH=.027  # m: edge of the 6 cm tail, tested as well as the centre line
SUBSTEPS=4
MAX_PUSH=.02       # m: largest collision correction per solver iteration
GROUP='BeltChain'

def rig_object():
    return next(o for o in bpy.data.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_'))

def convert():
    """Add belt_<side>_NN bones under pelvis, skin each tail to its chain, drop the cloth modifier."""
    rig=rig_object();W=rig.matrix_world;inv=W.inverted();scene=bpy.context.scene
    rig['BlenderCloth']=False;rig.update_tag();scene.frame_set(1)
    chains={}
    for side,name in TAILS:
        o=bpy.data.objects[name];pts=[o.matrix_world@v.co for v in o.data.vertices]
        top=max(p.z for p in pts);bottom=min(p.z for p in pts);cps=[]
        for k in range(SEGMENTS+1):
            z=top-(top-bottom)*k/SEGMENTS;window=(top-bottom)/SEGMENTS*.6
            sel=[p for p in pts if abs(p.z-z)<=window] or pts
            c=sum(sel,Vector())/len(sel);c.z=z;cps.append(c)
        chains[side]=cps
    with bpy.context.temp_override(active_object=rig,object=rig):bpy.ops.object.mode_set(mode='EDIT')
    eb=rig.data.edit_bones
    for side,cps in chains.items():
        parent=eb['pelvis']
        for k in range(SEGMENTS):
            b=eb.new(f'belt_{side}_{k+1:02d}');b.head=inv@cps[k];b.tail=inv@cps[k+1]
            b.parent=parent;b.use_connect=k>0;b.roll=0;parent=b
    with bpy.context.temp_override(active_object=rig,object=rig):bpy.ops.object.mode_set(mode='OBJECT')
    for side,name in TAILS:
        o=bpy.data.objects[name]
        for g in list(o.vertex_groups):
            if g.name in('pelvis','ClothPin','LiveCloth_Pin') or g.name.startswith('belt_'):o.vertex_groups.remove(g)
        for mod_name,typ in [(m.name,m.type) for m in o.modifiers]:
            if typ=='CLOTH' and o.animation_data:
                for d in list(o.animation_data.drivers):
                    if mod_name in d.data_path:o.animation_data.drivers.remove(d)
            if typ=='CLOTH' or mod_name in('Waist attachment','Belt chain'):o.modifiers.remove(o.modifiers[mod_name])
        groups=[o.vertex_groups.new(name=f'belt_{side}_{k+1:02d}') for k in range(SEGMENTS)]
        pts=[o.matrix_world@v.co for v in o.data.vertices];top=max(p.z for p in pts);bottom=min(p.z for p in pts)
        for v,p in zip(o.data.vertices,pts):
            x=max(0,min(SEGMENTS-1,(top-p.z)/(top-bottom)*SEGMENTS-.5));a=int(math.floor(x));f=x-a
            if a>=SEGMENTS-1:groups[-1].add([v.index],1,'REPLACE')
            else:groups[a].add([v.index],1-f,'REPLACE');groups[a+1].add([v.index],f,'REPLACE')
        mod=o.modifiers.new('Belt chain','ARMATURE');mod.object=rig
        with bpy.context.temp_override(active_object=o,object=o):bpy.ops.object.modifier_move_to_index(modifier='Belt chain',index=0)
        # smoothing modifier is driven by the old cloth flag; keep the subsurf on for the chain
        for m in o.modifiers:
            if m.type=='SUBSURF':
                if o.animation_data:
                    for d in list(o.animation_data.drivers):
                        if m.name in d.data_path:o.animation_data.drivers.remove(d)
                m.show_viewport=True;m.show_render=True
    return {s:[tuple(p) for p in c] for s,c in chains.items()}

def _bvh(dg,names):
    vs=[];ts=[]
    for n in names:
        o=bpy.data.objects[n].evaluated_get(dg);me=o.to_mesh();me.calc_loop_triangles();base=len(vs);mw=o.matrix_world
        vs+=[mw@v.co for v in me.vertices];ts+=[(base+t.vertices[0],base+t.vertices[1],base+t.vertices[2]) for t in me.loop_triangles];o.to_mesh_clear()
    return BVHTree.FromPolygons(vs,ts)

def simulate(shape_memory=.012,damping=.985,tail_gap=.025,iterations=8,bending=.2):
    """Verlet chains pinned at the knot; garments collide through a forward ray. Stores frames in driver_namespace."""
    scene=bpy.context.scene;rig=rig_object();W=rig.matrix_world;rig['BlenderCloth']=False;rig.update_tag()
    names=[n for n in COLLIDERS if n in bpy.data.objects];N=SEGMENTS
    scene.frame_set(1);dg=bpy.context.evaluated_depsgraph_get()
    pelvis=lambda dg:W@rig.evaluated_get(dg).pose.bones['pelvis'].matrix
    chains={sd:[W@rig.data.bones[f'belt_{sd}_{k+1:02d}'].head_local for k in range(N)]+[W@rig.data.bones[f'belt_{sd}_{N:02d}'].tail_local] for sd,_ in TAILS}
    seg={sd:[(pts[i+1]-pts[i]).length for i in range(N)] for sd,pts in chains.items()}
    pm0=pelvis(dg);inv0=pm0.inverted();fwd_local=inv0.to_3x3()@Vector((0,-1,0))
    side_local=inv0.to_3x3()@Vector((1,0,0))
    def clear(p,pm,bvh):
        # the tail is ~6 cm wide: test the centre and both edges, push forward by the worst one
        f=(pm.to_3x3()@fwd_local).normalized();side=(pm.to_3x3()@side_local).normalized();push=0.
        for lateral in (-TAIL_HALF_WIDTH,0.,TAIL_HALF_WIDTH):
            o=p+side*lateral+f*RAY_REACH;hit=bvh.ray_cast(o,-f,RAY_REACH+.06)
            if hit[0] is not None and hit[1].dot(f)>0:  # outer, forward-facing surface only
                s=(hit[0]-o).length;push=max(push,RAY_REACH-(s-CLEARANCE))
        return (p+f*push,True) if push>0 else (p,False)
    bvh=_bvh(dg,names)
    for sd in chains:
        for i in range(1,N+1):chains[sd][i],_=clear(chains[sd][i],pm0,bvh)
    rest={sd:[inv0@p for p in pts] for sd,pts in chains.items()}
    pos={sd:[p.copy() for p in chains[sd]] for sd in chains};prev={sd:[p.copy() for p in pos[sd]] for sd in chains}
    gravity=Vector((0,0,-9.81));dt=1/(scene.render.fps*SUBSTEPS);stats={'contacts':0}
    def step(bvh,pm):
        for sd in chains:
            P=pos[sd];Q=prev[sd]
            new=[pm@rest[sd][0] if i==0 else p+(p-Q[i])*damping+gravity*dt*dt for i,p in enumerate(P)]
            for _ in range(iterations):
                new[0]=pm@rest[sd][0]
                for i in range(1,N+1):new[i]=new[i]+(pm@rest[sd][i]-new[i])*shape_memory*max(0,1-i/(N+1))
                for i in range(N-1):  # woven cotton resists sharp folds: pull each joint toward its neighbours' line
                    ahead=new[i+1]+(new[i+1]-new[i]).normalized()*seg[sd][i+1];new[i+2]=new[i+2]+(ahead-new[i+2])*bending
                for i in range(1,N+1):
                    q,hit=clear(new[i],pm,bvh)
                    if hit:
                        delta=q-new[i]
                        if delta.length>MAX_PUSH:delta*=MAX_PUSH/delta.length
                        new[i]=new[i]+delta;stats['contacts']+=1
                new[0]=pm@rest[sd][0]
                for i in range(N):  # length constraints last, so a collision can never stretch the belt
                    a,b=new[i],new[i+1];d=b-a;L=d.length or 1e-9;err=(L-seg[sd][i])/L
                    if i==0:new[1]=b-d*err
                    else:new[i]=a+d*err*.5;new[i+1]=b-d*err*.5
            prev[sd]=P;pos[sd]=new
        for i in range(1,N+1):
            d=pos['l'][i]-pos['r'][i];L=d.length
            if 1e-6<L<tail_gap:c=d*(.5*(tail_gap-L)/L);pos['l'][i]+=c;pos['r'][i]-=c
    pm=pelvis(dg)
    for _ in range(120):step(bvh,pm)
    frames={}
    for f in range(scene.frame_start,scene.frame_end+1):
        for sub in range(SUBSTEPS):
            scene.frame_set(f-1 if f>1 else 1,subframe=(sub+1)/SUBSTEPS if f>1 else 0)
            dg=bpy.context.evaluated_depsgraph_get();step(_bvh(dg,names),pelvis(dg))
        frames[f]={sd:[p.copy() for p in pos[sd]] for sd in pos}
    scene.frame_set(1);bpy.app.driver_namespace['belt_frames']=frames
    return {'frames':len(frames),'contacts':stats['contacts']}

def bake():
    """Key the chain bones (rotation, plus knot location) into the rig's current action, group 'BeltChain'."""
    scene=bpy.context.scene;rig=rig_object();W=rig.matrix_world;Wi=W.inverted();rig['BlenderCloth']=False
    frames=bpy.app.driver_namespace['belt_frames'];bones=rig.data.bones;N=SEGMENTS
    for f in sorted(frames):
        scene.frame_set(f);ev=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for sd,_ in TAILS:
            pts=[Wi@p for p in frames[f][sd]]
            parent_arm=ev.pose.bones['pelvis'].matrix.copy();parent_rest=bones['pelvis'].matrix_local.copy()
            for k in range(N):
                name=f'belt_{sd}_{k+1:02d}';pb=rig.pose.bones[name];rest=bones[name].matrix_local
                expected=parent_arm@parent_rest.inverted()@rest
                q=(expected.to_3x3()@Vector((0,1,0))).normalized().rotation_difference((pts[k+1]-pts[k]).normalized())
                desired=Matrix.Translation(pts[k])@(q.to_matrix()@expected.to_3x3()).to_4x4()
                basis=expected.inverted()@desired
                pb.rotation_mode='QUATERNION';pb.rotation_quaternion=basis.to_quaternion()
                pb.location=basis.translation if k==0 else Vector((0,0,0))
                pb.keyframe_insert('rotation_quaternion',frame=f,group=GROUP)
                if k==0:pb.keyframe_insert('location',frame=f,group=GROUP)
                parent_arm=desired;parent_rest=rest
    scene.frame_set(1)

def crossings(frames=None):
    """Triangle-pair crossings per frame between each tail and the garments (sampled at integer frames)."""
    scene=bpy.context.scene;rig=rig_object();rig['BlenderCloth']=False;rows={}
    for f in (frames or range(scene.frame_start,scene.frame_end+1)):
        scene.frame_set(f);dg=bpy.context.evaluated_depsgraph_get()
        tl=_bvh(dg,['Belt_Tail_Left']);tr=_bvh(dg,['Belt_Tail_Right'])
        rows[f]=[len(t.overlap(_bvh(dg,[n]))) for n in ('Pants','Jacket','Belt_Waistband') if n in bpy.data.objects for t in (tl,tr)]
    return rows

def finish(kind,root=r'D:\Open-Stance-Gyeorugi\Resources\Models\FinalRefinement\BoneChainBelt'):
    """Bake, count crossings, render review frames and save a candidate copy next to them."""
    import json,os,sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).parent))
    import audit_sparring_styles as a
    scene=bpy.context.scene;rig=rig_object();out=Path(root)/kind;out.mkdir(parents=True,exist_ok=True)
    bake();rows=crossings()
    columns=('Pants L','Pants R','Jacket L','Jacket R','Waistband L','Waistband R')
    bad=[f for f,v in rows.items() if sum(v)>0]
    for p in out.glob('*.png'):p.unlink()
    scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578;scene.cycles.samples=8
    for f in (1,35,60,144):
        scene.frame_set(f)
        a.render(scene,rig,scale,out,'Close_%d'%f,(.2,-4,1.0),(0,0,.82),.55,480,480)
        a.render(scene,rig,scale,out,'Side_%d'%f,(-4,-1.2,1.0),(0,-.25,.85),.55,480,480)
    scene.frame_set(1);scene['ValidationStatus']='Experimental bone-chain belt tails; not installed as a master.'
    report={'source':bpy.data.filepath,'kind':kind,'frames':scene.frame_end,'columns':columns,
            'frames_with_crossings':bad,'max_pairs':[max(v[i] for v in rows.values()) for i in range(len(columns))],'production_installed':False}
    (out/'validation.json').write_text(json.dumps(report,indent=1))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Candidate.blend'),compress=True,copy=True)
    return {k:report[k] for k in ('kind','frames_with_crossings','max_pairs')}

def strip_keys():
    """Remove the baked chain keys so the belt bones sit at rest; runtime physics drives them in Unreal."""
    rig=rig_object();act=rig.animation_data.action;removed=0
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in [f for f in bag.fcurves if 'belt_' in f.data_path]:bag.fcurves.remove(fc);removed+=1
    for pb in rig.pose.bones:
        if pb.name.startswith('belt_'):pb.rotation_quaternion=(1,0,0,0);pb.location=(0,0,0)
    return removed

def export_fbx(path,names=('Body','Pants','Jacket','Belt','Belt_Waistband','Belt_Tail_Left','Belt_Tail_Right'),smooth='FACE',modifiers=True):
    """Export the rig plus the named meshes in centimetres with baked animation (no belt keys after strip_keys)."""
    rig=rig_object();rig['BlenderCloth']=False
    chosen=[bpy.data.objects[n] for n in names if n in bpy.data.objects]+[rig]
    for o in bpy.context.view_layer.objects:o.select_set(o in chosen)
    with bpy.context.temp_override(active_object=rig,object=rig,selected_objects=chosen,selected_editable_objects=chosen):
        return bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,
            bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,apply_scale_options='FBX_SCALE_NONE',
            use_armature_deform_only=False,mesh_smooth_type=smooth,use_mesh_modifiers=modifiers)
