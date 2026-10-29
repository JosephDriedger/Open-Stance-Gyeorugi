"""Watch the belt-tail bone chain simulate in engine (Simulate-in-Editor, no window).

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/belt_chain_test.py [Medium] [shots=N] [rate=0.5] quit"

Needs Tools/Unreal/setup_belt_chain.py to have run. Plays the study animation (a front kick) on
SK_BeltChain_<Kind> with the chain bodies below belt_l_01 / belt_r_01 simulating against the kinematic body
capsules, and photographs the hips from the front and the side at even intervals. Offscreen editors never tick
actors, so this runs a Simulate session like animation_test.py. Nothing is saved.

Images: Saved/Screenshots/BeltChain/<Kind>_<NN>_front.png / _side.png, log Saved/Logs/belt_chain_test.txt.
"""
import math
import os
import sys
import time
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/BeltChain"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/belt_chain_test.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
W, H = 960, 960
LOAD_SETTLE_S, SIM_START_S, WARMUP_S, SHOT_GAP_S = 100.0, 25.0, 3.0, 2.0
SKIN = unreal.LinearColor(0.78, 0.78, 0.76, 1.0)
BLACK = unreal.LinearColor(0.02, 0.02, 0.02, 1.0)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Test:
    def __init__(self, kind, shots, rate, quit_after):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.kind, self.shots, self.rate, self.quit_after = kind, shots, rate, quit_after
        self.state, self.until, self.taken = "load", 0.0, 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[belt_chain_test] {msg}")

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

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        folder = f"/Game/Characters/Fighters/BeltChain/{self.kind}"
        mesh = self.asset(f"{folder}/SK_BeltChain_{self.kind}")
        anim = self.asset(f"{folder}/SK_BeltChain_{self.kind}_Anim")
        self.length = anim.get_play_length()
        self.log(f"animation length {self.length:.2f}s")
        lib = getattr(unreal, "MaterialLibrary", None) or getattr(unreal, "KismetMaterialLibrary", None)
        base = self.asset("/Engine/BasicShapes/BasicShapeMaterial")
        light = lib.create_dynamic_material_instance(world, base)
        light.set_vector_parameter_value("Color", SKIN)
        dark = lib.create_dynamic_material_instance(world, base)
        dark.set_vector_parameter_value("Color", BLACK)
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
        a.set_actor_label("T_BeltChain")
        c = a.skeletal_mesh_component
        c.set_skinned_asset_and_update(mesh)
        slots = [str(n) for n in c.get_material_slot_names()]
        self.log("material slots: " + ", ".join(slots))
        for i, name in enumerate(slots):
            c.set_material(i, dark if "tail" in name.lower() or "belt" in name.lower() else light)
        ad = unreal.SingleAnimationPlayData()
        ad.set_editor_property("anim_to_play", anim)
        ad.set_editor_property("saved_looping", True)
        ad.set_editor_property("saved_playing", True)
        ad.set_editor_property("saved_play_rate", self.rate)
        c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        c.set_editor_property("animation_data", ad)
        c.set_editor_property("visibility_based_anim_tick_option",
                              unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 100))
        cam.set_actor_label("T_BeltCamera")
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
        self.actor = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)
                          if a.get_actor_label() == "T_BeltChain")
        self.comp = self.actor.skeletal_mesh_component
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        for root in ("belt_l_01", "belt_r_01"):
            self.comp.set_all_bodies_below_simulate_physics(root, True, True)
        self.comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        self.log("chain bodies set to simulate")

    def look(self, view):
        # camera 160 cm from the hips; "front" looks at the character, which faces +Y after import; "side" looks from -X
        origin = self.actor.get_actor_location() + unreal.Vector(0, 0, 90)
        offsets = {"front": unreal.Vector(0, 160, 5), "side": unreal.Vector(-160, 0, 5)}
        loc = origin + offsets[view]
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, origin), False, False)
        self.cam.capture_component2d.capture_scene()

    def step(self):
        now = time.time()
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
            self.state, self.until = "shoot", now + WARMUP_S
        elif self.state == "shoot":
            t = self.comp.get_position()
            for view in ("front", "side"):
                self.look(view)
                unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"{self.kind}_{self.taken:02d}_{view}.png")
            tip = self.comp.get_socket_location("belt_l_08")
            self.log(f"shot {self.taken:02d} anim t={t:.2f}s belt_l_08 at ({tip.x:.1f}, {tip.y:.1f}, {tip.z:.1f})")
            self.taken += 1
            if self.taken >= self.shots:
                return self.finish()
            self.until = now + SHOT_GAP_S


args = sys.argv[1:]
_kind = next((a for a in args if a[0].isupper()), "Medium")
_shots = next((int(a.split("=")[1]) for a in args if a.startswith("shots=")), 8)
_rate = next((float(a.split("=")[1]) for a in args if a.startswith("rate=")), 0.5)
_test = Test(_kind, _shots, _rate, "quit" in args)
