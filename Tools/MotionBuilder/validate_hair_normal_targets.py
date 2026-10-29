"""Open patched targets and test the existing control rig without saving changes."""
import sys,json,hashlib,os
from pathlib import Path
import pyfbstandalone
pyfbstandalone.initialize()
from pyfbsdk import *
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/HairNormalDelivery'
OUT=Path(os.environ.get('OPENSTANCE_PATCH_DELIVERY',str(OUT)))
source=OUT/'Files'/sys.argv[-1]
assert FBApplication().FileOpen(str(source),False)
scene=FBSystem().Scene
characters=list(scene.Characters);assert len(characters)==1
character=characters[0];assert character.GetCharacterize() and character.GetCurrentControlSet() is not None
effector=character.GetEffectorModel(FBEffectorId.kFBLeftWristEffectorId);hand=FBFindModelByLabelName('hand_l')
assert effector and hand
def position(model):
    vector=FBVector3d();model.GetVector(vector,FBModelTransformationType.kModelTranslation,True);return list(vector)
before=position(hand);original=list(effector.Translation)
character.InputType=FBCharacterInputType.kFBCharacterInputMarkerSet;character.ActiveInput=True
effector.PropertyList.Find('IK Reach Translation').Data=100.;effector.Translation.SetAnimated(True)
for node,start,offset in zip(effector.Translation.GetAnimationNode().Nodes,original,[0,20,20]):
    node.FCurve.KeyAdd(FBTime(0),start);node.FCurve.KeyAdd(FBTime(0,0,0,30),start+offset)
FBPlayerControl().Goto(FBTime(0,0,0,30));scene.Evaluate();after=position(hand)
movement=sum((b-a)**2 for a,b in zip(before,after))**.5;assert movement>5,movement
result={'file':sys.argv[-1],'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'characterized':True,'control_rig':True,'wrist_movement_cm':movement,'original_file_not_saved':True}
folder=OUT/'MotionBuilderChecks';folder.mkdir(exist_ok=True)
(folder/(hashlib.sha256(sys.argv[-1].encode()).hexdigest()[:16]+'.json')).write_text(json.dumps(result,indent=2))
print('MOTIONBUILDER_PATCH_CHECK_PASSED',source,flush=True)
