# Open Stance: Gyeorugi

Real taekwondo sparring, one on one: read the distance, choose your kick with a flick of the Skill Stick, and land it before your opponent does.

Open Stance is a 3D sports fighting game built in Unreal Engine 5.8. Matches follow World Taekwondo rules: 2-minute rounds, electronic protector scoring, gam-jeom penalties and a 12-point gap, with no health bar and no combo strings. Fighters are MetaHumans in doboks and blue (Chung) or red (Hong) gear, animated from motion capture of real practitioners. It is a BCIT Capstone project (2026–2027) targeting PlayStation 5 and Xbox Series X|S, with Windows PC used for development.

Open Stance covers sparring only. Forms (poomsae) and breaking are out of scope.

## Status

Milestone 1 (Skill Stick proof of concept, due 9 November 2026). The combat core is playable in a greybox match: two fighters throw techniques through the Skill Stick, animated with placeholder technique clips until motion capture starts at Milestone 2. What exists today:

- The combat core in C++ (`Source/OpenStance/Public/Combat`): Skill Stick recognition and input buffering, footwork and lead/back-leg resolution, the combat state machine with committed startup, active and recovery phases, and limb-trace hit registration with WT scoring, gam-jeom, stamina and rounds. 52 automation tests cover it.
- A greybox match reached from Sparring in the menus (Setup, Side Select, Fighter Select), with a HUD, a debug and Training overlay and development console commands such as `os.RunProof` and `os.ShowHitboxes`. See [Docs/Combat_Debug.md](Docs/Combat_Debug.md).
- 24 premade fighters on four body types in the layered traditional dobok and sparring gear, playing placeholder clips for every technique (Blender-keyed, mirrored for the left leg).
- Game Design Document (v0.14 draft), controls layout, project plan, mocap shot list and art asset inventory in `Docs/`.
- A base MetaHuman fighter with a seven-piece wardrobe (dobok jacket and pants, belt, chest protector, helmet, gloves, foot guards) and Chung/Hong materials. It passes a full-body range-of-motion test.
- A roster of six MetaHuman referees in uniform, with Chaos cloth on ties and trousers.
- Staging levels `L_CompetitionArena` (8 m octagon mat in a 12 m square) and `L_TrainingDojang`, plus arena and dojang props.
- A MotionBuilder test character for the first motion-capture session at Milestone 2: open `Models and Rigs/01 Mocap Test/1 OPEN IN MOTIONBUILDER - Medium Sparring` (the characterized `Resources/Models/Animation/MotionBuilder/Medium/OpenStance_Medium_Sparring.fbx`). The [test checklist](Docs/Mocap_Test.md), [recording-day workflow](Docs/Mocap_Record.md) and [Vicon/Nexus notes](Docs/Vicon_Nexus_Test.md) cover the session.
- The whole menu system (title, main menu, setup, fighter select, match HUD, results, bracket, training, Career, fighter creator, options, controls and the Future pages), written in C++ from the HTML prototype in `Docs/Prototype` and running in the empty level `L_MainMenu`. See [Docs/Menu_System.md](Docs/Menu_System.md).

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
| `Source/OpenStance` | Runtime game module: the menu system (`Public/Menu`, Slate and UMG written in C++) and the combat core and greybox match (`Public/Combat`) |
| `Source/OpenStanceEditorTools` | Editor module that exposes Chaos cloth creation and menu screenshots to Python |
| `Config/` | Engine, editor, game, input and MetaHuman wardrobe configuration |
| `Docs/` | Game Design Document, controls, project plan, mocap shot list, UML diagrams, [menu system notes](Docs/Menu_System.md), [combat data](Docs/Combat_Data.md), [Skill Stick input and footwork](Docs/Combat_Input.md), [combat state](Docs/Combat_State.md), [hit registration](Docs/Combat_Hits.md), [greybox and test commands](Docs/Combat_Debug.md), [character customization rules](Docs/Character_Customization.md), [Vicon/Nexus test plan](Docs/Vicon_Nexus_Test.md) |
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
4. Open `OpenStance.uproject` and load `L_CompetitionArena` or `L_TrainingDojang`, or press Play on `L_MainMenu` (the project's default map) to try the menu.

If Unreal reports a plugin "could not be found" at startup, rebuild the editor as in step 3.

## Character pipeline

Fighter gear is refit to MetaHuman bodies in Blender and imported back into Unreal as wardrobe items:

1. `Tools/Unreal/create_base_fighter.py` exports the MetaHuman body and head.
2. `Tools/Blender/fit_to_body.py` and `hidden_face_maps.py` refit the dobok and gear and bake hidden face maps.
3. `Tools/Unreal/import_fighter_gear.py` imports the result as wardrobe items.

Every gear piece is skinned to the MetaHuman body skeleton, so any animation on a MetaHuman body drives it, and mocap is retargeted with the IK Retargeter. Player-facing colour rules (side colours only on the protector and helmet; natural skin, hair and eye colours only) are in [Docs/Character_Customization.md](Docs/Character_Customization.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
