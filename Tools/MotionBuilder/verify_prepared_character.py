"""Fresh-process verification; never overwrites the delivered FBX."""
import argparse,json,hashlib
from pathlib import Path
import pyfbstandalone
pyfbstandalone.initialize()
from pyfbsdk import *
parser=argparse.ArgumentParser();parser.add_argument('--preparation',required=True);args=parser.parse_args()
path=Path(args.preparation);report=json.loads(path.read_text());output=Path(report['output'])
before_hash=hashlib.sha256(output.read_bytes()).hexdigest();app=FBApplication();app.FileNew();FBSystem().Scene.Evaluate();assert app.FileOpen(str(output),False)
scene=FBSystem().Scene;character=next(c for c in scene.Characters if c.Name==report['character'])
assert character.GetCharacterize() and character.GetCurrentControlSet() is not None
slots=['Reference','Hips','Spine','Spine1','Spine2','Spine3','Spine4','Neck','Neck1','Head']
for prefix in ('Left','Right'):
    slots += [prefix+s for s in ('Shoulder','Arm','ForeArm','Hand','UpLeg','Leg','Foot','ToeBase')]
    slots += [f'{prefix}Hand{finger}{joint}' for finger in ('Thumb','Index','Middle','Ring','Pinky') for joint in range(1,4)]
for slot in slots:
    link=character.PropertyList.Find(slot+'Link');assert link is not None and len(link)>0,slot
app.CurrentCharacter=character;effector=character.GetEffectorModel(FBEffectorId.kFBLeftWristEffectorId);hand=FBFindModelByLabelName('hand_l')
def position(model):
    value=FBVector3d();model.GetVector(value,FBModelTransformationType.kModelTranslation,True);return list(value)
player=FBPlayerControl();player.Goto(FBTime(0));scene.Evaluate();before=position(hand);local=list(effector.Translation)
effector.Translation.SetAnimated(True);effector.PropertyList.Find('IK Reach Translation').Data=100.0
for node,value in zip(effector.Translation.GetAnimationNode().Nodes,local):
    node.FCurve.EditClear();node.FCurve.KeyAdd(FBTime(0),value)
for axis,(node,value) in enumerate(zip(effector.Translation.GetAnimationNode().Nodes,local)):
    node.FCurve.KeyAdd(FBTime(0,0,0,30),value+(20 if axis in (1,2) else 0))
player.Goto(FBTime(0,0,0,30));scene.Evaluate();after=position(hand)
movement=sum((b-a)**2 for a,b in zip(before,after))**.5;assert movement>5,movement
assert before_hash==hashlib.sha256(output.read_bytes()).hexdigest()
report.update(reopened_successfully=True,fresh_process_verification=True,mapped_slots=len(slots),
              reopened_wrist_control_movement_cm=movement,output_sha256=before_hash,
              delivered_file_unchanged_by_test=True,visual_deformation_checked=False,mocap_applied=False)
(path.parent/f'validation_{report["character"]}.json').write_text(json.dumps(report,indent=2));print('FRESH_REOPEN_PASS',report['character'],flush=True)
