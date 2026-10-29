# Mocap record — separate recording day

Use this guide on recording day. For the limited model/rig readiness test, use [Mocap_Test.md](Mocap_Test.md).

Recording materials are grouped under **Models and Rigs / 03 Technical and Experiments / Mocap Record**: this guide, the shot list, proposed marker diagram and matching Blender cleanup rig.

1. Open `Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx` in MotionBuilder and save a new working FBX for the session.
2. Confirm the marker layout and calibrate to the actual performer with the operator. The supplied 41-marker diagram is a proposal.
3. Record the calibration pose and planned shots using `Docs/Open_Stance_Mocap_Shot_List.pdf`.
4. Collect labeled, processed calibration and movement C3Ds, performer measurements, FPS, units and axes. Collect a solved skeleton FBX and reference video if available; retain the original lab files.
5. For C3D, fit/calibrate a MotionBuilder Actor and its marker mapping, then use it as the fighter's source. For solved FBX, characterize the source skeleton and retarget. Plot to the control rig for cleanup, then bake to the body skeleton for export.
6. Save and reopen the animated result. Check timing, scale, left/right, hips, knees, foot contact and gear following the body. Use `Resources/Models/Animation/OpenStance_Medium_Animation.blend` for subsequent Blender cleanup. For Unreal, use a matching target skeleton or retarget through the project's workflow.

The recording workflow passes when the recorded movement replays on the fighter after reopening. The short readiness test alone does not validate capture solving or retargeting.
