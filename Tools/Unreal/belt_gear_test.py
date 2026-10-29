"""Belt-chain follower on the real Medium fighter, under Leader Pose, in a Simulate session.

    UnrealEditor-Cmd.exe D:/Open-Stance-Gyeorugi/OpenStance.uproject -RenderOffscreen -unattended -SCCProvider=None
        -ExecCmds="py D:/Open-Stance-Gyeorugi/Tools/Unreal/belt_gear_test.py [Medium|Compact|Stocky|LeanTall|Tall] [shots=N] [gap=S] [rate=R] [nosim] [bare] [leaderpose] [start=T] [metrics=S] [skipfirst] [fit] [noshadow] [gearmat] [mat=/Engine/Path] quit"

Assembles the way the game does: MH_FighterBase body plays MetaHuman's body range-of-motion animation, the head and
every gear piece (except the old Meshy belt) follow it with Leader Pose, plus the new SK_BeltFollower_Medium
(band, waistband and the two chain-skinned tails, made by setup_belt_chain.py with `follower`). The follower's
belt_l_01 / belt_r_01 bodies are set to simulate. `nosim` leaves them kinematic, for comparison; `bare` hides jacket, pants and protector so the belt shows; `leaderpose` uses plain Leader Pose for the belt (its chain
cannot simulate that way, kept to show the difference). Nothing is saved.

Images: Saved/Screenshots/BeltGear/<NN>_front.png / _side.png (+ _hip close-ups), log Saved/Logs/belt_gear_test.txt.
"""
import math
import os
import sys
import time
import traceback

import unreal

OUT = "D:/Open-Stance-Gyeorugi/Saved/Screenshots/BeltGear"
LOG = "D:/Open-Stance-Gyeorugi/Saved/Logs/belt_gear_test.txt"
LEVEL = "/Game/Maps/L_TrainingDojang"
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
KIND = next((a for a in sys.argv[1:] if a in ("Medium", "Compact", "Stocky", "LeanTall", "Tall")), "Medium")
_MH = "MH_FighterBase" if KIND == "Medium" else f"MH_Fighter{KIND}"
BODY = f"/Game/Characters/Fighters/Export/{_MH}_Body"
HEAD = f"/Game/Characters/Fighters/Export/{_MH}_Head"
GEAR = f"/Game/Characters/Fighters/Gear/{KIND}"
FLAGS = set(sys.argv[1:])  # sys.argv is not reliable once the editor is ticking
FOLLOWER = f"/Game/Characters/Fighters/BeltChain/{KIND}/SK_BeltFollower{'Fit' if 'fit' in FLAGS else ''}_{KIND}"
PARTS = ["Jacket", "Pants", "Protector", "Helmet", "Gloves", "FootGuards"]  # old belt replaced by the follower; `fit` = refitted one
W, H = 960, 960
LOAD_SETTLE_S, SIM_START_S, WARMUP_S = 100.0, 25.0, 4.0
SKIN = unreal.LinearColor(0.52, 0.34, 0.26, 1.0)
BLACK = unreal.LinearColor(0.02, 0.02, 0.02, 1.0)

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


class Test:
    def __init__(self, shots, gap, rate, simulate, bare, leaderpose, quit_after, start=0.0, metrics=0.0):
        os.makedirs(OUT, exist_ok=True)
        self.f = open(LOG, "w", encoding="utf-8")
        self.shots, self.gap, self.rate, self.simulate, self.bare, self.leaderpose, self.quit_after = shots, gap, rate, simulate, bare, leaderpose, quit_after
        self.start, self.metrics = start, metrics
        self.skipfirst = "skipfirst" in FLAGS
        # `noshadow` = also stop the follower casting shadows (checks whether the tail banding is self-shadowing)
        self.follower_props = ("cast_capsule_direct_shadow", "cast_capsule_indirect_shadow")
        self.state, self.until, self.taken = "load", 0.0, 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def log(self, msg):
        self.f.write(msg + "\n")
        self.f.flush()
        unreal.log(f"[belt_gear_test] {msg}")

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

    def spawn(self, label, mesh_path):
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
        a.set_actor_label(label)
        c = a.skeletal_mesh_component
        c.set_skinned_asset_and_update(self.asset(mesh_path))
        return a, c

    def build(self):
        world = unreal.EditorLevelLibrary.get_editor_world()
        lib = getattr(unreal, "MaterialLibrary", None) or getattr(unreal, "KismetMaterialLibrary", None)
        base = self.asset("/Engine/BasicShapes/BasicShapeMaterial")
        skin = lib.create_dynamic_material_instance(world, base)
        skin.set_vector_parameter_value("Color", SKIN)
        dark = lib.create_dynamic_material_instance(world, base)
        dark.set_vector_parameter_value("Color", BLACK)
        anim = self.asset(ANIM)
        self.length = anim.get_play_length()
        self.log(f"animation length {self.length:.2f}s")

        body, leader = self.spawn("T_Body", BODY)
        for s in range(leader.get_num_materials()):
            leader.set_material(s, skin)
        ad = unreal.SingleAnimationPlayData()
        ad.set_editor_property("anim_to_play", anim)
        ad.set_editor_property("saved_looping", True)
        ad.set_editor_property("saved_playing", True)
        ad.set_editor_property("saved_play_rate", self.rate)
        ad.set_editor_property("saved_position", self.start)
        leader.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        leader.set_editor_property("animation_data", ad)
        leader.set_editor_property("visibility_based_anim_tick_option",
                                   unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        head, hc = self.spawn("T_Head", HEAD)
        for s in range(hc.get_num_materials()):
            hc.set_material(s, skin)
        hc.set_leader_pose_component(leader)
        followers = [(f"T_{p}", f"{GEAR}/SK_Fighter_{p}") for p in PARTS] + [("T_BeltFollower", FOLLOWER)]
        for label, path in followers:
            a, c = self.spawn(label, path)
            a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                              unreal.AttachmentRule.KEEP_WORLD, False)
            if label == "T_BeltFollower" and not self.leaderpose:
                # Leader Pose overwrites the follower's bones every frame, so its bodies cannot simulate: copy the
                # pose in an anim instance instead (SetLeader is called once the simulate world exists)
                c.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                c.set_anim_class(unreal.OpenStanceBeltFollowerAnimInstance)
                c.set_editor_property("visibility_based_anim_tick_option",
                                      unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            else:
                c.set_leader_pose_component(leader)
            if self.bare and label in ("T_Jacket", "T_Pants", "T_Protector"):
                c.set_visibility(False)
            if label == "T_BeltFollower":
                for flag in FLAGS:
                    if flag.startswith("prop="):  # experiment: prop=name:value sets an editor property on the follower
                        name, _, value = flag[5:].partition(":")
                        try:
                            c.set_editor_property(name, None if value == "None" else value in ("true", "True"))
                            self.log(f"set {name} = {value}")
                        except Exception as e:
                            self.log(f"could not set {name}: {e}")
                pass
            if label == "T_BeltFollower" and "hidefollower" in FLAGS:
                c.set_visibility(False)
            if label == "T_BeltFollower":
                # the physics asset doubles as a capsule-shadow proxy, which shades each chain link as its own capsule
                for prop in self.follower_props:
                    try:
                        c.set_editor_property(prop, False)
                        if "noshadow" in FLAGS:
                            for sp in ("cast_shadow", "cast_dynamic_shadow", "cast_static_shadow", "cast_contact_shadow",
                                       "cast_far_shadow", "cast_inset_shadow", "cast_hidden_shadow"):
                                try:
                                    c.set_editor_property(sp, False)
                                except Exception as e:
                                    self.log(f"could not set {sp}: {e}")
                    except Exception as e:
                        self.log(f"could not set {prop}: {e}")
                slots = [str(n) for n in c.get_material_slot_names()]
                self.log("follower slots: " + ", ".join(slots))
                debug_mat = next((f.split("=", 1)[1] for f in FLAGS if f.startswith("mat=")), None)
                if debug_mat:
                    for i in range(len(slots)):
                        c.set_material(i, self.asset(debug_mat))
                elif "gearmat" in FLAGS:
                    # the real gear's belt material (what the old SK_Fighter_Belt uses) on every slot (band and tails share the real UV scheme)
                    old = self.asset(f"{GEAR}/SK_Fighter_Belt")
                    real = [m.get_editor_property("material_interface") for m in old.get_editor_property("materials")]
                    self.log("old belt materials: " + ", ".join(str(m.get_name()) if m else "None" for m in real))
                    for i, name in enumerate(slots):
                        c.set_material(i, real[0])
                else:
                    for i in range(len(slots)):
                        c.set_material(i, dark)
        if "hidebody" in FLAGS:
            leader.set_visibility(False)
            hc.set_visibility(False)
        body.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)
        head.set_actor_rotation(unreal.Rotator(0, 0, 180.0), False)

        rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        cam = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, -200, 100))
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
        by = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SkeletalMeshActor)}
        self.body = by["T_Body"].skeletal_mesh_component
        self.belt = by["T_BeltFollower"].skeletal_mesh_component
        self.cam = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SceneCapture2D)[0]
        self.rt = self.cam.capture_component2d.get_editor_property("texture_target")
        if not self.leaderpose:
            inst = self.belt.get_anim_instance()
            self.log(f"belt anim instance: {inst}")
            inst.set_leader(self.body)

    def start_chain(self):
        # only now: the bodies start from the pose the follower has at this moment, which must be the copied body pose
        if self.simulate:
            for root in ("belt_l_01", "belt_r_01"):
                self.belt.set_all_bodies_below_simulate_physics(root, True, not self.skipfirst)
            self.log("chain bodies set to simulate")
        self.rest_rel = self.link_rotations()
        self.dump("at chain start")

    def dump(self, label):
        """World rotation of pelvis and the first chain bones, as quaternions (debug)."""
        for name in ("pelvis", "belt_l_01", "belt_l_02", "belt_l_03"):
            r = self.belt.get_socket_transform(name).rotation
            self.log(f"  [{label}] {name}: ({r.x:.3f}, {r.y:.3f}, {r.z:.3f}, {r.w:.3f})")

    def link_rotations(self):
        """Rotation between each pair of consecutive chain bones, as transforms (a -> b)."""
        out = {}
        for side in "lr":
            rel = []
            for i in range(1, 8):
                a = self.belt.get_socket_transform(f"belt_{side}_{i:02d}")
                b = self.belt.get_socket_transform(f"belt_{side}_{i + 1:02d}")
                rel.append(unreal.MathLibrary.compose_transforms(b, a.inverse()))
            out[side] = rel
        return out

    def deviation(self):
        """Degrees each link has turned away from its rest relative rotation, per side."""
        now_rel = self.link_rotations()
        result = {}
        for side in "lr":
            devs = []
            for cur, rest in zip(now_rel[side], self.rest_rel[side]):
                q = unreal.MathLibrary.compose_transforms(cur, rest.inverse()).rotation
                devs.append(math.degrees(2 * math.acos(min(1.0, abs(q.w)))))
            result[side] = devs
        return result

    def look(self, view):
        pelvis = self.body.get_socket_location("pelvis")
        target = pelvis + unreal.Vector(0, 0, 0)
        offsets = {"front": unreal.Vector(0, -130, 10), "side": unreal.Vector(130, 0, 10)}
        loc = target + offsets[view]
        self.cam.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, target), False, False)
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
            self.state, self.until = "chain", now + 1.5
        elif self.state == "chain":
            self.start_chain()
            if self.metrics:
                self.window = {"l": [0.0] * 7, "r": [0.0] * 7}
                self.window_start, self.metric_end = now, now + self.metrics
                self.state, self.until = "metrics", now
            else:
                self.state, self.until = "shoot", now + WARMUP_S
        elif self.state == "metrics":
            dev = self.deviation()
            for side in "lr":
                self.window[side] = [max(a, b) for a, b in zip(self.window[side], dev[side])]
            if now - self.window_start >= 0.5:
                t = self.body.get_position()
                fmt = lambda v: "[" + " ".join(f"{x:5.1f}" for x in v) + "]"
                self.log(f"t={t:6.2f}s  max dev from rest  L {fmt(self.window['l'])}  R {fmt(self.window['r'])}")
                self.window = {"l": [0.0] * 7, "r": [0.0] * 7}
                self.window_start = now
            if not getattr(self, "dumped", False) and now - self.window_start > 0.3:
                self.dumped = True
                self.dump("0.3s after")
            if now >= self.metric_end:
                return self.finish()
        elif self.state == "shoot":
            t = self.body.get_position()
            for view in ("front", "side"):
                self.look(view)
                unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, f"{self.taken:02d}_{view}.png")
            pel = self.body.get_socket_location("pelvis")
            tip = self.belt.get_socket_location("belt_l_08")
            local = self.body.get_socket_transform("pelvis").inverse_transform_location(tip)
            if self.taken in (0, 12):
                for side in "lr":
                    angles = []
                    for i in range(1, 8):
                        a = self.belt.get_socket_transform(f"belt_{side}_{i:02d}")
                        b = self.belt.get_socket_transform(f"belt_{side}_{i + 1:02d}")
                        q = unreal.MathLibrary.compose_transforms(b, a.inverse()).rotation
                        angles.append(round(math.degrees(2 * math.acos(min(1.0, abs(q.w)))), 1))
                    self.log(f"  link rotation deg {side}: {angles}")
            self.log(f"shot {self.taken:02d} anim t={t:.2f}s pelvis z {pel.z:.1f}  belt_l_08 in pelvis space ({local.x:.1f}, {local.y:.1f}, {local.z:.1f})")
            self.taken += 1
            if self.taken >= self.shots:
                return self.finish()
            self.until = now + self.gap


args = sys.argv[1:]
_shots = next((int(a.split("=")[1]) for a in args if a.startswith("shots=")), 12)
_gap = next((float(a.split("=")[1]) for a in args if a.startswith("gap=")), 1.5)
_rate = next((float(a.split("=")[1]) for a in args if a.startswith("rate=")), 1.0)
_start = next((float(a.split("=")[1]) for a in args if a.startswith("start=")), 0.0)
_metrics = next((float(a.split("=")[1]) for a in args if a.startswith("metrics=")), 0.0)
_test = Test(_shots, _gap, _rate, "nosim" not in args, "bare" in args, "leaderpose" in args, "quit" in args, _start, _metrics)
