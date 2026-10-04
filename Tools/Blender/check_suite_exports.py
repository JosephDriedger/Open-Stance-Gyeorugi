"""Round-trip exported character meshes and animation-only FBXs."""
import bpy,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/CharacterSuite'
try:
 report={}
 for path in sorted(OUT.glob('*/*.fbx')):
  bpy.ops.wm.read_factory_settings(use_empty=True)
  bpy.ops.import_scene.fbx(filepath=str(path),use_image_search=False)
  arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(arms)==1,(path,len(arms));arm=arms[0]
  crowd=path.stem.startswith('Crowd');limit=2 if crowd else 4
  meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];maximum=0
  for o in meshes:
   names={g.index:g.name for g in o.vertex_groups};bones=set(arm.data.bones.keys())
   assert any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers),o.name
   for v in o.data.vertices:
    w=[g.weight for g in v.groups if names[g.group] in bones and g.weight>1e-6];maximum=max(maximum,len(w));assert w and abs(sum(w)-1)<.003,(path,o.name,v.index,sum(w))
  assert maximum<=limit,(path,maximum)
  assert len(arm.data.bones)==(25 if crowd else 341),(path,len(arm.data.bones))
  if not meshes:assert bpy.data.actions and arm.animation_data.action,(path,'missing action')
  report[str(path.relative_to(OUT))]={'meshes':len(meshes),'bones':len(arm.data.bones),'max_influences':maximum,'animation':bool(arm.animation_data and arm.animation_data.action),'passed':True}
 (OUT/'export_validation.json').write_text(json.dumps(report,indent=2))
except:
 (OUT/'export_error.log').write_text(traceback.format_exc());raise
