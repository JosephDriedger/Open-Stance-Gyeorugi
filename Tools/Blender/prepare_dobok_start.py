"""Make a body type's starting file for the traditional dobok layers: its Gameplay_High fighter plus the front-kick test.

The layered dobok (build_traditional_dobok.py) is built and checked against the front-kick test animation that the Stocky
studies use (Dummy_Front_Kick_Local_Ankle). Every body type shares the 341-bone MetaHuman rig, so the kick's bone-local
keys are appended from the Stocky starting file and played on this body's rig.

    blender.exe -b Resources/Models/CharacterSuite/<Kind>/Gameplay_High.blend -P prepare_dobok_start.py -- <out Work.blend>
"""
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
KICK_SOURCE = ROOT / 'Resources/Models/FinalRefinement/TraditionalDobok/Work.blend'
KICK = 'Dummy_Front_Kick_Local_Ankle.001'
out = Path(sys.argv[sys.argv.index('--') + 1])
out.parent.mkdir(parents=True, exist_ok=True)
with bpy.data.libraries.load(str(KICK_SOURCE), link=False) as (src, dst):
    dst.actions = [KICK]
kick = dst.actions[0]
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
rig.animation_data_create()
rig.animation_data.action = kick
try:  # Blender 5 slotted actions
    if kick.slots:
        rig.animation_data.action_slot = kick.slots[0]
except AttributeError:
    pass
for track in rig.animation_data.nla_tracks:
    track.mute = True
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 144
scene.frame_set(1)
rig['BlenderCloth'] = False
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out), compress=True)
print('START READY', rig.name, kick.name, out, flush=True)
