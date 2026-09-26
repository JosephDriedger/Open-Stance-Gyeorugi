# Open Stance: Gyeorugi

Real taekwondo sparring, one on one: read the distance, choose your kick with a flick of the Skill Stick, and land it before your opponent does.

Open Stance is a 3D sports fighting game built in Unreal Engine 5.8. Matches follow World Taekwondo rules: 2-minute rounds, electronic protector scoring, gam-jeom penalties and a 12-point gap, with no health bar and no combo strings. Fighters are MetaHumans in doboks and blue (Chung) or red (Hong) gear, animated from motion capture of real practitioners. It is a BCIT Capstone project (2026–2027) targeting PlayStation 5 and Xbox Series X|S, with Windows PC used for development.

Open Stance covers sparring only. Forms (poomsae) and breaking are out of scope.

## Status

Pre-production. The design is a draft and there is no gameplay prototype yet: `Source/OpenStance` has no gameplay code, so the Skill Stick is untested until Milestone 1. What exists today:

- Game Design Document (v0.6 draft), controls layout, project plan and mocap shot list in `Docs/`.
- A base MetaHuman fighter with a seven-piece wardrobe (dobok jacket and pants, belt, chest protector, helmet, gloves, foot guards) and Chung/Hong materials. It passes a full-body range-of-motion test.
- A roster of six MetaHuman referees in uniform, with Chaos cloth on ties and trousers.
- Staging levels `L_CompetitionArena` (8 m octagon mat in a 12 m square) and `L_TrainingDojang`, plus arena and dojang props.
- A MotionBuilder test character for the first motion-capture session (`Docs/Vicon_Nexus_Test.md`).

## Design at a glance

- **Skill Stick.** The right stick chooses the kick. Up gives a side or cut kick, left or right a roundhouse or hook kick, and circles and other motions give axe, spinning and tornado kicks. RT kicks with the back leg, RB aims at the head and LB fakes.
- **Real scoring.** 1 point for a punch, 2 for a body kick, 3 for the head, 4 for a spinning body kick and 6 for a spinning head kick.
- **Distance and commitment.** Attacks never home in from out of range, and every technique has startup, active and recovery phases that can be punished.
- **Stamina** limits how often a fighter can throw big techniques; it is separate from score.
- **Modes.** Training dojang, sparring against the AI or a friend on one console, and Career from white belt to a world final.

The full design is in `Docs/GDD_Open_Stance.docx`.

## Repository layout

| Path | Contents |
| --- | --- |
| `OpenStance.uproject` | Unreal project (UE 5.8 source build) |
| `Source/OpenStance` | Runtime game module |
| `Source/OpenStanceEditorTools` | Editor module that exposes Chaos cloth creation to Python |
| `Config/` | Engine, editor, game, input and MetaHuman wardrobe configuration |
| `Docs/` | Game Design Document, controls, project plan, mocap shot list, UML diagrams, [character customization rules](Docs/Character_Customization.md), [Vicon/Nexus test plan](Docs/Vicon_Nexus_Test.md) |
| `Resources/` | Source art outside the Unreal project: fighter and MetaHuman FBX files, fitted gear, referee outfits, environment meshes and textures, MotionBuilder test character, reference images |
| `Tools/Blender/` | Rig, gear-fitting, hidden-face-map and environment-mesh scripts ([README](Tools/Blender/README.md)) |
| `Tools/Unreal/` | Editor Python scripts for characters, wardrobe, referees, cloth and levels ([README](Tools/Unreal/README.md)) |
| `Tools/MotionBuilder/` | Script that prepares the MotionBuilder test character |
| `Tools/Environment/` | Procedural environment texture generator |

`Content/` is not tracked in git. Binary game assets are versioned in Perforce.

## Getting started

Requirements: Unreal Engine 5.8 (source build) on Windows with Visual Studio, plus Blender for the art pipeline. The project enables the MetaHuman Character, Chaos Outfit Asset, Groom (HairStrands), Python Script and Editor Scripting Utilities plugins.

1. Sync `Content/` from Perforce and clone this repository into the same folder.
2. Right-click `OpenStance.uproject` and choose **Generate Visual Studio project files**.
3. Build the editor:
   ```
   C:\UE_5.8.0\Engine\Build\BatchFiles\Build.bat OpenStanceEditor Win64 Development -Project="D:\Open-Stance-Gyeorugi\OpenStance.uproject" -WaitMutex
   ```
4. Open `OpenStance.uproject` and load `L_CompetitionArena` or `L_TrainingDojang`.

If Unreal reports a plugin "could not be found" at startup, rebuild the editor as in step 3.

## Character pipeline

Fighter gear is refit to MetaHuman bodies in Blender and imported back into Unreal as wardrobe items:

1. `Tools/Unreal/create_base_fighter.py` exports the MetaHuman body and head.
2. `Tools/Blender/fit_to_body.py` and `hidden_face_maps.py` refit the dobok and gear and bake hidden face maps.
3. `Tools/Unreal/import_fighter_gear.py` imports the result as wardrobe items.

Every gear piece is skinned to the MetaHuman body skeleton, so any animation on a MetaHuman body drives it, and mocap is retargeted with the IK Retargeter. Player-facing colour rules (side colours only on the protector and helmet; natural skin, hair and eye colours only) are in [Docs/Character_Customization.md](Docs/Character_Customization.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
