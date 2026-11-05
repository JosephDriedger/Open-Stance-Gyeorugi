"""Small paired shell/lining fit corrections over local ankle/toe stress poses."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
BASE=review.ROOT/'Resources/Models/FinalRefinement';both='--both-surfaces' in sys.argv
refine='--refine' in sys.argv
INPUT='GuardBodyVariantsV4' if refine else 'GuardBodyVariantsV3' if both else 'GuardBodyVariantsV2'
OUT=BASE/('GuardBodyVariantsV5' if refine else 'GuardBodyVariantsV4' if both else 'GuardBodyVariantsV3');OUT.mkdir(exist_ok=True)
prior=json.loads((BASE/INPUT/'rom_validation.json').read_text())
cases=[(None,'X',0)]+[(b,axis,a) for b in ('foot_l','foot_r','ball_l','ball_r') for axis in 'XYZ' for a in (-25,25)]
def geometry(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    pts=[obj.matrix_world@v.co for v in mesh.vertices];tris=[tuple(t.vertices) for t in mesh.loop_triangles];ev.to_mesh_clear();return pts,tris
report=dict(production_installed=False,presets=[])
for record in prior['presets']:
    kind=record['preset'];bpy.ops.wm.open_mainfile(filepath=str(BASE/INPUT/kind/'Gameplay_High_Staged.blend'))
    s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.data.pose_position='POSE';r['FootGuardsStyle']=0;review.build.refresh(r)
    guard=bpy.data.objects['FootGuards'];padded=bpy.data.objects['FootGuards_PaddedInstep']
    initial=[v.co.copy() for v in guard.data.vertices]
    weights=[[(guard.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in guard.data.vertices]
    probe=bpy.data.objects['Body'].copy();probe.data=probe.data.copy();s.collection.objects.link(probe);probe.hide_render=True
    for mod in list(probe.modifiers):
        if mod.type=='MASK':probe.modifiers.remove(mod)
    if not record['passed']:
        for iteration in range(8 if refine else 4):
            for bone,axis,angle in cases:
                for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
                if bone:r.pose.bones[bone].matrix_basis=Matrix.Rotation(math.radians(angle),4,axis)
                bpy.context.view_layer.update();bp,bt=geometry(probe);gp,_=geometry(guard);tree=BVHTree.FromPolygons(bp,bt,all_triangles=True)
                transforms={name:(r.matrix_world@r.pose.bones[name].matrix@r.data.bones[name].matrix_local.inverted()@r.matrix_world.inverted()@guard.matrix_world).to_3x3() for name in {n for row in weights for n,w in row}}
                for base in (0,6144):
                    deltas=np.zeros((48,64,3))
                    for i in range(3072):
                        inner=base+i+3072;hit,n,_,_=tree.find_nearest(gp[inner]);distance=(gp[inner]-hit).dot(n)
                        if both:
                            outer_hit,outer_n,_,_=tree.find_nearest(gp[base+i]);outer_d=(gp[base+i]-outer_hit).dot(outer_n)
                            if outer_d<distance:distance=outer_d;n=outer_n
                        if distance>=.0007:continue
                        blended=Matrix(((0,0,0),(0,0,0),(0,0,0)))
                        for name,w in weights[inner]:blended+=transforms[name]*w
                        if abs(blended.determinant())<1e-8:continue
                        delta=blended.inverted()@(n*min(.0015,.0007-distance))
                        deltas[i//64,i%64]=delta
                    for _ in range(2):
                        near=(np.roll(deltas,1,axis=1)+np.roll(deltas,-1,axis=1)+np.concatenate((deltas[:1],deltas[:-1]))+np.concatenate((deltas[1:],deltas[-1:])))/4
                        deltas=.7*deltas+.3*near
                    for i in range(3072):
                        delta=Vector(deltas[i//64,i%64]);inner=base+i+3072
                        if (guard.data.vertices[inner].co+delta-initial[inner]).length>.008:continue
                        for obj in (guard,padded):
                            obj.data.vertices[base+i].co+=delta;obj.data.vertices[inner].co+=delta
                guard.data.update();padded.data.update();guard.update_tag();padded.update_tag()
            print('FIT',kind,iteration,flush=True)
    offsets=[(v.co-start).length for v,start in zip(guard.data.vertices,initial)]
    bpy.data.objects.remove(probe,do_unlink=True)
    for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
    r.data.pose_position='REST';r['FootGuardsStyle']=0;review.build.refresh(r)
    dest=OUT/kind;dest.mkdir(exist_ok=True);s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
    scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
    review.render(s,r,scale,dest,'Rest_Guards',(1,-1,.35),(0,-.05,.12),.55,600,600)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Gameplay_High_Staged.blend'),compress=True)
    report['presets'].append(dict(preset=kind,changed_vertices=sum(x>1e-7 for x in offsets),maximum_offset_m=max(offsets),previous_pass=record['passed']))
    (OUT/'fit.json').write_text(json.dumps(report,indent=2))
