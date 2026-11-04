"""Rebuild redundant bind-pose metadata from SDK-validated skin bindings; repair zero normals only."""
import sys,json,hashlib,array,subprocess,copy
import numpy as np
import repair_fbx_hair_normals as f
from repair_fbx_uniform_geometry import polygons,set_array
ROOT=f.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/BindNormalsDelivery'

def fix_normals(g):
 if f.child(g,b'PolygonVertexIndex') is None:return 0
 raw,ids,faces=polygons(g);points=np.asarray(f.child(g,b'Vertices').props[0]).reshape(-1,3)
 count=0
 for layer in g.elems:
  if layer.id!=b'LayerElementNormal':continue
  elem=f.child(layer,b'Normals');normals=np.asarray(elem.props[0]).reshape(-1,3).copy()
  bad=np.linalg.norm(normals,axis=1)<1e-8
  if not np.any(bad):continue
  face_normals=[];smooth=np.zeros_like(points);fallback=np.zeros_like(points)
  for p in faces:
   q=points[ids[p]];n=sum((np.cross(q[j]-q[0],q[j+1]-q[0]) for j in range(1,len(q)-1)),np.zeros(3))
   length=np.linalg.norm(n);unit=n/length if length>1e-20 else np.zeros(3)
   face_normals.append(unit)
   for vi in ids[p]:smooth[vi]+=n;fallback[vi]=unit if length>1e-20 else fallback[vi]
  lengths=np.linalg.norm(smooth,axis=1);good=lengths>1e-20;smooth[good]/=lengths[good,None];smooth[~good]=fallback[~good]
  mapping=f.child(layer,b'MappingInformationType').props[0]
  ix=f.child(layer,b'NormalsIndex');indices=np.asarray(ix.props[0]).copy() if ix is not None else np.arange(len(normals))
  vertex_mapping=mapping in (b'ByVertice',b'ByVertex')
  assert vertex_mapping or mapping==b'ByPolygonVertex',mapping
  replacements={}
  if vertex_mapping:
   for vi,ni in enumerate(indices):
    if bad[ni] and np.linalg.norm(smooth[vi])>.5:replacements[vi]=smooth[vi]
  else:
   for p,n in zip(faces,face_normals):
    for corner in p:
     if not bad[indices[corner]]:continue
     candidate=smooth[ids[corner]]
     if np.linalg.norm(candidate)<.5:candidate=n
     assert np.linalg.norm(candidate)>.5,('No valid surface normal',g.props[1],int(corner))
     replacements[int(corner)]=candidate
  if ix is not None:
   appended=[]
   for position,n in replacements.items():indices[position]=len(normals)+len(appended);appended.append(n)
   if appended:
    set_array(elem,np.vstack([normals,appended]));set_array(ix,indices)
    w=f.child(layer,b'NormalsW')
    if w is not None:set_array(w,np.r_[np.asarray(w.props[0]),np.ones(len(appended))])
  else:
   for position,n in replacements.items():normals[position]=n
   set_array(elem,normals)
  count+=len(replacements)
 return count

def run(rel,delivery=None):
 out=delivery or OUT
 out.mkdir(parents=True,exist_ok=True);key=hashlib.sha256(rel.encode()).hexdigest()[:16]
 source=ROOT/rel;target=out/'Files'/rel;report_path=out/(key+'.json')
 audit=out/(key+'_pose.json')
 result=subprocess.run([str(ROOT/'Saved/Tools/audit_bind_pose.exe'),str(source),str(audit)],capture_output=True,text=True)
 assert result.returncode==0,(rel,result.stdout,result.stderr)
 pose= json.loads(audit.read_text());assert pose['failures']==0 and pose['max_cluster_conflict']<1e-4,(rel,pose['max_cluster_conflict'])
 tree,version=f.parse_fbx.parse(str(source));objects=f.child(tree,b'Objects')
 models={n.props[1].split(b'\x00')[0].decode():n.props[0] for n in objects.elems if n.id==b'Model'}
 assert len(models)==sum(n.id==b'Model' for n in objects.elems),'Ambiguous model names'
 pose_nodes=[]
 for row in pose['matrices']:
  assert row['name'] in models,row['name']
  node=f.parse_fbx.FBXElem(b'PoseNode',[],bytearray(),[])
  node.elems.extend([f.parse_fbx.FBXElem(b'Node',[models[row['name']]],bytearray(b'L'),[]),f.parse_fbx.FBXElem(b'Matrix',[array.array('d',row['matrix'])],bytearray(b'd'),[])])
  pose_nodes.append(node)
 original={n.props[0]:f.digest(n) for n in objects.elems if n.props};changed=set();normal_rows=[];pose_count=0
 for n in objects.elems:
  if n.id==b'Pose' and n.props[-1]==b'BindPose':
   n.elems[:]=[e for e in n.elems if e.id!=b'PoseNode']+copy.deepcopy(pose_nodes)
   f.child(n,b'NbPoseNodes').props[0]=len(pose_nodes);changed.add(n.props[0]);pose_count+=1
  elif n.id==b'Geometry':
   preserved=[f.digest(e) for e in n.elems if e.id!=b'LayerElementNormal']
   count=fix_normals(n)
   assert [f.digest(e) for e in n.elems if e.id!=b'LayerElementNormal']==preserved
   if count:changed.add(n.props[0]);normal_rows.append({'geometry':n.props[1].split(b'\x00')[0].decode(),'zero_normals_replaced':count})
 assert pose_count>0,rel
 assert all(f.digest(n)==original[n.props[0]] for n in objects.elems if n.props and n.props[0] not in changed)
 for tag,value in [(b'FileId',f.encode_bin._FILE_ID),(b'CreationTime',f.encode_bin._TIME_ID)]:
  e=f.child(tree,tag)
  if e is not None:e.props[0]=value
 expected=f.digest(tree);target.parent.mkdir(parents=True,exist_ok=True);f.encode_bin.write(str(target),f.encode(tree),version)
 reopened,_=f.parse_fbx.parse(str(target));assert f.digest(reopened)==expected
 reopen_audit=out/(key+'_reopen.json')
 checked=subprocess.run([str(ROOT/'Saved/Tools/audit_bind_pose.exe'),str(target),str(reopen_audit)],capture_output=True,text=True)
 assert checked.returncode==0,(rel,checked.stdout,checked.stderr)
 saved=json.loads(reopen_audit.read_text());assert saved['existing_pose_failures']==0,rel
 report={'file':rel,'before_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
 'bind_poses_rebuilt':pose_count,'pose_nodes':len(pose_nodes),'normal_repairs':normal_rows,'joint_skin_control_animation_nodes_preserved':True,'sdk_pose_candidate_passed':True,'saved_pose_checks':saved['existing_pose_checks'],'saved_pose_failures':saved['existing_pose_failures']}
 report_path.write_text(json.dumps(report,indent=2));print('BIND_NORMALS_STAGED',rel,pose_count,normal_rows,flush=True)
 return target,report

if __name__=='__main__':
 for rel in sys.argv[1:]:run(rel)

