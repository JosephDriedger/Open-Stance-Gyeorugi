"""A belt-chain mocap target playing in engine, with its belt chain simulating (Simulate session, no window).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/belt_target_test.py [Medium] [VNeck] [Dobok] [shots=N] [gap=S]
                   [start=T] [metrics=S] [nosim] quit"

Imports Resources/Models/Animation/MotionBuilder_BeltChain/<Kind>[/WhiteVNeck]/OpenStance_<Kind>[_Sparring].fbx (add-only) to
/Game/Characters/Fighters/BeltChainTargets/<tag>/, gives it a physics asset (kinematic body capsules, simulated ball-jointed chain
capsules: same C++ helper as setup_belt_chain.py), and plays MetaHuman's body range-of-motion clip on the project's own body of the
same type, invisible. The target is a separate skeleton, so it follows the body by bone name through
UOpenStanceBeltFollowerAnimInstance, exactly as a plotted mocap take would drive it; its own belt_ bones are left to physics.
Images: Saved/Screenshots/BeltTarget/, log Saved/Logs/belt_target_test.txt (with metrics=S: worst link deviation per half second).
"""
import math
import os
import sys
import time
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
ROOT = f"{REPO}/Resources/Models/Animation/MotionBuilder_BeltChain"
OUT = f"{REPO}/Saved/Screenshots/BeltTarget"
LOG = f"{REPO}/Saved/Logs/belt_target_test.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
FLAGS = set(sys.argv[1:])
KIND = next((a for a in sys.argv[1:] if a in ("Medium", "Compact", "Stocky", "LeanTall", "Tall", "Male_Athletic", "Male_Lean",
                                              "Female_Athletic", "Female_Strong")), "Medium")
OUTFIT = "Dobok" if "Dobok" in FLAGS else "Sparring"
STYLE = "WhiteVNeck" if "VNeck" in FLAGS else ""
TAG = f"{KIND}{'_VNeck' if STYLE else ''}_{OUTFIT}"
FOLDER = f"/Game/Characters/Fighters/BeltChainTargets/{TAG}"
MH = "MH_FighterBase" if KIND == "Medium" else f"MH_Fighter{KIND}"
BODY = f"/Game/Characters/Fighters/Export/{MH}_Body"
BODY_CAPSULES = [("pelvis", "spine_01", 14.0), ("thigh_l", "calf_l", 9.5), ("thigh_r", "calf_r", 9.5),
                 ("calf_l", "foot_l", 6.5), ("calf_r", "foot_r", 6.5)]
CHAIN_RADIUS_CM, CHAIN_MASS_KG, SWING_DEG, LINEAR_DAMPING, ANGULAR_DAMPING = 1.2, 0.1, 40.0, 0.3, 10.0
W, H = 960, 960
LOAD_SETTLE_S, SIM_START_S, WARMUP_S = 100.0, 25.0, 4.0

EAL = unreal.EditorAssetLibrary
Belt = unreal.OpenStanceBeltChainLibrary
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def prepare_assets(log):
    """Import the target and build its physics asset, once (add-only)."""
    mesh_path = f"{FOLDER}/SK_{TAG}"
    if not EAL.does_asset_exist(mesh_path):
        EAL.make_directory(FOLDER)
        fbx = f"{ROOT}/{KIND}{'/' + STYLE if STYLE else ''}/OpenStance_{KIND}{'_Sparring' if OUTFIT == 'Sparring' else ''}.fbx"
        ui = unreal.FbxImportUI()
        ui.set_editor_property("import_mesh", True)
        ui.set_editor_property("import_as_skeletal", True)
        ui.set_editor_property("import_animations", False)
        ui.set_editor_property("import_materials", False)
        ui.set_editor_property("import_textures", False)
        ui.set_editor_property("create_physics_asset", False)
        ui.set_editor_property("automated_import_should_detect_type", False)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", fbx)
        task.set_editor_property("destination_path", FOLDER)
        task.set_editor_property("destination_name", f"SK_{TAG}")
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)
        task.set_editor_property("options", ui)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        log("imported", fbx)
    mesh = EAL.load_asset(mesh_path)
    pa_path = f"{FOLDER}/PA_{TAG}"
    if not EAL.does_asset_exist(pa_path):
        pa = Belt.create_empty_physics_asset(FOLDER, f"PA_{TAG}")
        result = Belt.build_belt_chain_physics_asset(
            mesh, pa, [unreal.Name(b) for b, _, _ in BODY_CAPSULES], [unreal.Name(a) for _, a, _ in BODY_CAPSULES],
            [r for _, _, r in BODY_CAPSULES], "belt_", CHAIN_RADIUS_CM, CHAIN_MASS_KG, SWING_DEG, LINEAR_DAMPING, ANGULAR_DAMPING)
        log("physics asset:", result)
        EAL.save_asset(pa_path, only_if_is_dirty=False)
        EAL.save_asset(mesh_path, only_if_is_dirty=False)
    return mesh


class Test:
    def __init__(self, shots, gap, start, metrics, simulate, quit_after):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.shots, self.gap, self.start, self.metrics, self.simulate, self.quit_after = shots, gap, start, metrics, simulate, quit_after
        self.state, self.until, self.taken = "load", 0.0, 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, *a):
        msg = " ".join(str(x) for x in a)
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[belt_target_test] {msg}")

    def tick(self, dt):
        try:
            self.step()
        except Exception:
            self.log("ERROR\n" + traceback.format_exc())
            self.finish()

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        self.log("DONE")
        self.f.close()
        try:
            unreal.EditorLevelLibrary.editor_end_play()
        except Exception:
            pass
        if self.quit_after:
            unreal.SystemLibrary.quit_editor()

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        mesh = self.mesh
        anim = EAL.load_asset(ANIM)
        lib = getattr(unreal, "MaterialLibrary", None) or getattr(unreal, "KismetMaterialLibrary", None)
        base = EAL.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
        grey = lib.create_dynamic_material_instance(world, base)
        grey.set_vector_parameter_value("Color", unreal.LinearColor(0.7, 0.68, 0.64, 1.0))
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
        a.set_actor_label("T_Body")
        leader = a.skeletal_mesh_component
        leader.set_skinned_asset_and_update(EAL.load_asset(BODY))
        ad = unreal.SingleAnimationPlayData()
        ad.set_editor_property("anim_to_play", anim)
        ad.set_editor_property("saved_looping", True)
        ad.set_editor_property("saved_playing", True)
        ad.set_editor_property("saved_play_rate", 1.0)
        ad.set_editor_property("saved_position", self.start)
        leader.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        leader.set_editor_property("animation_data", ad)
        leader.set_editor_property("visibility_based_anim_tick_option",
                                   unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        leader.set_visibility(False)
        t = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
        t.set_actor_label("T_Target")
        c = t.skeletal_mesh_component
        c.set_skinned_asset_and_update(mesh)
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
        c.set_anim_class(unreal.OpenStanceBeltFollowerAnimInstance)
        c.set_editor_property("visibility_based_anim_tick_option",
                              unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        for prop in ("cast_capsule_direct_shadow", "cast_capsule_indirect_shadow"):
            c.set_editor_property(prop, False)
        for i in range(c.get_num_materials()):
            c.set_material(i, grey)
        self.log("target slots:", ", ".join(str(n) for n in c.get_material_slot_names()))
        t.attach_to_actor(a, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)
        a.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -200, 100))
        cam.set_actor_label("T_Camera")
        cc = cam.capture_component2d
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("always_persist_rendering_state", True)
        cc.set_editor_property("fov_angle", 50.0)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            cc.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            cc.set_editor_property("post_process_blend_weight", 1.0)

    def collect(self):
        self.world = unreal.EditorLevelLibrary.get_game_world()
        by = {x.get_actor_label(): x for x in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)}
        self.body = by["T_Body"].skeletal_mesh_component
        self.target = by["T_Target"].skeletal_mesh_component
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        inst = self.target.get_anim_instance()
        inst.set_leader(self.body)
        self.log("anim instance:", inst.get_class().get_name(), "leader:", inst.get_leader().get_name())

    def chain_rel(self):
        rel = {}
        for side in "lr":
            rel[side] = []
            for i in range(1, 8):
                a = self.target.get_socket_transform(f"belt_{side}_{i:02d}")
                b = self.target.get_socket_transform(f"belt_{side}_{i + 1:02d}")
                rel[side].append(unreal.MathLibrary.compose_transforms(b, a.inverse()))
        return rel

    def deviation(self):
        cur = self.chain_rel()
        out = {}
        for side in "lr":
            out[side] = [math.degrees(2 * math.acos(min(1.0, abs(unreal.MathLibrary.compose_transforms(c, r.inverse()).rotation.w))))
                         for c, r in zip(cur[side], self.rest_rel[side])]
        return out

    def look(self, view):
        pel = self.body.get_socket_location("pelvis")
        offsets = {"front": unreal.Vector(0, -170, 5), "side": unreal.Vector(170, 0, 5), "full": unreal.Vector(0, -330, 0)}
        loc = pel + offsets[view]
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, pel), False, False)
        self.cam.capture_component2d.capture_scene()

    def step(self):
        now = time.time()
        if now < self.until or getattr(self, "busy", False):
            return
        self.busy = True  # level loads and imports pump Slate, which would call this tick again
        try:
            self.advance(now)
        finally:
            self.busy = False

    def advance(self, now):
        if self.state == "load":
            # import and physics asset first, in their own tick: importing during a level load asserts
            self.mesh = prepare_assets(self.log)
            self.state, self.until = "level", now + 2.0
        elif self.state == "level":
            levels.load_level(LEVEL)
            self.build()
            self.state, self.until = "start_sim", now + LOAD_SETTLE_S
        elif self.state == "start_sim":
            self.log("starting simulate", TAG)
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "collect", now + SIM_START_S
        elif self.state == "collect":
            self.collect()
            self.state, self.until = "chain", now + 1.5
        elif self.state == "chain":
            if self.simulate:
                for root in ("belt_l_01", "belt_r_01"):
                    self.target.set_all_bodies_below_simulate_physics(root, True, True)
                self.log("chain bodies set to simulate")
            self.rest_rel = self.chain_rel()
            if self.metrics:
                self.window, self.window_start, self.metric_end = {"l": [0.0] * 7, "r": [0.0] * 7}, now, now + self.metrics
                self.state, self.until = "metrics", now
            else:
                self.state, self.until = "shoot", now + WARMUP_S
        elif self.state == "metrics":
            dev = self.deviation()
            for s in "lr":
                self.window[s] = [max(x, y) for x, y in zip(self.window[s], dev[s])]
            if now - self.window_start >= 0.5:
                fmt = lambda v: "[" + " ".join(f"{x:5.1f}" for x in v) + "]"
                self.log(f"t={self.body.get_position():6.2f}s max dev  L {fmt(self.window['l'])}  R {fmt(self.window['r'])}")
                self.window, self.window_start = {"l": [0.0] * 7, "r": [0.0] * 7}, now
            if now >= self.metric_end:
                return self.finish()
        elif self.state == "shoot":
            for view in ("front", "side", "full"):
                self.look(view)
                unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"{TAG}_{self.taken:02d}_{view}.png")
            tip = self.body.get_socket_transform("pelvis").inverse_transform_location(self.target.get_socket_location("belt_l_08"))
            self.log(f"shot {self.taken:02d} anim t={self.body.get_position():.2f}s belt_l_08 in pelvis space ({tip.x:.1f}, {tip.y:.1f}, {tip.z:.1f})")
            self.taken += 1
            if self.taken >= self.shots:
                return self.finish()
            self.until = now + self.gap


def arg(prefix, default):
    return next((float(a.split("=")[1]) for a in sys.argv[1:] if a.startswith(prefix)), default)


_test = Test(int(arg("shots=", 6)), arg("gap=", 1.5), arg("start=", 0.0), arg("metrics=", 0.0), "nosim" not in FLAGS, "quit" in FLAGS)
