"""Run with MotionBuilder's mobupy.exe; creates a separate characterized test FBX."""
from pathlib import Path
import json
import pyfbstandalone

pyfbstandalone.initialize()
from pyfbsdk import *

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Resources/Models/MotionBuilder'
OUT.mkdir(parents=True, exist_ok=True)
app = FBApplication()
assert app.FileOpen(str(ROOT / 'Resources/Models/Fighter_Rigged.fbx'), False)
scene = FBSystem().Scene
character = FBCharacter('OpenStance_TestFighter')
mapping = {
    'Reference': 'root', 'Hips': 'pelvis', 'Spine': 'spine_01',
    'Spine1': 'spine_02', 'Spine2': 'spine_03', 'Spine3': 'spine_04',
    'Spine4': 'spine_05', 'Neck': 'neck_01', 'Neck1': 'neck_02', 'Head': 'head',
}
for prefix, side in [('Left', 'l'), ('Right', 'r')]:
    for slot, bone in [('Shoulder', 'clavicle'), ('Arm', 'upperarm'),
                       ('ForeArm', 'lowerarm'), ('Hand', 'hand'),
                       ('UpLeg', 'thigh'), ('Leg', 'calf'), ('Foot', 'foot'),
                       ('ToeBase', 'ball')]:
        mapping[prefix + slot] = bone + '_' + side
    for finger in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']:
        for joint in range(1, 4):
            mapping[f'{prefix}Hand{finger}{joint}'] = f'{finger.lower()}_{joint:02}_{side}'
for slot, bone in mapping.items():
    model = FBFindModelByLabelName(bone)
    prop = character.PropertyList.Find(slot + 'Link')
    if model is None or prop is None:
        raise RuntimeError(f'Missing mapping: {slot} -> {bone}')
    prop.append(model)
scene.Evaluate()
if not character.SetCharacterizeOn(True):
    raise RuntimeError(character.GetCharacterizeError())
assert character.CreateControlRig(True), 'Control rig creation failed'
app.CurrentCharacter = character
character.InputType = FBCharacterInputType.kFBCharacterInputMarkerSet
character.ActiveInput = True
scene.Evaluate()

# Check that a control can actually drive the skeleton, then restore the pose.
effector = character.GetEffectorModel(FBEffectorId.kFBLeftWristEffectorId)
hand = FBFindModelByLabelName('hand_l')
def position(model):
    value = FBVector3d()
    model.GetVector(value, FBModelTransformationType.kModelTranslation, True)
    return list(value)
before = position(hand)
original = position(effector)
original_local = list(effector.Translation)
effector.Translation.SetAnimated(True)
effector.PropertyList.Find('IK Reach Translation').Data = 100.0
target_local = [original_local[0], original_local[1] + 20, original_local[2] + 20]
for node, value, start in zip(effector.Translation.GetAnimationNode().Nodes, target_local, original_local):
    node.FCurve.KeyAdd(FBTime(0, 0, 0, 0), start)
    node.FCurve.KeyAdd(FBTime(0, 0, 0, 30), value)
FBPlayerControl().Goto(FBTime(0, 0, 0, 30))
scene.Evaluate()
after = position(hand)
movement = sum((b-a)**2 for a,b in zip(before, after))**.5
assert movement > 5, f'Wrist control did not drive the hand: {movement}'
for node, value in zip(effector.Translation.GetAnimationNode().Nodes, original_local):
    node.FCurve.EditClear()
    node.FCurve.KeyAdd(FBTime(0), value)
scene.Evaluate()
character.SetTranslationPin(FBEffectorId.kFBLeftWristEffectorId, False)
FBPlayerControl().Goto(FBTime(0, 0, 0, 0))
FBSystem().CurrentTake.Name = 'Reference_ReadyForMocap'
options = FBFbxOptions(False)
options.EmbedMedia = True
output = OUT / 'OpenStance_TestFighter.fbx'
assert app.FileSave(str(output), options), 'FBX save failed'

# Verify the delivered file, not just the in-memory setup.
assert app.FileOpen(str(output), False)
reopened = next(c for c in FBSystem().Scene.Characters if c.Name == 'OpenStance_TestFighter')
assert reopened.GetCharacterize(), 'Characterization lost on save'
assert reopened.GetCurrentControlSet() is not None, 'Control rig lost on save'
report = {'source': 'Resources/Models/Fighter_Rigged.fbx', 'output': str(output),
          'character': reopened.Name, 'mapped_slots': len(mapping),
          'characterized': True, 'control_rig': True, 'reopened_successfully': True,
          'wrist_control_hand_movement_cm': movement,
          'visual_deformation_checked': False, 'mocap_applied': False}
(OUT / 'validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
