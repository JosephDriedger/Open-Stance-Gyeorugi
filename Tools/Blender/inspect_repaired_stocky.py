import bpy,json
from pathlib import Path
p=Path('D:/Open-Stance-Gyeorugi/Resources/Models/ROMRepair');bpy.ops.wm.open_mainfile(filepath=str(p/'Stocky/Gameplay_High.blend'))
(p/'stocky_objects.json').write_text(json.dumps([{'name':o.name,'hidden':o.hide_render,'type':o.type,'n':len(o.data.vertices) if o.type=='MESH' else 0} for o in bpy.context.scene.objects],indent=2))
