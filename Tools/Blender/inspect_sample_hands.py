import bpy,json
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/Animation/Samples')
bpy.ops.wm.open_mainfile(filepath=str(p/'Medium_Sparring_Samples.blend'))
r=bpy.data.objects['RIG_Body_Medium']
(p/'hands.json').write_text(json.dumps({b.name:{'head':list(b.head_local),'tail':list(b.tail_local),'x':list(b.matrix_local.to_3x3().col[0]),'z':list(b.matrix_local.to_3x3().col[2])} for b in r.data.bones if b.name.startswith(('index_','middle_','pinky_','thumb_','hand_'))},indent=2))
