import bpy,json
from pathlib import Path
O=Path('D:/Open-Stance-Gyeorugi/Resources/Models/TailoredDoboks')
bpy.ops.wm.open_mainfile(filepath=str(O/'Stocky/Preview.blend'));report={}
for name in ['Body','Pants']:
 o=bpy.data.objects[name];report[name]=[{'name':m.name,'group':m.vertex_group,'threshold':m.threshold,'invert':m.invert_vertex_group,'viewport':m.show_viewport,'render':m.show_render} for m in o.modifiers if m.type=='MASK']
(O/'mask_inspection.json').write_text(json.dumps(report,indent=2))
