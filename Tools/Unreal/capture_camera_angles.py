"""Capture the greybox match from several candidate camera angles at the same moments, to choose the combat camera.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_camera_angles.py quit"

Runs a Simulate session on the training dojang (the greybox auto-starts there), has Chung throw a few techniques
(`os.Throw <Row>`), and at the stance and at each strike shoots every camera in ANGLES at once, each placed from the
fighters' positions (side-on, three-quarter corner, several behind-the-fighter views including the game's own, and a
high judge's view). Images: Saved/Screenshots/CameraAngles/<Angle>/<Moment>.png;
log Saved/Logs/camera_angles.txt.
"""
import os
import sys
import time
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT = f"{REPO}/Saved/Screenshots/CameraAngles"
LOG = f"{REPO}/Saved/Logs/camera_angles.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
ROWS = ["Roundhouse_Trunk", "Hook_Head", "Axe_Head", "SpinHook_Head", "Tornado_Trunk"]
STRIKE_S = 0.30
W, H = 1280, 720
# The same angles as Source/OpenStance/Private/Combat/OpenStanceCameraPresets.cpp (keep the two in step); "Game" copies
# the game's own camera, which uses the Match preset unless os.CameraPreset chose another.
# Side and corner angles: (along the fighters' line from the midpoint, out to the side, height, look height, fov).
# Behind angles follow Chung: ("behind", back from Chung, to his right, height, look height, fov).
ANGLES = {
    "0_Game": "follow",
    "1_Match": ("behind", 360, 170, 200, 75, 55),
    "2_SideBroadcast": (0, 520, 135, 100, 40),
    "3_SideHigh": (0, 560, 260, 85, 40),
    "4_ThreeQuarterCorner": (-330, 420, 240, 95, 42),
    "5_BehindShoulder": ("behind", 320, 60, 200, 105, 90),
    "6_BehindClose": ("behind", 230, 70, 175, 115, 55),
    "7_BehindLow": ("behind", 300, 60, 140, 110, 50),
    "8_BehindHighWide": ("behind", 380, 40, 320, 80, 50),
    "9_HighJudge": (0, 420, 380, 60, 50),
}
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Angles:
    def __init__(self):
        self.f = open(LOG, "w", encoding="utf-8")
        self.state, self.until, self.row, self.busy = "load", 0.0, 0, False
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

    def spawn_cameras(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        pps = [p.get_editor_property("settings") for p in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume)]
        for name in ANGLES:
            rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
            cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200))
            cam.set_actor_label(f"CA_{name}")
            cc = cam.capture_component2d
            cc.set_editor_property("texture_target", rt)
            cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            cc.set_editor_property("capture_every_frame", False)
            cc.set_editor_property("always_persist_rendering_state", True)
            if pps:
                cc.set_editor_property("post_process_settings", pps[0])
                cc.set_editor_property("post_process_blend_weight", 1.0)

    def capture(self, moment):
        world = unreal.EditorLevelLibrary.get_game_world()
        bodies = [c for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                  for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "FighterBody"]
        follow = next((x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)), None)
        if len(bodies) < 2 or follow is None:
            self.log(f"{moment}: fighters {len(bodies)} follow camera {follow}")
            return
        fl = follow.get_actor_location()
        a, b = (body.get_socket_location("pelvis") for body in bodies[:2])
        chung, hong = (a, b) if (a - fl).length() < (b - fl).length() else (b, a)    # the camera follows Chung
        mid = (chung + hong) * 0.5
        line = hong - chung
        line.z = 0
        line = line.normal()
        side = unreal.Vector(-line.y, line.x, 0)
        if (fl - mid).dot(side) < 0:          # stay on the follow camera's side of the line
            side = side * -1.0
        for name, spec in ANGLES.items():
            cam = next(x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)
                       if x.get_actor_label() == f"CA_{name}")
            cc = cam.capture_component2d
            if spec == "follow":
                loc, rot, fov = fl, follow.get_actor_rotation(), follow.camera_component.field_of_view
            elif spec[0] == "behind":
                _, back, right, height, look_h, fov = spec
                loc = chung - line * back + side * right
                loc.z = height
                rot = unreal.MathLibrary.find_look_at_rotation(loc, unreal.Vector(mid.x, mid.y, look_h))
            else:
                along, out, height, look_h, fov = spec
                loc = mid + line * along + side * out
                loc.z = height
                rot = unreal.MathLibrary.find_look_at_rotation(loc, unreal.Vector(mid.x, mid.y, look_h))
            cam.set_actor_location_and_rotation(loc, rot, False, False)
            cc.set_editor_property("fov_angle", fov)
            cc.capture_scene()
            folder = f"{OUT}/{name}"
            os.makedirs(folder, exist_ok=True)
            unreal.RenderingLibrary.export_render_target(world, cc.get_editor_property("texture_target"), folder, f"{moment}.png")
        self.log(f"shot {moment}")

    def step(self):
        now = time.time()
        if now < self.until:
            return
        if self.state == "load":
            levels.load_level(LEVEL)
            self.spawn_cameras()
            self.state, self.until = "play", time.time() + 30
        elif self.state == "play":
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "warm", now + 12
        elif self.state == "warm":
            self.capture("0_Stance")
            self.capture("0_Stance")          # the first capture after load can miss streamed textures
            self.state = "throw"
        elif self.state == "throw":
            if self.row >= len(ROWS):
                return self.finish()
            world = unreal.EditorLevelLibrary.get_game_world()
            unreal.SystemLibrary.execute_console_command(world, f"os.Throw {ROWS[self.row]}")
            self.t0, self.state = now, "shoot"
        elif self.state == "shoot":
            if now - self.t0 >= STRIKE_S:
                self.capture(f"{self.row + 1}_{ROWS[self.row]}")
                self.row += 1
                self.state, self.until = "throw", now + 2.0


_angles = Angles()
