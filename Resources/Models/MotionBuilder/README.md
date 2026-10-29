> Legacy test-character folder. For the current nine-preset library, use `../Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx` or the matching preset, and read `../Animation/README.md`. The older files described below are retained pipeline history.

# Open Stance animation test character

Open **OpenStance_TestFighter.fbx** in Autodesk MotionBuilder.

- Character: `OpenStance_TestFighter`
- 56 mapped character slots, biped characterization, FK/IK Control Rig.
- Original fighter mesh and skeleton; embedded media enabled at save.
- Reference take: `Reference_ReadyForMocap`. No captured animation is included.

In Character Controls select `OpenStance_TestFighter`. For a characterized source
FBX, merge the source and select its Character as this character's source. For
BCIT C3D markers, first fit an Actor and map the actual marker set, then use that
Actor as the source. Plot to the Control Rig for cleanup, then to the skeleton
before exporting animation to Unreal. Save your working take under a new name.

This uses the project's custom fighter skeleton, not the MetaHuman body skeleton.
For Unreal, import it as a separate Skeletal Mesh/Skeleton; retarget to MetaHuman
when testing the production character. Do not force this FBX onto metahuman_base_skel.

Verified using MotionBuilder 2027: characterization, FK/IK rig creation, a keyed
wrist-control move resulting in 25.25 cm of hand movement, and save/reopen retaining
characterization and the control rig. The test motion was removed before saving.
Full-body visual deformation and BCIT capture retargeting remain unverified.

Regenerate with MotionBuilder's `mobupy.exe` and
`Tools/MotionBuilder/prepare_test_character.py` from the project root.

## MetaHuman test fighter (production skeleton)

`OpenStance_TestFighter_MH.fbx` is the textured Medium MetaHuman fighter in dobok and WT sparring gear, on the
production `metahuman_base_skel` skeleton, characterized as `OpenStance_TestFighter_MH` (56 slots, FK/IK control
rig; verified with a keyed wrist move of 28.3 cm and save/reopen, `validation_OpenStance_TestFighter_MH.json`).
Prefer it for captures headed to the game: plotted animation imports onto the Unreal fighters without a retarget.
Regenerate with `mobupy.exe Tools/MotionBuilder/prepare_test_character.py --metahuman` after
`Tools/Blender/build_test_model.py`. See `Resources/Models/TestFighter/README.md`.
