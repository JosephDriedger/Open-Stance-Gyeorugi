# Rig compatibility with the proposed marker set

Audit of the project rigs against the proposed 41-marker set ([Mocap_Marker_Set.md](Mocap_Marker_Set.md): Plug-in Gait
full body plus left/right fifth-metatarsal markers). Run it with `py Tools/Validation/marker_set_coverage.py`. This is
a structural audit of the rig against the marker set; no capture data exists yet, so nothing here proves a solve.

## Updated native Blender workspace — 2026-10-02

The rebuilt white-uniform fighters are now in `Resources/Models/OpenStance_Characters_Workspace.blend`, with individual scenes in `Resources/Models/Animation/`. Each keeps the 341 actual Blender body bones (the older FBX count below includes additional scene nodes) and restores the original separate 874-bone facial rig. The 41 proposed marker labels are present as hidden reference guides with a recorded body-segment mapping. Their positions are approximate, not a calibrated marker solve.

The new geometry has saved-scene structural tests, synthetic FK mesh-deformation tests, a jaw-deformation test, wardrobe restoration tests, and per-preset MotionBuilder characterization/control-rig save/reopen checks. See `Resources/Models/Animation/*_rig_validation.json`, `workspace_validation.json` and `MotionBuilder/<type>/validation_OpenStance_<type>.json`. Native FK bones and separate NLA tracks support future hand-keyed body, finger, toe and facial animation.

**The historical engine/14-pose results below apply to the earlier gear, not the rebuilt white uniform.** New sleeve/skirt geometry still needs capture-driven and in-engine cloth/corrective validation. No real marker capture solve has been verified. Instructions and limitations: [animation workspace guide](../Resources/Models/Animation/README.md).

## Historical rig audit

**Yes: every segment the marker set solves has a matching bone on both rigs, and the gear works with the rig as the
solved motion would drive it.** What the set cannot drive is limited and known: the finger joints and the toe joints.
Everything else is solved directly or follows from the solved bones by rule.

| Rig | Bones | Solved by markers | Derived by rule | Not driven by any marker |
| --- | ---: | ---: | ---: | ---: |
| MetaHuman body skeleton (production rig, retarget target in Unreal) | 343 | 16 | 269 | 58 (38 finger joints, 20 toe joints) |
| Custom fighter skeleton (the MotionBuilder test rig) | 88 | 16 | 34 | 38 (finger joints) |

## What each marker segment drives

| Segment (markers) | Rig bones |
| --- | --- |
| Pelvis (LASI RASI LPSI RPSI) | `pelvis` |
| Thorax (C7 T10 CLAV STRN RBAK) | `spine_05` / `spine_04` (chest) |
| Head (LFHD RFHD LBHD RBHD) | `head` |
| Upper arm (SHO ELB UPA) | `upperarm_l/r` |
| Forearm (ELB WRA WRB FRM) | `lowerarm_l/r` |
| Hand (WRA WRB FIN) | `hand_l/r` |
| Thigh (ASI KNE THI) | `thigh_l/r` |
| Shank (KNE ANK TIB) | `calf_l/r` |
| Foot (ANK HEE TOE MT5) | `foot_l/r` |

Derived without extra markers: `root` (pelvis footprint), `spine_01-03` (split between pelvis and chest),
`neck_01-02` (between chest and head), `clavicle_l/r` (follow the chest; the shoulder markers place the shoulder
joint), `ball_l/r` (from the foot segment), 26 twist bones (a share of the forearm, upper-arm, thigh and calf twist),
and about 230 corrective and helper bones that the engine drives from the main joints (finger correctives included).

## What the set cannot drive, and what to do

1. **Fingers (38 joints).** One hand marker (LFIN) gives the hand's orientation, not the fingers. Use pose rules:
   closed fist in guard and for punches, relaxed open hand otherwise. The gloves deform correctly on a closed fist
   (maximum stretch 0.6 cm), so this costs no visual quality in sparring. Hands out of gear (menus, ceremony,
   belt tying) are where open or hand-posed fingers would show; capture those with finger markers or pose by hand.
2. **Toes (20 joints).** Markers stop at the metatarsal heads, so toe curl and extension are not captured. The foot
   moves as one rigid segment. Foot guards cover the foot in sparring; barefoot menu animations would show it.
3. **Spine and shoulder girdle detail.** Only two trunk segments are solved (pelvis, chest). The spine bones in
   between interpolate, so torso twist in spinning techniques is spread evenly and any difference in how the
   performer actually twisted is lost. Shoulder shrug and protraction (clavicle and scapula motion) are not
   captured. If spinning kicks or arms-overhead celebrations look stiff, add a lower-back marker (L1/L3 level) and a
   marker on each acromion cluster, or correct by hand in MotionBuilder.
4. **Neck.** The head segment is solved; the neck between chest and head interpolates.

## Evidence the models work with the rig

- **In engine, on the real rig:** MetaHuman's full body range-of-motion animation played on all five fighter body
  types (with sparring gear and dobok only) and all six referees: head rolls, deep forward bend, arms overhead, deep
  squat, T-pose, torso twists. No tearing, spikes or skin showing through. Run it with
  `Tools/Unreal/animation_test.py` (frames in `Saved/Screenshots/AnimTest/`).
- **Numerically, in 14 extreme shot-list poses** (chamber, head-height kicks, splits, squat, kneel, seated,
  get-up, arms overhead, hands on head, arms crossed, bent over): worst garment stretch on any body type is
  3.3 cm (`Tools/Validation/check_gear_poses.py`).

## Not yet verified

- A real solve from marker data (BCIT capture, Actor marker mapping in MotionBuilder, plot to the skeleton).
- The MetaHuman corrective bones as the engine drives them (the numeric check keeps them rigid on their parents;
  the in-engine animation test includes them).
- Whether BCIT's actual template matches these labels and placement (see the lab handoff in the marker set document).
