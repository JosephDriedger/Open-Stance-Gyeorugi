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
| `import_fighter_gear.py` | Imports the fitted parts (`Resources/Models/Fitted/MH_FighterBase_Body`) onto the MetaHuman body skeleton, builds the two-sided recolour material `M_FighterGear` + `MI_FighterGear_Chung/Hong`, and creates or updates `WI_Fighter_<Part>` wardrobe items (SkeletalMesh slot pipeline + body hidden face maps). Safe to re-run in an open editor; close MetaHuman Creator first. |
| `gear_rom_test.py` | Deformation check: plays MetaHuman's body range-of-motion animation on the base body with all gear following (leader pose). `py ".../gear_rom_test.py"` spawns it at Z 20000 and frames the camera; `... 18.5` pauses at 18.5 s, `... 18.5 back` views from behind, `... play` resumes. Enable viewport Realtime (Ctrl+R) to see playback. |
| `fix_wardrobe_pipelines.py` | One-off repair for wardrobe items created before pipelines were assigned. |
| `create_referee.py` | Referee roster from MetaHuman presets (Kelvin, Bo, Jorge, Omari, Walter, Vivian) as `/Game/Characters/Officials/MH_Referee_<P>`; exports each body to `Resources/Models/MetaHuman/`. Matches pick one at random. |
| `import_referee_outfit.py` | Imports each referee's uniform (shirt, tie, trousers, belt, sneakers from `Tools/Blender/build_referee_outfit.py`) onto that referee, with hidden face maps; puts it on and removes the preset's default T-shirt. |
| `setup_cloth.py` | Chaos cloth on the garments that move: fighter belt tails, jacket skirt, pant hems; referee tie and trouser legs. Re-run after any re-import. Uses the C++ helper `unreal.OpenStanceClothLibrary`. |
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
- Verified with `gear_rom_test.py` (full body range of motion: arms overhead, squat, torso twist) and the
  Blender stress poses (`posetest`: guard, round-kick chamber, twist): no tearing or flapping.
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
