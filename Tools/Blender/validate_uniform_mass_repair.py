"""Reopen original and staged assets to verify the mass-only delivery."""
import bpy,sys,json,hashlib,array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import extend_garment_repairs as base
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Resources/Models/FinalRefinement/UniformMassDelivery'
baseline=json.loads((OUT.parent/'current_assets.json').read_text())
files=sorted((r for r in baseline['files'] if r['file'].endswith('.blend')),key=lambda r:r['file'])
batch=int(sys.argv[-1]);results=[]
def geometry():
    h=hashlib.sha256()
    for mesh in sorted(bpy.data.meshes,key=lambda m:m.name):
        h.update(mesh.name.encode());a=array.array('f',[0])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',a);h.update(a.tobytes())
        for p in mesh.polygons:h.update(str(tuple(p.vertices)).encode())
        if mesh.shape_keys:
            for key in mesh.shape_keys.key_blocks:
                h.update(key.name.encode());a=array.array('f',[0])*(len(key.data)*3);key.data.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
for row in files[batch::2]:
    rel=row['file'];key=hashlib.sha256(rel.encode()).hexdigest()[:16]
    report=json.loads((OUT/(key+'.json')).read_text())
    if not report['changes']:results.append({'file':rel,'unchanged':True});continue
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/rel))
    before_geometry=geometry();before_actions=base.actions()
    before_rigs={o.name:base.signature(o) for o in bpy.data.objects if o.type=='ARMATURE' and o.name.startswith('RIG_Body_')}
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Files'/rel))
    assert geometry()==before_geometry and base.actions()==before_actions,rel
    assert all(base.signature(bpy.data.objects[n])==signature for n,signature in before_rigs.items()),rel
    changes={r['object']:r for r in report['changes']};seen=set()
    for scene in bpy.data.scenes:
        bpy.context.window.scene=scene
        for o in list(scene.objects):
            if o.name not in changes or o.name in seen:continue
            seen.add(o.name);change=changes[o.name];cloth=next(m for m in o.modifiers if m.type=='CLOTH');value=o['GarmentMassKg']
            assert not cloth.point_cache.is_baked,(rel,o.name,'Old baked cloth cache must not be delivered with new mass settings')
            for factor in [1.0,1.5,1.0]:
                o['GarmentMassKg']=value*factor;o.update_tag();bpy.context.view_layer.update()
                assert abs(cloth.settings.mass*change['vertices']-value*factor)<1e-5,(rel,o.name,factor,cloth.settings.mass)
    assert seen==set(changes),rel
    results.append({'file':rel,'reopened_geometry_shape_keys_rigs_actions_preserved':True,'mass_controls_checked':len(seen)})
    print('MASS_REOPENED',rel,len(seen),flush=True)
(OUT/('reopen_validation_'+str(batch)+'.json')).write_text(json.dumps({'passed':True,'files':results},indent=2))
print('MASS_REOPEN_BATCH_COMPLETE',batch,len(results),flush=True)
