"""Deformation check: play the MetaHuman body range-of-motion animation on the exported base body
with every gear piece following it (leader pose), the same setup the game uses.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py"          spawn (or refresh) the test
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py" 3.5      jump to 3.5 s and frame the camera
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/gear_rom_test.py" 3.5 back view from behind

Actors are labelled GearROM_* and placed high above the level (Z 20000) so nothing overlaps them.
Note: the body here has no hidden face maps (those are applied by MetaHuman assembly), so small
skin poke-through under the cloth is expected; look for cloth tearing, stretching and flapping.
"""
import sys

import unreal

EAL = unreal.EditorAssetLibrary
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
BODY = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
GEAR = "/Game/Characters/Fighters/Gear"
PARTS = ["Jacket", "Pants", "Belt", "Protector", "Helmet", "Gloves", "FootGuards"]
ORIGIN = unreal.Vector(0, 0, 20000)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
args = sys.argv[1:]
existing = {a.get_actor_label(): a for a in actors.get_all_level_actors() if a.get_actor_label().startswith(("GearROM_", "FitTest_"))}

if not args:
    for a in existing.values():
        actors.destroy_actor(a)
    anim = EAL.load_asset(ANIM)
    body = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, ORIGIN)
    body.set_actor_label("GearROM_Body")
    leader = body.skeletal_mesh_component
    leader.set_skinned_asset_and_update(EAL.load_asset(BODY))
    leader.set_update_animation_in_editor(True)
    leader.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    leader.play_animation(anim, True)
    leader.set_play_rate(0.0)
    for p in PARTS:
        a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, ORIGIN)
        a.set_actor_label(f"GearROM_{p}")
        a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                          unreal.AttachmentRule.KEEP_WORLD, False)
        c = a.skeletal_mesh_component
        c.set_skinned_asset_and_update(EAL.load_asset(f"{GEAR}/SK_Fighter_{p}"))
        c.set_update_animation_in_editor(True)
        c.set_leader_pose_component(leader)
    unreal.log(f"[gear_rom_test] spawned; animation length {anim.get_play_length():.2f}s")
else:
    t = float(args[0])
    body = existing["GearROM_Body"]
    leader = body.skeletal_mesh_component
    leader.set_position(t, False)
    back = len(args) > 1 and args[1] == "back"
    y = 330 if not back else -330
    ues.set_level_viewport_camera_info(ORIGIN + unreal.Vector(0, y, 100), unreal.Rotator(0, -2, -90 if not back else 90))
