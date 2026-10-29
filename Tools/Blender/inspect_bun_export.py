import bpy,json
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairFormRefinement/Medium/CompactBun_Dobok.fbx')
bpy.ops.import_scene.fbx(filepath=str(p))
(p.parent/'import_names.json').write_text(json.dumps([o.name for o in bpy.context.scene.objects if 'Hair' in o.name],indent=2))
