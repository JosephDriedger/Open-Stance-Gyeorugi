"""Stage mass-only native-file repairs; never overwrite source assets."""
import bpy,sys,json,hashlib,array,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
from normalize_uniform_cloth_mass import configure
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/UniformMassDelivery';OUT.mkdir(exist_ok=True)
baseline=json.loads((OUT.parent/'current_assets.json').read_text())
files=sorted((r for r in baseline['files'] if r['file'].endswith('.blend')),key=lambda r:r['file'])
batch=int(sys.argv[-1]);files=files[batch::2]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8388608),b''):h.update(block)
    return h.hexdigest()
def geometry():
    h=hashlib.sha256()
    for mesh in sorted(bpy.data.meshes,key=lambda m:m.name):
        h.update(mesh.name.encode());data=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',data);h.update(data.tobytes())
        if mesh.shape_keys:
            for key in mesh.shape_keys.key_blocks:
                h.update(key.name.encode());data=array.array('f',[0])*(len(key.data)*3);key.data.foreach_get('co',data);h.update(data.tobytes())
    return h.hexdigest()
for row in files:
    rel=row['file'];source=ROOT/rel;key=hashlib.sha256(rel.encode()).hexdigest()[:16];report_path=OUT/(key+'.json')
    if report_path.exists():
        existing=json.loads(report_path.read_text())
        if existing['changes'] or not rel.endswith('OpenStance_Characters_Workspace.blend'):continue
    assert sha(source)==row['sha256'],('Source changed since baseline',rel)
    bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_')]
    before_geometry=geometry();before_actions=base.actions();signatures={r.name:base.signature(r) for r in rigs}
    flags={r.name:bool(r.get('BlenderCloth',False)) for r in rigs if 'BlenderCloth' in r}
    for name in flags:bpy.data.objects[name]['BlenderCloth']=False;bpy.data.objects[name].update_tag()
    bpy.context.view_layer.update();changes_by_object={}
    for scene in list(bpy.data.scenes):
        bpy.context.window.scene=scene
        for change in configure(scene):changes_by_object[change['object']]=change
    bpy.context.window.scene=s;changes=list(changes_by_object.values())
    for name,value in flags.items():bpy.data.objects[name]['BlenderCloth']=value;bpy.data.objects[name].update_tag()
    bpy.context.view_layer.update()
    assert geometry()==before_geometry and base.actions()==before_actions,rel
    assert all(base.signature(bpy.data.objects[n])==signature for n,signature in signatures.items()),rel
    for change in changes:
        o=bpy.data.objects[change['object']];cloth=next(m for m in o.modifiers if m.type=='CLOTH')
        actual=cloth.settings.mass*change['vertices']
        assert abs(actual-change['total_mass_kg'])<1e-5,(rel,o.name,actual)
    output_hash=row['sha256']
    if changes:
        target=OUT/'Files'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
        output_hash=sha(target)
    assert sha(source)==row['sha256'],rel
    report={'file':rel,'before_sha256':row['sha256'],'sha256':output_hash,'changes':changes,
            'geometry_shape_keys_rigs_actions_preserved':True,'source_flags_preserved':flags,'production_installed':False}
    report_path.write_text(json.dumps(report,indent=2));print('MASS_STAGED',rel,len(changes),flush=True)
print('MASS_BATCH_COMPLETE',batch,len(files),flush=True)
