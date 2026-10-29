"""Read original content's asset headers without loading or saving game assets."""
import unreal,json,traceback
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/FinalRefinement/UnrealAudit');out.mkdir(exist_ok=True)
report={'read_only':True,'scope':'Asset registry metadata in an isolated content-only audit project; no game-module, cloth or runtime verification.','meshes':[]}
try:
    registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
    assets=registry.get_assets_by_path('/Game',recursive=True)
    for asset in assets:
        if str(asset.asset_class_path.asset_name)!='SkeletalMesh':continue
        tags={}
        for key in ['Skeleton','LOD0Triangles','LOD0Vertices','LODs','NumLODs','Triangles','Vertices']:
            value=asset.get_tag_value(key)
            if value:tags[key]=str(value)
        report['meshes'].append({'package':str(asset.package_name),'name':str(asset.asset_name),'tags':tags})
    report['assets_scanned']=len(assets);report['complete']=True
except Exception:
    report['complete']=False;report['error']=traceback.format_exc()
(out/'registry_inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('CHARACTER_REGISTRY_AUDIT '+str(len(report['meshes'])))
