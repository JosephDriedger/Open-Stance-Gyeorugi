"""Keyframe placeholder poses for the match referee (GDD 8.5, 11.2), until captured referee motion exists.

The referees share the fighters' MetaHuman skeleton, so this reuses build_placeholder_techniques.py's rig, two-bone IK
pose model and FBX export: each pose is written as targets (feet, hands, hips, chest) and held for one second. Gestures
are made with the right arm; the _Mirror version uses the left (the game picks the arm on the named fighter's side).

    blender.exe -b Resources/Models/CharacterSuite/Medium/Gameplay_High.blend -P build_placeholder_referee.py -- <out folder>

Saves <out folder>/PlaceholderReferee.blend and Placeholder_Referee_<Pose>[_Mirror].fbx for
Tools/Unreal/import_placeholder_techniques.py referee.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else HERE.parents[1] / 'Resources/Models/Animation/PlaceholderReferee'

# The technique builder as a library: its pose model, solver and exporter, without building the techniques.
lib = {'NOEXPORT': True, '__name__': 'placeholder_techniques', '__file__': str(HERE / 'build_placeholder_techniques.py')}
exec(compile((HERE / 'build_placeholder_techniques.py').read_text(encoding='utf-8'), lib['__file__'], 'exec'), lib)
V, pose, key_pose, mirror, FOOT_Z, rig, scene = lib['V'], lib['pose'], lib['key_pose'], lib['mirror'], lib['FOOT_Z'], lib['rig'], lib['scene']
lib['OUT'] = OUT
import bpy  # noqa: E402  (after the library has loaded the scene)


def referee(**changes):
    """The referee's base: square to the fighters, upright, feet a little apart, hands relaxed in front of the belt."""
    base = dict(
        pelvis=dict(drop=.0, yaw=0, pitch=0, roll=0, shift=V(0, 0, 0)),
        chest=dict(yaw=0, pitch=0, roll=0),
        look=0,
        foot_l=dict(at=V(.14, -.02, FOOT_Z), pole=V(.1, -1, .1), toe=V(.15, -1, 0)),
        foot_r=dict(at=V(-.14, .02, FOOT_Z), pole=V(-.1, -1, .1), toe=V(-.15, -1, 0)),
        hand_l=dict(at=V(.12, -.20, .98), pole=V(1, .3, -1)),
        hand_r=dict(at=V(-.12, -.20, .98), pole=V(-1, .3, -1)),
    )
    p = pose(**base)
    for key, value in changes.items():
        p[key] = {**p[key], **value} if isinstance(value, dict) and isinstance(p.get(key), dict) else value
    return p


AT_SIDES = dict(hand_l=dict(at=V(.23, .0, .84), pole=V(1, .4, -.3)), hand_r=dict(at=V(-.23, .0, .84), pole=V(-1, .4, -.3)))
FEET_TOGETHER = dict(foot_l=dict(at=V(.07, -.02, FOOT_Z)), foot_r=dict(at=V(-.07, .02, FOOT_Z)))

# The facing is -Y (toward the fighters); the referee's right is -X.
POSES = {
    'Idle': referee(),
    # CHARYEOT: feet together, arms straight at the sides
    'Attention': referee(**FEET_TOGETHER, **AT_SIDES),
    # KYEONGRYE: a bow from the hips, about 30 degrees
    'Bow': referee(**FEET_TOGETHER, **AT_SIDES, pelvis=dict(pitch=14), chest=dict(pitch=18)),
    # JOON-BI: the right hand held out flat between the fighters at chest height
    'Ready': referee(hand_r=dict(at=V(-.04, -.58, 1.28), pole=V(-1, 0, -.4))),
    # SHI-JAK / KYE-SOK / GONG-GYEOK: the hand drawn down and forward to start play
    'Start': referee(hand_r=dict(at=V(-.04, -.52, .98), pole=V(-1, 0, -.6))),
    # KAL-YEO: both arms out flat, pushing the fighters apart
    'Separate': referee(hand_l=dict(at=V(.30, -.45, 1.26), pole=V(1, 0, -.4)), hand_r=dict(at=V(-.30, -.45, 1.26), pole=V(-1, 0, -.4))),
    # KEU-MAN: the right arm raised forward to stop the round
    'Stop': referee(hand_r=dict(at=V(-.08, -.36, 1.68), pole=V(-1, 0, -.2))),
    # GAM-JEOM: the right arm pointing at the penalized fighter, out to the right
    'Point': referee(hand_r=dict(at=V(-.64, -.12, 1.36), pole=V(0, .4, -1)), chest=dict(yaw=-12)),
    # HANA..YEODEOL: the right hand raised in front of the face, counting
    'Count': referee(hand_r=dict(at=V(-.10, -.34, 1.52), pole=V(-1, 0, -.5)), chest=dict(pitch=6)),
    # CHUNG SEUNG / HONG SEUNG: the right arm straight up for the winner
    'RaiseWinner': referee(hand_r=dict(at=V(-.26, .02, 2.10), pole=V(-1, .3, 0))),
}


def build():
    scene.render.fps = 30
    rig.animation_data_create()
    made = {}
    for name, p in POSES.items():
        for suffix, shape in (('', lambda q: q), ('_Mirror', mirror)):
            action = bpy.data.actions.new(f'Placeholder_Referee_{name}{suffix}')
            action.use_fake_user = True
            rig.animation_data.action = action
            key_pose(shape(p), 1)
            key_pose(shape(p), 31)
            made[f'Referee_{name}{suffix}'] = {'action': action.name, 'frames': 31}
    return made


made = build()
for o in scene.objects:
    for m in o.modifiers:
        if m.type == 'CLOTH':
            for prop in ('show_viewport', 'show_render'):
                m.driver_remove(prop)
            m.show_viewport = m.show_render = False
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'referee_poses.json').write_text(json.dumps(made, indent=1))
if '--' in sys.argv:
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'PlaceholderReferee.blend'), compress=True)
    lib['export'](made)
print('PLACEHOLDER REFEREE DONE', len(made), flush=True)
