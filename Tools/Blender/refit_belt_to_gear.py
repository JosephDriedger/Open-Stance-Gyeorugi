"""Refit the bone-chain belt tails (belt_bone_chain.py) to the real fighter gear and export the follower FBX.

The chain was built on the study dobok, which sits about 7 cm closer to the body than the real Medium jacket, so
the tails hung under the jacket skirt. This keeps the real gear's belt band and knot (the old SK_Fighter_Belt
FBX), drops its two small tails, and moves the chain tails (bones and mesh together) to hang straight down the
jacket's front surface from the old tails' root.

Usage inside Blender, with a Body_Type_Studies candidate open (the one made by belt_bone_chain.finish):
    import refit_belt_to_gear as r; r.refit(); r.export(path)
Run open_mainfile in one call and refit in the next (imports need a fresh context).
"""
import bpy,bmesh
from mathutils import Vector
from belt_bone_chain import rig_object,strip_keys,export_fbx,TAILS,SEGMENTS

FITTED=r'D:\Open-Stance-Gyeorugi\Resources\Models\Fitted'
FRONT_CLEARANCE=.015   # m, tail centre line in front of the jacket's front surface (Medium: jacket -0.217, tails -0.232)
TAIL_MAX_VERTS=60      # old-belt islands this small, hanging well below the band, are its tails
BELT_PATCH_UV=(.375,.875)  # atlas cell 1 ("belt") of build_clean_gear.py: GRID 4, u=(1+.5)/4, v=1-(0+.5)/4
WEAVE_TILE=.05         # m of surface per weave-normal repeat (build_clean_gear.TILE)
GEAR_MATERIAL='Belt_Gear'
CROSS_CURVE=.004     # m: how far the tail edges curl back towards the body across its width (cloth is never dead flat)

def _chain_world(rig,side):
    W=rig.matrix_world;bones=rig.data.bones
    return [W@bones[f'belt_{side}_{k+1:02d}'].head_local for k in range(SEGMENTS)]+[W@bones[f'belt_{side}_{SEGMENTS:02d}'].tail_local]

def _centre_y(chain,z):
    """y of the chain's centre line at height z (chain runs downwards)."""
    for a,b in zip(chain,chain[1:]):
        if b.z<=z<=a.z:
            t=(a.z-z)/((a.z-b.z) or 1e-9);return a.y+(b.y-a.y)*t
    return chain[0].y if z>chain[0].z else chain[-1].y

def gear_fbx(kind,part):
    folder='MH_FighterBase_Body' if kind=='Medium' else f'MH_Fighter{kind}_Body'
    return rf'{FITTED}\{folder}\SK_Fighter_{part}.fbx'

def _import(path):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=path);bpy.context.view_layer.update()
    new=[o for o in bpy.data.objects if o not in before]
    return next(o for o in new if o.type=='MESH'),next(o for o in new if o.type=='ARMATURE')

def _islands(bm):
    seen=set();out=[]
    for v in bm.verts:
        if v.index in seen:continue
        stack=[v];comp=[];seen.add(v.index)
        while stack:
            a=stack.pop();comp.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if b.index not in seen:seen.add(b.index);stack.append(b)
        out.append(comp)
    return out

def measure(kind,log=lambda *a:None):
    """(tail root z, tail centre-line y) for this body type, read from its real belt and jacket."""
    belt,brig=_import(gear_fbx(kind,'Belt'));me=belt.data;me.transform(belt.matrix_world)
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();isl=_islands(bm)
    band_min=min(c.co.z for c in max(isl,key=len))
    tails=[c for c in isl if len(c)<=TAIL_MAX_VERTS and min(v.co.z for v in c)<band_min-.1]
    root=max(v.co.z for c in tails for v in c);bm.free()
    jacket,jrig=_import(gear_fbx(kind,'Jacket'))
    front=min((jacket.matrix_world@v.co).y for v in jacket.data.vertices
              if root-.06<(jacket.matrix_world@v.co).z<root-.005 and abs((jacket.matrix_world@v.co).x)<.035)
    for o in (belt,brig,jacket,jrig):bpy.data.objects.remove(o,do_unlink=True)
    log('measured',kind,'tail root z',round(root,3),'jacket front y',round(front,3),'tails',len(tails))
    return root,front-FRONT_CLEARANCE

def _gear_material():
    return bpy.data.materials.get(GEAR_MATERIAL) or bpy.data.materials.new(GEAR_MATERIAL)

def _gear_uvs(o):
    """The real belt's two UV sets on a tail: UVMap = the belt patch of the colour atlas (one point), UVWeave = planar
    projection in world metres / 5 cm for the weave normal map, exactly as build_clean_gear.to_object does it."""
    me=o.data
    for layer in list(me.uv_layers):me.uv_layers.remove(layer)
    uv0=me.uv_layers.new(name='UVMap');uv1=me.uv_layers.new(name='UVWeave')
    co=[o.matrix_world@v.co for v in me.vertices]
    for p in me.polygons:
        pts=[co[me.loops[i].vertex_index] for i in p.loop_indices]
        n=(pts[1]-pts[0]).cross(pts[2]-pts[0]);ax=max(range(3),key=lambda k:abs(n[k]));dims=[d for d in range(3) if d!=ax]
        for li,q in zip(p.loop_indices,pts):
            uv0.data[li].uv=BELT_PATCH_UV;uv1.data[li].uv=(q[dims[0]]/WEAVE_TILE,q[dims[1]]/WEAVE_TILE)

def refit(kind='Medium',log=lambda *a:None):
    rig=rig_object();Wi=rig.matrix_world.inverted();W=rig.matrix_world
    TAIL_TOP_Z,FRONT_Y=measure(kind,log)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)  # the imports in measure() moved the active object
    log('start');dz=TAIL_TOP_Z-_chain_world(rig,'l')[0].z
    report={'kind':kind,'dz':round(dz,4),'tail_root_z':round(TAIL_TOP_Z,4),'front_y':round(FRONT_Y,4)}
    # 1. straighten and move the chain tails: mesh vertices first (they use the old chain), then the bones
    chains={side:_chain_world(rig,side) for side,_ in TAILS}
    for side,name in TAILS:
        o=bpy.data.objects[name];inv=o.matrix_world.inverted()
        world=[o.matrix_world@v.co for v in o.data.vertices]
        # flatten each row of vertices (same height) onto the front line, keeping its small front-to-back relief;
        # subtracting the chain's own polyline instead would put a slope change at every joint (shading bands)
        rows={}
        for p in world:rows.setdefault(round(p.z/.0005),[]).append(p.y)
        mean={k:sum(v)/len(v) for k,v in rows.items()}
        centre_x=sum(p.x for p in world)/len(world);half=(max(p.x for p in world)-min(p.x for p in world))/2 or 1e-6
        for v,p in zip(o.data.vertices,world):
            curl=CROSS_CURVE*((p.x-centre_x)/half)**2
            v.co=inv@Vector((p.x,FRONT_Y+(p.y-mean[round(p.z/.0005)])+curl,p.z+dz))
        o.data.update()
        for poly in o.data.polygons:poly.use_smooth=True  # the export keeps the mesh's own shading, so the tails read as cloth not facets
        _gear_uvs(o);o.data.materials.clear();o.data.materials.append(_gear_material())
    log('tail meshes moved');
    with bpy.context.temp_override(active_object=rig,object=rig):bpy.ops.object.mode_set(mode='EDIT')
    log('edit mode');eb=rig.data.edit_bones
    for side,_ in TAILS:
        pts=[Vector((p.x,FRONT_Y,p.z+dz)) for p in chains[side]]
        for k in range(SEGMENTS):
            b=eb[f'belt_{side}_{k+1:02d}'];b.head=Wi@pts[k];b.tail=Wi@pts[k+1];b.roll=0
            # a bone pointing straight down has no defined roll: left at 0 each link ends up turned arbitrarily (up to ~100 deg)
            # from its neighbours, so give every link the same frame, local Z towards the character's front
            b.align_roll(Vector((0,-1,0)))
    with bpy.context.temp_override(active_object=rig,object=rig):bpy.ops.object.mode_set(mode='OBJECT')
    log('bones moved')
    # 2. bring in the real belt band and knot
    old,imported_rig=_import(gear_fbx(kind,'Belt'));log('fbx imported')
    me=old.data;me.transform(old.matrix_world)  # world metres
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();isl=_islands(bm)
    band_min=min(c.co.z for c in max(isl,key=len))
    doomed=[v for c in isl if len(c)<=TAIL_MAX_VERTS and min(v.co.z for v in c)<band_min-.1 for v in c]
    report['old_tail_verts_removed']=len(doomed);log('islands done')
    bmesh.ops.delete(bm,geom=doomed,context='VERTS');log('deleted');bm.to_mesh(me);bm.free();log('mesh written')
    band=bpy.data.objects.new('Belt_Band_Gear',me)
    for c in rig.users_collection:c.objects.link(band)
    log('band linked')
    # vertex groups and weights live on the mesh data the band shares with the imported object: nothing to copy
    # one gear material for band and tails: they now share the same UV scheme (UVMap atlas patch, UVWeave tiling)
    me.materials.clear();me.materials.append(_gear_material())
    log('groups made');band.parent=rig;band.scale=(100,100,100);band.matrix_parent_inverse.identity()
    mod=band.modifiers.new('Body motion','ARMATURE');mod.object=rig
    log('modifier added')
    for o in (old,imported_rig):bpy.data.objects.remove(o,do_unlink=True)
    log('old removed')
    report['band_verts']=len(me.vertices);report['uv_layers']={o.name:[l.name for l in o.data.uv_layers] for o in (band,bpy.data.objects['Belt_Tail_Left'],bpy.data.objects['Belt_Tail_Right'])}
    return report

def export(path):
    strip_keys()
    return export_fbx(path,names=('Belt_Band_Gear','Belt_Tail_Left','Belt_Tail_Right'),smooth='OFF')
