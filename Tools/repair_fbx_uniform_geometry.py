"""Mesh-only FBX repair. Preserve skinning, controls, takes and all non-geometry nodes."""
import array,json,hashlib,sys
from pathlib import Path
import numpy as np
import repair_fbx_hair_normals as f
ROOT=f.ROOT
OUT=ROOT/'Resources/Models/FinalRefinement/UniformGeometryDelivery'

def set_array(node,values):
    node.props[0]=array.array(node.props[0].typecode,np.asarray(values).ravel().tolist())

def polygons(g):
    raw=np.asarray(f.child(g,b'PolygonVertexIndex').props[0]);ids=np.where(raw<0,-raw-1,raw)
    ends=np.flatnonzero(raw<0)+1;starts=np.r_[0,ends[:-1]]
    return raw,ids,[np.arange(a,b) for a,b in zip(starts,ends)]

def repair(g,name,has_shapes,metres_per_unit):
    raw,ids,faces=polygons(g);points=np.asarray(f.child(g,b'Vertices').props[0]).reshape(-1,3)
    result={}
    if name.split('.')[0]=='Body' and not has_shapes:
        valid=[]
        for p in faces:
            q=points[ids[p]]
            area=sum(np.linalg.norm(np.cross(q[j]-q[0],q[j+1]-q[0])) for j in range(1,len(q)-1))
            valid.append(area>1e-12)
        if not all(valid):
            keep_faces=np.flatnonzero(valid);keep_corners=np.concatenate([faces[i] for i in keep_faces])
            inverse=np.full(len(raw),-1);inverse[keep_corners]=np.arange(len(keep_corners))
            edge=f.child(g,b'Edges');keep_edges=None;edge_count=0
            if edge is not None:
                old=np.asarray(edge.props[0]);edge_count=len(old);keep_edges=np.flatnonzero(inverse[old]>=0)
                set_array(edge,inverse[old[keep_edges]])
            for layer in g.elems:
                if not layer.id.startswith(b'LayerElement'):continue
                mapping=f.child(layer,b'MappingInformationType');ref=f.child(layer,b'ReferenceInformationType')
                if mapping is None:continue
                mode=mapping.props[0];indexed=ref and ref.props[0] in (b'IndexToDirect',b'Index')
                choice,count=(keep_corners,len(raw)) if mode==b'ByPolygonVertex' else (keep_faces,len(faces)) if mode==b'ByPolygon' else (keep_edges,edge_count) if mode==b'ByEdge' else (None,0)
                if choice is None:continue
                for data in layer.elems:
                    if not data.props or not isinstance(data.props[0],array.array):continue
                    is_index=data.id.endswith(b'Index') or data.id in (b'Materials',b'Smoothing')
                    if indexed and not is_index:continue
                    assert len(data.props[0])%count==0,(name,data.id)
                    values=np.asarray(data.props[0]).reshape(count,-1)[choice]
                    set_array(data,values)
            set_array(f.child(g,b'PolygonVertexIndex'),raw[keep_corners])
            result['removed_zero_area_faces']=len(faces)-len(keep_faces)
            raw,ids,faces=polygons(g)
    if name.split('.')[0] in ('Jacket','Pants','Jacket_WhiteVNeck'):
        layers=[e for e in g.elems if e.id==b'LayerElementUV']
        if layers:
            layer=layers[0];uv=f.child(layer,b'UV');old=np.asarray(uv.props[0]).reshape(-1,2)
            if len(np.unique(old,axis=0))<3 or np.ptp(old,axis=0).max()<1e-5:
                physical=points*metres_per_unit
                assert .1<np.ptp(physical,axis=0).max()<3,(name,'unexpected geometry units',np.ptp(physical,axis=0))
                values=np.zeros((len(raw),2))
                for p in faces:
                    q=physical[ids[p]]
                    normal=sum((np.cross(q[j]-q[0],q[j+1]-q[0]) for j in range(1,len(q)-1)),np.zeros(3))
                    axis=int(np.argmax(np.abs(normal)));dims=[i for i in range(3) if i!=axis]
                    values[p]=q[:,dims]/.05
                set_array(uv,values)
                index=f.child(layer,b'UVIndex')
                assert index is not None,'Expected indexed UVs'
                set_array(index,np.arange(len(raw)))
                f.child(layer,b'MappingInformationType').props[0]=b'ByPolygonVertex'
                f.child(layer,b'ReferenceInformationType').props[0]=b'IndexToDirect'
                result['fabric_uv']='5 cm dominant-plane fabric coordinates; replaces collapsed atlas coordinates'
    return result

def run(rel):
    src=ROOT/rel;before=hashlib.sha256(src.read_bytes()).hexdigest()
    tree,version=f.parse_fbx.parse(str(src));objects=f.child(tree,b'Objects');nodes={n.props[0]:n for n in objects.elems if n.props}
    names={};shapes=set();models={};parents={}
    for c in f.child(tree,b'Connections').elems:
        if len(c.props)<3:continue
        a,b=c.props[1:3]
        if a not in nodes or b not in nodes:continue
        if nodes[a].id==b'Geometry' and nodes[b].id==b'Model':
            names[a]=nodes[b].props[1].split(b'\x00')[0].decode();models[a]=b
        if nodes[a].id==b'Model' and nodes[b].id==b'Model':parents[a]=b
        if nodes[a].id==b'Deformer' and nodes[b].id==b'Geometry' and nodes[a].props[-1]==b'BlendShape':shapes.add(b)
    original={n.props[0]:f.digest(n) for n in objects.elems if n.props};changed={}
    for ident,name in names.items():
        g=nodes[ident]
        if f.child(g,b'PolygonVertexIndex') is None:continue
        settings=f.child(f.child(tree,b'GlobalSettings'),b'Properties70')
        unit=next((float(p.props[-1])*.01 for p in settings.elems if p.props[0]==b'UnitScaleFactor'),.01)
        scale=np.ones(3)*unit;model=models[ident];seen=set()
        while model in nodes:
            assert model not in seen,'Cyclic model parenting';seen.add(model)
            props=f.child(nodes[model],b'Properties70')
            if props:
                for p in props.elems:
                    if p.props[0]==b'Lcl Scaling':scale*=np.asarray(p.props[-3:],dtype=float)
            if model not in parents:break
            model=parents[model]
        result=repair(g,name,ident in shapes,scale)
        if result:changed[ident]={'mesh':name,**result}
    assert all(f.digest(n)==original[n.props[0]] for n in objects.elems if n.props and n.props[0] not in changed)
    report={'file':rel,'before_sha256':before,'changes':list(changed.values()),'non_geometry_nodes_preserved':True}
    if changed:
        target=OUT/'Files'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        for tag,value in [(b'FileId',f.encode_bin._FILE_ID),(b'CreationTime',f.encode_bin._TIME_ID)]:
            e=f.child(tree,tag)
            if e is not None:e.props[0]=value
        expected=f.digest(tree);f.encode_bin.write(str(target),f.encode(tree),version)
        reopened,_=f.parse_fbx.parse(str(target));assert f.digest(reopened)==expected,rel
        report['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    else:report['sha256']=before
    OUT.mkdir(exist_ok=True);(OUT/('fbx_'+hashlib.sha256(rel.encode()).hexdigest()[:16]+'.json')).write_text(json.dumps(report,indent=2))
    print('GEOMETRY_STAGED',rel,len(changed),flush=True)

if __name__=='__main__':
    for rel in sys.argv[1:]:run(rel)
