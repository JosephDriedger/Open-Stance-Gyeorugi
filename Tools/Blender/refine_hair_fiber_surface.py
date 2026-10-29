"""Subtle, irregular tangent detail and lower-bob smoothing for staged review."""
import bpy,numpy as np
from mathutils.kdtree import KDTree

def apply(scene, rig, out):
    image=bpy.data.images.new('FineIrregularHairNormal',width=2048,height=512,alpha=True)
    image.colorspace_settings.name='Non-Color'
    rng=np.random.default_rng(421)
    x=np.arange(2048)[None,:];y=np.arange(512)[:,None]/512
    fine=rng.normal(0,1,2048);fine=(np.roll(fine,1)+2*fine+np.roll(fine,-1))/4
    phase=np.rint(2*np.sin(y*8)+np.sin(y*19)).astype(int)
    dx=.07*fine[(x+phase)%2048]+.012*np.sin(x*.31+y*13)
    dy=.006*np.sin(y*17+x*.03)
    rgba=np.ones((512,2048,4),dtype=np.float32)
    rgba[:,:,0]=(dx+1)/2;rgba[:,:,1]=(dy+1)/2;rgba[:,:,2]=(np.sqrt(1-dx*dx-dy*dy)+1)/2
    # Keep the existing alpha texture separately; this map supplies normals only.
    image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(out/'FineIrregularHairNormal.png');image.file_format='PNG';image.save();image.pack()
    for material in bpy.data.materials:
        if not material.name.startswith('FiberFinish_') or not material.use_nodes:continue
        for node in list(material.node_tree.nodes):
            if node.type=='NORMAL_MAP':
                tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
                material.node_tree.links.new(tex.outputs['Color'],node.inputs['Color']);node.inputs['Strength'].default_value=.4
            elif node.type=='BSDF_PRINCIPLED':
                node.inputs['Roughness'].default_value=.55
                if 'Anisotropic IOR Level' in node.inputs:node.inputs['Anisotropic IOR Level'].default_value=.4
    core=bpy.data.objects['Hair_Chin_Length_Bob__Scalp_Coverage']
    fibers=bpy.data.objects['Hair_Chin_Length_Bob__Combed_Hair_Fibers']
    scale=(rig.matrix_world@rig.data.bones['head'].head_local).z/1.578
    adjacent=[set() for _ in core.data.vertices]
    for e in core.data.edges:
        a,b=e.vertices;adjacent[a].add(b);adjacent[b].add(a)
    for key in core.data.shape_keys.key_blocks:
        original=[p.co.copy() for p in key.data];points=[p.copy() for p in original]
        for _ in range(4):
            next_points=[]
            for i,p in enumerate(points):
                weight=.3*max(0,min(1,(1.62*scale-(core.matrix_world@p).z)/(.08*scale)))
                average=sum((points[j] for j in adjacent[i]),p*0)/max(1,len(adjacent[i]))
                next_points.append(p.lerp(average,weight) if adjacent[i] else p)
            points=next_points
        tree=KDTree(len(original))
        for i,p in enumerate(original):tree.insert(core.matrix_world@p,i)
        tree.balance()
        target=fibers.data.shape_keys.key_blocks.get(key.name)
        if target:
            inverse=fibers.matrix_world.inverted().to_3x3()
            for p in target.data:
                _,i,_=tree.find(fibers.matrix_world@p.co)
                p.co+=inverse@(core.matrix_world.to_3x3()@(points[i]-original[i]))
        for p,value in zip(key.data,points):p.co=value
    for o in [core,fibers]:
        for v,p in zip(o.data.vertices,o.data.shape_keys.key_blocks[0].data):v.co=p.co
