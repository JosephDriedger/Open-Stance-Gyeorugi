"""Stage complete Stocky sparring exports with the revised guard weights."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as build
ROOT=build.ROOT;production_root='--production-root' in sys.argv
OUT=ROOT/'Resources/Models/FinalRefinement'/('StockyProductionRoot' if production_root else 'StockyGuardIntegration');OUT.mkdir(exist_ok=True)
rows=[]
for style,label in enumerate(('Standard','Padded')):
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardLocalROMSmooth/Candidate.blend'))
 r=bpy.data.objects['RIG_Body_Stocky'];r.animation_data_clear();r.data.pose_position='REST'
 for key in ('Wear_Helmet','Wear_Protector','Wear_Gloves','Wear_FootGuards','Wear_Jacket','Wear_Pants'):r[key]=True
 r['FootGuardsStyle']=style;r['BlenderCloth']=False;build.refresh(r)
 for name in ('FootGuards','FootGuards_PaddedInstep'):bpy.data.objects[name]['ExportUV']='UVInstepPanel'
 names=[o.name for o in build.meshes() if not o.hide_render]
 if production_root:r.name='root'
 path=OUT/f'Stocky_Sparring_{label}.fbx';build.export(r,path,False)
 rows.append({'style':label,'meshes':names,'file':path.name})
(OUT/'exports.json').write_text(json.dumps({'production_installed':False,'scope':'Complete Stocky sparring character, static rest export; cloth disabled, no mocap certification','exports':rows},indent=2))
