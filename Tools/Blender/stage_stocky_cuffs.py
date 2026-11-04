import bpy,sys,json,hashlib,array,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from repair_stocky_cuffs import configure
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery';OUT.mkdir(exist_ok=True)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def protected():
 h=hashlib.sha256();pants=bpy.data.objects['Pants'].data
 for mesh in sorted(bpy.data.meshes,key=lambda m:m.name):
  h.update(mesh.name.encode())
  if mesh!=pants:
   for vs in [mesh.vertices]+([k.data for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []):
    a=array.array('f',[0])*(len(vs)*3);vs.foreach_get('co',a);h.update(a.tobytes())
  a=array.array('i',[0])*len(mesh.loops);mesh.loops.foreach_get('vertex_index',a);h.update(a.tobytes())
  for uv in mesh.uv_layers:
   a=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',a);h.update(a.tobytes())
  h.update(repr([(m.name if m else None) for m in mesh.materials]).encode())
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o.type!='MESH':continue
  h.update(repr((o.name,[(g.name,g.index) for g in o.vertex_groups],[[ (g.group,g.weight) for g in v.groups] for v in o.data.vertices])).encode())
 return h.hexdigest()
files=[r['file'] for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if 'Stocky' in r['file'] and r['file'].endswith('.blend')]
(OUT/'native_inputs.json').write_text(json.dumps(files,indent=2))
for rel in files:
 source=ROOT/rel;before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;frame=s.frame_current;s.frame_set(1);bpy.context.view_layer.update()
 signature=protected();actions=base.actions();rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
 rows=configure(s);assert rows,rel
 pants=bpy.data.objects['Pants'];expected=np.array([v.co[:] for v in pants.data.vertices]);keys={k.name:np.array([v.co[:] for v in k.data]) for k in pants.data.shape_keys.key_blocks} if pants.data.shape_keys else {}
 s.frame_set(frame);target=OUT/'Files'/rel;target.parent.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(target));assert protected()==signature and base.actions()==actions,rel
 assert {o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}==rigs,rel
 pants=bpy.data.objects['Pants'];assert np.array_equal(np.array([v.co[:] for v in pants.data.vertices]),expected),rel
 for name,points in keys.items():assert np.array_equal(np.array([v.co[:] for v in pants.data.shape_keys.key_blocks[name].data]),points),(rel,name)
 report={'file':rel,'before_sha256':before,'sha256':sha(target),'repair':rows,'reopened_preservation_passed':True,'other_geometry_uv_skin_rigs_actions_preserved':True}
 key=hashlib.sha256(rel.encode()).hexdigest()[:16];(OUT/('native_'+key+'.json')).write_text(json.dumps(report,indent=2));print('STOCKY_CUFF_NATIVE_STAGED',rel,flush=True)
