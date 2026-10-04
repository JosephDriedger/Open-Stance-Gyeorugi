"""Build native Blender animation scenes from the approved modular creator fighters.
Run headless; never touches an existing interactive Blender session.
"""
from pathlib import Path
import json, math, re, shutil, sys, traceback
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'Resources/Models/CreatorFighters'
OUT=ROOT/'Resources/Models/Animation'
OUT.mkdir(parents=True,exist_ok=True)
ARGS=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TYPES=ARGS or ['Compact','Medium','Stocky','LeanTall','Tall']
sys.path.insert(0,str(Path(__file__).parent))
sys.argv=[sys.argv[0]]
import build_test_model as base
LOG=ROOT/'Saved/Logs/build_animation_workspace.txt'
LOG.write_text('')
def log(*args):
    with LOG.open('a') as f:f.write(' '.join(map(str,args))+'\n')

def update():
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

def organize(scene, obj, collection):
    for old in list(obj.users_collection):old.objects.unlink(obj)
    collection.objects.link(obj)

def collection(scene,name):
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

def evaluated_positions(obj):
    update()
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.array([tuple(e.matrix_world@v.co) for v in e.data.vertices])

def restore_face(kind,body_arm,anatomy,rigs):
    current=bpy.data.objects['Head']
    mats=list(current.data.materials)
    asset='MH_FighterBase' if kind=='Medium' else f'MH_Fighter{kind}'
    objects=base.import_fbx(str(ROOT/f'Resources/Models/MetaHuman/{asset}_Head.fbx'))
    arm=next(o for o in objects if o.type=='ARMATURE')
    mesh=max((o for o in objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    world=arm.matrix_world.copy();arm.parent=None;arm.matrix_world=world
    mi=[p.material_index for p in mesh.data.polygons]
    base.delete_faces(mesh,[i not in base.HEAD_KEEP for i in mi])
    remap={0:0,1:1,3:2,4:2,6:3}
    kept=[remap[p.material_index] for p in mesh.data.polygons]
    mesh.data.materials.clear()
    for m in mats:mesh.data.materials.append(m)
    for p,i in zip(mesh.data.polygons,kept):p.material_index=i
    bpy.data.objects.remove(current,do_unlink=True)
    mesh.name='Head'
    arm.name=f'RIG_Face_{kind}'
    base.bind(mesh,arm)
    for obj in objects:
        if obj not in (mesh,arm):bpy.data.objects.remove(obj,do_unlink=True)
    common=set(body_arm.data.bones.keys()) & set(arm.data.bones.keys())
    for name in common:
        c=arm.pose.bones[name].constraints.new('COPY_TRANSFORMS')
        c.name='Follow body motion'
        c.target=body_arm;c.subtarget=name
        c.target_space=c.owner_space='WORLD'
    organize(bpy.context.scene,mesh,anatomy);organize(bpy.context.scene,arm,rigs)
    # Scalp and eyebrow strands follow nearby facial skin, retaining future expression support.
    hair=bpy.data.objects['Hair_Buzzcut']
    tree=KDTree(len(mesh.data.vertices))
    for v in mesh.data.vertices:tree.insert(mesh.matrix_world@v.co,v.index)
    tree.balance()
    hair.vertex_groups.clear();groups={}
    names={g.index:g.name for g in mesh.vertex_groups}
    for v in hair.data.vertices:
        _,i,_=tree.find(hair.matrix_world@v.co)
        weights={names[g.group]:g.weight for g in mesh.data.vertices[i].groups if names[g.group] in arm.data.bones}
        total=sum(weights.values())
        if not total:weights={'head':1};total=1
        for n,w in weights.items():
            if n not in groups:groups[n]=hair.vertex_groups.new(name=n)
            groups[n].add([v.index],w/total,'REPLACE')
    base.bind(hair,arm)
    arm['Purpose']='Facial FK animation; shared body bones follow the body rig. No DNA/RigLogic solver installed in Blender.'
    return arm,mesh

def bone_collections(arm,face=False):
    for c in list(arm.data.collections):arm.data.collections.remove(c)
    groups={n:arm.data.collections.new(n) for n in (['Face_Keyable','Face_Detail','Body_Followers'] if face else ['Body_FK','Hands_FK','Toes_FK','Helpers_Correctives'])}
    for bone in arm.data.bones:
        if face:
            if not bone.name.startswith('FACIAL'):key='Body_Followers'
            elif any(x in bone.name for x in ('Jaw','Eye','Brow','Lip','Mouth')) and not '12IPV' in bone.name:key='Face_Keyable'
            else:key='Face_Detail'
        elif re.search(r'^(thumb|index|middle|ring|pinky)_(metacarpal|0[123])_[lr]$',bone.name):key='Hands_FK'
        elif 'toe_' in bone.name:key='Toes_FK'
        elif bone.name in base.MAIN_BONES:key='Body_FK'
        else:key='Helpers_Correctives'
        groups[key].assign(bone)
        bone.hide=False
    for key,c in groups.items():c.is_visible=key in ('Body_FK','Face_Keyable')
    arm.show_in_front=True;arm.data.display_type='STICK';arm.hide_set(False)
    for pb in arm.pose.bones:
        pb.rotation_mode='QUATERNION'
        pb.bone.color.palette='THEME03' if pb.name.endswith('_l') else 'THEME04' if pb.name.endswith('_r') else 'THEME02'

def add_marker_guides(arm,coll,kind):
    joint=lambda n:arm.matrix_world@arm.data.bones[n].head_local
    markers={}
    def add(label,bone,pos):markers[label]=(bone,Vector(pos))
    h=joint('head');pel=joint('pelvis')
    for side,prefix,sign in [('l','L',1),('r','R',-1)]:
        add(prefix+'FHD','head',h+Vector((sign*.055,-.075,.075)))
        add(prefix+'BHD','head',h+Vector((sign*.055,.065,.075)))
        add(prefix+'ASI','pelvis',pel+Vector((sign*.09,-.09,.02)))
        add(prefix+'PSI','pelvis',pel+Vector((sign*.07,.07,.02)))
        u,e,w=[joint(n+'_'+side) for n in ('upperarm','lowerarm','hand')]
        add(prefix+'SHO','clavicle_'+side,u+Vector((0,0,.045)))
        add(prefix+'UPA','upperarm_'+side,(u+e)/2+Vector((sign*.045,0,0)))
        add(prefix+'ELB','lowerarm_'+side,e+Vector((sign*.04,0,0)))
        add(prefix+'FRM','lowerarm_'+side,(e+w)/2+Vector((0,.035,0)))
        add(prefix+'WRA','hand_'+side,w+Vector((sign*.025,-.01,0)))
        add(prefix+'WRB','hand_'+side,w+Vector((-sign*.025,.01,0)))
        add(prefix+'FIN','hand_'+side,joint('index_01_'+side))
        hip,knee,ankle=[joint(n+'_'+side) for n in ('thigh','calf','foot')]
        add(prefix+'THI','thigh_'+side,(hip+knee)/2+Vector((sign*.055,0,0)))
        add(prefix+'KNE','calf_'+side,knee+Vector((sign*.045,0,0)))
        add(prefix+'TIB','calf_'+side,(knee+ankle)/2+Vector((sign*.04,0,0)))
        add(prefix+'ANK','foot_'+side,ankle+Vector((sign*.035,0,0)))
        add(prefix+'HEE','foot_'+side,ankle+Vector((0,.035,-.035)))
        ball=joint('ball_'+side)
        add(prefix+'TOE','foot_'+side,ball+Vector((0,-.025,.015)))
        add(prefix+'MT5','foot_'+side,ball+Vector((sign*.04,0,.005)))
    for label,bone,offset in [('C7','neck_01',(0,.065,0)),('T10','spine_03',(0,.12,0)),('CLAV','spine_05',(0,-.09,.02)),('STRN','spine_04',(0,-.12,-.035)),('RBAK','spine_05',(-.08,.08,-.04))]:
        add(label,bone,joint(bone)+Vector(offset))
    expected=[]
    for line in (ROOT/'Docs/Mocap_Marker_Set.md').read_text(encoding='utf-8').splitlines():
        cells=line.split('|')
        if len(cells)>4 and cells[1].strip() in ('Head','Torso','Arms','Hands','Pelvis','Legs','Feet','Feet, additional'):
            expected.extend(x.strip() for x in cells[2].split(','))
    assert set(markers)==set(expected) and len(markers)==41
    arm['Show_Marker_Guides']=False
    for label,(bone,p) in markers.items():
        o=bpy.data.objects.new(label,None);coll.objects.link(o)
        o.empty_display_type='SPHERE';o.empty_display_size=.008
        o.show_name=True;o.hide_render=True
        o.parent=arm;o.parent_type='BONE';o.parent_bone=bone
        bpy.context.view_layer.update();o.matrix_world=Matrix.Translation(p)
        o['MarkerLabel']=label;o['Purpose']='Approximate reference only; not calibrated actor-marker placement or captured data.'
        d=o.driver_add('hide_viewport').driver;d.type='SCRIPTED'
        var=d.variables.new();var.name='show';var.type='SINGLE_PROP';var.targets[0].id=arm;var.targets[0].data_path='["Show_Marker_Guides"]'
        d.expression='1-show'
    return {label:bone for label,(bone,p) in markers.items()}

def sample_action(arm,name,rotations):
    arm.animation_data_create();arm.animation_data.action=None
    for p in arm.pose.bones:p.matrix_basis=Matrix()
    for frame,amount in [(1,0),(16,1),(32,0)]:
        for bone,axis,angle in rotations:
            pb=arm.pose.bones[bone]
            from mathutils import Quaternion
            pb.rotation_quaternion=Quaternion(axis,angle*amount)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=bone)
    act=arm.animation_data.action;act.name=name;act.use_fake_user=True
    arm.animation_data.action=None
    for p in arm.pose.bones:p.matrix_basis=Matrix()
    update()
    return act

def build(kind):
    bpy.ops.wm.open_mainfile(filepath=str(LIB/kind/f'OpenStance_Creator_{kind}.blend'))
    scene=bpy.context.scene;scene.name=f'Fighter_{kind}'
    arm=bpy.data.objects['root'];arm.name=f'RIG_Body_{kind}'
    arm['RigRole']='Production MetaHuman deformation rig. Key these FK bones, or retarget solved mocap here.'
    anatomy=collection(scene,'01_Anatomy');uniform=collection(scene,'02_White_Dobok');gear=collection(scene,'03_Sparring_Gear');rigs=collection(scene,'04_Animation_Rigs');markers=collection(scene,'05_Marker_Reference');studio=collection(scene,'06_Studio')
    for o in list(scene.objects):
        target=rigs if o.type=='ARMATURE' else anatomy if o.name in ('Body','Head','Hair_Buzzcut') else uniform if o.name in ('Jacket','Pants','Belt') else gear if o.name in ('Helmet','Protector','Gloves','FootGuards') else studio
        organize(scene,o,target)
    face,head=restore_face(kind,arm,anatomy,rigs)
    bone_collections(arm);bone_collections(face,True)
    face.hide_set(True) # unhide to key facial joints; body rig is the default selection
    for o in studio.objects:o.hide_select=True
    marker_map=add_marker_guides(arm,markers,kind)
    fk=sample_action(arm,f'DIAG_FK_Reach_{kind}',[('upperarm_l',(1,0,0),.35),('lowerarm_l',(0,0,1),.55),('spine_03',(0,1,0),.12)])
    fingers=[(n,(1,0,0),.65) for n in arm.data.bones.keys() if re.match(r'^(thumb|index|middle|ring|pinky)_0[123]_[lr]$',n)]
    finger=sample_action(arm,f'DIAG_Finger_Curl_{kind}',fingers)
    jaw_name=next(n for n in face.data.bones.keys() if n=='FACIAL_C_Jaw')
    jaw=sample_action(face,f'DIAG_Jaw_Open_{kind}',[(jaw_name,(1,0,0),.12)])
    # Validate actual deformation, rather than bone names alone.
    neutral=evaluated_positions(bpy.data.objects['Body'])
    arm.animation_data.action=fk;scene.frame_set(16);bpy.context.view_layer.update()
    body=bpy.data.objects['Body'];evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    posed=np.array([tuple(evaluated.matrix_world@v.co) for v in evaluated.data.vertices])
    body_move=float(np.linalg.norm(posed-neutral,axis=1).max())
    assert body_move>.005,body_move
    arm.animation_data.action=None
    for pb in arm.pose.bones:pb.matrix_basis=Matrix()
    neutral_face=evaluated_positions(head)
    face.animation_data.action=jaw;scene.frame_set(16);bpy.context.view_layer.update()
    e=head.evaluated_get(bpy.context.evaluated_depsgraph_get())
    jaw_move=float(np.linalg.norm(np.array([tuple(e.matrix_world@v.co) for v in e.data.vertices])-neutral_face,axis=1).max())
    assert jaw_move>.0001,jaw_move
    face.animation_data.action=None
    for pb in face.pose.bones:pb.matrix_basis=Matrix()
    update()
    # Keep animation layers muted in the delivered rest-pose scene.
    for label,action in [('01_Mocap_Base__empty',None),('02_HandKeyed_Body',fk),('03_Finger_Overrides',finger)]:
        track=arm.animation_data.nla_tracks.new();track.name=label;track.mute=True
        if action:track.strips.new(action.name,1,action)
    ft=face.animation_data.nla_tracks.new();ft.name='Facial_Animation';ft.mute=True;ft.strips.new(jaw.name,1,jaw)
    # Blank keyable action ready for authored animation.
    arm.animation_data.action=None
    arm.pose.bones['pelvis'].keyframe_insert('rotation_quaternion',frame=1,group='pelvis')
    arm.animation_data.action.name=f'ANIM_New_{kind}'
    arm.animation_data.action.use_fake_user=True
    scene.frame_start=1;scene.frame_end=120;scene.render.fps=30
    # Create a persistent native bone selection; no add-on is required to animate.
    bpy.ops.object.select_all(action='DESELECT');arm.hide_set(False);arm.select_set(True);bpy.context.view_layer.objects.active=arm
    arm.data.bones.active=arm.data.bones['pelvis']
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.overlay.show_overlays=True
                space.region_3d.view_perspective='CAMERA'
    for c in list(bpy.data.collections):
        if not c.objects and not c.children:bpy.data.collections.remove(c)
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file:
            try:image.pack()
            except RuntimeError:pass
    text=bpy.data.texts.new('START_HERE.txt');text.write((OUT/'README.md').read_text())
    report={'body_type':kind,'body_bones':len(arm.data.bones),'face_bones':len(face.data.bones),'marker_count':len(marker_map),'marker_bones':marker_map,'body_fk_deformation_m':body_move,'jaw_deformation_m':jaw_move,'capture_solve_verified':False,'facial_riglogic':False,'parts':[o.name for o in anatomy.objects]+[o.name for o in uniform.objects]+[o.name for o in gear.objects]}
    (OUT/f'{kind}_rig_validation.json').write_text(json.dumps(report,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'OpenStance_{kind}_Animation.blend'),compress=True)
    log(kind,'DONE',report['body_bones'],report['face_bones'],body_move,jaw_move)

try:
    for kind in TYPES:build(kind)
except Exception:
    log(traceback.format_exc());raise
