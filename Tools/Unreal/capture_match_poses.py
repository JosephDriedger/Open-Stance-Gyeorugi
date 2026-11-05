"""Photograph the match fighters through every placeholder clip, one fighter of each body type and sex, in engine.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_match_poses.py quit"

Spawns the first eight roster fighters' match builds (every body type, both sexes; Chung and Hong alternate) on one
spot of the training dojang, runs a Simulate-in-Editor session (offscreen editors never tick actors otherwise), and for
every pose (the stance, each technique's chamber and strike) shows one fighter at a time and captures it from the
front, both sides and the back. Options: `keys=A+B` picks fighters, `clips=Stance+Axe` (ExecCmds splits on commas) picks clips. Nothing is saved.

Images: Saved/Screenshots/MatchPoses/<Key>_<Side>/<Clip>_<pct>_<view>.png. Log: Saved/Logs/capture_match_poses.txt.
"""
import json
import os
import sys
import time
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT = f"{REPO}/Saved/Screenshots/MatchPoses"
LOG = f"{REPO}/Saved/Logs/capture_match_poses.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
MATCH = "/Game/Characters/Fighters/Match"
CLIPS = "/Game/Animation/Moves/Placeholder"
# Clip and the fractions of it to show: the stance once, every technique at the chamber and the strike.
POSES = [("Stance", [0.5]), ("SideKick", [0.3, 0.5]), ("Roundhouse", [0.3, 0.5]), ("Hook", [0.3, 0.55]),
         ("Axe", [0.3, 0.5]), ("Punch", [0.45]), ("SpinSide", [0.35, 0.55]), ("SpinHook", [0.35, 0.55]),
         ("Tornado", [0.35, 0.55])]
VIEWS = [("front", 0.0), ("left", 90.0), ("back", 180.0), ("right", 270.0)]
SPOT = unreal.Vector(0.0, 330.0, 0.0)
DIST, HEIGHT, FOV = 330.0, 105.0, 42.0
W, H = 600, 800
LOAD_SETTLE_S, SIM_START_S, POSE_S, SHOT_S = 60.0, 20.0, 2.5, 0.6

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary


def arg(name, default):
    for a in sys.argv[1:]:
        if a.startswith(name + "="):
            return a.split("=", 1)[1].split("+")
    return default


class Capture:
    def __init__(self):
        self.f = open(LOG, "w", encoding="utf-8")
        roster = [f["key"] for f in json.load(open(f"{REPO}/Tools/Blender/portrait_roster.json"))["fighters"]]
        keys = arg("keys", roster[:8])
        self.fighters = [f"{k}_{'Chung' if i % 2 == 0 else 'Hong'}" if "_" not in k else k for i, k in enumerate(keys)]
        clips = arg("clips", None)
        self.poses = [(c, p) for c, ps in POSES if clips is None or c in clips for p in ps]
        self.jobs = []
        self.state, self.until, self.busy = "load", 0.0, False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()

    def tick(self, dt):
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
        self.log("DONE")
        self.f.close()
        if "quit" in sys.argv[1:]:
            unreal.SystemLibrary.quit_editor()

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        self.anims = {c: EAL.load_asset(f"{CLIPS}/AS_Placeholder_{c}") for c, _ in POSES}
        self.log("clips " + " ".join(f"{c}={a is not None}" for c, a in self.anims.items()))
        stance = self.anims["Stance"]
        for name in self.fighters:
            mesh = EAL.load_asset(f"{MATCH}/{name}/SK_Match_{name}")
            if not mesh:
                self.log(f"missing {name}")
                continue
            a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, SPOT)
            a.set_actor_label(f"MP_{name}")
            c = a.skeletal_mesh_component
            c.set_skinned_asset_and_update(mesh)
            ad = unreal.SingleAnimationPlayData()
            ad.set_editor_property("anim_to_play", stance)
            ad.set_editor_property("saved_looping", False)
            ad.set_editor_property("saved_playing", False)
            c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            c.set_editor_property("animation_data", ad)
            c.set_editor_property("visibility_based_anim_tick_option",
                                  unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200), unreal.Rotator(0, 0, 0))
        cam.set_actor_label("MP_Camera")
        c = cam.capture_component2d
        c.set_editor_property("texture_target", rt)
        c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        c.set_editor_property("fov_angle", FOV)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            c.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            c.set_editor_property("post_process_blend_weight", 1.0)

    def collect(self):
        self.world = unreal.EditorLevelLibrary.get_game_world()
        self.by_name = {a.get_actor_label()[3:]: a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)
                        if a.get_actor_label().startswith("MP_")}
        self.cam = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)
                        if a.get_actor_label() == "MP_Camera")
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        self.log(f"simulate world: {len(self.by_name)} fighters, {len(self.poses)} poses")


    def set_pose(self, clip, frac):
        anim = self.anims[clip]
        t = anim.get_play_length() * frac
        for a in self.by_name.values():
            c = a.skeletal_mesh_component
            c.play_animation(anim, False)
            c.set_play_rate(0.0)
            c.set_position(t, False)
        self.jobs = [(n, v, yaw) for n in self.by_name for v, yaw in VIEWS]
        self.shown = None

    def aim(self, name, view, yaw):
        if self.shown != name:
            for n, a in self.by_name.items():
                a.set_actor_hidden_in_game(n != name)
            self.shown = name
        body = self.by_name[name].skeletal_mesh_component
        look = body.get_socket_location("pelvis")
        look.z = HEIGHT
        rad = unreal.MathLibrary.degrees_to_radians(yaw + 90.0)
        loc = look + unreal.Vector(unreal.MathLibrary.cos(rad) * DIST, unreal.MathLibrary.sin(rad) * DIST, 15.0)
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, False)

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
            self.next_pose(now)
        elif self.state == "shoot":
            if self.job is not None:
                name, view, _ = self.job
                clip, frac = self.pose
                folder = f"{OUT}/{name}"
                os.makedirs(folder, exist_ok=True)
                unreal.RenderingLibrary.export_render_target(self.world, self.rt, folder, f"{clip}_{int(frac * 100):02d}_{view}.png")
            if not self.jobs:
                return self.next_pose(now)
            self.job = self.jobs.pop(0)
            self.aim(*self.job)
            self.until = now + SHOT_S

    def next_pose(self, now):
        if not self.poses:
            return self.finish()
        self.pose = self.poses.pop(0)
        self.set_pose(*self.pose)
        self.log(f"pose {self.pose[0]} {self.pose[1]}")
        self.job = None
        self.state, self.until = "shoot", now + POSE_S


_capture = Capture()
