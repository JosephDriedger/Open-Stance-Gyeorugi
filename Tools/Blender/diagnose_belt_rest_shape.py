"""Isolate animated rest-shape effects from belt contact, without changing masters."""
import bpy, sys, json, math, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import audit_sparring_styles as audit
mode = sys.argv[-1]
assert mode in ['DynamicRest', 'FixedRest', 'SelfOnly', 'ObjectOnly', 'FixedContact', 'ThinSelfContact', 'PhysicalMass']
root = audit.ROOT / 'Resources/Models/FinalRefinement'
out = root / ('BeltRestDiagnosis_' + mode)
assert not (out/'diagnosis.json').exists(), 'Use a new candidate name; do not reuse stale review renders'
out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'ClothRefinement_SharedAppliedScale/Candidate.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['RIG_Body_Medium']
proxy = bpy.data.objects['SIM_Shared_Belt_Tails']
cloth = next(m for m in proxy.modifiers if m.type == 'CLOTH')
cloth.collision_settings.use_collision = mode in ['ObjectOnly', 'FixedContact', 'ThinSelfContact', 'PhysicalMass']
cloth.collision_settings.use_self_collision = mode in ['SelfOnly', 'FixedContact', 'ThinSelfContact', 'PhysicalMass']
if mode == 'ThinSelfContact':
    cloth.collision_settings.self_distance_min = .0005
cloth.settings.use_dynamic_mesh = mode == 'DynamicRest'
if mode == 'PhysicalMass':
    cloth.settings.mass = .12 / len(proxy.data.vertices)
    cloth.settings.quality = 60
    cloth.settings.bending_stiffness = .2
    cloth.settings.bending_damping = .5
    cloth.settings.air_damping = 1
    cloth.collision_settings.self_distance_min = .001
scene.cycles.samples = 12
rows = []
started = time.monotonic()
points = [proxy.matrix_world @ v.co for v in proxy.data.vertices]
edge_lengths = [(points[e.vertices[0]]-points[e.vertices[1]]).length for e in proxy.data.edges]
mesh_audit = {'minimum_edge_length': min(edge_lengths), 'maximum_edge_length': max(edge_lengths),
              'self_collision_distance': cloth.collision_settings.self_distance_min,
              'proxy_scale': list(proxy.scale)}
for frame in range(1, 145):
    scene.frame_set(frame)
    ev = proxy.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    points = [proxy.matrix_world @ v.co for v in mesh.vertices]
    assert all(math.isfinite(c) and abs(c) < 5 for p in points for c in p), (mode, frame, 'unstable cloth')
    if frame in [1, 26, 35, 72, 144]:
        rows.append({'frame': frame, 'minimum_z': min(p.z for p in points),
                     'maximum_z': max(p.z for p in points)})
    ev.to_mesh_clear()
    if frame % 12 == 0:
        print('BELT_DIAGNOSIS', mode, frame, round(time.monotonic()-started, 2), flush=True)
    if frame in [72, 144]:
        audit.render(scene, rig, 1, out, 'Front_'+str(frame), (.2,-4,1.3), (0,0,.96), 1.25,640,720)
(out/'diagnosis.json').write_text(json.dumps({'mode':mode,
    'object_collision':cloth.collision_settings.use_collision,
    'self_collision':cloth.collision_settings.use_self_collision, 'mesh_audit':mesh_audit,
    'elapsed_seconds':time.monotonic()-started, 'rows':rows},indent=2))
