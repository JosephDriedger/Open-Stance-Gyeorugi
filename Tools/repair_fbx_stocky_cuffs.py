"""Apply the native cuff clearance without re-exporting MotionBuilder controls."""
import sys,json,hashlib,numpy as np
import repair_fbx_hair_normals as f
from repair_fbx_uniform_geometry import set_array,polygons
from stocky_cuff_math import local_repair,transform_normals
ROOT=f.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/StockyCuffDelivery'
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def run(rel):
 key=hashlib.sha256(rel.encode()).hexdigest()[:16];source=ROOT/rel
 audit=json.loads((ROOT/'Resources/Models/FinalRefinement/BindNormalsDelivery'/(key+'_pose.json')).read_text())
 tree,version=f.parse_fbx.parse(str(source));objects=f.child(tree,b'Objects');settings={n.props[0]:n.props[-1] for n in f.child(f.child(tree,b'GlobalSettings'),b'Properties70').elems}
 assert (settings[b'UpAxis'],settings[b'CoordAxis'],settings[b'FrontAxis'])==(1,0,2)
 unit=settings[b'UnitScaleFactor']/100
 conversion=np.array([[1,0,0],[0,0,-1],[0,1,0]])*unit
 matrices={r['name']:np.array(r['matrix']).reshape(4,4).T for r in audit['matrices']}
 def point(name):return conversion@matrices[name][:3,3]
 axes=np.array([[point(b+'_'+side) for b in ('calf','foot')] for side in 'lr']);scale=point('head')[2]/1.578
 models={n.props[0]:n for n in objects.elems if n.id==b'Model'}
 parents={n.props[1]:n.props[2] for n in f.child(tree,b'Connections').elems if n.props[0]==b'OO' and n.props[2] in models}
 originals={n.props[0]:f.digest(n) for n in objects.elems if n.props};changed=set();rows=[]
 for g in objects.elems:
  if g.id!=b'Geometry' or g.props[-1]!=b'Mesh' or b'Pants' not in g.props[1]:continue
  model=models[parents[g.props[0]]];name=model.props[1].split(b'\x00')[0].decode();matrix=matrices[name].copy();matrix[:3,:]=conversion@matrix[:3,:]
  before=np.asarray(f.child(g,b'Vertices').props[0]).reshape(-1,3);after,transforms=local_repair(before,matrix,axes,scale)
  raw,ids,faces=polygons(g)
  preserved=[f.digest(n) for n in g.elems if n.id not in (b'Vertices',b'LayerElementNormal')]
  for layer in g.elems:
   if layer.id!=b'LayerElementNormal':continue
   mapping=f.child(layer,b'MappingInformationType');reference=f.child(layer,b'ReferenceInformationType');normal=f.child(layer,b'Normals')
   values=np.asarray(normal.props[0]).reshape(-1,3);kind=mapping.props[0]
   if kind==b'ByPolygonVertex':indices=np.arange(len(ids))
   elif kind in (b'ByVertice',b'ByVertex'):indices=ids
   elif kind==b'AllSame':indices=np.zeros(len(ids),dtype=int)
   elif kind==b'ByPolygon':indices=np.concatenate([np.full(len(face),i) for i,face in enumerate(faces)])
   else:raise AssertionError(kind)
   if reference.props[0] in (b'IndexToDirect',b'Index'):indices=np.asarray(f.child(layer,b'NormalsIndex').props[0])[indices]
   adjusted=transform_normals(values[indices],ids,transforms)
   mapping.props[0]=b'ByPolygonVertex';reference.props[0]=b'Direct';set_array(normal,adjusted)
   layer.elems[:]=[n for n in layer.elems if n.id!=b'NormalsIndex']
   w=f.child(layer,b'NormalsW')
   if w is not None:set_array(w,np.ones(len(ids)))
  set_array(f.child(g,b'Vertices'),after)
  assert [f.digest(n) for n in g.elems if n.id not in (b'Vertices',b'LayerElementNormal')]==preserved
  changed.add(g.props[0]);rows.append({'mesh':name,'vertices_changed':int(np.sum(np.linalg.norm(after-before,axis=1)>1e-9))})
 assert rows,rel
 assert all(f.digest(n)==originals[n.props[0]] for n in objects.elems if n.props and n.props[0] not in changed)
 expected=f.digest(tree);target=OUT/'Files'/rel;target.parent.mkdir(parents=True,exist_ok=True);f.encode_bin.write(str(target),f.encode(tree),version)
 saved,_=f.parse_fbx.parse(str(target));assert f.digest(saved)==expected
 report={'file':rel,'before_sha256':sha(source),'sha256':sha(target),'meshes':rows,'non_geometry_nodes_preserved':True,'topology_uv_skin_shapes_preserved':True,'reopened_preservation_passed':True}
 (OUT/('fbx_'+key+'.json')).write_text(json.dumps(report,indent=2));print('STOCKY_CUFF_FBX_STAGED',rel,flush=True)
if __name__=='__main__':
 files=[r['file'] for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if 'Stocky' in r['file'] and r['file'].endswith('.fbx')]
 OUT.mkdir(exist_ok=True);(OUT/'fbx_inputs.json').write_text(json.dumps(files,indent=2))
 for rel in files:run(rel)
