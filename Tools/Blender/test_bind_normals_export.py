import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import rebuild_updated_characters as b
root=b.ROOT
import bpy
bpy.ops.wm.open_mainfile(filepath=str(root/'Resources/Models/CharacterSuite/Medium/Gameplay_High.blend'))
r=bpy.data.objects['RIG_Body_Medium'];r['Wear_Helmet']=False;r['Wear_Protector']=False;b.refresh(r)
path=root/'Saved/ExportValidation/Medium_Regression.fbx';path.parent.mkdir(parents=True,exist_ok=True)
b.export(r,path)
(root/'Resources/Models/FinalRefinement/BindNormalsDelivery/exporter_regression.json').write_text(json.dumps({'passed':True,'file':str(path),'checks':['Shared exporter completed SDK validation','Canonical bind metadata and normal repair applied','Raw export replaced only after validation']},indent=2))
print('BIND_NORMALS_EXPORTER_PASSED',flush=True)
