# Fighter rig and customization tools (Blender)

Scripts that turn the Meshy AI fighter (`Resources/Models/Fighter.fbx`) into an
Unreal-ready, customizable character:

- a UE5 Mannequin (Manny)-compatible skeleton, so MetaHuman Animator / Rokoko mocap
  retargets cleanly with the IK Retargeter;
- separate skinned meshes for each swappable part, all on that one skeleton;
- colour masks for team colour, belt rank, collar and skin tone;
- body-type morph targets.

## Running

From Blender's Python console (Scripting workspace):

```python
p = r"D:\Open-Stance-Gyeorugi\Tools\Blender\run.py"; exec(compile(open(p).read(), p, "exec"))
run("pipeline")
```

Or from a terminal:

```
blender --background --factory-startup --python Tools/Blender/run.py -- pipeline
```

`run("pipeline")` clears the current scene. To write somewhere other than
`Resources/Models` (e.g. a test run), set `os.environ["OPEN_STANCE_RIG_OUTPUT"]` first.
Logs go to `Tools/Blender/logs/`.

| Step | Script | What it does |
| --- | --- | --- |
| 1 | `import_source.py` | Clears the scene, imports `Fighter.fbx` |
| 2 | `build_rig.py` | Replaces the Meshy armature with the 87-bone Manny skeleton, binds with bone heat |
| 3 | `reweight.py` | Replaces body weights with region/joint-chain weights (keeps bone heat for hands) |
| 4 | `body_shapes.py` | Adds `BodyHeavy` / `BodyMuscular` / `BodySlim` shape keys |
| 5 | `export_fbx.py` | Exports the combined `Fighter_Rigged.fbx` |
| 6 | `verify_fbx.py` | Re-imports it in a scratch scene and reports scale/hierarchy/skin |
| 7 | `segment_parts.py` | Classifies faces by texture colour, grows patches along creases |
| 8 | `assign_parts.py` | Labels patches as parts, absorbs fragments (`part` face attribute) |
| 9 | `split_parts.py` | One skinned mesh object per part (`SK_Fighter_<Part>`) |
| 10 | `make_masks.py` | Bakes `Textures/T_Fighter_BaseColor.png` (with gear-off cleanup of the shell under the protector) and `T_Fighter_Masks.png` |
| 11 | `preview_material.py` | Blender preview of the recolour material on all parts |
| 12 | `export_parts.py` | `Modular/SK_Fighter_<Part>.fbx` per part |
| 13 | `save_blend.py` | Saves `Fighter_Rigged.blend` |

Interactive helpers:

- `run("viewtools")`: `look(center, dist, 'FRONT')`, `material_preview()`, `xray()`,
  `show_parts("Head", hide_others=True)`, `show_colour_attribute("viz_part")`,
  `set_body(heavy=1)`.
- `run("posetest")`: `pose_guard()`, `pose_chamber()`, `pose_twist()`, `reset_pose()`.
- `run("preview_material")` then `set_look(side="hong", belt=(0.8, 0.55, 0.02), collar=(0.8, 0.8, 0.8), skin_tone="MST06")`
  (`side` is `"chung"` or `"hong"`; belt/collar are linear RGB, `None` keeps the original;
  `skin_tone` is a Monk Skin Tone key). Colour rules: `Docs/Character_Customization.md`.
- `run("analyze_mesh")`: cross-section measurements used to place joints.
- `run("fit_to_body", TARGET_FBX=r".../MH_FighterBase_Body.fbx", TARGET_HEAD_FBX=r".../MH_FighterBase_Head.fbx")`:
  refits the dobok and gear onto a MetaHuman (bodies come from `Tools/Unreal/create_base_fighter.py`).
  Poses the fighter skeleton onto the MetaHuman joints, then pushes cloth out along rays from each
  bone axis (torso measured perpendicular to the spine; 4 passes, smoothed correction vectors), pulls
  the under-protector shell in to form the gear-free dobok top, makes face winding point outward
  (Unreal culls back faces), copies weights from the MetaHuman body with anti-warp rules (protector and
  belt on torso bones only, collar on upper spine/neck/clavicles, half the thigh influence on the
  jacket skirt moved to the pelvis, then smoothed) and exports centimetre FBX files to
  `Resources/Models/Fitted/<Body>/SK_Fighter_<Part>.fbx` on the body skeleton.
- `run("hidden_face_maps", TARGET_NAME="MH_FighterBase_Body")` (after `fit_to_body`): bakes
  `T_HFM_<Part>.png` body hidden face maps (black = body skin under that garment, removed in Unreal while
  it's worn). MetaHuman body UVs sit in UDIM tile 1002 and are wrapped to 0-1 like Unreal does.
- `run("build_referee_outfit", REFEREE="Kelvin")`: referee uniform (light-blue shirt with collar,
  pocket and placket, navy tie, beige straight-leg trousers, brown belt, white sneakers) grown from that
  referee's MetaHuman body, skinned to the body skeleton, exported to `Resources/Models/Referee/<P>/`
  with hidden face maps. Run once per roster member.
- `run("build_environment_meshes")`: arena and dojang props (mats, truss, judge tables, chairs, seat
  rows, scoreboard, heavy bags, paddles, shields, doboks, cubbies, windows...) in an "Environment"
  scene, exported to `Resources/Environment/Meshes/` (textures: `py Tools/Environment/make_env_textures.py`).
- `run("build_venue_meshes")`: Career venue props (GDD 6.2): stadium seat blocks and gym bleachers with
  stand-in seated crowds, club mates on benches, warm-up groups, portable and gym scoreboards, basketball hoop,
  high bays, ad boards, court signs, raised stage and steps, video cube, LED ribbon, hanging flags, broadcast
  camera and jib, entrance arch, runway, moving heads, podium. Both scripts share `env_builder.py` (prop
  conventions; large props are assembled in chunks because bmesh primitive ops slow down as a bmesh grows).
- Stress-testing a MetaHuman fit: `run("posetest"); use_armature("root", 25, followers=["root.001"])`, then
  `pose_chamber()` / `pose_twist()`. The follower matters: the MetaHuman head mesh (neck and shoulders)
  is on its own `root.001` skeleton and would otherwise stay still and look like the collar tore.
- **Clean gear (current):** `blender --background --factory-startup --python Tools/Blender/build_clean_gear.py [-- Base Compact Stocky LeanTall Tall]`
  carves the jacket, pants, belt, protector, helmet, gloves and foot guards from each MetaHuman body's own
  surface (tailored ease, V-neck collar, knot and tails), with the body's skin weights, so it deforms exactly like
  the body. The sparring gear follows World Taekwondo competition kit (Daedo / KP&P style): a 1.6 cm moulded trunk
  protector over the front and sides with white binding, V neck, white shoulder straps and a back tie (the plate is
  a blurred envelope of the jacket, so it shows no pecs or abs); a smooth superellipsoid foam head gear with ear
  holes, cheek pieces and chin strap; white fingerless gloves padded over the knuckles; thin white electronic sensor
  socks with the toes out, grey instep pad and grey sole. Textures from `py Tools/Blender/make_gear_textures.py`.
  Replaces the Meshy-based `fit_to_body` gear for MetaHuman bodies. Checks: `Tools/Validation/check_gear_poses.py`
  (pose stretch), `Tools/Validation/preview_gear.py` (quick shaded views) and `Tools/Unreal/animation_test.py`.
  Hidden face maps only cover skin on the bones a garment can reach (`allow` in `hidden_face_maps.py`), so long
  rays from fingers or toes can't hit a sleeve or hem and hide them.
- **Mocap test model:** `blender --background --factory-startup --python Tools/Blender/build_test_model.py -- Medium`
  assembles the fighter (body, head with eyes, teeth and lashes, clean gear) on the one MetaHuman body skeleton,
  textured (MetaHuman stock skin maps from `Tools/Unreal/export_stock_skin_textures.py`, tinted to one skin tone;
  gear atlas), with body skin under the gear removed, studio lights, a mat and a camera, and the range-of-motion
  take retargeted on. Writes `Resources/Models/TestFighter/OpenStance_TestFighter_MH.blend` and `.fbx` (rest pose,
  textures embedded) and `Resources/Previews/OpenStance_Medium_Gear_ROM.fbx`. Then
  `mobupy.exe Tools/MotionBuilder/prepare_test_character.py --metahuman` characterizes it for MotionBuilder.
- Other body types: `blender --background --factory-startup --python Tools/Blender/fit_all_body_types.py -- Compact Stocky LeanTall Tall`
  (headless, no window) runs `fit_to_body` and `hidden_face_maps` for each `MH_Fighter<Type>` exported by
  `Tools/Unreal/create_body_types.py`, writing `Resources/Models/Fitted/MH_Fighter<Type>_Body/`.
- Mocap shot-list check (no Blender needed): `py Tools/Validation/check_gear_poses.py` skins the exported
  `Fitted/<Body>/SK_Fighter_*.fbx` onto the body in 14 poses taken from
  `Docs/Open_Stance_Mocap_Shot_List.docx` (chamber, head-height kicks, splits, squat, kneel, seated,
  get-up, arms overhead...) and reports torn edges per garment, with the bare body as a control.
  Run it after every `fit_to_body`; the crotch, thigh-fade and armpit weight rules in `fit_to_body.py`
  came from it. `--render DIR` writes a quick image per pose.
- `run("transfer_weights", TRANSFER_TARGETS=["MyNewHelmet"])`: skins a new mesh placed on
  the T-posed fighter (new helmet, protector, face...) by copying weights and body-type
  shape keys from the base body, then parents it to the armature.

## Parts

| Part | Contents | Notes |
| --- | --- | --- |
| `Head` | Face, ears, neck | A face mask only: no skull/scalp (the helmet covers it) |
| `BodySkin` | Fingers, toes | |
| `Helmet` | Head guard, chin strap | |
| `Protector` | Chest protector (hogu) | A full shirt shell sits underneath, so it can be swapped without holes |
| `Jacket` | Dobok top, sleeves, skirt, collar | |
| `Pants` | Dobok pants | |
| `Belt` | Band, knot, tails | |
| `Gloves` | Fingerless gloves, wrist wraps | The glove is effectively the hand; swap, don't remove. On MetaHuman bodies `fit_to_body` replaces the Meshy shell with one carved from the body's hand (`build_gloves.py`: white hand, black cuff, body skin weights) |
| `FootGuards` | Foot protectors | |

## Masks (`T_Fighter_Masks.png`, linear / sRGB off)

| Channel | Region | Suggested UE use |
| --- | --- | --- |
| R | Blue areas of helmet + protector | Side colour: Chung blue (texture) or Hong red only |
| G | Belt | Belt rank colour |
| B | Black dan collar | Collar colour (black / red-black poom / white) |
| A | Skin | Real skin tone (preview only; in game skin comes from MetaHuman) |

Recolour per region: `lerp(Base, Colour * pow(clamp(Luminance(Base) / Ref, 0, 3), Detail), Mask)`,
with `Ref` = median linear luminance of the region (logged by `preview_material.py`) and
`Detail` = 0.8 for the Hong red, 0.35 for belt/collar. Side: `Mask = MaskR * TeamSide`
(0 = Chung, 1 = Hong, red fixed at sRGB `#C8102E`). Skin: `lerp(Base, Base * ToneMultiplier, MaskA)`,
where the multiplier maps the texture's measured skin colour to a Monk Skin Tone reference.
See `Docs/Character_Customization.md` for the colour rules.

## Unreal import

1. Import one part (e.g. `SK_Fighter_Jacket.fbx`) with **Import Morph Targets** on: it
   creates the Skeleton asset.
2. Import the other parts choosing that Skeleton.
3. Build the character with one leader Skeletal Mesh Component and the other parts following
   it (Leader Pose / `SetLeaderPoseComponent`), or merge with Skeletal Mesh Merge / Mutable.
4. Drive `BodyHeavy` / `BodyMuscular` / `BodySlim` with the same value on every part.
5. Textures: base colour sRGB; masks with sRGB off and `Masks` compression.

## Things to know

- Joint positions and weighting/segmentation thresholds are measured for this mesh's
  T-pose. If the source model changes, re-run `analyze_mesh` and check each step's result
  in the viewport (`show_colour_attribute("viz_part")`).
- Blender's bone heat fails on this mesh's torso (a shirt is modelled under the chest
  protector), which is why `reweight.py` exists. Body shapes push along body axes, not
  normals, for the same reason.
- The UV layout is Meshy's auto-atlas (thousands of tiny charts). Masks are generated
  procedurally; hand-painting new designs needs clean per-part UVs.
- Twist bones only move in Unreal if the animation source drives them or the AnimBP does.

## Creator fighter source library

`build_creator_fighters.py` builds the five fitted bodies with reversible garment coverage, a rebuilt dobok torso and collar, smoother chest pad, short hair and refined Blender skin shading. Run with `-- Medium` for one preset or omit body names for all five. Outputs, actual renders and integration limits are documented in `Resources/Models/CreatorFighters/README.md`; the existing production assets remain separate. Validate saved switches, bindings and both FBX exports with `Tools/Validation/check_creator_fighters.py` in background Blender.

## Native animation workspace

`build_animation_workspace.py` creates per-body animation scenes from the approved creator .blend files: organized modular parts, original body skeleton, restored original facial rig, keyable FK bone collections, 41 marker reference guides and separate animation tracks. `assemble_character_workspace.py` packages the five scenes into `Resources/Models/OpenStance_Characters_Workspace.blend`, archiving the previous workspace first. Both run headlessly and never alter an interactive Blender session. See `Resources/Models/Animation/README.md` for animation and capture workflow.
