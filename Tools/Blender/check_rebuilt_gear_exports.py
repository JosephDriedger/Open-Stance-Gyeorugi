"""Round-trip only the 15 regenerated sparring exports."""
import bpy,json,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'Resources/Models/GearUpgrade'
try:
 report={}
 paths=sorted(OUT.glob('*/*_Sparring.fbx'));assert len(paths)==15,len(paths)
 for path in paths:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_image_search=False)
  rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1
  rig=rigs[0];assert len(rig.data.bones)==341
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];maximum=0
  assert any(o.name.startswith('Helmet_Vented_Crown') for o in meshes)
  assert any(o.name.startswith('Protector_Quilted_Lace_Back') for o in meshes)
  assert not any(o.name.startswith(('Helmet_Padded_Open_Crown','Helmet_Perforated_Full_Crown','Protector_Smooth_Buckle_Back')) for o in meshes)
  for o in meshes:
   assert any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)
   names={g.index:g.name for g in o.vertex_groups}
   for v in o.data.vertices:
    w=[g.weight for g in v.groups if names[g.group] in rig.data.bones and g.weight>1e-6]
    assert w and abs(sum(w)-1)<.003
    maximum=max(maximum,len(w))
  assert maximum<=4
  report[str(path.relative_to(OUT))]={'passed':True,'meshes':len(meshes),'bones':341,'max_influences':maximum,'animation':False}
  (OUT/'export_validation.json').write_text(json.dumps(report,indent=2))
 (OUT/'exports.log').write_text('COMPLETE')
except:(OUT/'exports.log').write_text(traceback.format_exc());raise
