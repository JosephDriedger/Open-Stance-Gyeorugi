"""Export full high-detail sparring characters after the guard motion gate passes."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
BASE=build.ROOT/'Resources/Models/FinalRefinement/GuardBodyVariantsV7'
validation=json.loads((BASE/'surface_validation.json').read_text());assert validation['passed'] and len(validation['presets'])==9
OUT=build.ROOT/'Resources/Models/FinalRefinement/GuardBodyDelivery';OUT.mkdir(exist_ok=True)
report=dict(production_installed=False,exports=[],scope='Full static high-detail sparring FBXs with the improved guards and production root name. No cloth simulation transfer or recorded-mocap acceptance.')
for row in validation['presets']:
    kind=row['preset'];dest=OUT/kind;dest.mkdir(exist_ok=True)
    for style,label in enumerate(('Standard','Padded')):
        bpy.ops.wm.open_mainfile(filepath=str(BASE/kind/'Gameplay_High_Staged.blend'))
        r=bpy.data.objects['RIG_Body_'+kind];r.animation_data_clear();r.data.pose_position='REST'
        for key in ('Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','Wear_Jacket','Wear_Pants','Wear_Hair'):r[key]=True
        r['FootGuardsStyle']=style;r['BlenderCloth']=False;build.refresh(r)
        for name in ('FootGuards','FootGuards_PaddedInstep'):bpy.data.objects[name]['ExportUV']='UVInstepPanel'
        meshes=[o.name for o in build.meshes() if not o.hide_render]
        r.name='root';path=dest/f'{kind}_Sparring_{label}.fbx';build.export(r,path,False)
        report['exports'].append(dict(preset=kind,style=label,file=str(path.relative_to(OUT)),meshes=meshes,bones=len(r.data.bones)))
        (OUT/'exports.json').write_text(json.dumps(report,indent=2))
