import bpy,json,hashlib
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/VisualFitRepair');path=out/'LiveCloth_Pilot.blend'
report=json.loads((out/'cloth_pilot.json').read_text());assert report['completed'] and report['frames']==72
bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_Medium']
assert r['BlenderCloth'] and s['ClothDemoPreset'].startswith('Hybrid kick')
for name in ['Jacket','Jacket_WhiteVNeck','Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
 o=bpy.data.objects[name];g=o.vertex_groups['LiveCloth_Pin'];assert all(g.weight(v.index)>.999 for v in o.data.vertices)
for name in ['Belt_Tail_Left','Belt_Tail_Right']:
 o=bpy.data.objects[name];g=o.vertex_groups['LiveCloth_Pin'];assert any(g.weight(v.index)<.1 for v in o.data.vertices)
text=bpy.data.texts.get('LIVE_CLOTH_README') or bpy.data.texts.new('LIVE_CLOTH_README');text.clear()
text.write('HYBRID KICK DEMO: the reviewed baked uniform animation is retained and uniform cloth vertices are fully pinned. Belt-tail baked corrections are cleared and the tails use live Blender cloth. Play sequentially from frame 1. This is not a freely simulated uniform demonstration. General live uniform settings in other profiles remain experimental and need motion-specific tuning. See Animation/Physics/README.md.\n')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
report.update({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'preset':s['ClothDemoPreset'],'uniform_fully_pinned':True,'belt_tails_dynamic':True})
(out/'cloth_pilot.json').write_text(json.dumps(report,indent=2))
