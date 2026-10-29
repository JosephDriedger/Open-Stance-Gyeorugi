"""Keep combed fiber ribbons outside their matching scalp coverage surface."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def outward_coverage(scene,rig):
    scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
    center=Vector((0,0,1.65))*scale;rows=[]
    for o in scene.objects:
        if o.type!='MESH' or not o.name.endswith('__Scalp_Coverage'):continue
        normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
        score=sum((o.matrix_world@p.center-center).dot((normal_matrix@p.normal).normalized())*p.area for p in o.data.polygons)
        if score>=0:continue
        for polygon in o.data.polygons:
            maps=[{o.data.loops[i].vertex_index:layer.data[i].uv.copy() for i in polygon.loop_indices} for layer in o.data.uv_layers]
            polygon.flip()
            for layer,values in zip(o.data.uv_layers,maps):
                for i in polygon.loop_indices:layer.data[i].uv=values[o.data.loops[i].vertex_index]
        o.data.update();rows.append(o.name)
    return rows

def apply(scene):
    rows=[]
    for fibers in scene.objects:
        if fibers.type!='MESH' or not fibers.name.endswith('__Combed_Hair_Fibers'):continue
        core=bpy.data.objects.get(fibers.name.replace('__Combed_Hair_Fibers','__Scalp_Coverage'))
        if not core or not core.data.shape_keys or not fibers.data.shape_keys:continue
        inverse=fibers.matrix_world.inverted();count=0;maximum=0
        for key in fibers.data.shape_keys.key_blocks:
            target=core.data.shape_keys.key_blocks.get(key.name)
            if target is None:continue
            tree=BVHTree.FromPolygons([core.matrix_world@p.co for p in target.data],[tuple(p.vertices) for p in core.data.polygons])
            for v in key.data:
                point=fibers.matrix_world@v.co;hit,normal,_,distance=tree.find_nearest(point)
                if hit is None or distance>.012:continue
                clearance=.00035 if key.name=='HelmetFit' else .0008
                signed=(point-hit).dot(normal)
                if signed<clearance:
                    delta=normal*(clearance-signed);v.co=inverse@(point+delta)
                    count+=1;maximum=max(maximum,delta.length)
        for v,p in zip(fibers.data.vertices,fibers.data.shape_keys.key_blocks[0].data):v.co=p.co
        rows.append({'object':fibers.name,'adjusted_key_vertices':count,'maximum_shift_m':maximum})
    return rows
