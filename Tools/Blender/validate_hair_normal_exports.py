import bpy,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as a
out=a.ROOT/'Resources/Models/FinalRefinement/HairNormalDelivery';review=out/'ExportReview';review.mkdir(exist_ok=True)
rows=[]
for report in sorted(out.glob('fbx_*.json')):
    row=json.loads(report.read_text())
    if not row['changed_geometry_ids'] or '/MotionBuilder/' in row['file']:continue
    path=out/'Files'/row['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True)
    rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'];assert len(rigs)==1 and len(rigs[0].data.bones) in [25,341],row['file']
    hair=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'Scalp_Coverage' in o.name];assert hair,row['file']
    for o in hair:
        center=sum((v.co for v in o.data.vertices),o.data.vertices[0].co*0)/len(o.data.vertices)
        score=sum((p.center-center).dot(p.normal)*p.area for p in o.data.polygons)
        assert score>0,(row['file'],o.name,score)
        assert all(v.groups and abs(sum(g.weight for g in v.groups)-1)<.003 for v in o.data.vertices)
    rows.append({'file':row['file'],'bones':len(rigs[0].data.bones),'outward_hair_normals':True,'normalized_hair_weights':True})
    print('FBX_REIMPORT_PASSED',row['file'],flush=True)
for kind in ['Male_Lean','Female_Athletic','Female_Strong']:
    for gear in ['Dobok','Sparring']:
        native=a.ROOT/'Resources/Models/CharacterSuite'/kind/'Gameplay_High.blend'
        bpy.ops.wm.open_mainfile(filepath=str(native));s=bpy.context.scene;s.cycles.samples=16
        for o in list(s.objects):
            if o.type in ['MESH','ARMATURE'] and o.name not in ['Ground','Mat','Floor']:bpy.data.objects.remove(o,do_unlink=True)
        path=out/'Files/Resources/Models/CharacterSuite'/kind/('Gameplay_High_'+gear+'.fbx')
        bpy.ops.import_scene.fbx(filepath=str(path));r=next(o for o in s.objects if o.type=='ARMATURE');scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
        a.render(s,r,scale,review,kind+'_'+gear,(.5,1,1.84),(0,0,1.64),.54,600,650)
(out/'export_validation.json').write_text(json.dumps({'passed':True,'files':rows,'rendered_presets':['Male_Lean','Female_Athletic','Female_Strong'],'renders':6},indent=2))
