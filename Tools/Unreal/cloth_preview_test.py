"""Watch cloth physics in the editor viewport: a referee (or the fighter) plays the MetaHuman body
range-of-motion animation in real time with cloth simulating.

    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/cloth_preview_test.py"            referee Kelvin
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/cloth_preview_test.py" Vivian     another referee
    py "D:/Open-Stance-Gyeorugi/Tools/Unreal/cloth_preview_test.py" fighter    dobok + gear

Actors are labelled ClothTest_* at Z 20000; delete them or don't save the level afterwards.
"""
import sys

import unreal

EAL = unreal.EditorAssetLibrary
ANIM = "/MetaHumanCharacter/Optional/Animation/TemplateAnimations/Technical_Loops/BodyROM/mhc_body_rom_body"
ORIGIN = unreal.Vector(0, 0, 20000)
who = sys.argv[1] if len(sys.argv) > 1 else "Kelvin"
if who == "fighter":
    body_path = "/Game/Characters/Fighters/Export/MH_FighterBase_Body"
    parts = [f"/Game/Characters/Fighters/Gear/SK_Fighter_{p}" for p in ("Jacket", "Pants", "Belt")]
else:
    body_path = f"/Game/Characters/Officials/Export/MH_Referee_{who}_Body"
    parts = [f"/Game/Characters/Officials/Outfits/{who}/SK_Referee_{p}" for p in ("Shirt", "Trousers", "Belt", "Shoes", "Tie")]

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in actors.get_all_level_actors():
    if a.get_actor_label().startswith("ClothTest_"):
        actors.destroy_actor(a)
body = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, ORIGIN)
body.set_actor_label("ClothTest_Body")
leader = body.skeletal_mesh_component
leader.set_skinned_asset_and_update(EAL.load_asset(body_path))
leader.set_update_animation_in_editor(True)
leader.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
leader.play_animation(EAL.load_asset(ANIM), True)
for path in parts:
    a = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, ORIGIN)
    a.set_actor_label(f"ClothTest_{path.split('_')[-1]}")
    a.attach_to_actor(body, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                      unreal.AttachmentRule.KEEP_WORLD, False)
    c = a.skeletal_mesh_component
    c.set_skinned_asset_and_update(EAL.load_asset(path))
    c.set_update_animation_in_editor(True)
    c.set_update_cloth_in_editor(True)
    c.set_leader_pose_component(leader)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    ORIGIN + unreal.Vector(0, 260, 110), unreal.Rotator(0, -4, -90))
