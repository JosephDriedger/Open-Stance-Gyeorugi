# Mocap test

Use **OpenStance_Medium_Sparring.fbx** in **Autodesk MotionBuilder**.

From the project root, open **Models and Rigs / 01 Mocap Test / 1 OPEN IN MOTIONBUILDER - Medium Sparring**.

The actual file is `Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx`.
In MotionBuilder Character Controls, select **OpenStance_Medium_Sparring**.
This is the characterized Medium fighter with a control rig and sparring equipment.

## Three checks for test day

1. **Open:** confirm the fighter, sparring gear and characterized control rig load. Save As `Mocap_Test01.fbx` before making changes.
2. **Move:** use the control rig for a small hand move and one gentle knee lift. Check the correct limbs move and the clothing follows. Reset the pose afterward.
3. **Reopen:** save the test copy, close it and reopen it. Confirm the character and control rig are still available.

Pass means the target opens, responds to simple controls and survives save/reopen. Note any visible rig or clothing problems.

This is a limited model/rig readiness test. Production capture, the full shot list, marker solving, Blender cleanup and Unreal import belong to the separate recording workflow in [Mocap_Record.md](Mocap_Record.md).

For a lab computer, copy the actual FBX and any adjacent media folder; shortcuts point to this machine.

## Existing validation

**October 29, 2026 — automated readiness test passed in MotionBuilder 2027.** The existing characterized control rig moved the left hand 11.31 cm and left foot 18.00 cm. Evaluated body, gloves, jacket, pants and foot-guard meshes moved with the rig. Both controls returned to their initial pose within 0.001 cm. A separate test FBX was saved and reopened with characterization, control rig and keyed motion preserved. The library FBX hash remained unchanged.

Re-run with MotionBuilder's `mobupy.exe Tools/MotionBuilder/test_rig_readiness.py` from the project root. Timestamped reports and test copies are written under `tmp/mocap_rig_readiness/`. The test uses simple control movements; it does not inspect clothing intersections visually.

Capture solving/retargeting and cloth physics remain outside this limited test.
