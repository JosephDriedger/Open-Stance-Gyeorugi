"""Render venue levels from fixed cameras to PNG for review, with no editor window.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_levels.py [L_SchoolGym ...] quit"

Images go to Saved/Screenshots/Venues/<Level>_<view>.png. Runs on editor ticks so shaders, meshes and textures
finish compiling and streaming; each view is captured repeatedly by a SceneCapture2D (rendering state persists,
so auto exposure adapts) before it is exported. `quit` closes the editor when done.
"""
import os
import sys
import time

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/Venues"
# (location m, (pitch, yaw) degrees): "play" ~ side-on combat camera height, "wide" shows the venue
VIEWS = {
    "L_ClubDojang": {"play": ((0.0, -7.6, 1.8), (-6, 90)), "wide": ((-8.6, -7.4, 3.6), (-14, 48))},
    "L_SchoolGym": {"play": ((0.0, -9.5, 2.6), (-8, 90)), "wide": ((-16.5, -15.0, 6.5), (-18, 42))},
    "L_ProvincialHall": {"play": ((0.0, -10.5, 3.0), (-9, 90)), "wide": ((-30.0, -20.0, 11.0), (-18, 35))},
    "L_NationalArena": {"play": ((0.0, -13.0, 3.4), (-8, 90)), "wide": ((-24.0, -27.0, 14.0), (-20, 45))},
    "L_ContinentalArena": {"play": ((0.0, -14.0, 3.4), (-8, 90)), "wide": ((-28.0, -31.0, 16.0), (-20, 45))},
    "L_WorldFinalStage": {"play": ((0.0, -14.0, 3.6), (-9, 90)), "wide": ((-30.0, -28.0, 15.0), (-18, 40))},
    "L_CompetitionArena": {"play": ((0.0, -13.0, 3.4), (-8, 90)), "wide": ((-22.0, -26.0, 13.0), (-20, 45))},
    "L_TrainingDojang": {"play": ((0.0, -6.6, 1.7), (-4, 90)), "wide": ((7.6, -6.4, 3.4), (-16, 135))},
}
W, H = 1600, 900
SETTLE_S, FIRST_SETTLE_S, VIEW_S = 25.0, 120.0, 4.0   # wall-clock waits: compile after load, exposure per view

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Capture:
    def __init__(self, names, quit_after):
        os.makedirs(OUT, exist_ok=True)
        self.log_file = open("D:/Open-Stance-Gyeorugi/Saved/Logs/capture_levels.txt", "w", encoding="utf-8")
        self.levels = list(names)
        self.quit_after = quit_after
        self.views, self.cam, self.rt = [], None, None
        self.until, self.state, self.first = 0.0, "load", True
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.log_file.write(msg + "\n")
        self.log_file.flush()
        unreal.log(f"[capture_levels] {msg}")

    def tick(self, dt):
        try:
            self.step()
        except Exception:
            import traceback
            self.log("ERROR\n" + traceback.format_exc())
            self.finish()

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        self.log("DONE")
        self.log_file.close()
        if self.quit_after:
            unreal.SystemLibrary.quit_editor()

    def step(self):
        now = time.time()
        if self.state in ("settle", "expose"):
            if not unreal.SystemLibrary.is_valid(self.cam):   # a world reload can drop the actor: respawn it
                self.spawn_camera()
                self.place(self.views[0])
            self.cam.capture_component2d.capture_scene()
        if now < self.until:
            return
        if self.state == "load":
            if not self.levels:
                return self.finish()
            lvl = self.levels.pop(0)
            levels.load_level(f"/Game/Maps/{lvl}")
            self.spawn_camera()
            self.views = [(lvl, v, loc, rot) for v, (loc, rot) in VIEWS[lvl].items()]
            self.place(self.views[0])
            self.until = now + (FIRST_SETTLE_S if self.first else SETTLE_S)
            self.first = False
            self.state = "settle"
        elif self.state in ("settle", "expose"):
            lvl, view, _, _ = self.views.pop(0)
            world = unreal.EditorLevelLibrary.get_editor_world()
            unreal.RenderingLibrary.export_render_target(world, self.rt, OUT, f"{lvl}_{view}.png")
            self.log(f"shot {lvl}_{view}")
            if self.views:
                self.place(self.views[0])
                self.until = now + VIEW_S
                self.state = "expose"
            else:
                actors.destroy_actor(self.cam)
                self.cam = None
                self.state = "load"

    def spawn_camera(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        self.rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200), unreal.Rotator(0, 0, 0))
        c = self.cam.capture_component2d
        c.set_editor_property("texture_target", self.rt)
        c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("fov_angle", 60.0)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        # use the level's own post process (exposure, bloom) so captures match what the game shows
        world = unreal.EditorLevelLibrary.get_editor_world()
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            c.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            c.set_editor_property("post_process_blend_weight", 1.0)

    def place(self, item):
        _, _, loc, rot = item
        self.cam.set_actor_location_and_rotation(unreal.Vector(*(c * 100 for c in loc)), unreal.Rotator(0, rot[0], rot[1]), False, False)


args = sys.argv[1:]
names = [a for a in args if a in VIEWS] or [n for n in VIEWS if n not in ("L_CompetitionArena", "L_TrainingDojang")]
_capture = Capture(names, "quit" in args)
