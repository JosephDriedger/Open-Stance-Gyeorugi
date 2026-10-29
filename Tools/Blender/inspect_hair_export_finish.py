import bpy,json
from pathlib import Path
out=Path('D:/Open-Stance-Gyeorugi/Resources/Models/HairExportFinish');out.mkdir(exist_ok=True)
rows=[]
for level in ['Gameplay_High','Crowd_Near']:
 bpy.ops.wm.open_mainfile(filepath='D:/Open-Stance-Gyeorugi/Resources/Models/CharacterSuite/Medium/'+level+'.blend')
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or not o.name.startswith('Hair_Crew'):continue
  row={'level':level,'object':o.name,'vertices':len(o.data.vertices),'uv':[u.name for u in o.data.uv_layers],'materials':[]}
  for m in o.data.materials:
   b=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   row['materials'].append({'name':m.name,'sockets':{n:{'value':list(b.inputs[n].default_value) if n=='Base Color' else b.inputs[n].default_value,'links':[(l.from_node.name,l.from_socket.name) for l in b.inputs[n].links]} for n in ['Base Color','Alpha','Roughness']},'images':[(n.name,n.image.name,n.image.filepath,n.image.alpha_mode) for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
  rows.append(row)
(out/'inspect.json').write_text(json.dumps(rows,indent=2))
