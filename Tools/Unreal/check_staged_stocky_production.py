"""Load production fighter assets and test staged FBX imports without saving assets."""
import unreal,json,uuid,traceback,os
from pathlib import Path
ROOT=Path('D:/Open-Stance-Gyeorugi')
production_root=os.environ.get('OPENSTANCE_PRODUCTION_ROOT')=='1'
existing_skeleton=os.environ.get('OPENSTANCE_USE_PRODUCTION_SKELETON')=='1'
OUT=ROOT/'Resources/Models/FinalRefinement'/('ProductionSkeletonCheck_20261102' if existing_skeleton else 'ProductionRootCheck_20261102' if production_root else 'ProductionCheck_20261102');OUT.mkdir(exist_ok=True)
scratch='/Game/__CharacterValidation__/Run_'+uuid.uuid4().hex
EAL=unreal.EditorAssetLibrary
report={'production_assets_saved':False,'scratch':scratch,'installed':[],'staged_imports':[],'errors':[]}
def bones(mesh):
 return {row.split('|')[0]:row.split('|')[1:] for row in unreal.OpenStanceBeltChainLibrary.list_bones(mesh)}
try:
 unreal.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 for kind,stem in [('Medium','MH_FighterBase'),('Compact','MH_FighterCompact'),('Stocky','MH_FighterStocky'),('LeanTall','MH_FighterLeanTall'),('Tall','MH_FighterTall')]:
  path=f'/Game/Characters/Fighters/Export/{stem}_Body';mesh=EAL.load_asset(path)
  assert isinstance(mesh,unreal.SkeletalMesh),path
  skeleton=mesh.get_editor_property('skeleton');assert skeleton,path
  report['installed'].append({'preset':kind,'mesh':path,'skeleton':skeleton.get_path_name(),'bones':len(bones(mesh))})
 for label in ('Standard','Padded'):
  folder='StockyProductionRoot' if production_root else 'StockyGuardIntegration'
  source=ROOT/f'Resources/Models/FinalRefinement/{folder}/Stocky_Sparring_{label}.fbx'
  ui=unreal.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=True;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
  ui.automated_import_should_detect_type=False;ui.import_animations=False;ui.import_materials=False;ui.import_textures=False;ui.create_physics_asset=False
  production_skeleton=EAL.load_asset('/Game/Characters/Fighters/Export/MH_FighterStocky_Body').get_editor_property('skeleton')
  if existing_skeleton:ui.skeleton=production_skeleton
  ui.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
  ui.skeletal_mesh_import_data.set_editor_property('normal_import_method',unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=scratch+'/'+label;task.destination_name='SK_Test';task.automated=True;task.save=False;task.options=ui
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  mesh=EAL.load_asset(task.destination_path+'/SK_Test');assert isinstance(mesh,unreal.SkeletalMesh),label
  imported=bones(mesh);ref=bones(EAL.load_asset('/Game/Characters/Fighters/Export/MH_FighterStocky_Body'))
  missing=sorted(set(ref)-set(imported));shared=set(ref)&set(imported)
  differences=[name for name in shared if ref[name][0]!=imported[name][0]]
  rest_error=max((sum((float(a)-float(b))**2 for a,b in zip(ref[name][1:],imported[name][1:]))**.5 for name in shared),default=0)
  morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
  if existing_skeleton:assert mesh.get_editor_property('skeleton')==production_skeleton,label
  report['staged_imports'].append({'style':label,'bones':len(imported),'missing_production_bones':missing,'extra_bones':sorted(set(imported)-set(ref)),'parent_differences':differences,'max_shared_rest_position_error_cm':rest_error,'morph_targets':morphs,'shared_bones':len(shared),'skeleton':mesh.get_editor_property('skeleton').get_path_name()})
 report['structural_checks_completed']=True
except Exception:report['errors'].append(traceback.format_exc());report['structural_checks_completed']=False
finally:
 if EAL.does_directory_exist(scratch):report['scratch_deleted']=EAL.delete_directory(scratch)
 report['scope']='Production body load and staged skeletal/morph import only. No gameplay, visual, collision, cloth, material, animation retarget or packaged-build acceptance.'
 (OUT/'unreal_structure.json').write_text(json.dumps(report,indent=2))
 unreal.log('STAGED_PRODUCTION_CHECK '+json.dumps(report))
