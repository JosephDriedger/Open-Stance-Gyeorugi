"""Run with mobupy.exe. Solve a labelled Vicon C3D through a MotionBuilder Actor onto a characterized fighter.

  mobupy.exe Tools/MotionBuilder/retarget_c3d.py --calibration <cal.c3d> --trial <trial.c3d> --out-dir <dir>

The Actor is fitted from joint centres estimated from the calibration pose markers (Harrington hip regression,
knee/ankle/elbow markers shifted medially), the marker set offsets are snapped on that pose, then the trial's
markers replace the calibration markers by name. The character is driven by the Actor and plotted to its
skeleton. Writes <trial>_Actor.fbx (editable: optical data, Actor, character) and <trial>_Baked.fbx (character
and baked skeleton only), plus report.json. The source fighter FBX is opened read-only and never saved over.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import pyfbstandalone
pyfbstandalone.initialize()
from pyfbsdk import *

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--fighter', default='Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx')
ap.add_argument('--calibration', required=True)
ap.add_argument('--trial', required=True)
ap.add_argument('--out-dir', required=True)
ap.add_argument('--cal-frame', type=int, default=None, help='calibration frame (120 Hz) to fit on; default middle')
ap.add_argument('--plot-fps', type=int, default=60, choices=[30, 60, 120])
args = ap.parse_args()

FIGHTER = (ROOT / args.fighter).resolve()
OUT = Path(args.out_dir).resolve()
OUT.mkdir(parents=True, exist_ok=True)
app = FBApplication()
sysm = FBSystem()
player = FBPlayerControl()
report = {'fighter': str(FIGHTER), 'fighter_sha256': hashlib.sha256(FIGHTER.read_bytes()).hexdigest(),
          'calibration': args.calibration, 'trial': args.trial, 'plot_fps': args.plot_fps, 'passed': False}
N = FBSkeletonNodeId
MODES = {30: FBTimeMode.kFBTimeMode30Frames, 60: FBTimeMode.kFBTimeMode60Frames, 120: FBTimeMode.kFBTimeMode120Frames}


# ---------- small vector helpers (tuples of 3) ----------
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a): n = norm(a); return mul(a, 1.0 / n)
def mean(*pts): return mul(tuple(map(sum, zip(*pts))), 1.0 / len(pts))
def dist(a, b): return norm(sub(a, b))


def world(model):
    v = FBVector3d()
    model.GetVector(v, FBModelTransformationType.kModelTranslation, True)
    return tuple(v)


def goto_frame(frame, mode=FBTimeMode.kFBTimeMode120Frames):
    player.Goto(FBTime(0, 0, 0, frame, 0, mode))
    sysm.Scene.Evaluate()


def optical_root():
    roots = [m for m in sysm.Scene.RootModel.Children if isinstance(m, FBModelOptical)]
    assert len(roots) == 1, f'expected one optical model, found {len(roots)}'
    return roots[0]


def markers(optical):
    return {m.Name.upper(): m for m in optical.Children}


try:
    # 1. Fighter and capture rate
    print('STAGE 1', flush=True)
    app.FileNew()
    assert app.FileOpen(str(FIGHTER), False), f'cannot open {FIGHTER}'
    chars = list(sysm.Scene.Characters)
    assert len(chars) == 1 and chars[0].GetCharacterize(), 'fighter must hold one characterized character'
    char = chars[0]
    report['character'] = char.Name
    player.SetTransportFps(FBTimeMode.kFBTimeMode120Frames)

    # The library fighter is characterized in the MetaHuman A-pose (upper arms ~53 deg down, elbows bent).
    # MotionBuilder reads the characterization pose as a T-pose, so an Actor solve would rotate every arm by
    # that difference. In this working copy only, rotate the arm chain to a T-pose and re-characterize.
    def bone_dir(a, b):
        return unit(sub(world(FBFindModelByLabelName(b)), world(FBFindModelByLabelName(a))))

    def rotate_global(model, d, t):
        axis = cross(d, t)
        s = norm(axis); c = dot(d, t)
        if s < 1e-6:
            return 0.0
        k = mul(axis, 1.0 / s)
        ang = math.atan2(s, c)
        K = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]
        R = [[(1 if i == j else 0) + math.sin(ang)*K[i][j] + (1 - math.cos(ang))*sum(K[i][m]*K[m][j] for m in range(3))
              for j in range(3)] for i in range(3)]
        M = FBMatrix()
        model.GetMatrix(M, FBModelTransformationType.kModelTransformation, True)
        for row in range(3):   # rows of FBMatrix are the bone's world axes
            v = (M[row*4], M[row*4+1], M[row*4+2])
            nv = [sum(R[i][j]*v[j] for j in range(3)) for i in range(3)]
            M[row*4], M[row*4+1], M[row*4+2] = nv
        model.SetMatrix(M, FBModelTransformationType.kModelTransformation, True)
        sysm.Scene.Evaluate()
        return math.degrees(ang)

    char.InputType = FBCharacterInputType.kFBCharacterInputStance
    char.ActiveInput = True
    sysm.Scene.Evaluate()
    char.ActiveInput = False
    char.SetCharacterizeOff()
    sysm.Scene.Evaluate()
    tpose = {}
    for side, x in (('l', 1.0), ('r', -1.0)):
        for a, b in (('upperarm', 'lowerarm'), ('lowerarm', 'hand'), ('hand', 'middle_metacarpal')):
            bone = FBFindModelByLabelName(f'{a}_{side}')
            tpose[f'{a}_{side}'] = round(rotate_global(bone, bone_dir(f'{a}_{side}', f'{b}_{side}'), (x, 0.0, 0.0)), 1)
    report['tpose_rotation_deg'] = tpose
    report['tpose_residual'] = {s: bone_dir(f'upperarm_{s}', f'hand_{s}') for s in 'lr'}
    assert char.SetCharacterizeOn(True), f're-characterize failed: {char.GetCharacterizeError()}'
    sysm.Scene.Evaluate()

    # 2. Calibration markers. MotionBuilder converts the C3D to cm, Y up.
    print('STAGE 2', flush=True)
    assert app.FileImport(args.calibration, False), 'calibration import failed'
    opt = optical_root()
    mk = markers(opt)
    report['marker_labels'] = sorted(mk)
    span = sysm.CurrentTake.LocalTimeSpan
    last = span.GetStop().GetFrame(FBTimeMode.kFBTimeMode120Frames)
    cal_frame = args.cal_frame if args.cal_frame is not None else last // 2
    goto_frame(cal_frame)
    P = {k: world(m) for k, m in mk.items()}

    # Face the Actor's stance (+Z forward, performer's left = +X): yaw the optical root about Y.
    fwd = unit(sub(mean(P['LASI'], P['RASI']), mean(P['LPSI'], P['RPSI'])))
    fwd = unit((fwd[0], 0.0, fwd[2]))
    yaw = math.degrees(math.atan2(fwd[0], fwd[2]))   # rotation that brings +Z onto fwd
    opt.Rotation = FBVector3d(0, -yaw, 0)
    sysm.Scene.Evaluate()
    P = {k: world(m) for k, m in mk.items()}
    hip_mid = mean(P['LASI'], P['RASI'], P['LPSI'], P['RPSI'])
    opt.Translation = FBVector3d(-hip_mid[0], 0, -hip_mid[2])
    sysm.Scene.Evaluate()
    P = {k: world(m) for k, m in mk.items()}
    left = unit(sub(P['LASI'], P['RASI']))
    fwd = unit(sub(mean(P['LASI'], P['RASI']), mean(P['LPSI'], P['RPSI'])))
    report['calibration_frame_120hz'] = cal_frame
    report['optical_yaw_deg'] = -yaw
    report['facing_check'] = {'forward': fwd, 'left': left}
    assert fwd[2] > 0.9 and left[0] > 0.9, f'orientation fix failed: fwd {fwd} left {left}'

    # 3. Joint centres from markers (cm). Marker radius ~0.7 cm.
    print('STAGE 3', flush=True)
    asis_mid = mean(P['LASI'], P['RASI'])
    psis_mid = mean(P['LPSI'], P['RPSI'])
    pw = dist(P['LASI'], P['RASI'])
    pd = dist(asis_mid, psis_mid)
    up = unit(cross(fwd, left))           # pelvis superior axis (+Y)
    fw = unit(cross(left, up))            # pelvis anterior axis (+Z)
    J = {}
    for s, sign in (('L', 1), ('R', -1)):
        # Harrington et al. 2007 (mm -> cm)
        J[s + 'Hip'] = add(asis_mid, add(add(mul(fw, -0.24*pd - 0.99), mul(up, -0.30*pw - 1.09)), mul(left, sign*(0.33*pw + 0.73))))
        med = (-sign, 0, 0)
        J[s + 'Knee'] = add(P[s + 'KNE'], mul(med, 5.0))
        J[s + 'Ankle'] = add(P[s + 'ANK'], mul(med, 3.5))
        toe = mean(P[s + 'TOE'], P[s + 'MT5'])
        J[s + 'Foot'] = (toe[0] - sign*1.0, max(toe[1] - 1.5, 1.5), toe[2])
        J[s + 'Shoulder'] = add(P[s + 'SHO'], (-sign*1.5, -4.5, 0))
        J[s + 'Elbow'] = add(P[s + 'ELB'], (0, -1.5, 0))
        J[s + 'Wrist'] = mean(P[s + 'WRA'], P[s + 'WRB'])
    J['Hips'] = add(mean(J['LHip'], J['RHip']), (0, 4.0, 0))
    J['Chest'] = mean(P['STRN'], P['T10'])
    J['Waist'] = mean(J['Hips'], J['Chest'])
    neck = add(mean(P['C7'], P['CLAV']), (0, 2.0, 0))
    J['Neck'] = neck
    J['Head'] = add(mean(P['LFHD'], P['RFHD'], P['LBHD'], P['RBHD']), (0, -8.0, 0))
    for s, sign in (('L', 1), ('R', -1)):
        J[s + 'Collar'] = (P['CLAV'][0] + sign*3.0, P['CLAV'][1], (P['CLAV'][2] + P['C7'][2]) / 2)
    report['joint_centres_cm'] = {k: [round(c, 2) for c in v] for k, v in J.items()}
    report['performer_estimates_cm'] = {
        'head_marker_height': round(max(P[k][1] for k in ('LFHD', 'RFHD', 'LBHD', 'RBHD')), 1),
        'pelvis_width_asis': round(pw, 1), 'left_leg': round(dist(J['LHip'], J['LKnee']) + dist(J['LKnee'], J['LAnkle']), 1),
        'right_leg': round(dist(J['RHip'], J['RKnee']) + dist(J['RKnee'], J['RAnkle']), 1),
        'left_arm': round(dist(J['LShoulder'], J['LElbow']) + dist(J['LElbow'], J['LWrist']), 1),
        'right_arm': round(dist(J['RShoulder'], J['RElbow']) + dist(J['RElbow'], J['RWrist']), 1)}

    # The Actor definition must be a clean T-stance (arms along +-X, legs straight down, facing +Z): MotionBuilder
    # measures segment rotations from it. Build that stance from the performer's measured segment lengths; the
    # marker offsets snapped below absorb how the real calibration pose differs from it.
    def seg(a, b): return (dist(J['L' + a], J['L' + b]) + dist(J['R' + a], J['R' + b])) / 2
    thigh, shank = seg('Hip', 'Knee'), seg('Knee', 'Ankle')
    upper, fore = seg('Shoulder', 'Elbow'), seg('Elbow', 'Wrist')
    hip_w = dist(J['LHip'], J['RHip']) / 2
    hip_y = (J['LHip'][1] + J['RHip'][1]) / 2
    hip_z = (J['LHip'][2] + J['RHip'][2]) / 2
    ank_y = hip_y - thigh - shank
    foot_fwd = (dist(J['LAnkle'], J['LFoot']) + dist(J['RAnkle'], J['RFoot'])) / 2
    sho_y = (J['LShoulder'][1] + J['RShoulder'][1]) / 2
    sho_w = dist(J['LShoulder'], J['RShoulder']) / 2
    col_w = min(sho_w * 0.25, 4.0)
    arm_z = (J['LShoulder'][2] + J['RShoulder'][2]) / 2
    S = {'Hips': (0.0, J['Hips'][1], hip_z), 'Waist': (0.0, J['Waist'][1], J['Waist'][2]),
         'Chest': (0.0, J['Chest'][1], J['Chest'][2]), 'Neck': (0.0, J['Neck'][1], J['Neck'][2]),
         'Head': (0.0, J['Head'][1], J['Head'][2])}
    for s, sign in (('L', 1), ('R', -1)):
        S[s + 'Hip'] = (sign*hip_w, hip_y, hip_z)
        S[s + 'Knee'] = (sign*hip_w, hip_y - thigh, hip_z)
        S[s + 'Ankle'] = (sign*hip_w, ank_y, hip_z)
        S[s + 'Foot'] = (sign*hip_w, max(ank_y - 6.0, 1.5), hip_z + math.sqrt(max(foot_fwd**2 - 36.0, 25.0)))
        S[s + 'Collar'] = (sign*col_w, J[s + 'Collar'][1], arm_z)
        S[s + 'Shoulder'] = (sign*sho_w, sho_y, arm_z)
        S[s + 'Elbow'] = (sign*(sho_w + upper), sho_y, arm_z)
        S[s + 'Wrist'] = (sign*(sho_w + upper + fore), sho_y, arm_z)
    droop = {s: round(math.degrees(math.atan2(J[s + 'Shoulder'][1] - J[s + 'Wrist'][1],
                                              abs(J[s + 'Wrist'][0] - J[s + 'Shoulder'][0]))), 1) for s in 'LR'}
    report['calibration_arm_droop_deg'] = droop
    report['segment_lengths_cm'] = {k: round(v, 1) for k, v in dict(thigh=thigh, shank=shank, upperarm=upper,
                                                                     forearm=fore, hip_half_width=hip_w,
                                                                     shoulder_half_width=sho_w).items()}
    J = S

    # 4. Actor fitted to the joint centres
    print('STAGE 4', flush=True)
    actor = FBActor('Subject1_Actor')
    for sym in ('SymmetryEditTranslation', 'SymmetryEditRotation', 'SymmetryEditScaling'):
        if hasattr(actor, sym):
            setattr(actor, sym, False)
    node = {'Hips': N.kFBSkeletonHipsIndex, 'Waist': N.kFBSkeletonWaistIndex, 'Chest': N.kFBSkeletonChestIndex,
            'Neck': N.kFBSkeletonNeckIndex, 'Head': N.kFBSkeletonHeadIndex}
    for s, side in (('L', 'Left'), ('R', 'Right')):
        for part in ('Hip', 'Knee', 'Ankle', 'Foot', 'Collar', 'Shoulder', 'Elbow', 'Wrist'):
            node[s + part] = getattr(N, f'kFBSkeleton{side}{part}Index')
    for _ in range(3):   # parents first, repeated so later sets cannot drag earlier ones
        for name, nid in node.items():
            actor.SetDefinitionTranslationVector(nid, FBVector3d(*J[name]))
    sysm.Scene.Evaluate()
    fit_err = {}
    for name, nid in node.items():
        v = FBVector3d(); actor.GetDefinitionTranslationVector(nid, v)
        fit_err[name] = round(dist(tuple(v), J[name]), 2)
    report['actor_fit_error_cm'] = fit_err

    # 5. Marker set on the calibration pose
    print('STAGE 5', flush=True)
    seg_markers = {
        'Hips': ['LASI', 'RASI', 'LPSI', 'RPSI'], 'Chest': ['C7', 'T10', 'CLAV', 'STRN'],
        'Head': ['LFHD', 'RFHD', 'LBHD', 'RBHD']}
    for s in 'LR':
        seg_markers.update({s + 'Shoulder': [s + 'SHO', s + 'UPA'], s + 'Elbow': [s + 'ELB', s + 'FRM'],
                            s + 'Wrist': [s + 'WRA', s + 'WRB', s + 'FIN'], s + 'Hip': [s + 'HIP', s + 'THI'],
                            s + 'Knee': [s + 'KNE', s + 'TIB'], s + 'Ankle': [s + 'ANK', s + 'HEE', s + 'MT5', s + 'TOE']})
    ms = FBMarkerSet('Subject1_MarkerSet')
    actor.MarkerSet = ms
    used = []
    for seg, labels in seg_markers.items():
        for lab in labels:
            if lab in mk:
                ms.AddMarker(node[seg], mk[lab]); used.append(lab)
    report['markers_assigned'] = len(used)
    report['markers_unassigned'] = sorted(set(mk) - set(used))
    goto_frame(cal_frame)
    # Snap() can return False headless while still computing the offsets, so verify the offsets instead.
    report['snap_returned'] = bool(actor.Snap(FBRecalcMarkerSetOffset.kFBRecalcMarkerSetOffsetTR))
    zero = []
    for seg, labels in seg_markers.items():
        for i in range(len([l for l in labels if l in mk])):
            v = FBVector3d(); ms.GetMarkerTOffset(node[seg], i, v)
            if norm(tuple(v)) < 1e-6:
                zero.append(f'{seg}[{i}]')
    report['zero_marker_offsets'] = zero
    assert not zero, f'marker offsets not computed: {zero}'
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    actor.Active = True
    sysm.Scene.Evaluate()

    # 6. Swap in the trial markers (same names) and keep the calibration transform on the optical root
    print('STAGE 6', flush=True)
    assert app.FileImport(args.trial, True), 'trial import failed'
    roots = [m for m in sysm.Scene.RootModel.Children if isinstance(m, FBModelOptical)]
    report['optical_roots_after_trial_import'] = len(roots)
    opt = roots[0]
    opt.Rotation = FBVector3d(0, -yaw, 0)
    opt.Translation = FBVector3d(-hip_mid[0], 0, -hip_mid[2])
    mk = markers(opt)
    take = sysm.CurrentTake
    start = opt.SamplingStart; stop = opt.SamplingStop
    take.LocalTimeSpan = FBTimeSpan(start, stop)
    nframes = stop.GetFrame(FBTimeMode.kFBTimeMode120Frames) - start.GetFrame(FBTimeMode.kFBTimeMode120Frames) + 1
    report['trial_frames_120hz'] = nframes
    take.Name = Path(args.trial).stem.replace(' ', '_')

    # 7. Drive the character from the Actor and plot to its skeleton
    print('STAGE 7', flush=True)
    char.InputActor = actor
    char.InputType = FBCharacterInputType.kFBCharacterInputActor
    char.ActiveInput = True
    app.CurrentCharacter = char
    sysm.Scene.Evaluate()
    po = FBPlotOptions()
    po.PlotAllTakes = False
    po.PlotOnFrame = True
    po.PlotPeriod = FBTime(0, 0, 0, 1, 0, MODES[args.plot_fps])
    po.UseConstantKeyReducer = False
    po.PlotTranslationOnRootOnly = True
    po.RotationFilterToApply = FBRotationFilter.kFBRotationFilterUnroll
    assert char.PlotAnimation(FBCharacterPlotWhere.kFBCharacterPlotOnSkeleton, po), 'plot failed'
    char.ActiveInput = False
    sysm.Scene.Evaluate()

    # 8. Compare plotted skeleton with marker-derived joint centres through the trial
    print('STAGE 8', flush=True)
    bones = {'pelvis': None, 'thigh_l': 'LHip', 'thigh_r': 'RHip', 'calf_l': 'LKnee', 'calf_r': 'RKnee',
             'foot_l': 'LAnkle', 'foot_r': 'RAnkle', 'lowerarm_l': 'LElbow', 'lowerarm_r': 'RElbow',
             'hand_l': 'LWrist', 'hand_r': 'RWrist', 'head': None}
    B = {b: FBFindModelByLabelName(b) for b in bones}
    missing = [b for b, m in B.items() if m is None]
    assert not missing, f'missing bones {missing}'

    def trial_joints():
        Q = {k: world(m) for k, m in mk.items()}
        out = {}
        for s, sign in (('L', 1), ('R', -1)):
            out[s + 'Knee'] = Q[s + 'KNE']; out[s + 'Ankle'] = Q[s + 'ANK']
            out[s + 'Wrist'] = mean(Q[s + 'WRA'], Q[s + 'WRB']); out[s + 'Elbow'] = Q[s + 'ELB']
            out[s + 'Hip'] = mean(Q[s + 'HIP'], Q[s + 'ASI'])
        out['pelvis'] = mean(Q['LASI'], Q['RASI'], Q['LPSI'], Q['RPSI'])
        out['head'] = mean(Q['LFHD'], Q['RFHD'], Q['LBHD'], Q['RBHD'])
        out['LFootMin'] = min(Q['LHEE'][1], Q['LTOE'][1]); out['RFootMin'] = min(Q['RHEE'][1], Q['RTOE'][1])
        return out

    step = 120 // args.plot_fps
    samples = []
    s0 = start.GetFrame(FBTimeMode.kFBTimeMode120Frames)
    lr_swaps = 0
    foot_floor = {'l': [], 'r': []}
    for f in range(s0, s0 + nframes, max(step, 4)):
        goto_frame(f)
        T = trial_joints()
        W = {b: world(m) for b, m in B.items()}
        # side check: character left limb should be closer to the performer's left limb than the right one
        for lb, rb, lj, rj in (('foot_l', 'foot_r', 'LAnkle', 'RAnkle'), ('hand_l', 'hand_r', 'LWrist', 'RWrist')):
            if dist(W[lb], T[lj]) + dist(W[rb], T[rj]) > dist(W[lb], T[rj]) + dist(W[rb], T[lj]) + 5:
                lr_swaps += 1
        foot_floor['l'].append(W['foot_l'][1]); foot_floor['r'].append(W['foot_r'][1])
        samples.append({'frame': f, 'pelvis': dist(W['pelvis'], T['pelvis']), 'head': dist(W['head'], T['head']),
                        'foot_l': dist(W['foot_l'], T['LAnkle']), 'foot_r': dist(W['foot_r'], T['RAnkle']),
                        'hand_l': dist(W['hand_l'], T['LWrist']), 'hand_r': dist(W['hand_r'], T['RWrist'])})
    stats = {}
    for k in ('pelvis', 'head', 'foot_l', 'foot_r', 'hand_l', 'hand_r'):
        vals = sorted(s[k] for s in samples)
        stats[k] = {'median_cm': round(vals[len(vals)//2], 1), 'p95_cm': round(vals[int(len(vals)*.95)], 1),
                    'max_cm': round(vals[-1], 1)}
    report['bone_vs_marker_distance'] = stats
    report['left_right_swapped_samples'] = lr_swaps
    report['samples_checked'] = len(samples)
    report['foot_bone_height_cm'] = {s: {'min': round(min(v), 1), 'median': round(sorted(v)[len(v)//2], 1)}
                                     for s, v in foot_floor.items()}
    worst = max(samples, key=lambda s: s['foot_l'] + s['foot_r'])
    report['worst_foot_frame_120hz'] = worst['frame']

    # 9. Save editable scene, then a baked character-only file
    print('STAGE 9', flush=True)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    stem = Path(args.trial).stem.replace(' ', '_')
    opts = FBFbxOptions(False)
    editable = OUT / f'{stem}_Actor.fbx'
    assert app.FileSave(str(editable), opts), 'editable save failed'
    for comp in list(opt.Children) + [opt, actor, ms]:   # deleting the optical root alone leaves its markers
        comp.FBDelete()
    sysm.Scene.Evaluate()
    # Unreal's MetaHuman skeleton starts at a bone named root; the fighter's armature null plays that part.
    rig = FBFindModelByLabelName('pelvis').Parent
    report['baked_root'] = {'was': rig.Name, 'scaling': list(rig.Scaling), 'rotation': list(rig.Rotation)}
    rig.Name = 'root'
    left_over = [c.Name for c in sysm.Scene.RootModel.Children if isinstance(c, FBModelMarkerOptical)]
    assert not left_over, f'markers left in baked file: {left_over[:5]}'
    baked = OUT / f'{stem}_Baked.fbx'
    assert app.FileSave(str(baked), FBFbxOptions(False)), 'baked save failed'
    report.update(editable_fbx=str(editable), baked_fbx=str(baked))

    # 10. Reopen the baked file and confirm the motion is on the skeleton
    print('STAGE 10', flush=True)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    app.FileNew()
    assert app.FileOpen(str(baked), False), 'baked reopen failed'
    pel = FBFindModelByLabelName('pelvis')
    tk = sysm.CurrentTake
    a = tk.LocalTimeSpan.GetStart(); b = tk.LocalTimeSpan.GetStop()
    player.Goto(a); sysm.Scene.Evaluate(); p0 = world(pel)
    player.Goto(b); sysm.Scene.Evaluate(); p1 = world(pel)
    curves = pel.Rotation.GetAnimationNode()
    keys = len(curves.Nodes[0].FCurve.Keys) if curves and curves.Nodes else 0
    report['reopened'] = {'take': tk.Name, 'seconds': round((b - a).GetSecondDouble(), 3), 'pelvis_rot_keys': keys,
                          'pelvis_start_cm': [round(x, 1) for x in p0], 'pelvis_end_cm': [round(x, 1) for x in p1]}
    assert keys > 10, 'baked skeleton has no animation'
    assert hashlib.sha256(FIGHTER.read_bytes()).hexdigest() == report['fighter_sha256'], 'fighter source changed'
    report['fighter_unchanged'] = True
    report['passed'] = True
except Exception as exc:
    import traceback
    report['error'] = f'{exc}\n{traceback.format_exc()}'
    raise
finally:
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)
