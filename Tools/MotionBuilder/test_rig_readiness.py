"""Run with mobupy.exe. Exercise the existing rig and save only a scratch copy."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pyfbstandalone
pyfbstandalone.initialize()
from pyfbsdk import *

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx'
OUT = ROOT / 'tmp/mocap_rig_readiness' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT.mkdir(parents=True, exist_ok=False)
report = {'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'passed': False, 'captured_motion_tested': False, 'visual_clipping_checked': False}
app = FBApplication()


def position(model):
    value = FBVector3d()
    model.GetVector(value, FBModelTransformationType.kModelTranslation, True)
    return list(value)


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def load(path):
    assert app.FileOpen(str(path), False), f'Cannot open {path}'
    scene = FBSystem().Scene
    characters = list(scene.Characters)
    assert len(characters) == 1, f'Expected one character, found {len(characters)}'
    char = characters[0]
    assert char.GetCharacterize(), 'Character is not characterized'
    assert char.GetCurrentControlSet() is not None, 'Missing control rig'
    app.CurrentCharacter = char
    char.InputType = FBCharacterInputType.kFBCharacterInputMarkerSet
    char.ActiveInput = True
    scene.Evaluate()
    return scene, char


def sample_meshes(scene):
    result = {}
    for model in scene.Components:
        if isinstance(model, FBModel) and model.Geometry and model.IsDeformable:
            values = model.ModelVertexData.GetVertexArray(FBGeometryArrayID.kFBGeometryArrayID_Point, True)
            assert values and all(math.isfinite(v) for v in values), f'Invalid mesh data: {model.Name}'
            # Gear uses metre-sized local geometry under a 100x model transform;
            # the body uses centimetres. Compare all vertices in world centimetres.
            assert list(model.GeometricScaling) == [1.0, 1.0, 1.0], 'Unexpected geometric scale'
            matrix = FBMatrix()
            model.GetMatrix(matrix, FBModelTransformationType.kModelTransformation, True)
            world = []
            for index in range(0, len(values), 4):
                x, y, z = values[index:index+3]
                world.extend(matrix[row]*x + matrix[4+row]*y + matrix[8+row]*z + matrix[12+row] for row in range(3))
            result[model.Name] = world
    return result


try:
    scene, char = load(SOURCE)
    report.update(character=char.Name, characterized=True, control_rig=True)
    tests = [('left_wrist', FBEffectorId.kFBLeftWristEffectorId, 'hand_l', [0, 8, 8], 'Gloves'),
             ('left_ankle', FBEffectorId.kFBLeftAnkleEffectorId, 'foot_l', [0, 15, 10], 'Pants')]
    effectors = []
    for name, eid, bone_name, offset, garment in tests:
        effector = char.GetEffectorModel(eid)
        bone = FBFindModelByLabelName(bone_name)
        assert effector and bone, f'Missing {name} control or {bone_name}'
        original = list(effector.Translation)
        effector.PropertyList.Find('IK Reach Translation').Data = 100.0
        effector.Translation.SetAnimated(True)
        for node, start, delta in zip(effector.Translation.GetAnimationNode().Nodes, original, offset):
            node.FCurve.EditClear()
            for frame, value in [(0, start), (15, start+delta), (30, start)]:
                node.FCurve.KeyAdd(FBTime(0, 0, 0, frame), value)
        effectors.append((name, bone, garment))
    FBSystem().CurrentTake.Name = 'Rig_Readiness_Test'
    FBSystem().CurrentTake.LocalTimeSpan = FBTimeSpan(FBTime(0), FBTime(0, 0, 0, 30))
    meshes = [m for m in scene.Components if isinstance(m, FBModel) and m.Geometry and m.IsDeformable]
    for mesh in meshes:
        mesh.ModelVertexData.VertexArrayMappingRequest()
    player = FBPlayerControl()
    player.Goto(FBTime(0))
    scene.Evaluate()
    base_bones = {name: position(bone) for name, bone, _ in effectors}
    base_meshes = sample_meshes(scene)
    player.Goto(FBTime(0, 0, 0, 15))
    scene.Evaluate()
    moved_bones = {name: position(bone) for name, bone, _ in effectors}
    moved_meshes = sample_meshes(scene)
    report['controls'] = {}
    for name, bone, garment in effectors:
        movement = distance(base_bones[name], moved_bones[name])
        assert movement > 3, f'{name} did not move its skeleton joint: {movement}'
        report['controls'][name] = {'joint': bone.Name, 'movement_cm': movement,
                                    'rest_position': base_bones[name], 'moved_position': moved_bones[name]}
    report['mesh_checks'] = []
    for name in base_meshes:
        maximum = max(abs(x-y) for x, y in zip(base_meshes[name], moved_meshes[name]))
        report['mesh_checks'].append({'mesh': name, 'max_coordinate_change_cm': maximum})
    report['deformed_arrays_nonzero'] = any(max(abs(v) for v in values) > 1 for values in base_meshes.values())
    for garment in ['Gloves', 'Pants', 'FootGuards', 'Jacket']:
        matches = [r for r in report['mesh_checks'] if r['mesh'].startswith(garment + '.')]
        assert matches and max(r['max_coordinate_change_cm'] for r in matches) > 1, f'{garment} did not deform'
    player.Goto(FBTime(0, 0, 0, 30))
    scene.Evaluate()
    for name, bone, _ in effectors:
        error = distance(base_bones[name], position(bone))
        report['controls'][name]['return_error_cm'] = error
        assert error < 0.5, f'{name} did not return to its initial pose: {error}'
    for mesh in meshes:
        mesh.ModelVertexData.VertexArrayMappingRelease()
    player.Goto(FBTime(0))
    scene.Evaluate()
    options = FBFbxOptions(False)
    options.EmbedMedia = True
    output = OUT / 'Medium_Sparring_Rig_Test.fbx'
    assert app.FileSave(str(output), options), 'Scratch save failed'
    scene, char = load(output)
    for frame, expected in [(0, base_bones), (15, moved_bones), (30, base_bones)]:
        player.Goto(FBTime(0, 0, 0, frame))
        scene.Evaluate()
        for name, eid, bone_name, _, _ in tests:
            error = distance(expected[name], position(FBFindModelByLabelName(bone_name)))
            assert error < 0.5, f'Reopened {name} at frame {frame} differs by {error} cm'
    report.update(reopened_successfully=True, animation_preserved=True, test_copy=str(output))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == report['source_sha256'], 'Library source changed'
    report.update(source_unchanged=True, passed=True)
except Exception as exc:
    report['error'] = str(exc)
    raise
finally:
    path = OUT / 'report.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('READINESS_REPORT ' + str(path), flush=True)
    print(json.dumps(report, indent=2), flush=True)
