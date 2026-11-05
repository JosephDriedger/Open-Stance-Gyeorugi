"""Unsaved crowd LOD and animation import checks in a unique scratch folder."""
import unreal, json, uuid, traceback
from pathlib import Path
ROOT=Path('D:/Open-Stance-Gyeorugi')
OUT=ROOT/'Resources/Models/FinalRefinement/CrowdEngineCheck_20261102';OUT.mkdir(exist_ok=True)
scratch='/Game/__CharacterValidation__/Crowd_'+uuid.uuid4().hex
EAL=unreal.EditorAssetLibrary
report=dict(meshes=[],animations=[],errors=[],production_assets_saved=False,scratch=scratch)
def bones(mesh):return {row.split('|')[0]:row.split('|')[1:] for row in unreal.OpenStanceBeltChainLibrary.list_bones(mesh)}
def import_file(source,dest,ui):
    assert source.is_file(),source
    task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=source.stem
    task.automated=True;task.save=False;task.options=ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return [EAL.load_asset(path) for path in task.imported_object_paths]
try:
    unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    for kind in ('Medium','Compact','Stocky','LeanTall','Tall','Male_Athletic','Male_Lean','Female_Athletic','Female_Strong'):
        reference=None;skeleton=None
        for lod in ('Near','Far'):
            ui=unreal.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=True;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
            ui.automated_import_should_detect_type=False;ui.import_animations=False;ui.import_materials=False;ui.import_textures=False;ui.create_physics_asset=False
            if skeleton:ui.skeleton=skeleton
            ui.skeletal_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
            assets=import_file(ROOT/f'Resources/Models/CharacterSuite/{kind}/Crowd_{lod}.fbx',scratch+'/'+kind,ui)
            mesh=next(a for a in assets if isinstance(a,unreal.SkeletalMesh)); current=bones(mesh)
            if reference is not None:assert current==reference,(kind,'LOD skeleton/rest disagreement')
            else:reference=current;skeleton=mesh.get_editor_property('skeleton')
            report['meshes'].append(dict(preset=kind,lod=lod,bones=len(current),lod_skeleton_matches=True))
        if kind=='Medium':
            for label in ('StandingIdle','SeatedIdle','SeatedClap','Cheer','Wave'):
                ui=unreal.FbxImportUI();ui.import_mesh=False;ui.import_animations=True;ui.skeleton=skeleton
                ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;ui.automated_import_should_detect_type=False
                ui.import_materials=False;ui.import_textures=False
                assets=import_file(ROOT/f'Resources/Models/CharacterSuite/{kind}/Crowd_{label}.fbx',scratch+'/'+kind+'/Animations',ui)
                animations=[a for a in assets if isinstance(a,unreal.AnimSequence)];assert animations,label
                for anim in animations:
                    duration=anim.get_play_length();assert duration>0,label
                    assert anim.get_editor_property('skeleton')==skeleton,label
                    report['animations'].append(dict(clip=label,asset=anim.get_name(),seconds=duration,skeleton_matches=True))
        (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    report['passed']=True
except Exception:
    report['passed']=False;report['errors'].append(traceback.format_exc())
finally:
    report['scratch_deleted']=EAL.delete_directory(scratch) if EAL.does_directory_exist(scratch) else True
    report['scope']='Nine default-uniform Near/Far FBX pairs and five Medium animation clips. Structural import only; no rendered animation, crowd density, alternate uniforms, or frame-time acceptance.'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
