"""Correct scalp winding in FBX without rebuilding skeletons, controls or animation.

Uses Blender's binary reader/writer and verifies the entire parsed output tree
against the intended result. Only scalp polygon/layer arrays may change.
"""
import sys,types,json,hashlib,array
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('_hair_fbx');pkg.__path__=[str(ROOT/'Saved/Tools/Blender522/5.2/scripts/addons_core/io_scene_fbx')];sys.modules[pkg.__name__]=pkg
from _hair_fbx import parse_fbx,encode_bin
OUT=ROOT/'Resources/Models/FinalRefinement/HairNormalDelivery'

def child(node,name):return next((e for e in node.elems if e.id==name),None)
def digest(node):
    h=hashlib.sha256()
    def walk(n):
        h.update(n.id);h.update(bytes(n.props_type));h.update(str(len(n.props)).encode())
        for value in n.props:
            if isinstance(value,array.array):h.update(value.tobytes())
            elif isinstance(value,bytes):h.update(value)
            else:h.update(repr(value).encode())
            h.update(b'\0property\0')
        for e in n.elems:walk(e)
        h.update(b'\0end\0')
    walk(node);return h.hexdigest()
def encode(node):
    result=encode_bin.FBXElem(node.id)
    methods={'Y':'add_int16','C':'add_char','B':'add_bool','Z':'add_int8','I':'add_int32','F':'add_float32','D':'add_float64','L':'add_int64','R':'add_bytes','S':'add_string','f':'add_float32_array','d':'add_float64_array','l':'add_int64_array','i':'add_int32_array','b':'add_bool_array','c':'add_byte_array'}
    for kind,value in zip(node.props_type,node.props):getattr(result,methods[chr(kind)])(value)
    result.elems=[encode(e) for e in node.elems];return result
def reorder(element,permutation,stride=1,negate=False):
    old=element.props[0];values=np.asarray(old).reshape((-1,stride))
    if permutation is not None:values=values[permutation]
    if negate:values=-values
    element.props[0]=array.array(old.typecode,values.ravel().tolist())
def repair(geometry):
    vertex=child(geometry,b'Vertices');indices=child(geometry,b'PolygonVertexIndex')
    if vertex is None or indices is None:return False
    points=np.asarray(vertex.props[0]).reshape((-1,3));raw=np.asarray(indices.props[0]);ids=np.where(raw<0,-raw-1,raw)
    polygons=[];start=0;score=0.;center=points.mean(axis=0)
    for end in np.flatnonzero(raw<0):
        corners=np.arange(start,end+1);polygon=points[ids[corners]]
        for j in range(1,len(polygon)-1):score+=np.dot(np.cross(polygon[j]-polygon[0],polygon[j+1]-polygon[0]),polygon[[0,j,j+1]].mean(axis=0)-center)
        polygons.append(corners);start=end+1
    assert start==len(raw)
    if score>=0:return False
    permutation=np.concatenate([p[::-1] for p in polygons]);inverse=np.empty(len(raw),dtype=int);inverse[permutation]=np.arange(len(raw))
    new=ids[permutation].copy()
    for p in polygons:new[p[-1]]=-new[p[-1]]-1
    indices.props[0]=array.array(indices.props[0].typecode,new.tolist())
    edges=child(geometry,b'Edges')
    if edges:
        next_corner=np.empty(len(raw),dtype=int)
        for p in polygons:next_corner[p]=np.roll(p,-1)
        edges.props[0]=array.array(edges.props[0].typecode,inverse[next_corner[np.asarray(edges.props[0])]].tolist())
    for layer in geometry.elems:
        if not layer.id.startswith(b'LayerElement'):continue
        mapping=child(layer,b'MappingInformationType');reference=child(layer,b'ReferenceInformationType')
        if mapping is None or reference is None:continue
        mode=mapping.props[0];indexed=reference.props[0] in [b'IndexToDirect',b'Index']
        for data in layer.elems:
            if not data.props or not isinstance(data.props[0],array.array):continue
            normal=data.id==b'Normals'
            if mode==b'ByPolygonVertex':
                is_index=data.id.endswith(b'Index') or data.id in [b'Materials']
                if indexed and not is_index:
                    if normal:reorder(data,None,3,True)
                else:
                    assert len(data.props[0])%len(raw)==0,(layer.id,data.id)
                    reorder(data,permutation,len(data.props[0])//len(raw),normal)
            elif normal:reorder(data,None,3,True)
    return True

def run(relative):
    source=ROOT/relative;baseline=json.loads((OUT.parent/'current_assets.json').read_text())['files'];before=next(r['sha256'] for r in baseline if r['file']==relative)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    tree,version=parse_fbx.parse(str(source));changed=[];objects=child(tree,b'Objects')
    untouched={i:digest(node) for i,node in enumerate(objects.elems)}
    for i,node in enumerate(objects.elems):
        if node.id==b'Geometry' and any(isinstance(p,bytes) and b'Scalp_Coverage' in p for p in node.props):
            if repair(node):changed.append(i)
    assert all(digest(node)==untouched[i] for i,node in enumerate(objects.elems) if i not in changed)
    result={'file':relative,'before_sha256':before,'changed_geometry_ids':[objects.elems[i].props[0] for i in changed],'all_other_nodes_preserved':True}
    if changed:
        target=OUT/'Files'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        # Blender's writer normalizes these two container identifiers. Object
        # IDs, takes, connections, characterization and all scene nodes remain.
        for tag,value in [(b'FileId',encode_bin._FILE_ID),(b'CreationTime',encode_bin._TIME_ID)]:
            element=child(tree,tag)
            if element is not None:element.props[0]=value
        expected=digest(tree);encode_bin.write(str(target),encode(tree),version)
        reopened,_=parse_fbx.parse(str(target))
        if digest(reopened)!=expected:
            def difference(a,b,path=''):
                if digest(a)==digest(b):return
                path+='/'+a.id.decode(errors='replace')
                if a.id!=b.id or a.props_type!=b.props_type or len(a.elems)!=len(b.elems):raise AssertionError(('Node structure changed',path))
                for i,(av,bv) in enumerate(zip(a.props,b.props)):
                    equal=av==bv
                    if not equal:raise AssertionError(('Property changed',path,i,type(av).__name__,type(bv).__name__,repr(av)[:80],repr(bv)[:80]))
                for ac,bc in zip(a.elems,b.elems):difference(ac,bc,path)
            difference(tree,reopened)
            raise AssertionError('FBX digest representation changed')
        result['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        result['container_identifiers_normalized']=['FileId','CreationTime']
    else:result['sha256']=before
    report=OUT/('fbx_'+hashlib.sha256(relative.encode()).hexdigest()[:16]+'.json');report.write_text(json.dumps(result,indent=2))
    print('FBX_NORMALS_STAGED',relative,len(changed),flush=True)
if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    paths=sys.argv[1:]
    if paths and paths[0]=='--all':
        batch=int(paths[1]);paths=[r['file'] for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if r['file'].endswith('.fbx')][batch::2]
    for relative in paths:
        report=OUT/('fbx_'+hashlib.sha256(relative.encode()).hexdigest()[:16]+'.json')
        if report.exists():continue
        run(relative)
