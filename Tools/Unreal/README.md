# Unreal tools

Python scripts run inside the Open Stance project (`OpenStance.uproject`, UE 5.8 source build with the
MetaHuman Creator, Chaos Outfit Asset, Groom and Python plugins enabled).

## Running a script

At startup:

```
C:\UE_5.8.0\Engine\Binaries\Win64\UnrealEditor.exe D:\Open-Stance-Gyeorugi\OpenStance.uproject -ExecutePythonScript="D:/Open-Stance-Gyeorugi/Tools/Unreal/<script>.py"
```

Or in the editor's Output Log command box (Cmd mode): `py "D:/Open-Stance-Gyeorugi/Tools/Unreal/<script>.py" [args]`.

Scripts that write logs put them in `Saved/Logs/<script>.txt`.

## Scripts

| Script | What it does |
| --- | --- |
| `create_base_fighter.py` | Creates `/Game/Characters/Fighters/MH_FighterBase` (MetaHuman, 175 cm medium build), exports its head, body and full-body skeletal meshes, writes FBX copies to `Resources/Models/MetaHuman/` for the Blender refit, and exports MetaHuman's iris colour chart for the natural eye-colour presets. No cloud requests. |
| `create_body_types.py` | Creates the four non-base body types (Compact 165 cm/60 kg, Stocky 172/80, Lean tall 185/72, Tall 192/84; GDD 5.4.2) as `/Game/Characters/Fighters/MH_Fighter<Type>` and exports their meshes to `Resources/Models/MetaHuman/`. Height is set directly; weight becomes girth (circumferences scaled by sqrt(BMI / Medium's BMI)), since MetaHuman has no weight control. Then run `Tools/Blender/fit_all_body_types.py`. |
| `point_base_at_clean_gear.py` | Points the Medium fighter (`MH_FighterBase`) at its clean gear in `Gear/Medium/`: adds the wardrobe items and replaces the SkeletalMesh selection (verified: 7 selections, not 14). `MH_FighterBase.uasset` is a Perforce file and must be writable first. Done 2026-10-02 (read-only flag cleared locally on that one file; reconcile or check it out when Perforce is reachable). |
| `capture_fighters.py` | Offscreen renders of the five body types in a row, with and without gear, plus close-ups: `UnrealEditor-Cmd.exe ... -ExecCmds="py .../capture_fighters.py quit"`. No window. Images in `Saved/Screenshots/Fighters/`. |
| `animation_test.py` | Plays MetaHuman's body range-of-motion on every fighter (gear and dobok-only) and referee and photographs 16 poses each. Offscreen editors never tick actors, so it runs a Simulate-in-Editor session with the animation set through persistent animation data. Images in `Saved/Screenshots/AnimTest/`. Rerun it after any gear change. |
| `import_fighter_gear.py` | Set `OPEN_STANCE_BODY_TYPE` to Medium, Compact, Stocky, LeanTall or Tall to import that body's clean gear (from `Tools/Blender/build_clean_gear.py`) to `/Game/Characters/Fighters/Gear/<Type>/`; the shared material and textures are built into `Gear/Clean/` on first use (`OPEN_STANCE_REBUILD_MATERIAL=1` rebuilds them). Add-only: the earlier Gear/ root assets are never touched. Imports the fitted parts (`Resources/Models/Fitted/MH_FighterBase_Body`) onto the MetaHuman body skeleton, builds the two-sided recolour material `M_FighterGear` + `MI_FighterGear_Chung/Hong`, and creates or updates `WI_Fighter_<Part>` wardrobe items (SkeletalMesh slot pipeline + body hidden face maps). Safe to re-run in an open editor; close MetaHuman Creator first. |
| `gear_rom_test.py` | Deformation check: plays MetaHuman's body range-of-motion animation on the base body with all gear following (leader pose). `py ".../gear_rom_test.py"` spawns it at Z 20000 and frames the camera; `... 18.5` pauses at 18.5 s, `... 18.5 back` views from behind, `... play` resumes. Enable viewport Realtime (Ctrl+R) to see playback. |
| `fix_wardrobe_pipelines.py` | One-off repair for wardrobe items created before pipelines were assigned. |
| `create_pose_library.py` | Hand-keyed (not mocap) poses. Hands: `Animation/Hands/AS_Hand_<Guard\|Punch\|Relaxed\|Open>_<Both\|L\|R>`, additive (local space, on the reference pose), only the 38 finger joints, so they layer over any body animation on every body type. Face: `Animation/Face/AS_Face_<Neutral\|Focus\|Kiai\|Wince\|Celebrate>` (1 s holds) and `AS_Face_Blink` (0.25 s), `ctrl_expressions_*` curves for MetaHuman's RigLogic face solver, strengths modelled on MetaHuman's own facial poses. **The face clips need a rigged face:** the fighter heads were exported geometry-only and their DNA is empty, so nothing moves until each fighter's face is rigged in MetaHuman Creator (Rig step, uses Epic's cloud auto-rigger) and the head re-exported. |
| `capture_pose_library.py` | Photographs every hand pose and expression on the Medium fighter in a Simulate session (`Saved/Screenshots/PoseLibrary/`). The face shots use an unsaved copy of the head with the face post-process AnimBP. |
| `export_stock_skin_textures.py` | Exports MetaHuman's stock body skin, normal, eye and teeth maps to `Resources/Models/MetaHuman/Textures/Stock/` for the Blender/MotionBuilder test model (the fighters have no Creator-synthesized skin textures). |
| `export_fighter_animation_fbx.py` | Exports MetaHuman's body range-of-motion animation (skeleton only, template proportions) to `Saved/Exports/<Type>_ROM_skeleton.fbx`; `Tools/Blender/build_test_model.py` retargets it onto the fighter. |
| `create_referee.py` | Referee roster from MetaHuman presets (Kelvin, Bo, Jorge, Omari, Walter, Vivian) as `/Game/Characters/Officials/MH_Referee_<P>`; exports each body to `Resources/Models/MetaHuman/`. Matches pick one at random. |
| `import_referee_outfit.py` | Imports each referee's uniform (shirt, tie, trousers, belt, sneakers from `Tools/Blender/build_referee_outfit.py`) onto that referee, with hidden face maps; puts it on and removes the preset's default T-shirt. |
| `setup_cloth.py` | Chaos cloth on the garments that move: fighter belt tails, jacket skirt, pant hems (all five body types); referee tie and trouser legs. Re-run after any re-import. Uses the C++ helper `unreal.OpenStanceClothLibrary`. |
| `cloth_preview_test.py` | Plays the body range-of-motion animation on a referee (`Kelvin`, `Vivian`...) or `fighter` with cloth simulating in the viewport. |
| `build_arenas.py` | Imports environment textures/props and builds the staging levels `L_CompetitionArena` and `L_TrainingDojang` (WT mat: 8 m octagon in a 12 m square). |
| `build_venues.py` | Builds the six Career venues (GDD 6.2), one per tournament tier: `L_ClubDojang`, `L_SchoolGym`, `L_ProvincialHall`, `L_NationalArena`, `L_ContinentalArena`, `L_WorldFinalStage`. Environments only. Imports only new or writable assets, so it runs without checking out the read-only Perforce files; pass venue names (`club gym ...`) to build a subset. Needs `build_arenas.py` to have run once. |
| `capture_levels.py` | Renders venue levels from fixed cameras to `Saved/Screenshots/Venues/` for review, with no editor window: `UnrealEditor-Cmd.exe <project> -RenderOffscreen -unattended -ExecCmds="py .../capture_levels.py [L_Name ...] quit"`. |
| `env_common.py` | Shared helpers for the level scripts (placement, lights, material instances, asset locks). |

## C++ editor helper

`Source/OpenStanceEditorTools` exposes cloth creation to Python (the engine only offers it in the mesh
editor UI). After changing it, close the editor and build:
`C:\UE_5.8.0\Engine\Build\BatchFiles\Build.bat OpenStanceEditor Win64 Development -Project="D:\Open-Stance-Gyeorugi\OpenStance.uproject" -WaitMutex`

## Pipeline position

1. `create_base_fighter.py` (this folder): MetaHuman body and head to FBX.
2. `Tools/Blender/fit_to_body.py` then `Tools/Blender/hidden_face_maps.py`: refit the dobok and gear onto
   that body, bake hidden face maps.
3. `import_fighter_gear.py`: back into Unreal as wardrobe items.
4. In MetaHuman Creator → Hair & Clothing → **Skeletal Clothing**, select a piece and press **Wear**
   (Remove takes it off). The Gear folder is listed there through `Config/DefaultMetaHumanCharacter.ini`
   (`WardrobePaths`). Match view: all seven pieces; career menu: Jacket, Pants and Belt only.

## Animation compatibility

For the Vicon Nexus lab evaluation, see `Docs/Vicon_Nexus_Test.md` for verified local
asset assignments, remaining uncertainties, and a capture-to-character acceptance test.

- Every gear piece is skinned to the MetaHuman body skeleton (`metahuman_base_skel`) and follows the
  body with Leader Pose, so any animation on a MetaHuman body drives it. Mocap (Rokoko, MetaHuman
  Animator, Manny-based clips) is retargeted to MetaHumans with the IK Retargeter; the plugin ships
  `IK_MH_IKRig` / `RTG_MH_IKRig`.
- `gear_rom_test.py` (body range of motion) and the Blender `posetest` poses don't reach the shot list's
  extremes. `Tools/Validation/check_gear_poses.py` does (head-height kicks, splits, squat, seated,
  arms overhead). The gear exported 2026-09-12 tore at the pants crotch and jacket armpits/waist in
  those poses (20-38 cm spikes); after the `fit_to_body.py` weight fixes the worst stretch on all five
  body types is about 10 cm of cloth (the crotch gusset in full splits, the armpits with hands on
  head) and no gaps show in renders. The gloves were rebuilt from each body's own hand surface
  (`Tools/Blender/build_gloves.py`) and stretch at most 0.6 cm in any pose, including a closed fist.
  Always check kicks and splits in Unreal too: MetaHuman's corrective bones aren't modelled here.
- Skin can't poke through cloth when the body bends: body triangles under the jacket, pants, gloves and
  foot guards are removed via hidden face maps while those pieces are worn.
- FBX units: gear FBX files are centimetres (UnitScaleFactor 1, root scale 1), matching the MetaHuman
  export. Metre-scale files import 100x too small because the importer doesn't convert scene units.

Colour and appearance rules for anything exposed to players: `Docs/Character_Customization.md`.

## Notes

- Auto-rigging the face and downloading texture sources are cloud services that need an Epic account
  sign-in in the editor. They are only needed for DCC/DNA/material export, not for geometry.
- The engine is a source build. If Unreal reports a plugin "could not be found" at startup, rebuild
  the editor for the project:
  `C:\UE_5.8.0\Engine\Build\BatchFiles\Build.bat UnrealEditor Win64 Development -Project="D:\Open-Stance-Gyeorugi\OpenStance.uproject" -WaitMutex`
