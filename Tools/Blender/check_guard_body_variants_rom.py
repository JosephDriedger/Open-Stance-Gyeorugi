"""Local ankle/toe stress checks on staged body-specific guard variants."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
OUT=review.ROOT/'Resources/Models/FinalRefinement'/('GuardBodyVariantsV7' if '--v7' in sys.argv else 'GuardBodyVariantsV6' if '--v6' in sys.argv else 'GuardBodyVariantsV5' if '--v5' in sys.argv else 'GuardBodyVariantsV4' if '--v4' in sys.argv else 'GuardBodyVariantsV3' if '--v3' in sys.argv else 'GuardBodyVariantsV2')
report=dict(production_installed=False,presets=[],scope='25 static local-axis stress poses per style and body. 1 mm vertex-clearance tolerance; no anatomical-limit, swept-collision, or whole-body acceptance.')
parity='--parity' in sys.argv
visible='--visible' in sys.argv
report_name='surface_validation.json' if visible else 'parity_validation.json' if parity else 'rom_validation.json'
directions=[Vector(d).normalized() for d in ((1,.317,.193),(-.219,1,.371),(.311,.193,1),(-1,.173,.293),(.271,-1,.133))]
def containment(tree,p):
    votes=[]
    for direction in directions:
        origin=p.copy();count=0
        for _ in range(100):
            hit,normal,index,distance=tree.ray_cast(origin,direction)
            if hit is None:break
            count+=1;origin=hit+direction*.000001
        if count==100:return None
        votes.append(count%2)
    return bool(votes[0]) if len(set(votes))==1 else None
def winding(points,triangles,p):
    tri=np.asarray(points)[np.asarray(triangles)]-np.asarray(p)
    a,b,c=tri[:,0],tri[:,1],tri[:,2];la=np.linalg.norm(a,axis=1);lb=np.linalg.norm(b,axis=1);lc=np.linalg.norm(c,axis=1)
    determinant=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=la*lb*lc+np.einsum('ij,ij->i',a,b)*lc+np.einsum('ij,ij->i',b,c)*la+np.einsum('ij,ij->i',c,a)*lb
    return abs(float(np.sum(2*np.arctan2(determinant,denominator)))/(4*math.pi))
cases=[('Rest',None,'X',0)]+[(f'{b}_{axis}_{a}',b,axis,a) for b in ('foot_l','foot_r','ball_l','ball_r') for axis in 'XYZ' for a in (-25,25)]
def geometry(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    pts=[obj.matrix_world@v.co for v in mesh.vertices];tris=[tuple(t.vertices) for t in mesh.loop_triangles];ev.to_mesh_clear();return pts,tris
for folder in sorted(p for p in OUT.iterdir() if p.is_dir()):
    source=folder/'Gameplay_High_Staged.blend'
    if not source.exists():continue
    bpy.ops.wm.open_mainfile(filepath=str(source));s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+folder.name];r.data.pose_position='POSE'
    assert len([o for o in s.objects if o.type=='ARMATURE'])==1,folder.name
    probe=bpy.data.objects['Body'].copy();probe.data=probe.data.copy();s.collection.objects.link(probe);probe.hide_render=True
    for mod in list(probe.modifiers):
        if mod.type=='MASK':probe.modifiers.remove(mod)
    rows=[]
    for label,bone,axis,angle in cases:
        for style,name in enumerate(('FootGuards','FootGuards_PaddedInstep')):
            r['FootGuardsStyle']=style;review.build.refresh(r)
            for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
            if bone:r.pose.bones[bone].matrix_basis=Matrix.Rotation(math.radians(angle),4,axis)
            bpy.context.view_layer.update();bp,bt=geometry(probe);gp,gt=geometry(bpy.data.objects[name]);tree=BVHTree.FromPolygons(bp,bt,all_triangles=True);ds=[]
            false_positives=0;ambiguous=0;actual_inside=0;winding_checks=[]
            for p in gp:
                hit,n,_,_=tree.find_nearest(p);d=(p-hit).dot(n);ds.append(d)
                if parity and d<-.001:
                    inside=containment(tree,p)
                    if inside is None:
                        value=winding(bp,bt,p);winding_checks.append(value)
                        if value<.1:inside=False
                        elif value>.9:inside=True
                    if inside is None:ambiguous+=1
                    elif inside:actual_inside+=1
                    else:false_positives+=1
            own=BVHTree.FromPolygons(gp,gt,all_triangles=True);overlap=sum(a<b and not set(gt[a])&set(gt[b]) for a,b in own.overlap(own))
            row=dict(pose=label,style=style,minimum_m=min(ds),inside_1mm=actual_inside if parity else sum(d<-.001 for d in ds),self_overlap_pairs=overlap)
            if parity:row.update(signed_candidates=sum(d<-.001 for d in ds),confirmed_outside=false_positives,ambiguous=ambiguous,winding_cross_checks=winding_checks,body_surface_overlap_pairs=len(tree.overlap(own)))
            if visible:
                vp,vt=geometry(bpy.data.objects['Body']);visible_tree=BVHTree.FromPolygons(vp,vt,all_triangles=True)
                row['visible_body_overlap_pairs']=len(visible_tree.overlap(own))
            rows.append(row)
    worst=min(rows,key=lambda x:x['minimum_m'])
    passed=all(x['inside_1mm']==0 and x['self_overlap_pairs']==0 and x.get('ambiguous',0)==0 and x.get('visible_body_overlap_pairs',0)==0 for x in rows)
    report['presets'].append(dict(preset=folder.name,passed=passed,worst=worst,checks=rows))
    (OUT/report_name).write_text(json.dumps(report,indent=2));print('ROM',folder.name,passed,flush=True)
report['passed']=len(report['presets'])==9 and all(x['passed'] for x in report['presets'])
if parity:report['scope']+=' Signed-negative candidates cross-checked by five parity rays, with solid-angle winding fallback (<0.1 outside, >0.9 inside) when rays disagree; unresolved samples fail. Full-body surface overlaps are reported separately; visible-body overlaps fail the --visible check.'
(OUT/report_name).write_text(json.dumps(report,indent=2))
