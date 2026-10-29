"""Read-only inventory of installed character meshes and cloth for delivery review."""
import unreal,json,traceback
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/FinalRefinement/UnrealAudit')
out.mkdir(exist_ok=True)
report={'read_only':True,'meshes':[],'errors':[]}
try:
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    assets=registry.get_assets_by_path('/Game/Characters',recursive=True)
    for asset in assets:
        if str(asset.asset_class_path.asset_name)!='SkeletalMesh':continue
        mesh=asset.get_asset()
        skeleton=mesh.get_editor_property('skeleton')
        row={'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name() if skeleton else None}
        try:row['cloth']=unreal.OpenStanceClothLibrary.describe_cloth(mesh)
        except Exception as error:row['cloth_error']=str(error)
        report['meshes'].append(row)
    report['complete']=True
except Exception:
    report['errors'].append(traceback.format_exc());report['complete']=False
(out/'inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('CHARACTER_DELIVERY_AUDIT '+str(len(report['meshes'])))
