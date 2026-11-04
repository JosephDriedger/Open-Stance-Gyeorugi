"""Deterministic local-axis stress poses; not anatomical joint limits."""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).parent))
import audit_sparring_styles as review
ROOT = review.ROOT
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
OUT = ROOT/'Resources/Models/FinalRefinement'/('FootguardLocalROMSmooth' if '--smooth' in args else 'FootguardLocalROMPaired' if '--paired' in args else 'FootguardLocalROM')
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Resources/Models/FinalRefinement/FootguardVariantReview/Candidate.blend'))
s = bpy.context.scene
r = bpy.data.objects['RIG_Body_Stocky']
if '--paired' in args:
    for name in ('FootGuards','FootGuards_PaddedInstep'):
        obj=bpy.data.objects[name]
        if '--smooth' in args:
            import numpy as np
            for base in (0,6144):
                weights=np.zeros((48,64,len(obj.vertex_groups)))
                for i in range(3072):
                    for g in obj.data.vertices[base+i].groups: weights[i//64,i%64,g.group]=g.weight
                for iteration in range(8):
                    near=(np.roll(weights,1,axis=1)+np.roll(weights,-1,axis=1)+np.concatenate((weights[:1],weights[:-1]))+np.concatenate((weights[1:],weights[-1:])))/4
                    weights=.5*weights+.5*near
                for i in range(3072):
                    row=weights[i//64,i%64];indices=np.argsort(row)[-4:];total=sum(row[j] for j in indices)
                    for group in obj.vertex_groups:group.remove([base+i])
                    for j in indices:
                        if row[j]>0:obj.vertex_groups[int(j)].add([base+i],float(row[j]/total),'REPLACE')
        for base in (0,6144):
            for i in range(3072):
                outer=obj.data.vertices[base+i]
                inner=base+i+3072
                weights=[(g.group,g.weight) for g in outer.groups]
                for group in obj.vertex_groups: group.remove([inner])
                for index,weight in weights: obj.vertex_groups[index].add([inner],weight,'REPLACE')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
r.animation_data_clear()
r['BlenderCloth'] = False
r['Wear_FootGuards'] = True
review.build.refresh(r)
probe = bpy.data.objects['Body'].copy()
probe.data = probe.data.copy()
s.collection.objects.link(probe)
probe.hide_render = True
for mod in list(probe.modifiers):
    if mod.type == 'MASK': probe.modifiers.remove(mod)
def geometry(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh(); mesh.calc_loop_triangles()
    result = ([obj.matrix_world@v.co for v in mesh.vertices], [tuple(t.vertices) for t in mesh.loop_triangles])
    ev.to_mesh_clear()
    return result
cases = [('Rest', None, 'X', 0)]
for bone in ('foot_l', 'foot_r', 'ball_l', 'ball_r'):
    for axis in ('X','Y','Z'):
        for angle in (-25,25): cases.append((f'{bone}_{axis}_{angle}',bone,axis,angle))
rows = []
for label, bone, axis, angle in cases:
    for p in r.pose.bones: p.matrix_basis = Matrix.Identity(4)
    if bone: r.pose.bones[bone].matrix_basis = Matrix.Rotation(math.radians(angle),4,axis)
    bpy.context.view_layer.update()
    bp,bt = geometry(probe); bodytree = BVHTree.FromPolygons(bp,bt,all_triangles=True)
    for style,name in enumerate(('FootGuards','FootGuards_PaddedInstep')):
        r['FootGuardsStyle']=style; review.build.refresh(r)
        gp,gt = geometry(bpy.data.objects[name]); distances=[]
        for point in gp:
            hit,n,_,_=bodytree.find_nearest(point); distances.append((point-hit).dot(n))
        tree=BVHTree.FromPolygons(gp,gt,all_triangles=True)
        overlaps=sum(a<b and not set(gt[a])&set(gt[b]) for a,b in tree.overlap(tree))
        rows.append({'pose':label,'style':style,'minimum_clearance_m':min(distances),'inside_over_1mm':sum(d<-.001 for d in distances),'self_overlap_pairs':overlaps})
    print(label, rows[-2:], flush=True)
worst=min(rows,key=lambda x:x['minimum_clearance_m'])
label,bone,axis,angle=next(c for c in cases if c[0]==worst['pose'])
for p in r.pose.bones: p.matrix_basis=Matrix.Identity(4)
if bone:r.pose.bones[bone].matrix_basis=Matrix.Rotation(math.radians(angle),4,axis)
r['FootGuardsStyle']=worst['style'];review.build.refresh(r)
scale=(r.matrix_world@r.data.bones['head'].head_local).z/1.578
side='r' if bone and bone.endswith('_r') else 'l'
target=r.matrix_world@r.pose.bones['foot_'+side].matrix.translation+Vector((0,0,.03*scale))
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True
review.render(s,r,1,OUT,'Worst_Clearance',tuple(target+Vector((.8,-.7,.35))*scale),tuple(target),.43*scale,700,700)
bpy.data.objects.remove(probe,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Worst_Pose.blend'),compress=True)
(OUT/'report.json').write_text(json.dumps({'production_installed':False,'scope':'25 static local-axis stress poses per style; no cloth, no anatomical limit claim, no swept collision test','worst':worst,'passed':all(x['inside_over_1mm']==0 and x['self_overlap_pairs']==0 for x in rows),'checks':rows},indent=2))
