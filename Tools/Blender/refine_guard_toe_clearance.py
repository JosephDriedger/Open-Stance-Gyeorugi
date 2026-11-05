"""Small smooth opening clearance for exposed-toe surface intersections."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import audit_sparring_styles as review
BASE=review.ROOT/'Resources/Models/FinalRefinement';OUT=BASE/'GuardBodyVariantsV7';OUT.mkdir(exist_ok=True)
prior=json.loads((BASE/'GuardBodyVariantsV4/surface_validation.json').read_text());report=dict(production_installed=False,presets=[])
for record in prior['presets']:
    kind=record['preset'];bpy.ops.wm.open_mainfile(filepath=str(BASE/f'GuardBodyVariantsV4/{kind}/Gameplay_High_Staged.blend'))
    s=bpy.context.scene;r=bpy.data.objects['RIG_Body_'+kind];r.data.pose_position='REST'
    body=bpy.data.objects['Body'].copy();body.data=body.data.copy();s.collection.objects.link(body);body.hide_render=True
    for mod in list(body.modifiers):
        if mod.type=='MASK':body.modifiers.remove(mod)
    bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mesh.calc_loop_triangles()
    tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in mesh.vertices],[tuple(t.vertices) for t in mesh.loop_triangles],all_triangles=True);ev.to_mesh_clear()
    guard=bpy.data.objects['FootGuards'];padded=bpy.data.objects['FootGuards_PaddedInstep'];maximum=0
    if not record['passed']:
        for base in (0,6144):
            delta=np.zeros((48,64,3))
            for i in range(3072):
                row=i//64;fade=max(0,1-row/12)
                if not fade:continue
                p=guard.matrix_world@guard.data.vertices[base+i+3072].co;hit,n,_,_=tree.find_nearest(p)
                delta[row,i%64]=guard.matrix_world.inverted().to_3x3()@(n*(.003 if kind=='Stocky' else .0015)*fade)
            for _ in range(3):
                near=(np.roll(delta,1,axis=1)+np.roll(delta,-1,axis=1)+np.concatenate((delta[:1],delta[:-1]))+np.concatenate((delta[1:],delta[-1:])))/4
                delta=.7*delta+.3*near
            for i in range(3072):
                d=Vector(delta[i//64,i%64]);maximum=max(maximum,d.length)
                for obj in (guard,padded):
                    obj.data.vertices[base+i].co+=d;obj.data.vertices[base+i+3072].co+=d
        guard.data.update();padded.data.update()
    bpy.data.objects.remove(body,do_unlink=True)
    dest=OUT/kind;dest.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Gameplay_High_Staged.blend'),compress=True)
    report['presets'].append(dict(preset=kind,maximum_added_offset_m=maximum))
(OUT/'fit.json').write_text(json.dumps(report,indent=2))
