import bpy,sys,json,hashlib,array,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from refine_pants_cloth import configure
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/PantsClothDeliveryV3';OUT.mkdir(exist_ok=True)
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def geometry(names):
 h=hashlib.sha256()
 for name in sorted(names):
  mesh=bpy.data.meshes[name];h.update(name.encode())
  for vs in [mesh.vertices]+([k.data for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []):
   a=array.array('f',[0])*(len(vs)*3);vs.foreach_get('co',a);h.update(a.tobytes())
  a=array.array('i',[0])*len(mesh.loops);mesh.loops.foreach_get('vertex_index',a);h.update(a.tobytes())
  for uv in mesh.uv_layers:
   a=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',a);h.update(a.tobytes())
 return h.hexdigest()
def skin():
 h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  if o.type!='MESH' or o.get('SimulationOnly'):continue
  h.update(o.name.encode())
  names={g.index:g.name for g in o.vertex_groups if g.name!='LiveCloth_Pin'}
  for v in o.data.vertices:
   h.update(repr([(names[g.group],g.weight) for g in v.groups if g.group in names]).encode())
 return h.hexdigest()
files=sorted(r['file'] for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if r['file'].endswith('.blend'))
(OUT/'inputs.json').write_text(json.dumps(files,indent=2))
for rel in files[int(os.environ.get('OPENSTANCE_STAGE_SLOT','0'))::int(os.environ.get('OPENSTANCE_STAGE_COUNT','1'))]:
 key=hashlib.sha256(rel.encode()).hexdigest()[:16];report=OUT/('native_'+key+'.json')
 if report.exists():continue
 source=ROOT/rel;before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source))
 names=[m.name for m in bpy.data.meshes];geo=geometry(names);weights=skin();actions=base.actions();rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
 s=bpy.context.scene;frame=s.frame_current;s.frame_set(1);bpy.context.view_layer.update();changed=configure(s);s.frame_set(frame)
 row={'file':rel,'before_sha256':before,'sha256':before,'changed':changed}
 if changed:
  target=OUT/'Files'/rel;target.parent.mkdir(parents=True,exist_ok=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
  bpy.ops.wm.open_mainfile(filepath=str(target))
  assert geometry(names)==geo and skin()==weights and base.actions()==actions,rel
  assert {o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}==rigs,rel
  assert bpy.data.objects['Pants']['KneeClothRevision']=='2026-10-30-lower-leg'
  row.update(sha256=sha(target),reopened_preservation_passed=True)
 report.write_text(json.dumps(row,indent=2));print('PANTS_CLOTH_STAGED',rel,changed,flush=True)
print('PANTS_CLOTH_STAGE_COMPLETE',os.environ.get('OPENSTANCE_STAGE_SLOT','0'),flush=True)


