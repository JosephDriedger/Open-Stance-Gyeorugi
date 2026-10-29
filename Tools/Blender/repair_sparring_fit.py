"""Preserve rigs/actions while correcting dressed clearance and helmet-fit hair."""
import bpy,sys,math,json,traceback
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
import repair_visual_fit as old
import audit_sparring_styles as review
ROOT=old.ROOT;OUT=ROOT/'Resources/Models/SparringFitRepair';OUT.mkdir(exist_ok=True)

def tree(o,evaluated=False):
    ob=o.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else o
    mesh=ob.to_mesh() if evaluated else ob.data
    result=BVHTree.FromPolygons([o.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons])
    if evaluated:ob.to_mesh_clear()
    return result

def repair(scene):
    if scene.get('SparringFitRepair')=='2026-10-18':return {'already_repaired':True}
    rig=next(o for o in scene.objects if o.name.startswith('RIG_Body_'))
    scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
    poses={o:o.data.pose_position for o in scene.objects if o.type=='ARMATURE'}
    for o in poses:o.data.pose_position='REST'
    bpy.context.view_layer.update()
    rows={};body=bpy.data.objects.get('Body')
    head=bpy.data.objects.get('Head');headtree=tree(head,True) if head else None
    # Retain anatomy at openings; move the shoulder fabric outside the body.
    if body:
        surf=tree(body)
        for name in ['Jacket','Jacket_WhiteVNeck']:
            o=bpy.data.objects.get(name)
            if not o:continue
            ds=[]
            for v in o.data.vertices:
                p=o.matrix_world@v.co;d=Vector()
                if .09*scale<abs(p.x)<.34*scale and p.z>1.29*scale:
                    for surface in [surf]+([headtree] if headtree else []):
                        hit,n,_,distance=surface.find_nearest(p+d)
                        if hit is not None and distance<.025*scale:
                            sep=(p+d-hit).dot(n)
                            if sep<.009*scale:d+=n*min(.018*scale,.009*scale-sep)
                ds.append(d)
            old.shift(o,ds);rows[name]={'max_offset':max((d.length for d in ds),default=0)}
    # Clear both jacket styles rather than hiding skin or shortening the apron.
    jackets=[tree(bpy.data.objects[n]) for n in ['Jacket','Jacket_WhiteVNeck'] if bpy.data.objects.get(n)]
    for o in scene.objects:
        if o.type!='MESH' or not o.name.startswith(('Quilted_Lace_Back__','Smooth_Buckle_Back__')):continue
        ds=[]
        for v in o.data.vertices:
            p=o.matrix_world@v.co;d=Vector()
            if p.z<1.29*scale and p.y<-.045*scale:
                origin=Vector((0,0,p.z));axis=p-origin;radius=axis.length;axis.normalize()
                need=radius
                for surf in jackets:
                    hit=surf.ray_cast(origin,axis,.36*scale)[0]
                    if hit is not None:need=max(need,(hit-origin).length+.014*scale)
                d=axis*min(.045*scale,max(0,need-radius))
            ds.append(d)
        old.shift(o,ds)
        rows[o.name]={'max_offset':max((d.length for d in ds),default=0)}
    center=Vector((0,.002,1.650))*scale
    # Preserve front face opening; taper the flat rear wall and round the crown.
    for o in scene.objects:
        if o.type!='MESH' or not o.name.startswith(tuple(n+'__' for n in review.build.HELMETS)):continue
        ds=[]
        for v in o.data.vertices:
            p=o.matrix_world@v.co;q=p.copy();rear=old.smooth((p.y/scale+.005)/.075)
            q.x*=1-.055*rear
            q.y=center.y+(p.y-center.y)*(1-.10*rear)
            crown=old.smooth((p.z/scale-1.725)/.055)
            q.z-=.010*scale*crown*min(1,abs(p.x)/(.10*scale))**2
            ds.append(q-p)
        old.shift(o,ds)
    # The original compression was below the evaluated scalp in some presets.
    # Refit only the helmet shape; retain the user's ungeared hairstyles.
    hairrows=[]
    if headtree:
        for o in scene.objects:
            if o.type!='MESH' or not o.name.startswith('Hair_') or not o.data.shape_keys:continue
            key=o.data.shape_keys.key_blocks.get('HelmetFit')
            if not key or any(s in o.name for s in ['__Ponytail','__Coiled_Bun','__Hair_Tie']):continue
            inv=o.matrix_world.inverted();count=0
            for v in key.data:
                p=o.matrix_world@v.co;axis=(p-center).normalized()
                hit=headtree.ray_cast(center,axis,.30*scale)[0]
                if hit is None:continue
                clearance=(.004 if 'Scalp_Coverage' in o.name else .0055)*scale
                v.co=inv@(hit+axis*clearance);count+=1
            hairrows.append({'object':o.name,'fitted_vertices':count})
        # Reduce plastic shine without changing the chosen hair color.
        for o in scene.objects:
            if o.type!='MESH' or not o.name.startswith('Hair_'):continue
            for m in o.data.materials:
                if not m or not m.use_nodes:continue
                for n in m.node_tree.nodes:
                    if n.type=='BSDF_PRINCIPLED':
                        n.inputs['Roughness'].default_value=.82
                        n.inputs['Specular IOR Level'].default_value=.18
    for o,pos in poses.items():o.data.pose_position=pos
    bpy.context.view_layer.update()
    scene['SparringFitRepair']='2026-10-18'
    return {'clearance':rows,'hair':hairrows,'rig_rest_and_actions_preserved':True}

def pilot(kind,level):
    s,r,z,source=review.load(kind,level)
    result=repair(s);d=OUT/'PilotsV3'/kind/level;d.mkdir(parents=True,exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(d/(level+'.blend')),compress=True)
    s.cycles.samples=24
    for j,h,p in [(0,0,0),(1,2,1)]:
        review.select(r,j,h,p,0,1)
        for pose in ['Neutral','Arms_Overhead']:
            review.audit.pose(r,pose,z)
            review.render(s,r,z,d,f'J{j}_H{h}_P{p}_{pose}',(1.7,-4,1.65),(0,0,1.05),2.1,640,720)
    review.audit.pose(r,'Neutral',z)
    for h in range(3):
        for hair in [1,3]:
            review.select(r,0,h,0,0,hair)
            for side,pos in [('Front',(.50,-1,1.84)),('Rear',(.5,1,1.84))]:
                review.render(s,r,z,d,f'H{h}_Hair{hair}_{side}',pos,(0,0,1.65),.55,640,640)
    (d/'repair.json').write_text(json.dumps(result,indent=2))

if __name__=='__main__':
    try:
        for k,l in [('Tall','Preview'),('Female_Athletic','Gameplay_High')]:pilot(k,l)
        (OUT/'pilot_complete.txt').write_text('Complete')
    except:(OUT/'pilot_error.txt').write_text(traceback.format_exc());raise
