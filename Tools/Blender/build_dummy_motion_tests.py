"""Build separate, labeled full-body deformation tests on the current nine rigs."""
import bpy,sys,json,hashlib,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_fighter_range as rom
import audit_sparring_styles as visual
import extend_garment_repairs as base
ROOT=rom.ROOT;OUT=ROOT/'Resources/Models/Animation/DummyMotionTests';OUT.mkdir(exist_ok=True)
labels=[p for p in rom.POSES if p!='Neutral']
for kind in sys.argv[sys.argv.index('--')+1:]:
    source=ROOT/'Resources/Models/Animation'/('OpenStance_'+kind+'_Animation.blend')
    out=OUT/kind;out.mkdir(exist_ok=True)
    assert not (out/'validation.json').exists(), 'Review an existing test instead of overwriting it'
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind]
    signature=base.signature(r);original_actions=base.actions()
    r.animation_data_create();r.animation_data.action=None
    for track in r.animation_data.nla_tracks:track.mute=True
    if 'BlenderCloth' in r:r['BlenderCloth']=False
    for prop in ['Wear_Jacket','Wear_Pants','Wear_Hair','Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards']:r[prop]=True
    r.update_tag();scene.frame_set(1);bpy.context.view_layer.update()
    scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
    action=bpy.data.actions.new('Dummy_FullBody_Range_'+kind);action.use_fake_user=True
    markers=[]
    for i,label in enumerate(labels):
        start=i*48+1
        for frame,pose in [(start,'Neutral'),(start+18,label),(start+28,label),(start+47,'Neutral')]:
            r.animation_data.action=None;scene.frame_set(frame);rom.pose(r,pose,scale)
            values={p.name:(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in r.pose.bones}
            r.animation_data.action=action
            for p in r.pose.bones:
                p.location,p.rotation_quaternion,p.scale=values[p.name]
                for channel in ['location','rotation_quaternion','scale']:p.keyframe_insert(channel,frame=frame,group=p.name)
        markers.append({'pose':label,'start':start,'peak':start+18,'end':start+47})
        scene.timeline_markers.new('TEST '+label,frame=start)
    for curve in base.curves(action):
        for key in curve.keyframe_points:key.interpolation='LINEAR'
    assert base.signature(r)==signature
    current_actions=base.actions()
    assert all(current_actions.get(k)==v for k,v in original_actions.items()),'Existing animation changed'
    scene.frame_start=1;scene.frame_end=len(labels)*48;scene.render.fps=24
    scene['TestPurpose']='Synthetic deformation tests, not captured motion or production combat choreography. Cloth is disabled to isolate skinning.'
    scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    for o in scene.objects:
        if o.get('MarkerLabel'):o.hide_render=True
    for label in ['Arms_Overhead','Side_Kick_L','Deep_Squat']:
        scene.frame_set(next(x['peak'] for x in markers if x['pose']==label));bpy.context.view_layer.update()
        visual.render(scene,r,scale,out,label,(.8,-4,1.7),(0,0,.96),2.35,480,540)
    scene.frame_set(1)
    rom.build.view.camera(scene,(.8*scale,-4*scale,1.7*scale),(0,0,.96*scale),2.35*scale)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(out/('DummyMotion_'+kind+'.blend')),compress=True)
    (out/'validation.json').write_text(json.dumps({'source':str(source),'source_sha256':source_hash,'rig_preserved':True,'original_actions_preserved':True,'synthetic_motion':True,'cloth_enabled':False,'fps':24,'frames':scene.frame_end,'tests':markers},indent=2))
    print('DUMMY_TEST_READY',kind,flush=True)
