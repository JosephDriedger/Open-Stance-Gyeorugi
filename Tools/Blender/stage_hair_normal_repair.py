"""Stage only scalp winding corrections, verifying rigs, actions, shape keys and UVs."""
import bpy,sys,json,hashlib
from array import array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from fit_hair_fibers_to_coverage import outward_coverage
ROOT=base.ROOT;OUT=ROOT/'Resources/Models/FinalRefinement/HairNormalDelivery';OUT.mkdir(exist_ok=True)
sources=[r for r in json.loads((OUT.parent/'current_assets.json').read_text())['files'] if r['file'].endswith('.blend')]
dummy=ROOT/'Resources/Models/Animation/DummyMotionTests/delivery_validation.json'
for row in json.loads(dummy.read_text())['rows']:
    sources.append({'file':Path(row['file']).relative_to(ROOT).as_posix(),'sha256':row['sha256']})
batch=int(sys.argv[-1])
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8388608),b''):h.update(block)
    return h.hexdigest()
def coordinates():
    h=hashlib.sha256()
    for o in sorted(bpy.data.objects,key=lambda o:o.name):
        if o.type!='MESH':continue
        h.update(o.name.encode())
        arrays=[o.data.vertices]+([k.data for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [])
        for values in arrays:
            data=array('f',[0])*(len(values)*3);values.foreach_get('co',data);h.update(data.tobytes())
    return h.hexdigest()
def hair_uv():
    h=hashlib.sha256()
    for o in sorted(bpy.data.objects,key=lambda o:o.name):
        if o.type!='MESH' or not o.name.endswith('__Scalp_Coverage'):continue
        for layer in o.data.uv_layers:
            for polygon in o.data.polygons:
                corners=sorted((o.data.loops[i].vertex_index,tuple(layer.data[i].uv)) for i in polygon.loop_indices)
                h.update(repr(corners).encode())
    return h.hexdigest()
for index,row in enumerate(sources):
    if index%3!=batch:continue
    report=OUT/(hashlib.sha256(row['file'].encode()).hexdigest()[:16]+'.json')
    if report.exists():continue
    source=ROOT/row['file'];assert sha(source)==row['sha256'],source
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
    actions=base.actions();geo=coordinates();uv=hair_uv();changed=[]
    for scene in bpy.data.scenes:
        rig=next((o for o in scene.objects if o.type=='ARMATURE' and 'RIG_Body_' in o.name),None)
        if rig:changed+=outward_coverage(scene,rig)
    assert coordinates()==geo and hair_uv()==uv,'Repair altered coordinates or UV mapping'
    result={'file':row['file'],'before_sha256':row['sha256'],'changed_objects':changed,'coordinates_uv_rigs_actions_preserved':True}
    if changed:
        target=OUT/'Files'/row['file'];target.parent.mkdir(parents=True,exist_ok=True)
        for image in bpy.data.images:
            if image.source=='FILE' and image.filepath and not image.packed_file:image.pack()
        bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(target))
        assert coordinates()==geo and hair_uv()==uv and base.actions()==actions
        assert rigs=={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE'}
        result['sha256']=sha(target)
    else:result['sha256']=row['sha256']
    report.write_text(json.dumps(result,indent=2));print('NORMALS_STAGED',row['file'],len(changed),flush=True)
print('NORMALS_BATCH_COMPLETE',batch,flush=True)
