"""Compare body-surface-derived knee weights, without enlarging the trousers."""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).parent))
import audit_sparring_styles as review
OUT=review.ROOT/'Resources/Models/FinalRefinement/KneeSurfaceWeights'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(review.ROOT/'Resources/Models/FinalRefinement/FootguardSmoothKickReview/Animation_Test.blend'))
s=bpy.context.scene; rig=bpy.data.objects['RIG_Body_Stocky']; pants=bpy.data.objects['Pants']; body=bpy.data.objects['Body']
scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
probe=body.copy(); probe.data=body.data.copy(); s.collection.objects.link(probe); probe.hide_render=True
for mod in list(probe.modifiers):
    if mod.type=='MASK': probe.modifiers.remove(mod)
disabled=[]
for mod in pants.modifiers:
    if mod.type!='ARMATURE': disabled.append((mod,mod.show_viewport)); mod.show_viewport=False
def geometry(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh(); mesh.calc_loop_triangles()
    pts=[obj.matrix_world@v.co for v in mesh.vertices]; tris=[tuple(t.vertices) for t in mesh.loop_triangles]
    ev.to_mesh_clear(); return pts,tris
indices=[v.index for v in pants.data.vertices if .16*scale<(pants.matrix_world@v.co).z<.65*scale]
def check():
    rows=[]
    for frame in range(1,145):
        s.frame_set(frame); bpy.context.view_layer.update(); bp,bt=geometry(probe); pp,_=geometry(pants)
        tree=BVHTree.FromPolygons(bp,bt,all_triangles=True); distances=[]
        for i in indices:
            hit,n,_,_=tree.find_nearest(pp[i]); distances.append((pp[i]-hit).dot(n))
        rows.append(dict(frame=frame,minimum_m=min(distances),inside_1mm=sum(d<-.001 for d in distances)))
    return rows
before=check(); s.frame_set(1); rig.data.pose_position='REST'; bpy.context.view_layer.update()
bp,bt=geometry(probe); assert len(bp)==len(probe.data.vertices)
tree=BVHTree.FromPolygons(bp,bt,all_triangles=True)
bodyweights=[{probe.vertex_groups[g.group].name:g.weight for g in v.groups if probe.vertex_groups[g.group].name in rig.data.bones} for v in probe.data.vertices]
changed=0
for v in pants.data.vertices:
    p=pants.matrix_world@v.co; z=p.z/scale
    alpha=max(0,min(1,(z-.34)/.08,(.68-z)/.08)); alpha=alpha*alpha*(3-2*alpha)
    if not alpha: continue
    hit,normal,face,distance=tree.find_nearest(p); tri=bt[face]
    bary=barycentric_transform(hit,*[bp[i] for i in tri],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    old={pants.vertex_groups[g.group].name:g.weight for g in v.groups if pants.vertex_groups[g.group].name in rig.data.bones}
    new={n:w*(1-alpha) for n,w in old.items()}
    for index,factor in zip(tri,bary):
        for name,weight in bodyweights[index].items(): new[name]=new.get(name,0)+alpha*max(0,factor)*weight
    new=dict(sorted(new.items(),key=lambda item:-item[1])[:4]); total=sum(new.values())
    for name in old: pants.vertex_groups[name].remove([v.index])
    for name,weight in new.items():
        (pants.vertex_groups.get(name) or pants.vertex_groups.new(name=name)).add([v.index],weight/total,'REPLACE')
    changed+=1
rig.data.pose_position='POSE'; pants.update_tag(); after=check()
(OUT/'comparison.json').write_text(json.dumps(dict(changed_vertices=changed,before=before,after=after,
    production_installed=False,scope='Full-body nearest-surface vertex clearance over a dummy kick; no surface-intersection or visual acceptance'),indent=2))
for mod,enabled in disabled: mod.show_viewport=enabled
bpy.data.objects.remove(probe,do_unlink=True)
s.render.engine='CYCLES'; s.cycles.samples=16; s.cycles.use_denoising=True
for frame in (17,26,31,35,61):
    s.frame_set(frame); review.render(s,rig,scale,OUT,'Full_'+str(frame),(4,-.8,1.65),(0,-.25,.95),2.25,700,850)
s.frame_set(1); bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Candidate.blend'),compress=True)
