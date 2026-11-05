"""Capture the greybox character fighters throwing every Skill Stick technique (headless, Play-in-Editor).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_technique_demo.py quit"

Starts Play on the training dojang (the greybox auto-starts there), then for each technique row in DT_MoveData asks the
simulation to throw it with Chung (os.* debug command `os.Throw <Row>`) and saves side-on captures at the chamber, the
strike and the recovery (`follow`: from the player's follow camera, into Follow/). Images: Saved/Screenshots/TechniqueDemo/<Row>_<phase>.png; log Saved/Logs/technique_demo.txt.
"""
import os
import sys
import time
import traceback

import unreal

REPO = "D:/Open-Stance-Gyeorugi"
OUT = f"{REPO}/Saved/Screenshots/TechniqueDemo"
LOG = f"{REPO}/Saved/Logs/technique_demo.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
ROWS = ["SideKick_Trunk", "Roundhouse_Trunk", "Hook_Head", "Axe_Head", "Punch_Trunk", "SpinSide_Trunk", "SpinHook_Head",
        "Tornado_Trunk"]
W, H = 900, 700
FOLLOW = "follow" in sys.argv[1:]          # shoot from the player's follow camera instead of side-on
if FOLLOW:
    OUT += "/Follow"
    W, H = 1280, 720
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Demo:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.state, self.until, self.row, self.shot, self.busy = "load", 0.0, 0, 0, False
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
        unreal.SystemLibrary.quit_editor()

    def capture(self, name):
        world = unreal.EditorLevelLibrary.get_game_world()
        fighters = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                    if a.get_component_by_class(unreal.SkeletalMeshComponent) and a.get_actor_label() != "TD_Camera"]
        bodies = [c for a in fighters for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "FighterBody"]
        if len(bodies) < 2:
            self.log(f"{name}: character fighters not found ({len(bodies)})")
            return
        cam = next(x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D))
        cc = cam.capture_component2d
        follow = next((x for x in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)), None)
        if FOLLOW and follow:
            # the player's view: the greybox follow camera's pose and field of view
            cam.set_actor_location_and_rotation(follow.get_actor_location(), follow.get_actor_rotation(), False, False)
            cc.set_editor_property("fov_angle", follow.camera_component.field_of_view)
        else:
            a, b = bodies[0].get_socket_location("pelvis"), bodies[1].get_socket_location("pelvis")
            mid = (a + b) * 0.5
            line = b - a
            line.z = 0
            side = unreal.Vector(-line.y, line.x, 0).normal()
            loc = mid + side * 380 + unreal.Vector(0, 0, 20)
            cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, mid), False, False)
        cc.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, cc.get_editor_property("texture_target"), OUT, name + ".png")

    def spawn_camera(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -300, 150))
        cam.set_actor_label("TD_Camera")
        cc = cam.capture_component2d
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("capture_every_frame", False)
        cc.set_editor_property("always_persist_rendering_state", True)
        cc.set_editor_property("fov_angle", 50.0)

    def step(self):
        now = time.time()
        if now < self.until:
            return
        if self.state == "load":
            self.state = "loading"
            levels.load_level(LEVEL)
            self.spawn_camera()
            self.state, self.until = "play", time.time() + 30
        elif self.state == "play":
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "warm", now + 12
        elif self.state == "warm":
            self.capture("Stance")
            self.state = "throw"
        elif self.state == "throw":
            if self.row >= len(ROWS):
                return self.finish()
            row = ROWS[self.row]
            world = unreal.EditorLevelLibrary.get_game_world()
            unreal.SystemLibrary.execute_console_command(world, f"os.Throw {row}")
            self.t0, self.shot = now, 0
            self.state = "shoot"
            self.log(f"throw {row}")
        elif self.state == "shoot":
            delays = (0.12, 0.30, 0.55)
            if self.shot < len(delays) and now - self.t0 >= delays[self.shot]:
                self.capture(f"{ROWS[self.row]}_{self.shot}")
                self.shot += 1
            if self.shot >= len(delays):
                self.row += 1
                self.state, self.until = "throw", now + 2.0


_demo = Demo()
