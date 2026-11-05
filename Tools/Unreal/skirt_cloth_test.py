"""Chaos cloth on the staged Stocky jacket skirt, played through the front kick in a Simulate session.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/skirt_cloth_test.py [fbx=PATH] [kind=Body] [max=CM] [tailpin=Z] [tailfree=Z] [tailmax=CM] [pin=Z] [free=Z] [inflate=CM] [chain] [tailcloth] [nocloth] [tag=NAME] quit"

Imports Resources/Models/FinalRefinement/SkirtChaosClothTest/Stocky_SkirtCloth.fbx (Tools/Blender/export_skirt_cloth_test.py)
into a scratch folder on the installed Stocky production skeleton, with its kick animation, and puts cloth on the skirt
section ('Dobok_Skirt_Cloth'): skinned at and above `pin` cm, free to move up to `max` cm at and below `free` cm, colliding
with the Stocky body physics asset (`inflate` grows its pelvis, thigh and calf capsules by that many cm, in a scratch copy
used only by the cloth, so they reach the trouser surface). `nocloth` skips the cloth (the skinned skirt alone, for comparison). The kick plays twice;
the second pass is captured at the listed frames. Nothing is saved; the scratch folder is deleted at the end.

Images: Saved/Screenshots/SkirtCloth/<tag>/F<frame>_<view>.png, log Saved/Logs/skirt_cloth_test.txt.
"""
import os
import sys
import time
import traceback
import uuid

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
FBX_DEFAULT = f"{REPO}/Resources/Models/FinalRefinement/SkirtChaosClothTest/Stocky_SkirtCloth.fbx"
LOG = f"{REPO}/Saved/Logs/skirt_cloth_test.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
_KIND = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("kind=")), "Stocky")
# Production bodies exist for five types; the others borrow Stocky's (only its physics asset is used in chain mode).
_STEM = {"Medium": "MH_FighterBase", "Compact": "MH_FighterCompact", "LeanTall": "MH_FighterLeanTall",
         "Stocky": "MH_FighterStocky", "Tall": "MH_FighterTall"}.get(_KIND, "MH_FighterStocky")
PRODUCTION = f"/Game/Characters/Fighters/Export/{_STEM}_Body"
SCRATCH = "/Game/__SkirtClothTest__/Run_" + uuid.uuid4().hex[:8]
ARGS = sys.argv[1:]
FLAGS = set(ARGS)


def arg(name, default):
    return next((type(default)(a.split("=", 1)[1]) for a in ARGS if a.startswith(name + "=")), default)


MAX_CM, PIN_Z, FREE_Z = arg("max", 10.0), arg("pin", 91.0), arg("free", 80.0)
FBX = arg("fbx", FBX_DEFAULT)
TAIL_PIN_Z, TAIL_FREE_Z, TAIL_MAX_CM = arg("tailpin", 93.0), arg("tailfree", 86.0), arg("tailmax", 30.0)
INFLATE_CM = arg("inflate", 0.0)
GRAVITY = arg("gravity", 1.0)  # cloth gravity scale (a debug lever: a heavy skirt shows at once whether cloth renders)
INFLATE_BONES = ("pelvis", "thigh", "calf")
CHAIN = "chain" in FLAGS
# kinematic capsules for the chain links (and the skirt cloth): bone, bone it runs towards, radius cm, sized to the
# traditional trousers and skirt (setup_belt_chain.py's fitted-gear values)
CHAIN_BODY = [("pelvis", "spine_01", 20.0), ("thigh_l", "calf_l", 13.0), ("thigh_r", "calf_r", 13.0),
              ("calf_l", "foot_l", 8.5), ("calf_r", "foot_r", 8.5)]
# Per-body radii measured on the trousers at export (<fbx>_capsules.json), when present.
import json as _json
_caps = os.path.splitext(FBX)[0] + "_capsules.json"
if os.path.exists(_caps):
    _measured = _json.load(open(_caps))
    CHAIN_BODY = [(b, a, float(_measured.get(b, {}).get("radius_cm") or r)) for b, a, r in CHAIN_BODY]
TAG = arg("tag", "cloth" if "nocloth" not in FLAGS else "skinned")
OUT = f"{REPO}/Saved/Screenshots/SkirtCloth/{TAG}"
FRAMES = (1, 20, 25, 30, 35, 45, 55, 65)  # kick frames, as in the Blender reviews
FPS = 30.0  # the kick exports at 30 fps (144 frames, 4.77 s)
W, H = 800, 800
LOAD_SETTLE_S, SIM_START_S = 60.0, 15.0
EAL = unreal.EditorAssetLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Test:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.state, self.until, self.next_shot, self.passes, self.last_t = "load", 0.0, 0, 0, 0.0
        self.busy = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[skirt_cloth_test] {msg}")

    def tick(self, dt):
        # Loading the level and importing pump editor ticks, which would re-enter this callback mid-step.
        if self.busy:
            return
        self.busy = True
        try:
            self.step()
        except Exception:
            self.log("ERROR\n" + traceback.format_exc())
            self.finish()
        finally:
            self.busy = False

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        try:
            unreal.EditorLevelLibrary.editor_end_play()
        except Exception:
            pass
        self.state = "cleanup"
        self.handle = unreal.register_slate_post_tick_callback(self.cleanup)
        self.until = time.time() + 5.0

    def cleanup(self, dt):
        if time.time() < self.until:
            return
        unreal.unregister_slate_post_tick_callback(self.handle)
        for a in actors.get_all_level_actors():
            if a.get_actor_label().startswith("SC_"):
                actors.destroy_actor(a)
        if EAL.does_directory_exist(SCRATCH):
            self.log(f"scratch deleted: {EAL.delete_directory(SCRATCH)}")
        self.log("DONE")
        self.f.close()
        if "quit" in FLAGS:
            unreal.SystemLibrary.quit_editor()

    def import_mesh(self):
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
        production = EAL.load_asset(PRODUCTION)
        ui = unreal.FbxImportUI()
        ui.import_mesh = True
        ui.import_as_skeletal = True
        ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        ui.automated_import_should_detect_type = False
        ui.import_animations = True
        ui.import_materials = True
        ui.import_textures = True
        ui.create_physics_asset = False
        if not CHAIN:  # chain bones are not on the production skeleton: a chain import gets its own scratch skeleton
            ui.skeleton = production.get_editor_property("skeleton")
        ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", True)  # driven keys baked as morph curves
        ui.skeletal_mesh_import_data.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = FBX, SCRATCH, "SK_SkirtTest"
        task.automated, task.save, task.options = True, False, ui
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        self.mesh = EAL.load_asset(f"{SCRATCH}/SK_SkirtTest")
        if not isinstance(self.mesh, unreal.SkeletalMesh):
            raise RuntimeError("import failed")
        anims = [EAL.load_asset(p) for p in EAL.list_assets(SCRATCH, recursive=True)]
        anims = [a for a in anims if isinstance(a, unreal.AnimSequence)]
        if not anims:
            raise RuntimeError("no animation imported")
        self.anim = anims[0]
        morphs = [m.get_name() for m in self.mesh.get_editor_property("morph_targets")]
        try:
            curves = [str(c) for c in unreal.AnimationLibrary.get_animation_curve_names(self.anim, unreal.RawCurveTrackTypes.RCT_FLOAT)]
        except Exception as error:
            curves = [f"(curve list failed: {error})"]
        self.log(f"morph targets {len(morphs)}: {sorted(set(morphs))[:6]}; animation curves {len(curves)}: {curves[:6]}")
        phys = production.get_editor_property("physics_asset")
        self.mesh.set_editor_property("physics_asset", phys)
        if CHAIN:
            # Kinematic leg and pelvis capsules sized to the garments, simulated ball-jointed links on every belt_ bone
            # (C++ OpenStanceBeltChainLibrary, as for the game's belt follower). The skirt cloth collides with it too.
            phys = unreal.OpenStanceBeltChainLibrary.create_empty_physics_asset(SCRATCH, "PA_SkirtTest")
            bones = [b for b, _, _ in CHAIN_BODY]
            result = unreal.OpenStanceBeltChainLibrary.build_belt_chain_physics_asset(
                self.mesh, phys, bones, [a for _, a, _ in CHAIN_BODY], [r for _, _, r in CHAIN_BODY],
                "belt_", 1.2, 0.1, 40.0, 0.3, 10.0)
            self.log("belt chain physics: " + result + "; capsules " + ", ".join(f"{b} {r:.1f}" for b, _, r in CHAIN_BODY))
        if INFLATE_CM > 0:
            phys = self.inflated_physics(phys)
        self.log(f"imported {self.mesh.get_path_name()}, animation {self.anim.get_name()} {self.anim.get_play_length():.2f}s, physics {phys.get_name() if phys else None}")
        skeletal = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        slots = [m.get_editor_property("material_slot_name") for m in self.mesh.get_editor_property("materials")]
        sections = skeletal.get_num_sections(self.mesh, 0)
        skirt = [s for s in range(sections) if "Skirt" in str(slots[skeletal.get_lod_material_slot(self.mesh, 0, s)])]
        tails = [s for s in range(sections) if "Belt_Tail" in str(slots[skeletal.get_lod_material_slot(self.mesh, 0, s)])]
        self.log(f"{sections} sections; skirt sections {skirt}; belt tail sections {tails}")
        if not skirt:
            raise RuntimeError("skirt section not found; slots: " + ", ".join(str(s) for s in slots))
        if "nocloth" not in FLAGS:
            for s in skirt:
                result = unreal.OpenStanceClothLibrary.setup_section_cloth(
                    self.mesh, s, phys, PIN_Z, FREE_Z, MAX_CM, unreal.Vector(-1e5, -1e5, -1e5), unreal.Vector(1e5, 1e5, 1e5))
                self.log(f"cloth on section {s} (pin {PIN_Z} free {FREE_Z} max {MAX_CM} cm): {result}")
            # Belt tails hang from the knot and swing; the rising thigh and knee push them through the body capsules.
            for s in (tails if "tailcloth" in FLAGS else []):
                result = unreal.OpenStanceClothLibrary.setup_section_cloth(
                    self.mesh, s, phys, TAIL_PIN_Z, TAIL_FREE_Z, TAIL_MAX_CM, unreal.Vector(-1e5, -1e5, -1e5), unreal.Vector(1e5, 1e5, 1e5))
                self.log(f"belt tail cloth on section {s} (pin {TAIL_PIN_Z} free {TAIL_FREE_Z} max {TAIL_MAX_CM} cm): {result}")
            self.log(unreal.OpenStanceClothLibrary.describe_cloth(self.mesh))
            for asset in self.mesh.get_editor_property("mesh_clothing_assets"):
                configs = asset.get_editor_property("cloth_configs")
                for name, config in configs.items():
                    if GRAVITY != 1.0 and hasattr(config, "set_editor_property"):
                        try:
                            config.set_editor_property("gravity_scale", GRAVITY)
                        except Exception as error:
                            self.log(f"could not set gravity on {name}: {error}")
                    values = []
                    for prop in ("gravity_scale", "anim_drive_stiffness", "collision_thickness", "damping_coefficient", "iteration_count"):
                        try:
                            values.append(f"{prop}={config.get_editor_property(prop)}")
                        except Exception:
                            pass
                    self.log(f"cloth config {name} ({config.get_class().get_name()}): " + ", ".join(values))

    def inflated_physics(self, phys):
        """Scratch copy of the body physics asset with the hip and leg capsules grown by INFLATE_CM.

        The capsules fit the body, but the trousers sit outside it, so cloth that collides with them can still slide
        behind the trouser surface. Only the cloth uses this copy."""
        copy = EAL.duplicate_asset(phys.get_path_name(), f"{SCRATCH}/PHYS_SkirtCloth")
        self.log("inflated capsules: " + unreal.OpenStanceClothLibrary.inflate_capsules(copy, list(INFLATE_BONES), INFLATE_CM))
        return copy

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
        actor.set_actor_label("SC_Fighter")
        c = actor.skeletal_mesh_component
        c.set_skinned_asset_and_update(self.mesh)
        slots = [str(n) for n in c.get_material_slot_names()]
        for i, name in enumerate(slots):
            material = c.get_material(i)
            if 'Belt' in name:
                self.log(f"slot {i} {name}: {material.get_path_name() if material else None}")
            if 'onlybelt' in FLAGS and 'Belt' not in name and 'Skin' not in name:  # debug: hide every garment but the belt
                c.show_material_section(i, 0, False, 0)
            if 'tailmat' in FLAGS and 'Belt_Tail' in name:
                c.set_material(i, unreal.EditorAssetLibrary.load_asset('/Engine/BasicShapes/BasicShapeMaterial'))
        data = unreal.SingleAnimationPlayData()
        data.set_editor_property("anim_to_play", self.anim)
        data.set_editor_property("saved_looping", True)
        data.set_editor_property("saved_playing", True)
        data.set_editor_property("saved_play_rate", 1.0)
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_editor_property("animation_data", data)
        c.set_editor_property("visibility_based_anim_tick_option", unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -200, 100))
        cam.set_actor_label("SC_Camera")
        cc = cam.capture_component2d
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("always_persist_rendering_state", True)
        cc.set_editor_property("fov_angle", 40.0)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            cc.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            cc.set_editor_property("post_process_blend_weight", 1.0)

    def collect(self):
        self.world = unreal.EditorLevelLibrary.get_game_world()
        by = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)}
        self.body = by["SC_Fighter"].skeletal_mesh_component
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        if CHAIN and "nosim" not in FLAGS:
            for root in ("belt_l_01", "belt_r_01"):
                self.body.set_all_bodies_below_simulate_physics(root, True, True)
            self.body.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            self.log("belt chain links simulating")
        origin, extent, radius = unreal.SystemLibrary.get_component_bounds(self.body)
        self.log(f"component bounds origin {origin} extent {extent}")
        for bone in ("pelvis", "belt_l_01", "belt_l_08"):
            self.log(f"  ref pose {bone}: {self.body.get_ref_pose_position(self.body.get_bone_index(bone))}")
        imported = self.mesh.get_bounds()
        self.log(f"mesh asset bounds origin {imported.origin} extent {imported.box_extent}")
        self.log("cloth at simulate start: " + unreal.OpenStanceClothLibrary.describe_cloth_simulation(self.body))

    def shoot(self, frame):
        pelvis = self.body.get_socket_location("pelvis")
        target = pelvis + unreal.Vector(0, 0, -5)
        # Blender's front is -Y and the kicking (left) leg is +X; the FBX import keeps those directions in Unreal.
        # The FBX import turns Blender's -Y front into +Y here, so 'back' (from +Y) is the fighter's front, 'front' the back.
        views = {"side": unreal.Vector(120, -40, 20), "front": unreal.Vector(30, -130, 15), "back": unreal.Vector(-50, 120, 15)}
        if CHAIN:
            # straight at the tails, from the side they hang on
            tails = self.body.get_socket_location("belt_l_04")
            out = self.body.get_socket_location("belt_l_01") - pelvis
            out.z = 0
            out = out.normal()
            views["tails"] = (tails, out * 75 + unreal.Vector(0, 0, 10))
            if "wide" in FLAGS:
                views["wide"] = (pelvis, out * 420 + unreal.Vector(0, 0, 60))
        for view, offset in views.items():
            look = target
            if isinstance(offset, tuple):
                look, offset = offset
            loc = look + offset
            target_now = look
            self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, target_now), False, False)
            self.cam.capture_component2d.capture_scene()
            unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"F{frame:03d}_{view}.png")

    def step(self):
        now = time.time()
        if now < self.until:
            return
        if self.state == "load":
            self.state = "loading"
            levels.load_level(LEVEL)
            self.import_mesh()
            self.build()
            self.state, self.until = "start_sim", time.time() + LOAD_SETTLE_S
        elif self.state == "start_sim":
            self.log("starting simulate")
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "collect", now + SIM_START_S
        elif self.state == "collect":
            self.collect()
            self.state = "shoot"
        elif self.state == "shoot":
            t = self.body.get_position()
            if t < self.last_t:
                self.passes += 1
                self.next_shot = 0
                self.log(f"kick pass {self.passes} begins")
            self.last_t = t
            if self.passes < 1:
                return  # first full pass only warms up the cloth
            if self.next_shot < len(FRAMES) and t >= (FRAMES[self.next_shot] - 1) / FPS:
                frame = FRAMES[self.next_shot]
                self.shoot(frame)
                if CHAIN:
                    pelvis = self.body.get_socket_location("pelvis")
                    for bone in ("belt_l_01", "belt_l_08", "belt_r_08"):
                        q = self.body.get_socket_location(bone) - pelvis
                        self.log(f"  {bone} from pelvis: ({q.x:.1f}, {q.y:.1f}, {q.z:.1f}) cm")
                self.log(f"shot frame {frame} at anim t={t:.3f}s (frame {t * FPS + 1:.1f}); cloth: "
                         + unreal.OpenStanceClothLibrary.describe_cloth_simulation(self.body))
                self.next_shot += 1
                if self.next_shot >= len(FRAMES):
                    return self.finish()


_test = Test()
