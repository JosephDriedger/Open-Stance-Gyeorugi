import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
paths=['Resources/Models/CharacterSuite/Medium/Gameplay_High.blend','Resources/Models/FinalRefinement/BeltTargetImportAudit/GeometryDiagnosis/OpenStance_Medium.fbx']
for rel in paths:
 p=root/rel
 if not p.exists():continue
 if p.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(p))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(p))
 for o in bpy.data.objects:
  if o.type!='MESH' or o.name.split('.')[0] not in ('Jacket','Pants','Body'):continue
  print('UV_SOURCE',rel,o.name,'export',o.get('ExportUV'),'layers',[(l.name,len(set(tuple(d.uv) for d in l.data))) for l in o.data.uv_layers])
  for m in o.data.materials:
   if m and m.use_nodes:print('MATERIAL',m.name,[(n.type,getattr(n,'uv_map',''),getattr(getattr(n,'image',None),'filepath','')) for n in m.node_tree.nodes],[(l.from_node.type,l.from_socket.name,l.to_node.type,l.to_socket.name) for l in m.node_tree.links])
