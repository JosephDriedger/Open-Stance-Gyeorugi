"""Reopen delivered dummy rigs and confirm animation, skeleton and source integrity."""
import bpy,sys,json,hashlib,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
root=Path(__file__).resolve().parents[2]/'Resources/Models/Animation/DummyMotionTests'
presets=['Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong']
rows=[]
for kind in presets:
    folder=root/kind;report=json.loads((folder/'validation.json').read_text())
    assert hashlib.sha256(Path(report['source']).read_bytes()).hexdigest()==report['source_sha256'],kind+' source changed'
    path=folder/('DummyMotion_'+kind+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene;rig=bpy.data.objects['RIG_Body_'+kind]
    assert len(rig.data.bones)==341 and len(report['tests'])==22
    assert rig.animation_data.action.name=='Dummy_FullBody_Range_'+kind
    assert scene.frame_end==1056 and scene.render.fps==24 and not rig.get('BlenderCloth',False)
    action=rig.animation_data.action;assert len(base.curves(action))>0
    scene.frame_set(1);bpy.context.view_layer.update()
    neutral={n:rig.pose.bones[n].matrix.copy() for n in ['upperarm_l','thigh_l','thigh_r','hand_l','foot_l']}
    checks=[]
    for label,bone in [('Arms_Overhead','upperarm_l'),('Side_Kick_L','thigh_l'),('Side_Kick_R','thigh_r'),('Wrists_Flexed','hand_l'),('Ankle_Flexed','foot_l')]:
        frame=next(t['peak'] for t in report['tests'] if t['pose']==label)
        scene.frame_set(frame);bpy.context.view_layer.update();matrix=rig.pose.bones[bone].matrix
        difference=max(abs(matrix[i][j]-neutral[bone][i][j]) for i in range(4) for j in range(4))
        assert difference>.001,(kind,label,'No limb motion')
        assert all(math.isfinite(v) for p in rig.pose.bones for row in p.matrix for v in row)
        checks.append({'pose':label,'bone':bone,'matrix_change':difference})
    rows.append({'preset':kind,'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reopened':True,'checks':checks})
    print('REOPEN_VERIFIED',kind,flush=True)
(root/'delivery_validation.json').write_text(json.dumps({'presets':9,'synthetic_only':True,'source_files_unchanged':True,'rows':rows},indent=2))
