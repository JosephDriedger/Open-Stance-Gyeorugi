"""Photograph the hand poses and facial expressions from create_pose_library.py on the Medium fighter, in engine.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_pose_library.py quit"

Runs a Simulate-in-Editor session in the training dojang (offscreen editors never tick actors otherwise). Each hand
pose plays on its own copy of the Medium body. Each expression plays on its own copy of the Medium head; the head
used here is an unsaved duplicate with MetaHuman's face post-process AnimBP (the RigLogic face solver) assigned, so
the ctrl_expressions curves move the face exactly as they will on an assembled MetaHuman. Nothing is saved.

Images: Saved/Screenshots/PoseLibrary/<name>.png. Log: Saved/Logs/capture_pose_library.txt.
"""
import os
import sys
import time
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/PoseLibrary"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/capture_pose_library.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
EXPORT = "/Game/Characters/Fighters/Export"
HANDS = "/Game/Characters/Fighters/Animation/Hands"
FACE = "/Game/Characters/Fighters/Animation/Face"
FACE_PP = "/MetaHumanCharacter/Face/ABP_Face_PostProcess.ABP_Face_PostProcess_C"
TEST_HEAD = "/Game/Developers/PoseLibraryTest/MH_FighterBase_Head_FaceSolver"
HAND_POSES = ["Guard", "Punch", "Relaxed", "Open"]
EXPRESSIONS = [("Neutral", 0.5), ("Focus", 0.5), ("Kiai", 0.5), ("Wince", 0.5), ("Celebrate", 0.5), ("Blink", 0.085)]
ROW_Y, HAND_X0, HAND_DX, FACE_X0, FACE_DX = 330.0, -300.0, 200.0, 600.0, 70.0
W, H = 1600, 1000
LOAD_SETTLE_S, SIM_START_S, SHOT_S = 100.0, 25.0, 4.0

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary


class Capture:
    def __init__(self, quit_after):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.quit_after = quit_after
        self.state, self.until = "load", 0.0
        self.jobs = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()

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

    def spawn(self, label, loc, mesh, anim):
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, loc)
        a.set_actor_label(label)
        a.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
        c = a.skeletal_mesh_component
        c.set_skinned_asset_and_update(mesh)
        c.set_forced_lod(1)
        ad = unreal.SingleAnimationPlayData()
        ad.set_editor_property("anim_to_play", anim)
        ad.set_editor_property("saved_looping", True)
        ad.set_editor_property("saved_playing", True)
        ad.set_editor_property("saved_play_rate", 1.0)
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_editor_property("animation_data", ad)
        c.set_editor_property("visibility_based_anim_tick_option",
                              unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        return a

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        body = EAL.load_asset(f"{EXPORT}/MH_FighterBase_Body")
        if EAL.does_asset_exist(TEST_HEAD):
            EAL.delete_asset(TEST_HEAD)
        head = EAL.duplicate_asset(f"{EXPORT}/MH_FighterBase_Head", TEST_HEAD)
        pp = unreal.load_class(None, FACE_PP)
        head.set_editor_property("post_process_anim_blueprint", pp)
        self.log(f"test head {head.get_path_name()} post-process {pp}")
        for i, p in enumerate(HAND_POSES):
            x = HAND_X0 + i * HAND_DX
            self.spawn(f"H_{p}", unreal.Vector(x, ROW_Y, 0), body, EAL.load_asset(f"{HANDS}/AS_Hand_{p}_Both"))
            self.jobs.append((f"hands_{p}_front", unreal.Vector(x, ROW_Y - 150, 92), unreal.Vector(x, ROW_Y, 88), 42.0, f"H_{p}", 0.5))
            self.jobs.append((f"hands_{p}_right", unreal.Vector(x - 95, ROW_Y - 60, 105), unreal.Vector(x - 30, ROW_Y, 86), 30.0, f"H_{p}", 0.5))
        for i, (e, t) in enumerate(EXPRESSIONS):
            x = FACE_X0 + i * FACE_DX
            self.spawn(f"F_{e}", unreal.Vector(x, ROW_Y, 0), head, EAL.load_asset(f"{FACE}/AS_Face_{e}"))
            self.jobs.append((f"face_{e}", unreal.Vector(x, ROW_Y - 58, 162), unreal.Vector(x, ROW_Y, 160), 30.0, f"F_{e}", t))
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200), unreal.Rotator(0, 0, 0))
        c = cam.capture_component2d
        c.set_editor_property("texture_target", rt)
        c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            c.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            c.set_editor_property("post_process_blend_weight", 1.0)

    def collect(self):
        self.world = unreal.EditorLevelLibrary.get_game_world()
        self.by_label = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)}
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        self.log(f"simulate world: {len(self.by_label)} skeletal actors")

    def setup_job(self):
        name, loc, look, fov, label, t = self.jobs[0]
        c = self.by_label[label].skeletal_mesh_component
        c.set_play_rate(0.0)
        c.set_position(t, False)
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, False)
        self.cam.capture_component2d.set_editor_property("fov_angle", fov)

    def step(self):
        now = time.time()
        if self.state == "shoot":
            self.cam.capture_component2d.capture_scene()
        if now < self.until:
            return
        if self.state == "load":
            levels.load_level(LEVEL)
            self.build()
            self.state, self.until = "sim", now + LOAD_SETTLE_S
        elif self.state == "sim":
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "collect", now + SIM_START_S
        elif self.state == "collect":
            self.collect()
            self.setup_job()
            self.state, self.until = "shoot", now + SHOT_S
        elif self.state == "shoot":
            name = self.jobs.pop(0)[0]
            unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"{name}.png")
            self.log(f"shot {name}")
            if not self.jobs:
                return self.finish()
            self.setup_job()
            self.until = now + SHOT_S


_capture = Capture("quit" in sys.argv[1:])
