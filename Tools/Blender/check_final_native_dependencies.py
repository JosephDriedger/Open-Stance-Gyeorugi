import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];stage=ROOT/'Resources/Models/FinalRefinement/HairRepeat'
manifest=json.loads((stage/'published.json').read_text());rows=[]
for item in manifest['files']:
 p=ROOT/item['file'];bpy.ops.wm.open_mainfile(filepath=str(p));external=[]
 for im in bpy.data.images:
  if im.source not in ['FILE','MOVIE'] or im.packed_file or not im.filepath:continue
  q=Path(bpy.path.abspath(im.filepath,library=im.library));assert q.is_file(),(p,im.name,q);external.append(str(q))
 for lib in bpy.data.libraries:
  q=Path(bpy.path.abspath(lib.filepath));assert q.is_file(),(p,q)
 mats={m for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Hair_') for m in o.data.materials if m and m.use_nodes}
 for m in mats:
  for n in m.node_tree.nodes:
   if n.type=='TEX_IMAGE':assert n.extension=='REPEAT',(p,m.name,n.name)
 rows.append({'file':item['file'],'external_images':external,'hair_repeat_verified':True})
(stage/'dependency_validation.json').write_text(json.dumps({'passed':True,'files':rows},indent=2))
print('NATIVE_DEPENDENCIES_VERIFIED '+str(len(rows)),flush=True)
