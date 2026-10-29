"""Rebuild only the simulation surface; retain editable belt parts and body rig."""
import bpy
from mathutils import Vector,Matrix

def normalize_world_mesh(o):
    """Bake the complete parent/world transform, not just the local scale."""
    matrix=o.matrix_world.copy()
    points=[matrix@v.co for v in o.data.vertices]
    keys=[[matrix@v.co for v in key.data] for key in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
    o.parent=None;o.matrix_world=Matrix.Identity(4)
    for v,p in zip(o.data.vertices,points):v.co=p
    if keys:
        for key,coords in zip(o.data.shape_keys.key_blocks,keys):
            for v,p in zip(key.data,coords):v.co=p
    bpy.context.view_layer.update()
    assert max((o.matrix_world@v.co-p).length for v,p in zip(o.data.vertices,points))<1e-6
    return list(o.matrix_world.to_scale())

def rebuild(proxy, rig, fitted=False, anchor_fit=False):
    old = proxy.data
    points = [proxy.matrix_world @ v.co for v in old.vertices]
    top = max(p.z for p in points)
    roots = [p for p in points if p.z > top-.012]
    y = sum(p.y for p in roots)/len(roots)
    scale = (rig.matrix_world @ rig.data.bones['head'].head_local).z/1.578
    if fitted:
        garment_points = [o.matrix_world@v.co for name in ['Jacket_Front_Left','Jacket_Front_Right']
                          for o in [bpy.data.objects[name]] for v in o.data.vertices
                          if abs((o.matrix_world@v.co).x)<.09*scale and top-.28*scale<(o.matrix_world@v.co).z<top]
        assert garment_points
        y = min(y,min(p.y for p in garment_points)-.008*scale)
    cols, rows = 5, 25
    verts, faces, sides, uv = [], [], [], []
    inverse = proxy.matrix_world.inverted()
    for side, sign, length in [(0,1,.28),(1,-1,.245)]:
        start = len(verts)
        for row in range(rows):
            t = row/(rows-1)
            for col in range(cols):
                u = col/(cols-1)
                spread=min(1,t/.18) if anchor_fit else 1
                center=.014*(1-spread)+(.027+.018*t)*spread
                width=.024*(1-spread)+.04*spread
                p = Vector((scale*(sign*center+(u-.5)*width), y-.012*scale*t, top-length*scale*t))
                verts.append(inverse @ p); sides.append(side); uv.append((u*.08,t*.5))
        for row in range(rows-1):
            for col in range(cols-1):
                a = start+row*cols+col
                faces.append((a+cols,a+cols+1,a+1,a) if fitted else (a,a+1,a+cols+1,a+cols))
    mesh = bpy.data.meshes.new('Belt clean simulation grid')
    mesh.from_pydata(verts,[],faces); mesh.update()
    for material in old.materials: mesh.materials.append(material)
    attr = mesh.attributes.new('BeltSide','INT','POINT')
    for item, side in zip(attr.data,sides): item.value = side
    layer = mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for loop in polygon.loop_indices: layer.data[loop].uv = uv[mesh.loops[loop].vertex_index]
    proxy.data = mesh
    proxy.vertex_groups.clear()
    pelvis = proxy.vertex_groups.new(name='pelvis'); pelvis.add(list(range(len(verts))),1,'REPLACE')
    pin = proxy.vertex_groups.new(name='LiveCloth_Pin')
    for i in range(len(verts)):
        row = (i % (rows*cols))//cols
        weight=(1 if row==0 else 0) if anchor_fit else (1 if row<2 else (.5 if row==2 else 0))
        pin.add([i],weight,'REPLACE')
    cloth = next(m for m in proxy.modifiers if m.type=='CLOTH')
    cs = cloth.settings
    cs.vertex_group_mass = pin.name; cs.use_dynamic_mesh=False
    cs.mass = .001; cs.quality=40; cs.bending_stiffness=1
    cs.bending_damping=2; cs.air_damping=2
    cc = cloth.collision_settings
    cc.use_self_collision=True; cc.self_distance_min=.001*scale
    cc.self_friction=0; cc.vertex_group_self_collisions=''
    cc.vertex_group_object_collisions=''
    return {'vertices':len(verts),'faces':len(faces),'root_y':y,'top_z':top,'scale':scale,'knot_width_attachment':anchor_fit}

def garment_contact(scene, cloth):
    collection=bpy.data.collections.new('SIM_Low_Resolution_Garment_Contact')
    scene.collection.children.link(collection)
    for name in ['Pants','Jacket_Front_Left','Jacket_Front_Right','Jacket_Back']:
        source=bpy.data.objects[name]; proxy=source.copy();proxy.data=source.data.copy()
        proxy.name='SIM_LowRes_'+name;collection.objects.link(proxy)
        proxy.animation_data_clear();proxy.hide_render=False;proxy.hide_viewport=False;proxy.hide_set(False)
        proxy['SimulationOnly']=True;proxy.display_type='WIRE'
        for mod in list(proxy.modifiers):
            if mod.type!='ARMATURE':proxy.modifiers.remove(mod)
        bpy.ops.object.select_all(action='DESELECT');proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        proxy.modifiers.new('Low resolution garment contact','COLLISION')
        proxy.collision.thickness_outer=.003;proxy.collision.thickness_inner=.001;proxy.collision.cloth_friction=0
        for prop in ['visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow']:setattr(proxy,prop,False)
    cloth.collision_settings.collection=collection
    return collection.name
