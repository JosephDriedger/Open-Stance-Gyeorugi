import bpy,sys,json,hashlib,array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from repair_uniform_export_data import fabric_uv
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/UniformGeometryDelivery'
files=sorted({r['file'] for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if r['file'].endswith('.blend')})
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def geometry():
 h=hashlib.sha256()
 for mesh in sorted(bpy.data.meshes,key=lambda m:m.name):
  h.update(mesh.name.encode())
  for vertices in [mesh.vertices]+([k.data for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []):
   a=array.array('f',[0])*(len(vertices)*3);vertices.foreach_get('co',a);h.update(a.tobytes())
  a=array.array('i',[0])*len(mesh.loops);mesh.loops.foreach_get('vertex_index',a);h.update(a.tobytes())
  for uv in mesh.uv_layers:
   a=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',a);h.update(a.tobytes())
 return h.hexdigest()
for rel in files[int(sys.argv[-1])::2]:
 key=hashlib.sha256(rel.encode()).hexdigest()[:16];report=OUT/('native_'+key+'.json')
 if report.exists():continue
 src=ROOT/rel;before=sha(src);bpy.ops.wm.open_mainfile(filepath=str(src))
 signature=geometry();actions=base.actions();rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
 changed=[o.name for o in bpy.data.objects if fabric_uv(o)]
 row={'file':rel,'before_sha256':before,'changes':changed,'sha256':before}
 if changed:
  dst=OUT/'Files'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
  bpy.ops.wm.save_as_mainfile(filepath=str(dst),compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(dst))
  assert geometry()==signature and base.actions()==actions,rel
  assert {o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}==rigs,rel
  for name in changed:
   o=bpy.data.objects[name];assert o['ExportUV']=='UVWeave' and o.data.uv_layers.active.name=='UVWeave' and o.data.uv_layers['UVWeave'].active_render
  row['sha256']=sha(dst);row['reopened_preservation_passed']=True
 OUT.mkdir(exist_ok=True);report.write_text(json.dumps(row,indent=2));print('NATIVE_UV_STAGED',rel,len(changed),flush=True)
