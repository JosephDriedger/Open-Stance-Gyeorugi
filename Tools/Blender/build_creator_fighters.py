"""Build five modular creator fighters, preserving the full body and reversible coverage.

blender --background --factory-startup --python Tools/Blender/build_creator_fighters.py -- Medium
Outputs are isolated in Resources/Models/CreatorFighters/<type>.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('types', nargs='*', default=['Compact', 'Medium', 'Stocky', 'LeanTall', 'Tall'])
parser.add_argument('--no-render', action='store_true')
opts = parser.parse_args(args)
sys.argv = [sys.argv[0]]
import build_test_model as base

ROOT = Path(base.ROOT)
TYPES = {'Compact': (165, 60), 'Medium': (175, 68), 'Stocky': (172, 80), 'LeanTall': (185, 72), 'Tall': (192, 84)}
SPARRING = ('Helmet', 'Protector', 'Gloves', 'FootGuards')
export_original = base.export_fbx
coverage_counts = {}


def drive(owner, path, arm, prop, invert=False):
    driver = owner.driver_add(path).driver
    driver.type = 'SCRIPTED' if invert else 'AVERAGE'
    var = driver.variables.new()
    var.name = 'enabled'
    var.type = 'SINGLE_PROP'
    var.targets[0].id = arm
    var.targets[0].data_path = '["%s"]' % prop
    if invert:
        driver.expression = '1-enabled'


def coverage(body):
    """Keep every source vertex; each garment independently controls its own mask."""
    arm = body.parent
    base.say('Coverage owner', arm.name, arm.type)
    centres = base.face_uv_centres(body.data) % 1.0
    for part in base.HFM_PARTS:
        path = f'{base.FITTED}/T_HFM_{part}.png'
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        px, img = base.image_array(path)
        h, w = px.shape[:2]
        hidden = px[np.clip((centres[:, 1]*h).astype(int), 0, h-1),
                    np.clip((centres[:, 0]*w).astype(int), 0, w-1), 0] < .5
        bpy.data.images.remove(img)
        # Only remove a vertex if ALL adjacent polygons are covered. Keep opening boundaries.
        keep = set()
        for face, masked in zip(body.data.polygons, hidden):
            if not masked:
                keep.update(face.vertices)
        remove = sorted(set(range(len(body.data.vertices))) - keep)
        group = body.vertex_groups.new(name=f'CoveredBy_{part}')
        if remove:
            group.add(remove, 1.0, 'REPLACE')
        mod = body.modifiers.new(f'Coverage_{part}', 'MASK')
        mod.vertex_group = group.name
        mod.invert_vertex_group = True
        arm[f'Wear_{part}'] = True
        drive(mod, 'show_viewport', arm, f'Wear_{part}')
        drive(mod, 'show_render', arm, f'Wear_{part}')
        coverage_counts[part] = len(remove)
        base.say('Coverage', part, len(remove))


def skin_detail(material):
    nt = material.node_tree
    shader = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    coord = nt.nodes.new('ShaderNodeTexCoord')
    pores = nt.nodes.new('ShaderNodeTexNoise')
    pores.name = 'Subtle skin microstructure (object metres)'
    pores.inputs['Scale'].default_value = 1400
    pores.inputs['Detail'].default_value = 2
    nt.links.new(coord.outputs['Object'], pores.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .16
    bump.inputs['Distance'].default_value = .00012
    if shader.inputs['Normal'].is_linked:
        nt.links.new(shader.inputs['Normal'].links[0].from_socket, bump.inputs['Normal'])
    nt.links.new(pores.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    rough = nt.nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .40
    rough.inputs['To Max'].default_value = .57
    nt.links.new(pores.outputs['Fac'], rough.inputs['Value'])
    nt.links.new(rough.outputs['Result'], shader.inputs['Roughness'])
    shader.inputs['Subsurface Weight'].default_value = .075
    shader.inputs['Subsurface Scale'].default_value = .002


def buzzcut(head, arm):
    """Short tapered strands on scalp triangles; independently removable under helmet."""
    rng = np.random.default_rng(142)
    mesh = head.data
    mesh.calc_loop_triangles()
    world = head.matrix_world
    co = np.array([(world @ v.co)[:] for v in mesh.vertices])
    top = co[:, 2].max()
    eye_ids = {i for f in mesh.polygons if f.material_index == 2 for i in f.vertices}
    eye_z = float(co[list(eye_ids),2].mean())
    verts, faces = [], []
    for tri in mesh.loop_triangles:
        if mesh.polygons[tri.polygon_index].material_index != 0:
            continue
        pts = co[list(tri.vertices)]
        centre = pts.mean(axis=0)
        # Higher hairline on forehead, lower at back; no strands on face/ears.
        is_front = centre[1] < -.025
        cutoff = top - (.062 if is_front else .118)
        brow_t = (abs(centre[0])-.018)/.043
        brow_arc = eye_z+.024+.006*math.sin(math.pi*max(0,min(1,brow_t)))
        brow = (abs(centre[2]-brow_arc) < .0025*(1-.6*max(0,brow_t)) and 0 < brow_t < 1 and centre[1] < -.055)
        if centre[2] < cutoff and not brow:
            continue
        normal = np.cross(pts[1]-pts[0], pts[2]-pts[0])
        area = np.linalg.norm(normal)/2
        normal /= max(2*area, 1e-10)
        if normal[2] < -.2:
            continue
        count = int(area*(2200000 if brow else 1200000) + rng.random())
        for _ in range(count):
            u, v = rng.random(2)
            if u+v > 1:
                u, v = 1-u, 1-v
            p = pts[0]+u*(pts[1]-pts[0])+v*(pts[2]-pts[0])
            tangent = np.cross(normal, [0, 1, 0])
            tangent /= max(np.linalg.norm(tangent), 1e-8)
            across = np.cross(normal, tangent)
            length = rng.uniform(.0012, .0025) if brow else rng.uniform(.0025, .0045)
            width = .00013
            j = len(verts)
            verts.extend([p+tangent*width, p-tangent*width, p+across*width,
                          p+normal*length+np.array([0,.0005,0])])
            faces.extend([(j,j+1,j+3), (j+1,j+2,j+3), (j+2,j,j+3)])
    data = bpy.data.meshes.new('ShortHair')
    data.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new('Hair_Buzzcut', data)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name='head').add(list(range(len(verts))), 1, 'REPLACE')
    base.bind(obj, arm)
    mat = base.flat_material('Natural_DarkBrown_Hair', (.018,.009,.004), .65)
    data.materials.append(mat)
    arm['Wear_Hair'] = True
    drive(obj, 'hide_render', arm, 'Wear_Hair', True)
    drive(obj, 'hide_viewport', arm, 'Wear_Hair', True)
    return obj


def tailored_jacket(obj, arm):
    """Blank white wrap-style dobok with an overlapping hip-length skirt."""
    from mathutils.kdtree import KDTree
    old = obj.data
    coords = [obj.matrix_world @ v.co for v in old.vertices]
    tree = KDTree(len(coords))
    for i, v in enumerate(coords):
        tree.insert(v, i)
    tree.balance()
    source_weights = [{obj.vertex_groups[g.group].name: g.weight for g in v.groups} for v in old.vertices]
    joints = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
    pel, clav = joints['pelvis'], joints['clavicle_l']
    height, weight = TYPES[base.TYPE]
    scale = height/175
    girth = math.sqrt((weight/(height/100)**2)/(68/1.75**2))*scale
    verts, faces, uvs, weights = [], [], [], []
    # Continuous sleeve rings replace the jagged cropped sleeve islands.
    # Their roots tuck beneath the yoke; cuffs have clearance around the wrists.
    for side in ('l','r'):
        upper, elbow, wrist = [joints[f'{n}_{side}'] for n in ('upperarm','lowerarm','hand')]
        u, f = elbow-upper, wrist-elbow
        split = u.length/(u.length+f.length)
        sleeve_start = len(verts)
        sleeve_rows, sleeve_segments = 42, 48
        for row in range(sleeve_rows+1):
            t = -.16+1.15*row/sleeve_rows
            if t < split:
                centre = upper+u*(t/split)
            else:
                centre = elbow+f*((t-split)/(1-split))
            turn = max(0,min(1,(t-split+.10)/.20))
            axis = (u.normalized()*(1-turn)+f.normalized()*turn).normalized()
            across = Vector((0,-1,0))
            across = (across-axis*across.dot(axis)).normalized()
            around = axis.cross(across).normalized()
            radius = float(np.interp(t,[-.16,.04,.45,.80,.99],[.035,.094,.083,.072,.063]))*girth
            lower_w = max(0,min(1,(t-split+.12)/.24))
            lower_w = lower_w*lower_w*(3-2*lower_w)
            clav_w = max(0,min(1,(.10-t)/.26))
            row_weights = {f'clavicle_{side}':clav_w,
                           f'upperarm_{side}':(1-clav_w)*(1-lower_w),
                           f'lowerarm_{side}':(1-clav_w)*lower_w}
            for col in range(sleeve_segments):
                theta = 2*math.pi*col/sleeve_segments
                fold = .0018*scale*math.cos(theta*6+t*9)*math.exp(-((t-split)/.15)**2)
                point = centre+(across*math.cos(theta)+around*math.sin(theta))*(radius+fold)
                verts.append(tuple(point))
                weights.append({n:w for n,w in row_weights.items() if w>0})
        for row in range(sleeve_rows):
            for col in range(sleeve_segments):
                nxt=(col+1)%sleeve_segments
                faces.append([sleeve_start+row*sleeve_segments+col,
                              sleeve_start+row*sleeve_segments+nxt,
                              sleeve_start+(row+1)*sleeve_segments+nxt,
                              sleeve_start+(row+1)*sleeve_segments+col])
                uvs.append((.125,.875))
    rings, segments = 36, 96
    start = len(verts)
    z0, z1 = pel.z-.275*scale, joints['neck_02'].z-.022*scale
    old_hem = pel.z-.17*scale
    keys = [0,(pel.z+.058*scale-z0)/(z1-z0)] + [(old_hem+t*(z1-old_hem)-z0)/(z1-z0) for t in (.68,.84,.94,1)]
    widths = np.array([.255,.185,.22,.235,.21,.078])*girth
    depths = np.array([.185,.128,.157,.160,.132,.068])*girth
    for row in range(rings+1):
        t = row/rings
        a, b = np.interp(t, keys, widths), np.interp(t, keys, depths)
        for col in range(segments):
            theta = 2*math.pi*col/segments
            front = max(math.cos(theta),0)
            zz = z0+(z1-z0)*t - .135*scale*front**5*max((t-.80)/.20,0)
            # The V lies on the chest, not inside it.
            depth = b + .067*girth*front**4*max((t-.85)/.15,0)
            fold = .0035*math.sin(theta*12+t*5)*math.exp(-((t-keys[1])/.19)**2)
            point = Vector(((a+fold)*math.sin(theta), (pel.y*(1-t)+joints['neck_01'].y*t)-(depth+fold)*math.cos(theta),zz))
            verts.append(tuple(point))
            _, near, _ = tree.find(point)
            # Torso weights only: sleeves must never pull the new chest with an arm.
            w = {n:v for n,v in source_weights[near].items() if n.startswith(('pelvis','spine','clavicle','neck'))}
            total = sum(w.values())
            weights.append({n:v/total for n,v in w.items()} if total else {'spine_03':1})
    for row in range(rings):
        for col in range(segments):
            nxt = (col+1)%segments
            # Short side vents free the skirt over the hips and upper thighs.
            if row/rings < (pel.z-.11*scale-z0)/(z1-z0) and col in (23,24,71,72):
                continue
            faces.append([start+row*segments+col,start+row*segments+nxt,
                          start+(row+1)*segments+nxt,start+(row+1)*segments+col])
            uvs.append((.125,.875))
    # Plain white collar, without rank trim, patches or logos.
    collar_start = len(verts)
    for row in (0,1):
        for col in range(segments):
            vi = start+rings*segments+col
            point = Vector(verts[vi])
            if row:
                toward = Vector(verts[vi-segments])-point
                point += toward.normalized()*min(.025*scale,toward.length)
            point.x *= 1.03
            point.y -= .005*math.cos(2*math.pi*col/segments)
            verts.append(tuple(point))
            weights.append(weights[vi].copy())
    for col in range(segments):
        nxt = (col+1)%segments
        faces.append([collar_start+col,collar_start+segments+col,
                      collar_start+segments+nxt,collar_start+nxt])
        uvs.append((.125,.875))
    # Raised wrap edge: continue one lapel diagonally to the belt, then down
    # the overlapping front skirt. Project onto the new torso so it fits every preset.
    from mathutils.bvhtree import BVHTree
    surface = BVHTree.FromPolygons([Vector(v) for v in verts], faces)
    seam_start = len(verts)
    seam_rows = 44
    seam_top = z1-.137*scale
    belt_z = pel.z+.058*scale
    for row in range(seam_rows+1):
        z = seam_top+(z0+.002*scale-seam_top)*row/seam_rows
        if z >= belt_z:
            progress = (seam_top-z)/(seam_top-belt_z)
            centre_x = .155*girth*progress
            width = .024*scale
        else:
            progress = (belt_z-z)/(belt_z-z0)
            centre_x = (.155-.035*progress)*girth
            width = .008*scale
        for side in (-1,1):
            x = centre_x+side*width/2
            hit = surface.ray_cast(Vector((x,-1,z)), Vector((0,1,0)))
            if hit[0] is None:
                raise RuntimeError('Wrap seam did not reach the torso')
            point = hit[0]+Vector((0,-.0035,0))
            verts.append(tuple(point))
            # Same local torso weights as the supporting surface.
            nearest = min(range(start,start+(rings+1)*segments), key=lambda i:(Vector(verts[i])-point).length_squared)
            weights.append(weights[nearest].copy())
    for row in range(seam_rows):
        a = seam_start+2*row
        faces.append([a,a+1,a+3,a+2])
        uvs.append((.125,.875))
    data = bpy.data.meshes.new('Tailored_Dobok')
    # Preserve world placement; imported FBX meshes may carry a transform.
    inv = obj.matrix_world.inverted()
    data.from_pydata([inv @ Vector(v) for v in verts], [], faces)
    for mat in old.materials:
        data.materials.append(mat)
    obj.data = data
    obj.vertex_groups.clear()
    groups = {}
    for i, row in enumerate(weights):
        for n, w in row.items():
            if n not in groups:
                groups[n] = obj.vertex_groups.new(name=n)
            groups[n].add([i],w,'REPLACE')
    uv = data.uv_layers.new(name='UVMap')
    weave = data.uv_layers.new(name='UVWeave')
    for face, patch in zip(data.polygons,uvs):
        face.use_smooth = True
        for li in face.loop_indices:
            uv.data[li].uv = patch
            point = verts[data.loops[li].vertex_index]
            weave.data[li].uv = (point[0]/.05,point[2]/.05)
    # Recalculate winding consistently, including original sleeve islands.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()


def clean_ankle_cuffs(obj, arm):
    """Relax the source ankle hems into level, open cuffs with sock clearance."""
    co = np.array([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
    inv = obj.matrix_world.inverted()
    scale = TYPES[base.TYPE][0]/175
    # Geometric boundary detection ignores FBX UV/normal vertex splits.
    canonical = {}
    ids = []
    for p in co:
        key = tuple(np.round(p,5))
        ids.append(canonical.setdefault(key,len(canonical)))
    edges = {}
    for face in obj.data.polygons:
        vs=list(face.vertices)
        for i,a in enumerate(vs):
            b=vs[(i+1)%len(vs)]
            key=tuple(sorted((ids[a],ids[b])))
            edges[key]=edges.get(key,0)+1
    boundary={v for edge,count in edges.items() if count==1 for v in edge}
    unique=np.zeros((len(canonical),3))
    counts=np.zeros(len(canonical))
    for i,k in enumerate(ids):
        unique[k]+=co[i]
        counts[k]+=1
    unique/=counts[:,None]
    neighbours=[set() for _ in unique]
    for a,b in edges:
        neighbours[a].add(b)
        neighbours[b].add(a)
    for side, sign in [('l',1),('r',-1)]:
        ankle=arm.matrix_world@arm.data.bones[f'foot_{side}'].head_local
        knee=arm.matrix_world@arm.data.bones[f'calf_{side}'].head_local
        hem=ankle.z+.065*scale
        top=ankle.z+.22*scale
        lower=[i for i,p in enumerate(unique) if p[0]*sign>0 and p[2]<top]
        blend={i:max(0,min(1,(top-unique[i,2])/(top-hem))) for i in lower}
        rim={i for i in lower if i in boundary and unique[i,2]<hem+.055*scale}
        for _ in range(50):
            previous=unique.copy()
            for i in lower:
                if neighbours[i]:
                    average=previous[list(neighbours[i])].mean(axis=0)
                    unique[i]=previous[i]+.55*blend[i]*(average-previous[i])
                if i in rim:
                    unique[i,2]=hem
        for i in lower:
            p=Vector(unique[i])
            frac=(p.z-ankle.z)/(knee.z-ankle.z)
            centre=ankle.lerp(knee,frac)
            delta=Vector((p.x-centre.x,p.y-centre.y,0))
            radius=delta.length
            cuff=max(0,min(1,(top-p.z)/(.10*scale)))
            desired=.064*scale
            if radius>1e-6:
                delta*=((1-cuff)*radius+cuff*desired)/radius
                p.x,p.y=centre.x+delta.x,centre.y+delta.y
            if i in rim:
                p.z=hem
            unique[i]=p
    for i,k in enumerate(ids):
        obj.data.vertices[i].co=inv@Vector(unique[k])
    obj.data.update()


def smooth_protector(obj, arm):
    """A broad convex pad surface, retaining the existing perimeter, straps and weights."""
    joints = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
    pel, clav = joints['pelvis'], joints['clavicle_l']
    h, weight = TYPES[base.TYPE]
    girth = math.sqrt((weight/(h/100)**2)/(68/1.75**2))*(h/175)
    inv = obj.matrix_world.inverted()
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        x = abs(p.x)
        front = max(0,min(1,(pel.y-p.y-.02)/.055))
        below_straps = max(0,min(1,(clav.z-.018-p.z)/.045))
        w = front*below_straps
        if w <= 0:
            continue
        # Inner and outer surfaces retain a small physical separation.
        inner = max(0, v.normal.y)*.013
        t = max(0,min(1,(p.z-pel.z-.06)/.40))
        a = (.238+.012*t)*girth
        depth = (.178+.022*t)*girth
        desired = pel.y-depth*math.sqrt(max(.04,1-(x/a)**2))+inner
        p.y = p.y*(1-w)+desired*w
        v.co = inv @ p
    obj.data.update()


def set_mode(arm, sparring):
    for part in SPARRING:
        arm[f'Wear_{part}'] = sparring
    for part in ('Jacket','Pants','Belt'):
        arm[f'Wear_{part}'] = True
    arm.update_tag()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def finish(cam, action):
    arm = bpy.data.objects['root']
    body, head = bpy.data.objects['Body'], bpy.data.objects['Head']
    tailored_jacket(bpy.data.objects['Jacket'], arm)
    smooth_protector(bpy.data.objects['Protector'], arm)
    # Hide only the trousers fully underneath the jacket, keeping overlap at the hem.
    # This follows the jacket switch, so trousers return intact when it is removed.
    pants = bpy.data.objects['Pants']
    clean_ankle_cuffs(pants, arm)
    pelvis_z = (arm.matrix_world @ arm.data.bones['pelvis'].head_local).z
    hem = pelvis_z-.275*(TYPES[base.TYPE][0]/175)
    covered = [v.index for v in pants.data.vertices if (pants.matrix_world @ v.co).z > hem+.065]
    group = pants.vertex_groups.new(name='CoveredBy_Jacket')
    group.add(covered,1,'REPLACE')
    mask = pants.modifiers.new('Jacket overlap','MASK')
    mask.vertex_group = group.name
    mask.invert_vertex_group = True
    arm['Wear_Jacket'] = True
    drive(mask,'show_viewport',arm,'Wear_Jacket')
    drive(mask,'show_render',arm,'Wear_Jacket')
    for part in base.PARTS:
        arm[f'Wear_{part}'] = True
        obj = bpy.data.objects[part]
        drive(obj, 'hide_render', arm, f'Wear_{part}', True)
        drive(obj, 'hide_viewport', arm, f'Wear_{part}', True)
        if part in ('Jacket', 'Pants', 'Belt'):
            thick = obj.modifiers.new('Fabric thickness', 'SOLIDIFY')
            thick.thickness = .0012 if part != 'Belt' else .0025
            thick.offset = 0
    for name in ('M_Skin_Body', 'M_Skin_Head'):
        skin_detail(bpy.data.materials[name])
    hair = buzzcut(head, arm)
    arm['BodyType'] = base.TYPE
    arm['Height_cm'], arm['Weight_kg'] = TYPES[base.TYPE]
    # Importers may invalidate drivers while loading successive FBX armatures.
    # Create the final driver graph only after every part and property exists.
    body.animation_data_clear()
    for mod in body.modifiers:
        if mod.type == 'MASK':
            prop = 'Wear_' + mod.name.removeprefix('Coverage_')
            drive(mod, 'show_viewport', arm, prop)
            drive(mod, 'show_render', arm, prop)
    arm['Instructions'] = 'Object Properties > Custom Properties: Wear_* toggles clothing and matching skin coverage.'
    meshes = [body, head, hair] + [bpy.data.objects[p] for p in base.PARTS]
    scene = bpy.context.scene
    # Softer neutral photographic lighting, with enough contrast to inspect surfaces.
    for name, watts in [('Key',380),('Fill',90),('Rim',220),('Top',80)]:
        bpy.data.lights[name].energy = watts
    scene.view_settings.exposure = -.2
    scene.render.resolution_x, scene.render.resolution_y = 1100, 1400
    scene.render.resolution_percentage = 100
    height = TYPES[base.TYPE][0]/100
    cam.location = (.95, -3.9, height*.58)
    cam.rotation_euler = (Vector((0,0,height*.51))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens = 62
    report = {'body_type':base.TYPE, 'height_cm':TYPES[base.TYPE][0], 'weight_kg':TYPES[base.TYPE][1],
              'source_body_vertices':len(body.data.vertices), 'coverage_vertices':dict(coverage_counts),
              'skeleton_bones':len(arm.data.bones), 'modes':{}}
    # Export evaluated meshes so coverage and garment thickness survive outside Blender.
    for mode, wearing in [('Dobok',False),('Sparring',True)]:
        set_mode(arm, wearing)
        selected = [m for m in meshes if not m.hide_render]
        base.say('Mask states', [(m.name,m.show_viewport,m.show_render) for m in body.modifiers])
        deps = bpy.context.evaluated_depsgraph_get()
        copies = []
        for mesh in selected:
            for mod in mesh.modifiers:
                if mod.type == 'ARMATURE':
                    mod.show_viewport = False
            bpy.context.view_layer.update()
            data = bpy.data.meshes.new_from_object(mesh.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
            copy = mesh.copy()
            copy.data = data
            copy.animation_data_clear()
            copy.modifiers.clear()
            bpy.context.scene.collection.objects.link(copy)
            copy.hide_viewport = copy.hide_render = False
            base.bind(copy, arm)
            copies.append(copy)
            for mod in mesh.modifiers:
                if mod.type == 'ARMATURE':
                    mod.show_viewport = True
            bpy.context.view_layer.update()
        report['modes'][mode] = {'visible_parts':[m.name for m in selected],
                                'body_vertices':len(copies[0].data.vertices)}
        export_original(f'{base.OUT}/{base.NAME}_{mode}.fbx', [arm]+copies, False)
        for obj in copies:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(data)
        if not opts.no_render:
            scene.render.filepath = f'{base.OUT}/{mode}.png'
            bpy.ops.render.render(write_still=True)
    # Every switch must restore the intact source skin.
    for part in base.HFM_PARTS:
        arm[f'Wear_{part}'] = False
    arm.update_tag()
    bpy.context.scene.frame_set(2)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    restored = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
    base.say('Restoration', restored, len(body.data.vertices), report['modes'])
    assert restored == len(body.data.vertices), (restored,len(body.data.vertices))
    assert report['modes']['Dobok']['body_vertices'] > report['modes']['Sparring']['body_vertices']
    report['full_body_restoration_passed'] = True
    report['limitations'] = ['Stock skin maps, not individually authored facial textures',
                            'Head follows body head joint; full facial RigLogic remains Unreal-side',
                            'Five discrete fitted bodies, not continuous body morphs',
                            'Blender procedural surface detail must be recreated or baked for Unreal']
    Path(base.OUT, 'manifest.json').write_text(json.dumps(report, indent=2))
    set_mode(arm, False)
    bpy.ops.object.select_all(action='DESELECT')
    arm.hide_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm


base.apply_body_coverage = coverage
base.check_renders = finish
base.export_fbx = lambda *a, **k: None  # finish exports each explicit wardrobe state
for body_type in opts.types:
    if body_type not in TYPES:
        raise ValueError(f'Unknown body type: {body_type}; expected {list(TYPES)}')
    base.TYPE = body_type
    base.ASSET = 'MH_FighterBase' if body_type == 'Medium' else f'MH_Fighter{body_type}'
    base.FITTED = f'{base.MH}/../Fitted/{base.ASSET}_Body'
    base.OUT = str(ROOT/'Resources'/'Models'/'CreatorFighters'/body_type).replace('\\','/')
    base.TEX_OUT = f'{base.OUT}/Textures'
    base.NAME = f'OpenStance_Creator_{body_type}'
    base.ROM = ''
    coverage_counts.clear()
    try:
        base.build()
    except Exception:
        import traceback
        base.say(traceback.format_exc())
        raise
