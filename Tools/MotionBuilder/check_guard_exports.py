"""Read-only standalone import/deformation check of staged guard-only FBXs."""
import json, math, hashlib, time
from pathlib import Path
import pyfbstandalone
pyfbstandalone.initialize()
from pyfbsdk import *
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Resources/Models/FinalRefinement/FootguardSmoothExportReview'
app=FBApplication();rows=[]
def vertices(model):
    model.ModelVertexData.VertexArrayMappingRequest()
    FBSystem().Scene.Evaluate()
    FBSystem().Scene.EvaluateDeformations()
    time.sleep(.1)
    FBSystem().Scene.Evaluate()
    FBSystem().Scene.EvaluateDeformations()
    values=list(model.ModelVertexData.GetVertexArray(FBGeometryArrayID.kFBGeometryArrayID_Point,True))
    model.ModelVertexData.VertexArrayMappingRelease()
    assert values and all(math.isfinite(v) for v in values)
    matrix=FBMatrix();model.GetMatrix(matrix,FBModelTransformationType.kModelTransformation,True)
    points=[]
    for i in range(0,len(values),4):
        x,y,z=values[i:i+3]
        points.append([matrix[row]*x+matrix[4+row]*y+matrix[8+row]*z+matrix[12+row] for row in range(3)])
    return points
def delta(a,b):
    assert len(a)==len(b)
    return max(math.sqrt(sum((x-y)**2 for x,y in zip(p,q))) for p,q in zip(a,b))
for style in ('Standard','Padded'):
    path=OUT/f'Stocky_{style}_Guard.fbx';digest=hashlib.sha256(path.read_bytes()).hexdigest()
    assert app.FileOpen(str(path),False)
    scene=FBSystem().Scene;scene.Evaluate()
    meshes=[m for m in scene.Components if isinstance(m,FBModel) and m.Geometry and m.IsDeformable]
    assert len(meshes)==1,len(meshes)
    mesh=meshes[0];scene.Evaluate()
    checks=[]
    for bone_name in ('foot_l','foot_r','ball_l','ball_r'):
        bone=FBFindModelByLabelName(bone_name);assert bone,bone_name
        original=list(bone.Rotation)
        bone.Rotation.SetAnimated(True)
        for index,(node,value) in enumerate(zip(bone.Rotation.GetAnimationNode().Nodes,original)):
            node.FCurve.EditClear()
            for frame,offset in ((0,0),(15,25 if index==0 else 0),(30,0)):
                node.FCurve.KeyAdd(FBTime(0,0,0,frame),value+offset)
        FBPlayerControl().Goto(FBTime(0));scene.Evaluate()
        baseline=vertices(mesh)
        stable_baseline=delta(baseline,vertices(mesh));assert stable_baseline<.001,('unstable baseline',bone_name,stable_baseline)
        FBPlayerControl().Goto(FBTime(0,0,0,15));scene.Evaluate()
        moved=vertices(mesh)
        stable_moved=delta(moved,vertices(mesh));assert stable_moved<.001,('unstable pose',bone_name,stable_moved)
        movement=delta(baseline,moved)
        FBPlayerControl().Goto(FBTime(0,0,0,30));scene.Evaluate()
        returned=vertices(mesh)
        stable_return=delta(returned,vertices(mesh));assert stable_return<.001,('unstable return',bone_name,stable_return)
        restored=delta(baseline,returned)
        for node in bone.Rotation.GetAnimationNode().Nodes:node.FCurve.EditClear()
        bone.Rotation.SetAnimated(False);bone.Rotation=FBVector3d(*original);scene.Evaluate()
        checks.append({'bone':bone_name,'max_vertex_movement_cm':movement,'restoration_error_cm':restored,'repeat_sample_errors_cm':[stable_baseline,stable_moved,stable_return]})
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    rows.append({'style':style,'source_sha256':digest,'vertices':len(baseline),'checks':checks})
passed=all(c['restoration_error_cm']<.001 and c['max_vertex_movement_cm']>.01 for row in rows for c in row['checks'])
(OUT/'motionbuilder_fresh_mapping.json').write_text(json.dumps({'passed':passed,'restoration_tolerance_cm':.001,'production_installed':False,'sampling':'Request CPU mapping before evaluating; allow 100 ms for standalone evaluation; reevaluate; read and release mapping. Require repeat samples at each pose to agree within 0.001 cm.','scope':'Standalone MotionBuilder import and keyed local bone rotation, finite deformation and restoration. No characterization, control rig, capture retargeting or visual collision acceptance. Source files not saved.','checks':rows},indent=2))
print('GUARD_MOTIONBUILDER_CHECK',passed,flush=True)
