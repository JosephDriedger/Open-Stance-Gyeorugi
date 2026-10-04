"""Play the MetaHuman body range-of-motion animation on every fighter body type and referee, in engine, and
photograph key poses, so deformation of the gear can be judged on the real rig and the real skinning.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/animation_test.py [group ...] [poses=N] quit"

Groups: gear (fighters with full sparring gear), dobok (jacket, pants, belt only), referees.
No editor window. An offscreen editor never ticks actors, so the animation would never advance in the editor
world; this runs a Simulate-in-Editor session instead (the engine then ticks animation and cloth normally), with
the animation set through the component's persistent animation data so it survives into that session. The training
dojang is loaded read-only for lighting and nothing is saved. Every gear piece follows the body with Leader Pose,
exactly as the game assembles it, and the heads follow the body skeleton too.

Images: Saved/Screenshots/AnimTest/<group>_<NN>.png (NN = pose index) and a log with the pose times.
"""
import math
import os
import sys
import time
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/AnimTest"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/animation_test.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
GEAR = "/Game/Characters/Fighters/Gear"
OFFICIALS = "/Game/Characters/Officials"
FIGHTERS = ["Compact", "Medium", "Stocky", "LeanTall", "Tall"]
REFEREES = ["Bo", "Jorge", "Kelvin", "Omari", "Vivian", "Walter"]
FIGHTER_PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
GEAR_ONLY = {"Protector", "Helmet", "Gloves", "FootGuards"}
REF_PARTS = ["Shirt", "Trousers", "Belt", "Tie", "Shoes"]
SPACING, ROW_Y = 170.0, 330.0
POSES = 16
W, H = 2560, 1440
SKIN = unreal.LinearColor(0.52, 0.34, 0.26, 1.0)
LOAD_SETTLE_S, SIM_START_S, GROUP_S, POSE_S = 100.0, 25.0, 6.0, 4.0

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Test:
    def __init__(self, groups, quit_after):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.groups = groups or ["gear", "dobok", "referees"]
        self.quit_after = quit_after
        self.state, self.until = "load", 0.0
        self.queue = []
        self.world = None
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[animation_test] {msg}")

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

    def asset(self, path):
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a is None:
            raise RuntimeError(f"missing asset {path}")
        return a

    # --- setup in the editor world ---------------------------------------------------------------------
    def spawn(self, label, loc, mesh_path):
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, loc)
        a.set_actor_label(label)
        c = a.skeletal_mesh_component
        c.set_skinned_asset_and_update(self.asset(mesh_path))
        return a, c

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        lib = getattr(unreal, "MaterialLibrary", None) or getattr(unreal, "KismetMaterialLibrary", None)
        skin = lib.create_dynamic_material_instance(world, self.asset("/Engine/BasicShapes/BasicShapeMaterial"))
        skin.set_vector_parameter_value("Color", SKIN)
        self.anim = self.asset(ANIM)
        self.length = self.anim.get_play_length()
        self.log(f"animation {ANIM} length {self.length:.2f}s")

        def skin_all(c):
            for s in range(c.get_num_materials()):
                c.set_material(s, skin)

        def animate(c):
            """Persistent single-node animation data: it is what survives into the simulate session."""
            ad = unreal.SingleAnimationPlayData()
            ad.set_editor_property("anim_to_play", self.anim)
            ad.set_editor_property("saved_looping", True)
            ad.set_editor_property("saved_playing", True)
            ad.set_editor_property("saved_play_rate", 1.0)
            c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            c.set_editor_property("animation_data", ad)
            c.set_editor_property("visibility_based_anim_tick_option",
                                  unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)

        def attach(a, body):
            a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)

        for i, t in enumerate(FIGHTERS):
            loc = unreal.Vector((i - (len(FIGHTERS) - 1) / 2) * SPACING, ROW_Y, 0)
            name = "MH_FighterBase" if t == "Medium" else f"MH_Fighter{t}"
            body, leader = self.spawn(f"T_{t}_Body", loc, f"/Game/Characters/Fighters/Export/{name}_Body")
            skin_all(leader)
            animate(leader)
            head, hc = self.spawn(f"T_{t}_Head", loc, f"/Game/Characters/Fighters/Export/{name}_Head")
            skin_all(hc)
            hc.set_leader_pose_component(leader)
            for p in FIGHTER_PARTS:
                a, c = self.spawn(f"T_{t}_{p}", loc, f"{GEAR}/{t}/SK_Fighter_{p}")
                attach(a, body)
                c.set_leader_pose_component(leader)
            body.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
            head.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
        for i, r in enumerate(REFEREES):
            loc = unreal.Vector((i - (len(REFEREES) - 1) / 2) * SPACING, ROW_Y, 0)
            body, leader = self.spawn(f"R_{r}_Body", loc, f"{OFFICIALS}/Export/MH_Referee_{r}_Body")
            animate(leader)
            head, hc = self.spawn(f"R_{r}_Head", loc, f"{OFFICIALS}/Export/MH_Referee_{r}_Head")
            hc.set_leader_pose_component(leader)
            for p in REF_PARTS:
                path = f"{OFFICIALS}/Outfits/{r}/SK_Referee_{p}"
                if not unreal.EditorAssetLibrary.does_asset_exist(path):
                    continue
                a, c = self.spawn(f"R_{r}_{p}", loc, path)
                attach(a, body)
                c.set_leader_pose_component(leader)
            body.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
            head.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)

        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 200), unreal.Rotator(0, 0, 0))
        cam.set_actor_label("T_Camera")
        c = cam.capture_component2d
        c.set_editor_property("texture_target", rt)
        c.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        for ppv in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PostProcessVolume):
            c.set_editor_property("post_process_settings", ppv.get_editor_property("settings"))
            c.set_editor_property("post_process_blend_weight", 1.0)

    # --- the simulate session ---------------------------------------------------------------------------
    def collect(self):
        """Index the simulate world's copies of the actors by label."""
        self.world = unreal.EditorLevelLibrary.get_game_world()
        by_label = {}
        for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor):
            by_label[a.get_actor_label()] = a
        self.by_label = by_label
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        self.log(f"simulate world: {len(by_label)} skeletal actors")

    def comp(self, label):
        return self.by_label[label].skeletal_mesh_component

    def show(self, group):
        for t in FIGHTERS:
            on = group in ("gear", "dobok")
            self.comp(f"T_{t}_Body").set_visibility(on)
            self.comp(f"T_{t}_Head").set_visibility(on)
            for p in FIGHTER_PARTS:
                self.comp(f"T_{t}_{p}").set_visibility(on and (group == "gear" or p not in GEAR_ONLY))
        for r in REFEREES:
            on = group == "referees"
            self.comp(f"R_{r}_Body").set_visibility(on)
            self.comp(f"R_{r}_Head").set_visibility(on)
            for p in REF_PARTS:
                lab = f"R_{r}_{p}"
                if lab in self.by_label:
                    self.comp(lab).set_visibility(on)

    def pose(self, group, t):
        labels = [f"T_{x}_Body" for x in FIGHTERS] if group in ("gear", "dobok") else [f"R_{x}_Body" for x in REFEREES]
        for lab in labels:
            c = self.comp(lab)
            c.set_play_rate(0.0)
            c.set_position(t, False)

    def set_camera(self, group):
        n = len(FIGHTERS) if group in ("gear", "dobok") else len(REFEREES)
        width = (n - 1) * SPACING + 260
        dist = 760.0
        loc = unreal.Vector(0, ROW_Y - dist, 105)
        look = unreal.Vector(0, ROW_Y, 95)
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, False)
        self.cam.capture_component2d.set_editor_property("fov_angle", float(math.degrees(2 * math.atan(width / 2 / dist))))

    def next_job(self):
        group, idx, t = self.queue[0]
        self.show(group)
        self.set_camera(group)
        self.pose(group, t)

    def step(self):
        now = time.time()
        if self.state == "pose" and self.world is not None:
            self.cam.capture_component2d.capture_scene()
        if now < self.until:
            return
        if self.state == "load":
            levels.load_level(LEVEL)
            self.build()
            self.state, self.until = "start_sim", now + LOAD_SETTLE_S
        elif self.state == "start_sim":
            self.log("starting simulate")
            unreal.EditorLevelLibrary.editor_play_simulate()
            self.state, self.until = "collect", now + SIM_START_S
        elif self.state == "collect":
            self.collect()
            times = [self.length * (k + 0.5) / POSES for k in range(POSES)]
            for g in self.groups:
                for k, t in enumerate(times):
                    self.queue.append((g, k, t))
            self.log("pose times: " + ", ".join(f"{t:.2f}" for t in times))
            self.next_job()
            self.state, self.until = "pose", now + GROUP_S
        elif self.state == "pose":
            group, idx, t = self.queue.pop(0)
            unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"{group}_{idx:02d}.png")
            self.log(f"shot {group}_{idx:02d} t={t:.2f}")
            if not self.queue:
                return self.finish()
            changed = self.queue[0][0] != group
            self.next_job()
            self.until = now + (GROUP_S if changed else POSE_S)


args = sys.argv[1:]
for a in args:
    if a.startswith("poses="):
        POSES = int(a.split("=")[1])
_test = Test([a for a in args if a != "quit" and not a.startswith("poses=")], "quit" in args)
