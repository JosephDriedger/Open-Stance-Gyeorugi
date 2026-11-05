"""Validate all corrected guard character FBXs against the production skeleton, without saving."""
import json, traceback, uuid
from pathlib import Path
import unreal

ROOT = Path('D:/Open-Stance-Gyeorugi')
OUT = ROOT/'Resources/Models/FinalRefinement/GuardBodyDelivery'
EAL = unreal.EditorAssetLibrary
scratch = '/Game/__CharacterValidation__/Guards_' + uuid.uuid4().hex
report = dict(passed=False, models=[], errors=[], production_assets_saved=False)
def bones(mesh):
    return {r.split('|')[0]:r.split('|')[1] for r in unreal.OpenStanceBeltChainLibrary.list_bones(mesh)}
try:
    unreal.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
    reference = EAL.load_asset('/Game/Characters/Fighters/Export/MH_FighterBase_Body')
    skeleton = reference.get_editor_property('skeleton')
    expected = bones(reference)
    sources = sorted(OUT.glob('*/*_Sparring_*.fbx'))
    assert len(sources) == 18, len(sources)
    for source in sources:
        ui = unreal.FbxImportUI()
        ui.import_mesh=True; ui.import_as_skeletal=True
        ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
        ui.automated_import_should_detect_type=False
        ui.import_animations=False; ui.import_materials=False; ui.import_textures=False
        ui.create_physics_asset=False; ui.skeleton=skeleton
        ui.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
        ui.skeletal_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task=unreal.AssetImportTask()
        task.filename=str(source); task.destination_path=scratch+'/'+source.stem
        task.destination_name='SK_Test'; task.automated=True; task.save=False; task.options=ui
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=EAL.load_asset(task.destination_path+'/SK_Test')
        assert isinstance(mesh,unreal.SkeletalMesh),source
        actual=bones(mesh)
        assert actual == expected, (source, 'bone name/parent mismatch')
        assert mesh.get_editor_property('skeleton') == skeleton, source
        morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
        assert morphs, (source,'missing correctives')
        report['models'].append(dict(source=str(source),bones=len(actual),production_skeleton_matches=True,morph_targets=morphs))
        (OUT/'unreal_validation.json').write_text(json.dumps(report,indent=2))
    report['passed']=True
except Exception:
    report['errors'].append(traceback.format_exc())
finally:
    report['scratch_deleted']=EAL.delete_directory(scratch) if EAL.does_directory_exist(scratch) else True
    report['scope']='Structural import and shared skeleton only; no rendered animation, runtime corrective driving, material or physics acceptance. No production assets saved.'
    (OUT/'unreal_validation.json').write_text(json.dumps(report,indent=2))
