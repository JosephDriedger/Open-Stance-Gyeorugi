# Vicon Nexus lab test — September 25, 2026

Objective: capture a short taekwondo motion and replay it on the Open Stance fighter
in Unreal. A marker display or a connected stream alone does not establish success.

Constraint: capture takes place in BCIT's mocap lab. Nexus is available only there.
Use Autodesk MotionBuilder for cleanup outside Nexus; MotionBuilder 2027 is
installed on this machine. Its standalone Python runtime successfully opened,
characterized, animated a wrist control, saved and reopened the supplied test fighter.
No captured trials were found in Resources, so cleanup has not yet been performed.

Ready-to-open test character: `Resources/Models/MotionBuilder/OpenStance_TestFighter.fbx`.
This separate custom-fighter target includes a MotionBuilder Character and FK/IK
Control Rig. Use its adjacent README; it uses a different skeleton from MetaHuman.

## What is available locally

- `Resources/References/` contains reference images. Model sources are in `Resources/Models/`.
- Start with `Resources/Models/MetaHuman/MH_FighterBase_Body.fbx` as the target body.
  The Unreal equivalent is `/Game/Characters/Fighters/Export/MH_FighterBase_Body`.
- Fitted fighter clothing is in `Resources/Models/Fitted/MH_FighterBase_Body/`;
  imported clothing is in `/Game/Characters/Fighters/Gear/`.
- `Resources/Models/Fighter_Rigged.fbx` is the separate custom fighter skeleton.
  Its exporter explicitly disables animation baking. It is a skinned target,
  not a supplied motion clip. Manny-style names alone do not establish identical
  bone orientations or direct animation compatibility.
- Unreal 5.8 loaded 58 skeletal meshes: 51 reference the MetaHuman body skeleton,
  and seven heads reference the face skeleton. The body ROM animation loads and
  uses that same body skeleton. These checks do not validate skin deformation.
- No Vicon plugin installation was found in the project or the inspected engine
  plugin tree. No project-specific Vicon retarget setup was found under Content.

## Local baseline before the lab

In Unreal's Output Log, run:

```text
py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py"
```

Enable viewport Realtime (Ctrl+R). The script frames the fighter at Z=20000 and
plays the body ROM with seven clothing pieces following it. To inspect a pose:

```text
py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py" 18.5
py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py" play
```

The preview now starts at speed 1 and loads assets directly, avoiding a reproduced
startup asset-registry lookup failure. Headless Unreal checks passed for spawning
eight actors, seven leader-pose followers, playback rate, seeking/pausing, and
resuming. No level or model assets were saved by these checks. The preview omits
the separate head and assembled-body hidden face maps; evaluate motion separately
from skin showing through the garments. Visual deformation remains to be checked.

## Primary workflow: BCIT Nexus → MotionBuilder → Unreal

Before leaving BCIT, obtain a **labeled, processed C3D of both the calibration
pose and motion trial**, with marker names preserved. Also collect the marker-placement
diagram, performer measurements used by the lab, capture rate, units, axis convention,
frame range, and a reference video if available. Ask the operator to finish reconstruction,
label corrections and initial gap filling in Nexus while you still have lab access.
Keep original trials and the calibrated subject/template as archival material; they
are not substitutes for an export that opens without Nexus.

If BCIT can also provide a solved skeleton FBX, collect it alongside the C3D.
Otherwise use MotionBuilder's optical Actor workflow:

1. Import the C3D optical data and verify timing, scale, and marker labels.
2. Fit a MotionBuilder Actor to the performer in the calibration frame. Create its
   Marker Set, assign markers by the lab's actual placement, and calculate offsets.
   Save this mapping for that performer/session. Do not guess mappings from a generic
   marker set or assume a clinical lower-body set can solve the full character.
3. Import the target body FBX and define/characterize its skeleton. Check its
   characterization stance and axes; an imported skin skeleton is not automatically
   a MotionBuilder Character or Control Rig. Preserve the original FBX unchanged.
4. Set the Actor as the characterized body's motion source; inspect the solve,
   then plot to a Control Rig for cleanup. For a solved FBX, characterize the source
   skeleton and use character-to-character retargeting instead.
5. Correct marker swaps/gaps and solve errors before polishing body motion. Use
   animation layers for foot contact, hip motion and limb corrections; avoid
   smoothing away the acceleration and impact timing of kicks.
6. Save an editable MotionBuilder FBX with the Actor/mapping and Control Rig.
   Plot the cleaned animation to the target skeleton and save a separate baked FBX
   for Unreal, preserving bone names, hierarchy, scale, frame rate and root motion.
7. Import the baked animation onto the matching MetaHuman body skeleton in Unreal.
   If exporting an intermediate source skeleton instead, import that separately
   and use Unreal's IK Retargeter. Check a bare body first, then the clothing.

Autodesk documents C3D optical import, Actor Marker Set solving, and plotting
character animation to the skeleton for export:
[C3D import](https://help.autodesk.com/cloudhelp/2022/ENU/MotionBuilder/files/GUID-68575BCA-F847-4362-9515-500A990387B7.htm),
[Actor Marker Set](https://help.autodesk.com/cloudhelp/2022/ENU/MotionBuilder/files/GUID-BA14C51F-20A1-4305-9273-E44022B8D389.htm),
[character animation](https://help.autodesk.com/cloudhelp/2024/ENU/MotionBuilder/files/GUID-7C0455EB-A67A-4B8D-AE04-5139DC676D50.htm).

The decisive test at BCIT is opening their exported sample in MotionBuilder and
getting it through to Unreal. Once that works, the home workflow needs MotionBuilder
and Unreal, with no Nexus installation or live lab connection.

## Optional live demonstration at BCIT

Vicon currently lists Nexus as supported by its Unreal Live Link plugin and
provides plugin 1.13 for UE 5.8. This establishes a supported integration option,
not verification with this project's particular source build or the lab's Nexus
version. Install/build and test the matching plugin before relying on live output.
[Vicon Unreal integration](https://www.vicon.com/software/plugins-integrations/unreal-engine/)

For live evaluation: Nexus subject calibration and segment output → Vicon
DataStream/Live Link → source skeleton → retargeting → MetaHuman body → clothing
followers. Confirm which segment transforms the lab's subject actually produces.
The DataStream SDK supports Nexus; an SDK connection alone does not supply a
finished character retarget configuration.
[Vicon DataStream SDK](https://www.vicon.com/software/datastream-sdk/)

For the export handoff: ask the operator to demonstrate their existing route to
a baked, animated skeleton (preferably FBX), including the solve step and software
licenses it needs. Nexus documents C3D and ASCII export; do not assume its installed
version directly exports a game-ready FBX. A marker-only C3D needs a skeleton-solving
stage before character retargeting.
[Nexus export operations](https://vicon-help.atlassian.net/wiki/spaces/Nexus216/pages/11602663/Configure%2Bfile%2Bexport%2Bpipeline%2Boperations)

## Lab acceptance test

1. Record the Nexus version, marker set, solver/model, capture rate, available
   export formats, and software used between capture and animated-skeleton export.
2. Capture a calibration pose and a 10–20 second trial: guard, step forward,
   knee chamber, controlled kick, and return. Include a turn to expose axis errors.
3. View the solved source skeleton first. Check left/right, joint rotation,
   foot contact, root motion, and missing-marker recovery.
4. Open the export in MotionBuilder and complete the solve/cleanup/bake workflow
   above. Import animation directly onto MetaHuman only if baked to that exact
   target skeleton; otherwise import the source separately and retarget it.
5. Replay on the bare target body, then enable the clothing. This separates
   capture/retarget errors from clothing weights or follower problems.
6. Save and reopen the resulting animation. Pass requires correct timing and
   scale, credible hips/knees/ankles, clothing following the body, and replay
   without the capture system connected or Nexus installed.

Take home the raw trial, calibrated subject/template, processed C3D, reference
video if available, solved skeleton animation, rest pose, units/up-axis/frame-rate
settings, and notes on the exact conversion steps. If only markers are available,
record that the solve-to-character part remains unproven.
