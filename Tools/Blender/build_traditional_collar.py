"""Add the broad collar band of a traditional wrap-front dobok jacket.

The band (BAND_WIDTH wide, lying LIFT proud of the cloth) runs as one strip: up the wrapped skirt's front overlap edge
from the hem, up the jacket's diagonal overlap edge to the neck, then round the neckline past the back of the neck until
it tucks under the overlap on the far side. Each point's surface normal and the side the garment lies on come from the
garment itself; the band is skinned with the weights of the garment vertex under it and shares its cotton material.

Run after build_traditional_jacket_skirt.py:
    blender.exe -b <Candidate.blend> -P build_traditional_collar.py -- <out folder>

Adds the object `Jacket_Collar` (Armature + 3 mm Solidify) to the jacket's collection and saves <out folder>/Candidate.blend.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

OUT = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else None
scene = bpy.context.scene
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('RIG_Body_'))
jacket = bpy.data.objects['Jacket']
skirt = bpy.data.objects['Jacket_Skirt']
BAND_WIDTH = .04
LIFT = .004
ACROSS = 5          # vertices across the band
SPACING = .01       # m between band rows along the path
END_TAPER = .08     # m over which the band narrows to nothing at its neck end
NECK_TUCK = math.radians(70)  # the band stops this far short of closing the neck loop: it ends at the side of the neck,
                              # where it would run under the overlap (any further and it lies on the outer band)


def boundary_loops(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    links = defaultdict(list)
    for e in bm.edges:
        if e.is_boundary:
            a, b = (v.index for v in e.verts)
            links[a].append(b)
            links[b].append(a)
    loops, seen = [], set()
    for start in links:
        if start in seen:
            continue
        stack, members = [start], []
        while stack:
            i = stack.pop()
            if i not in seen:
                seen.add(i)
                members.append(i)
                stack += links[i]
        loops.append([obj.matrix_world @ bm.verts[i].co for i in members])
    bm.free()
    return loops


def resample(points, spacing):
    out = [points[0]]
    carry = 0.0
    for a, b in zip(points, points[1:]):
        seg = (b - a).length
        t = spacing - carry
        while t <= seg:
            out.append(a.lerp(b, t / seg))
            t += spacing
        carry = seg - (t - spacing)
    if (out[-1] - points[-1]).length > spacing * .3:
        out.append(points[-1])
    return out


# Garment surfaces for normals and weights.
sources = []
for obj in (jacket, skirt):
    mesh = obj.data
    mesh.calc_loop_triangles()
    pts = [obj.matrix_world @ v.co for v in mesh.vertices]
    tris = [tuple(t.vertices) for t in mesh.loop_triangles]
    sources.append((obj, pts, tris, BVHTree.FromPolygons(pts, tris, all_triangles=True)))
body_centre = Vector((0, sum(p.y for p in sources[0][1]) / len(sources[0][1]), 0))


def nearest(point):
    best = None
    for obj, pts, tris, tree in sources:
        hit, normal, face, dist = tree.find_nearest(point)
        if hit is not None and (best is None or dist < best[3]):
            best = (obj, hit, normal, dist, pts, tris[face])
    return best


# 1. Skirt overlap edge, hem to top: the skirt's outermost front column (it starts at the jacket's overlap edge).
loops = boundary_loops(jacket)
hem_level = min(p.z for l in loops for p in l)
diagonal_loop = max((l for l in loops if min(p.z for p in l) < hem_level + .02),
                    key=lambda l: max(p.z for p in l) - min(p.z for p in l))
if 'OverlapEdgeVerts' in jacket:  # recorded by the jacket layer before it moved anything
    diagonal_loop = [jacket.matrix_world @ jacket.data.vertices[i].co for i in jacket['OverlapEdgeVerts']]
edge_bottom = min(diagonal_loop, key=lambda p: p.z)
# The skirt keeps its build order (rows of SkirtColumns, column 0 = the outer flap's edge), so its edge is column 0.
columns = skirt.get('SkirtColumns', 150)
skirt_edge = sorted((skirt.matrix_world @ v.co for v in skirt.data.vertices if v.index % columns == 0), key=lambda p: p.z)

# 2. Diagonal overlap edge, waist to neck: the front-most boundary point per height.
by_level = {}
for p in diagonal_loop:
    key = round(p.z / .01)
    if key not in by_level or p.y < by_level[key].y:
        by_level[key] = p
diagonal = [by_level[k] for k in sorted(by_level)]

# 3. Neckline: the widest neck loop, from the point nearest the diagonal's top, round the side away from the overlap,
#    past the back, and on until NECK_TUCK short of closing.
neck = max((l for l in loops if min(p.z for p in l) > hem_level + .3), key=lambda l: max(p.x for p in l) - min(p.x for p in l))
neck_centre = sum(neck, Vector()) / len(neck)
top = diagonal[-1]
start_angle = math.atan2(top.y - neck_centre.y, top.x - neck_centre.x)
turn = -1 if edge_bottom.x > 0 else 1   # go round the far side from the overlap edge first
ordered = sorted(neck, key=lambda p: (turn * (math.atan2(p.y - neck_centre.y, p.x - neck_centre.x) - start_angle)) % (2 * math.pi))
ordered = [p for p in ordered if (turn * (math.atan2(p.y - neck_centre.y, p.x - neck_centre.x) - start_angle)) % (2 * math.pi)
           < 2 * math.pi - NECK_TUCK]

path = resample(skirt_edge + diagonal + ordered, SPACING)
# The draped edge carries small wrinkles and a step where the skirt meets the jacket under the belt; a collar band is
# stiff, so its line is relaxed along its length (ends fixed).
for _ in range(6):
    path = [path[0]] + [(path[i - 1] + path[i] * 2 + path[i + 1]) / 4 for i in range(1, len(path) - 1)] + [path[-1]]
segment = []
for p in path:
    segment.append('neck' if p.z > hem_level + .3 and (p - top).length > .03 else 'edge')

# Frames along the path: surface normal and the across-band direction, relaxed so the band does not twist.
frames = []
for i, p in enumerate(path):
    a, b = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
    tangent = (b - a).normalized()
    found = nearest(p)
    normal = found[2].normalized()
    if normal.dot((p - Vector((neck_centre.x if segment[i] == 'neck' else body_centre.x,
                               neck_centre.y if segment[i] == 'neck' else body_centre.y, p.z)))) < 0:
        normal = -normal
    across = normal.cross(tangent).normalized()
    # The band lies on the garment side of the opening edge. That side is fixed once, at the hem (toward the overlap
    # flap's body, away from the open edge), and then kept the same side of the path all the way round: separate rules
    # for the front edges and the neckline disagreed where they meet and folded the band into a tab at the neck.
    if not frames:
        if (across.x > 0) == (edge_bottom.x > 0):
            across = -across
    elif across.dot(frames[-1][1]) < 0:
        across = -across
    frames.append([normal, across, found])
for _ in range(4):
    for j in (0, 1):
        values = [f[j] for f in frames]
        for i in range(1, len(frames) - 1):
            frames[i][j] = (values[i - 1] + values[i] * 2 + values[i + 1]).normalized()

# Build the strip.
bm = bmesh.new()
rows = []
weights_src = []
for i, (p, (normal, across, found)) in enumerate(zip(path, frames)):
    # The far end round the neck runs on under the overlap: taper it to nothing, flush with the jacket, rather than
    # stopping as a square stub that stands off the shoulder.
    end = min(1.0, (len(path) - 1 - i) * SPACING / END_TAPER)
    end = end * end * (3 - 2 * end)
    row = []
    for k in range(ACROSS):
        t = k / (ACROSS - 1)
        lift = LIFT * (1.0 if k else 1.3) * end
        row.append(bm.verts.new(p + across * BAND_WIDTH * t * end + normal * lift))
    rows.append(row)
    weights_src.append(found)
for r0, r1 in zip(rows, rows[1:]):
    for k in range(ACROSS - 1):
        bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
sys.path.insert(0, str(Path(__file__).resolve().parent))
from garment_normals import face_outward
normals_flipped = face_outward(bm, bpy.data.objects["Body"])
for f in bm.faces:
    f.smooth = True
mesh = bpy.data.meshes.new('Jacket_Collar')
bm.to_mesh(mesh)
bm.free()
collar = bpy.data.objects.get('Jacket_Collar')
if collar:
    bpy.data.objects.remove(collar, do_unlink=True)
collar = bpy.data.objects.new('Jacket_Collar', mesh)
for collection in jacket.users_collection:
    collection.objects.link(collar)
for material in jacket.data.materials:
    mesh.materials.append(material)

# Weights from the garment vertex under each band row.
bone_names = set(rig.data.bones.keys())
groups = {}
for i, found in enumerate(weights_src):
    obj, hit, _, _, pts, tri = found
    names = {g.index: g.name for g in obj.vertex_groups}
    vi = min(tri, key=lambda j: (pts[j] - hit).length)
    mix = {names[g.group]: g.weight for g in obj.data.vertices[vi].groups if names[g.group] in bone_names}
    total = sum(mix.values()) or 1
    for name, w in mix.items():
        group = groups.get(name) or collar.vertex_groups.new(name=name)
        groups[name] = group
        group.add([i * ACROSS + k for k in range(ACROSS)], w / total, 'REPLACE')
weave = mesh.uv_layers.new(name='UVWeave')
plain = mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    for li in poly.loop_indices:
        vi = mesh.loops[li].vertex_index
        u, v = (vi % ACROSS) * BAND_WIDTH / (ACROSS - 1), (vi // ACROSS) * SPACING
        weave.data[li].uv = (u / .05, v / .05)
        plain.data[li].uv = (u, v)
weave.active_render = True
arm = collar.modifiers.new('Deform', 'ARMATURE')
arm.object = rig
solid = collar.modifiers.new('Collar thickness', 'SOLIDIFY')
solid.thickness = .003
solid.offset = 1
collar['ExportUV'] = 'UVWeave'
report = {'path_points': len(path), 'skirt_edge': len(skirt_edge), 'diagonal': len(diagonal), 'neck': len(ordered),
          'vertices': len(mesh.vertices), 'groups': len(groups)}
print('COLLAR DONE', json.dumps(report), flush=True)
if OUT:
    (OUT / 'collar_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
