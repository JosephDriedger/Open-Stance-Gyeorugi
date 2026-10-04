"""Render the five fighter body types in a row, with and without sparring gear, to PNG for review.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/capture_fighters.py quit"

No editor window. Loads the training dojang read-only for its lighting (nothing is saved), stands the
fighters on the mat (A-pose, leader-pose gear exactly as the game assembles it) and photographs them with a
SceneCapture2D on editor ticks so shaders and meshes finish compiling. Skin is a flat tone and the heads are
bare: hair, eyes and MetaHuman skin come from MetaHuman Creator, so this checks the dobok and gear, not the face.

Images: Saved/Screenshots/Fighters/<shot>.png
  gear_*      helmet, protector, gloves, foot guards, dobok (Chung blue; the *_hong shot is red)
  dobok_*     jacket, pants and belt only (menus and Career)
  <view>: front, three-quarter, back; close_* are per-body head-and-shoulders and hands views
"""
import math
import os
import sys
import time
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/Fighters"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/capture_fighters.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
TYPES = [("Compact", 165), ("Medium", 175), ("Stocky", 172), ("LeanTall", 185), ("Tall", 192)]
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
GEAR_ONLY = {"Protector", "Helmet", "Gloves", "FootGuards"}
GEAR = "/Game/Characters/Fighters/Gear"
SPACING = 130.0                       # cm between fighters (along X; they face -Y)
ROW_Y = 250.0                         # the row stands this far +Y of the mat centre so the camera stays inside the room
FLOOR_Z = 0.0
SKIN = unreal.LinearColor(0.52, 0.34, 0.26, 1.0)
W, H = 2560, 1440
SETTLE_S, FIRST_SETTLE_S, VIEW_S = 20.0, 120.0, 3.0

# name: (gear on, hong, fighters' turn deg (0 = facing the camera, 180 = back), camera distance cm, camera height cm, look height cm, fov, type index or None for all)
SHOTS = {
    "gear_front": (True, False, 0, 720, 110, 95, 52, None),
    "gear_three_quarter": (True, False, 35, 720, 110, 95, 52, None),
    "gear_back": (True, False, 180, 720, 110, 95, 52, None),
    "gear_front_hong": (True, True, 0, 720, 110, 95, 52, None),
    "dobok_front": (False, False, 0, 720, 110, 95, 52, None),
    "dobok_three_quarter": (False, False, 35, 720, 110, 95, 52, None),
    "dobok_back": (False, False, 180, 720, 110, 95, 52, None),
}
for i, (t, h) in enumerate(TYPES):
    SHOTS[f"close_gear_{t}"] = (True, False, 25, 190, h * 0.80, h * 0.80, 40, i)
    SHOTS[f"close_dobok_{t}"] = (False, False, 25, 190, h * 0.80, h * 0.80, 40, i)
    SHOTS[f"hands_gear_{t}"] = (True, False, 30, 110, h * 0.58, h * 0.58, 38, i)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Capture:
    def __init__(self, quit_after, only):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.quit_after = quit_after
        self.todo = [k for k in SHOTS if not only or any(k.startswith(o) for o in only)]
        self.state, self.until, self.cam, self.rt = "load", 0.0, None, None
        self.fighters = []          # (type index, body comp, {part: comp}, head comp)
        self.shot = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[capture_fighters] {msg}")

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
        if self.quit_after:
            unreal.SystemLibrary.quit_editor()

    def asset(self, path):
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a is None:
            raise RuntimeError(f"missing asset {path}")
        return a

    def spawn_fighters(self):
        skin_base = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/BasicShapeMaterial")
        world = unreal.EditorLevelLibrary.get_editor_world()
        lib = getattr(unreal, "MaterialLibrary", None) or getattr(unreal, "KismetMaterialLibrary", None)
        if lib is None:
            raise RuntimeError("no material library; unreal has: " + ", ".join(n for n in dir(unreal) if "MaterialLib" in n))
        skin = lib.create_dynamic_material_instance(world, skin_base)
        skin.set_vector_parameter_value("Color", SKIN)
        self.skin = skin
        self.chung = self.asset(f"{GEAR}/Clean/MI_FighterGear_Chung")
        self.hong = self.asset(f"{GEAR}/Clean/MI_FighterGear_Hong")
        n = len(TYPES)
        for i, (t, _) in enumerate(TYPES):
            x = (i - (n - 1) / 2) * SPACING
            name = "MH_FighterBase" if t == "Medium" else f"MH_Fighter{t}"
            body = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, ROW_Y, FLOOR_Z))
            body.set_actor_label(f"Cap_{t}_Body")
            leader = body.skeletal_mesh_component
            leader.set_skinned_asset_and_update(self.asset(f"/Game/Characters/Fighters/Export/{name}_Body"))
            for s in range(leader.get_num_materials()):
                leader.set_material(s, skin)
            head = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, ROW_Y, FLOOR_Z))
            head.set_actor_label(f"Cap_{t}_Head")
            head.skeletal_mesh_component.set_skinned_asset_and_update(self.asset(f"/Game/Characters/Fighters/Export/{name}_Head"))
            for s in range(head.skeletal_mesh_component.get_num_materials()):
                head.skeletal_mesh_component.set_material(s, skin)
            comps = {}
            gdir = f"{GEAR}/{t}"
            for part in PARTS:
                a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, ROW_Y, FLOOR_Z))
                a.set_actor_label(f"Cap_{t}_{part}")
                a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                  unreal.AttachmentRule.KEEP_WORLD, False)
                c = a.skeletal_mesh_component
                c.set_skinned_asset_and_update(self.asset(f"{gdir}/SK_Fighter_{part}"))
                c.set_leader_pose_component(leader)
                comps[part] = c
            self.fighters.append((i, leader, comps, head.skeletal_mesh_component, body, head))
        self.log(f"spawned {n} fighters")

    def configure(self, name):
        gear, hong, az_deg, dist, cam_z, look_z, fov, only = SHOTS[name]
        for i, leader, comps, head, body_actor, head_actor in self.fighters:
            body_actor.set_actor_rotation(unreal.Rotator(0, 0, az_deg + 180.0), False)   # attached gear follows
            head_actor.set_actor_rotation(unreal.Rotator(0, 0, az_deg + 180.0), False)
            show = only is None or i == only
            leader.set_visibility(show)
            head.set_visibility(show)
            for part, c in comps.items():
                on = show and (gear or part not in GEAR_ONLY)
                c.set_visibility(on)
                c.set_material(0, self.hong if hong else self.chung)
        # The camera stays in front of the row (inside the room); the fighters turn instead (they face +Y at yaw 0, so +180 faces the camera).
        centre = unreal.Vector(0, ROW_Y, 0)
        if only is not None:
            centre = unreal.Vector((only - (len(TYPES) - 1) / 2) * SPACING, ROW_Y, 0)
        loc = unreal.Vector(centre.x, centre.y - dist, cam_z)
        look = unreal.Vector(centre.x, centre.y, look_z)
        rot = unreal.MathLibrary.find_look_at_rotation(loc, look)
        self.cam.set_actor_location_and_rotation(loc, rot, False, False)
        self.cam.capture_component2d.set_editor_property("fov_angle", float(fov))

    def spawn_camera(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        self.rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200), unreal.Rotator(0, 0, 0))
        c = self.cam.capture_component2d
        c.set_editor_property("texture_target", self.rt)
        c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            c.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            c.set_editor_property("post_process_blend_weight", 1.0)

    def step(self):
        now = time.time()
        if self.state in ("settle", "expose"):
            self.cam.capture_component2d.capture_scene()
        if now < self.until:
            return
        if self.state == "load":
            levels.load_level(LEVEL)
            self.spawn_camera()
            self.spawn_fighters()
            self.configure(self.todo[0])
            self.until = now + FIRST_SETTLE_S
            self.state = "settle"
        elif self.state in ("settle", "expose"):
            name = self.todo.pop(0)
            world = unreal.EditorLevelLibrary.get_editor_world()
            unreal.RenderingLibrary.export_render_target(world, self.rt, OUT, f"{name}.png")
            self.log(f"shot {name}")
            if not self.todo:
                return self.finish()
            self.configure(self.todo[0])
            self.until = now + VIEW_S
            self.state = "expose"


args = sys.argv[1:]
_capture = Capture("quit" in args, [a for a in args if a != "quit"])
