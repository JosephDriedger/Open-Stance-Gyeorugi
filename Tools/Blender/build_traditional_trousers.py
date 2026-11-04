"""Build wide, straight traditional dobok trousers as a sewn garment, drape them with cloth, and swap them in for `Pants`.

The fitted trousers hug the leg (the thigh muscles read through them). Traditional dobok trousers hang straight and wide
from a roomy, gathered seat to the ankle. The garment is built the way it is sewn: a seat tube whose bottom ring splits at
a crotch seam into two leg tubes (the inseam), sized from the body's measured girths plus pattern ease, then draped with
Blender cloth on the bind-pose body (waistband held, gravity, body collision, self collision) so the folds come from the
fabric instead of an inflated shell. Skin weights, the jacket-coverage group and the cloth pin are copied from the fitted
trousers (their crotch and knee weights are tuned), and the weave UVs match theirs (`UVWeave`, 20 per metre).

Run inside Blender (GUI or background) with a fighter .blend open:
    exec(open(r'D:/Open-Stance-Gyeorugi/Tools/Blender/build_traditional_trousers.py').read())
or  blender.exe -b <file.blend> -P build_traditional_trousers.py -- <out folder>

With an out folder it saves <out folder>/Candidate.blend and trousers_report.json; the `Pants` object keeps its modifiers
and drivers, its old shape keys (fitted to the old mesh) are dropped.
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
body = bpy.data.objects['Body']
pants = bpy.data.objects['Pants']
W = rig.matrix_world

# Pattern ease (cm of circumference over the body) and proportions of a traditional straight-leg dobok trouser.
SEAT_EASE = 6.0          # sparring photos: room to kick, no blousing at the seat
WAIST_GATHER = 1.04      # waistband / body waist: snug under the belt (the jacket skirt must lie over it)
THIGH_OPENING = 1.12     # leg girth at the crotch / body thigh girth there
KNEE_GIRTH, HEM_GIRTH = .86, .80   # of the crotch-level leg girth: a straight leg, close to the body (sparring photos)
CROTCH_DROP = .05        # m below the body's crotch
HEM_ABOVE_ANKLE = .03    # m above the ankle joint
SEAT_RING = 72           # vertices round the seat (half per leg side)
SEAM = 19                # vertices across the crotch seam
STEP = .014              # m between rings
INNER_GAP = .006         # m: leg tubes start this far from the centre line
DRAPE_FRAMES = 70
SNAPSHOT, MAX_ROUGHNESS = 10, .0028   # drape snapshot interval (frames), crumple limit (m, see roughness())
SEAT_BLEND = .12         # m below the crotch over which the seat outline eases into the straight leg


def head(name):
    return W @ rig.data.bones[name].head_local


def hull(points):
    pts = sorted({(round(p.x, 4), round(p.y, 4)) for p in points})
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def perimeter(h):
    return sum(math.dist(h[i], h[(i + 1) % len(h)]) for i in range(len(h)))


def ray_hull(h, centre, angle):
    """Distance from centre to the hull boundary along angle."""
    d = (math.cos(angle), math.sin(angle))
    best = 0.0
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        ax, ay = a[0] - centre[0], a[1] - centre[1]
        t = (ax * ey - ay * ex) / den
        s = (ax * d[1] - ay * d[0]) / den
        if t > 0 and 0 <= s <= 1:
            best = max(best, t)
    return best


# --- body measurements -------------------------------------------------------------------------------------------------
bone_names = set(rig.data.bones.keys())
group_names = {g.index: g.name for g in body.vertex_groups}
by_bone = defaultdict(list)
for v in body.data.vertices:
    ws = [(group_names[g.group], g.weight) for g in v.groups if group_names[g.group] in bone_names]
    if ws:
        by_bone[max(ws, key=lambda w: w[1])[0]].append(body.matrix_world @ v.co)
trunk = [p for n, pts in by_bone.items() if n.startswith(('pelvis', 'spine', 'thigh')) for p in pts]
legs = {s: [p for n, pts in by_bone.items() if n.endswith('_' + s) and n.startswith(('thigh', 'calf')) for p in pts] for s in 'lr'}
crotch_z = min(p.z for p in by_bone['pelvis'] if abs(p.x) < .02)
waist_z = max((pants.matrix_world @ v.co).z for v in pants.data.vertices)
seam_z = crotch_z - CROTCH_DROP
hem_z = head('foot_l').z + HEM_ABOVE_ANKLE
knee_z = head('calf_l').z
centre_y = sum(p.y for p in trunk if abs(p.z - .88) < .02) / max(1, sum(1 for p in trunk if abs(p.z - .88) < .02))


def slice_hull(points, z, band=.012):
    return hull([p for p in points if abs(p.z - z) < band])


seat_girth = perimeter(slice_hull(trunk, crotch_z + .08)) + SEAT_EASE / 100
waist_girth = perimeter(slice_hull(trunk, waist_z - .01)) * WAIST_GATHER
thigh_girth = perimeter(slice_hull(legs['l'], seam_z)) * THIGH_OPENING
report = {'crotch_z': round(crotch_z, 3), 'seam_z': round(seam_z, 3), 'waist_z': round(waist_z, 3), 'hem_z': round(hem_z, 3),
          'seat_girth_cm': round(seat_girth * 100, 1), 'waist_girth_cm': round(waist_girth * 100, 1),
          'thigh_opening_cm': round(thigh_girth * 100, 1), 'knee_girth_cm': round(thigh_girth * KNEE_GIRTH * 100, 1),
          'hem_girth_cm': round(thigh_girth * HEM_GIRTH * 100, 1)}

# --- garment construction ----------------------------------------------------------------------------------------------
bm = bmesh.new()
half = SEAT_RING // 2
# Seat ring angles: index 0 = front centre (-y), half = back centre (+y); 1..half-1 run round the left (+x) side.
seat_angles = [-math.pi / 2 + math.pi * k / half for k in range(SEAT_RING)]


def seat_ring(z):
    h = slice_hull(trunk, z) or slice_hull(trunk, z, .03)
    girth = waist_girth + (seat_girth - waist_girth) * min(1, max(0, (waist_z - z) / max(.01, waist_z - (crotch_z + .08))))
    reach = [ray_hull(h, (0, centre_y), a) for a in seat_angles]
    scale = girth / perimeter(h) if h else 1
    ring = []
    for a, r in zip(seat_angles, reach):
        r = max(r * scale, .04)
        ring.append(bm.verts.new((r * math.cos(a), centre_y + r * math.sin(a), z)))
    return ring


seat = []
z = waist_z + .01
while z > seam_z + STEP * .5:
    seat.append(seat_ring(z))
    z -= STEP
seat.append(seat_ring(seam_z))
# Hip slices differ ring to ring; relax each angle's reach vertically so the seat has no horizontal ridges.
for _ in range(4):
    reach = [[math.hypot(v.co.x, v.co.y - centre_y) for v in ring] for ring in seat]
    for j in range(1, len(seat) - 1):
        for k, v in enumerate(seat[j]):
            r = (reach[j - 1][k] + 2 * reach[j][k] + reach[j + 1][k]) / 4
            a = seat_angles[k]
            v.co.x, v.co.y = r * math.cos(a), centre_y + r * math.sin(a)
for a, b in zip(seat, seat[1:]):
    for i in range(SEAT_RING):
        bm.faces.new((a[i], a[(i + 1) % SEAT_RING], b[(i + 1) % SEAT_RING], b[i]))
bottom = seat[-1]
front, back = bottom[0], bottom[half]
# Crotch seam: from back centre under to front centre, dipping slightly.
seam = []
for k in range(1, SEAM):
    t = k / SEAM
    co = back.co.lerp(front.co, t)
    co.z -= .012 * math.sin(math.pi * t)
    seam.append(bm.verts.new(co))


def leg_loops(side):
    if side == 'l':
        first = bottom[0:half + 1] + seam            # front centre -> left side -> back centre -> seam back->front
    else:
        first = [bottom[half]] + bottom[half + 1:] + [bottom[0]] + list(reversed(seam))  # back -> right -> front -> seam
    sign = 1 if side == 'l' else -1
    pts = legs[side]
    centre0 = Vector((sum(p.x for p in pts if abs(p.z - seam_z) < .02) / max(1, sum(1 for p in pts if abs(p.z - seam_z) < .02)),
                      sum(p.y for p in pts if abs(p.z - seam_z) < .02) / max(1, sum(1 for p in pts if abs(p.z - seam_z) < .02))))
    angles = [math.atan2(v.co.y - centre0.y, v.co.x - centre0.x) for v in first]
    # The leg hangs round the smooth hip-knee-ankle line (body slice centroids jump ring to ring and ripple the profile),
    # offset so the line passes through the leg's measured centre at the crotch.
    hip, knee, ankle = head('thigh_' + side), head('calf_' + side), head('foot_' + side)
    offset = Vector((centre0.x, centre0.y)) - (hip.lerp(knee, (hip.z - seam_z) / (hip.z - knee.z))).to_2d()

    def axis_at(zz):
        a, b = (hip, knee) if zz > knee.z else (knee, ankle)
        return a.lerp(b, (a.z - zz) / (a.z - b.z)).to_2d() + offset * max(0.0, min(1.0, (zz - ankle.z) / (seam_z - ankle.z)))
    rings = [first]
    z = seam_z - STEP
    while z > hem_z - STEP * .5:
        zz = max(z, hem_z)
        cx, cy = axis_at(zz)
        if zz > knee_z:
            girth = thigh_girth * (1 + (KNEE_GIRTH - 1) * (seam_z - zz) / (seam_z - knee_z))
        else:
            girth = thigh_girth * (KNEE_GIRTH + (HEM_GIRTH - KNEE_GIRTH) * (knee_z - zz) / (knee_z - hem_z))
        r = girth / (2 * math.pi)
        ring = []
        # Just below the crotch the leg keeps the seat's outline and eases into the straight leg over SEAT_BLEND; a hard
        # change leaves a shelf, which shows as a pouch on each hip below a short jacket.
        blend = min(1.0, (seam_z - zz) / SEAT_BLEND)
        blend = blend * blend * (3 - 2 * blend)
        for a, start in zip(angles, first):
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            if sign * x < INNER_GAP + .02:   # soften the inner side so the legs hang apart
                x = sign * (INNER_GAP + .02) - (sign * (INNER_GAP + .02) - x) * .25
            x, y = start.co.x + (x - start.co.x) * blend, start.co.y + (y - start.co.y) * blend
            ring.append(bm.verts.new((x, y, zz)))
        rings.append(ring)
        if zz == hem_z:
            break
        z -= STEP
    n = len(first)
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    return rings


leg_rings = {s: leg_loops(s) for s in 'lr'}
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
new = bpy.data.meshes.new('Pants_Traditional')
bm.to_mesh(new)
bm.free()
for poly in new.polygons:
    poly.use_smooth = True
garment = bpy.data.objects.new('TraditionalTrousers_Drape', new)
scene.collection.objects.link(garment)
report['vertices'] = len(new.vertices)

# --- drape on the bind-pose body ---------------------------------------------------------------------------------------
pose_position = rig.data.pose_position
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
collider = body.copy()
collider.data = body.data.copy()
collider.name = 'TraditionalTrousers_BodyContact'
scene.collection.objects.link(collider)
for modifier in list(collider.modifiers):
    if modifier.type != 'ARMATURE':
        collider.modifiers.remove(modifier)
collider.modifiers.new('Contact', 'COLLISION')
collider.collision.thickness_outer = .006
collider.collision.cloth_friction = 5
# Other colliders in the file (pants/jacket proxies, capsules) would fight the drape.
muted = []
for obj in scene.objects:
    if obj is collider:
        continue
    for modifier in obj.modifiers:
        if modifier.type == 'COLLISION' and modifier.show_viewport:
            modifier.show_viewport = False
            muted.append(modifier)
pin = garment.vertex_groups.new(name='Drape_Waistband')
for v in new.vertices:
    pin.add([v.index], 1.0 if v.co.z > waist_z - .035 else 0.0, 'REPLACE')
cloth = garment.modifiers.new('Drape', 'CLOTH')
settings = cloth.settings
settings.quality = 14
settings.mass = .45 / len(new.vertices)   # heavy cotton trousers, about 450 g
# Woven cotton hardly stretches: soft tension lets the legs sag under gravity and buckle into accordion ripples.
settings.tension_stiffness = settings.compression_stiffness = 400
settings.shear_stiffness = 60
settings.bending_stiffness = 8
settings.air_damping = 2
settings.vertex_group_mass = pin.name
settings.use_internal_springs = False
settings.shrink_min = 0.0
cloth.collision_settings.use_collision = True
cloth.collision_settings.collection = None
cloth.collision_settings.distance_min = .004
cloth.collision_settings.use_self_collision = True
cloth.collision_settings.self_distance_min = .004
cloth.point_cache.frame_start = 1
cloth.point_cache.frame_end = DRAPE_FRAMES
frame = scene.frame_current
drape_links = defaultdict(list)
for e in new.edges:
    drape_links[e.vertices[0]].append(e.vertices[1])
    drape_links[e.vertices[1]].append(e.vertices[0])


def roughness(points):
    """Mean distance of each point from its neighbours' centre: about 2-2.5 mm for a soft drape, 3+ when crumpled."""
    total = count = 0
    for i, p in enumerate(points):
        ring = drape_links[i]
        if ring:
            total += (p - sum((points[j] for j in ring), Vector()) / len(ring)).length
            count += 1
    return total / max(1, count)


# On some bodies (long-legged ones) the legs buckle into crumples as the drape runs; keep a snapshot every SNAPSHOT
# frames and use the last one that is still smooth enough.
draped_points, used = [v.co.copy() for v in new.vertices], 0
for f in range(1, DRAPE_FRAMES + 1):
    scene.frame_set(f)
    if f % SNAPSHOT == 0 or f == DRAPE_FRAMES:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        draped = bpy.data.meshes.new_from_object(garment.evaluated_get(depsgraph), depsgraph=depsgraph)
        points = [v.co.copy() for v in draped.vertices]
        bpy.data.meshes.remove(draped)
        if roughness(points) > MAX_ROUGHNESS:
            break
        draped_points, used = points, f
report['drape_frames_used'] = used
report['roughness_mm'] = round(roughness(draped_points) * 1000, 2)
garment.modifiers.remove(cloth)
report['drape_max_move_cm'] = round(max((v.co - co).length for v, co in zip(new.vertices, draped_points)) * 100, 1)
for v, co in zip(new.vertices, draped_points):
    v.co = co
for modifier in muted:
    modifier.show_viewport = True
bpy.data.objects.remove(collider, do_unlink=True)
rig.data.pose_position = pose_position
scene.frame_set(frame)
report['drape_frames'] = DRAPE_FRAMES

# --- weights, coverage and pin from the fitted trousers ----------------------------------------------------------------
old = pants.data
old.calc_loop_triangles()
old_points = [pants.matrix_world @ v.co for v in old.vertices]
old_tris = [tuple(t.vertices) for t in old.loop_triangles]
old_tree = BVHTree.FromPolygons(old_points, old_tris, all_triangles=True)
old_groups = {g.index: g.name for g in pants.vertex_groups}
old_weights = [{old_groups[g.group]: g.weight for g in v.groups} for v in old.vertices]
weights = []
for v in new.vertices:
    hit, _, face, _ = old_tree.find_nearest(v.co)
    a, b, c = (old_points[i] for i in old_tris[face])
    v0, v1, v2 = b - a, c - a, hit - a
    d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
    den = d00 * d11 - d01 * d01 or 1e-12
    wb, wc = (d11 * d20 - d01 * d21) / den, (d00 * d21 - d01 * d20) / den
    mix = defaultdict(float)
    for i, f in zip(old_tris[face], (max(0, 1 - wb - wc), max(0, wb), max(0, wc))):
        for name, w in old_weights[i].items():
            mix[name] += w * f
    weights.append(mix)
neighbours = defaultdict(list)
for e in new.edges:
    neighbours[e.vertices[0]].append(e.vertices[1])
    neighbours[e.vertices[1]].append(e.vertices[0])
for _ in range(4):
    smoothed = []
    for i, mix in enumerate(weights):
        blend = defaultdict(float)
        for name, w in mix.items():
            blend[name] += .5 * w
        for n in neighbours[i]:
            for name, w in weights[n].items():
                blend[name] += .5 * w / len(neighbours[i])
        smoothed.append(blend)
    weights = smoothed
for mix in weights:
    deform = sorted(((w, n) for n, w in mix.items() if n in bone_names), reverse=True)[:4]
    total = sum(w for w, _ in deform) or 1
    for n in [n for n in mix if n in bone_names]:
        del mix[n]
    for w, n in deform:
        mix[n] = w / total

# --- weave UVs: round each leg (seam on the inner side) and the seat, 20 per metre -------------------------------------
weave = new.uv_layers.new(name='UVWeave')
plain = new.uv_layers.new(name='UVMap')
leg_centre = {s: Vector((sum(p.x for p in legs[s]) / len(legs[s]), sum(p.y for p in legs[s]) / len(legs[s]), 0)) for s in 'lr'}
for poly in new.polygons:
    corners = []
    for li in poly.loop_indices:
        p = new.vertices[new.loops[li].vertex_index].co
        if p.z > seam_z:
            angle, radius = math.atan2(p.y - centre_y, p.x), .2
        else:
            side = 'l' if p.x >= 0 else 'r'
            sign = 1 if side == 'l' else -1
            angle, radius = math.atan2(p.y - leg_centre[side].y, sign * (p.x - leg_centre[side].x)), .13
        corners.append((li, angle, radius, p.z))
    angles = [a for _, a, _, _ in corners]
    if max(angles) - min(angles) > math.pi:
        corners = [(li, a + 2 * math.pi if a < 0 else a, r, z) for li, a, r, z in corners]
    for li, a, r, z in corners:
        weave.data[li].uv = (a * r / .05, z / .05)
        plain.data[li].uv = (a * r, z)
weave.active_render = True
new.uv_layers.active = weave

# --- swap into the Pants object ----------------------------------------------------------------------------------------
bpy.data.objects.remove(garment, do_unlink=True)
for group in list(pants.vertex_groups):
    pants.vertex_groups.remove(group)
old_mesh = pants.data
pants.data = new
for material in old_mesh.materials:
    new.materials.append(material)
groups = {}
for i, mix in enumerate(weights):
    for name, w in mix.items():
        if w > 1e-4:
            if name not in groups:
                groups[name] = pants.vertex_groups.new(name=name)
            groups[name].add([i], min(1.0, w), 'REPLACE')
report.update({'faces': len(new.polygons), 'groups': len(groups), 'old_vertices': len(old_mesh.vertices)})
bpy.data.meshes.remove(old_mesh)
print('TROUSERS DONE', json.dumps(report), flush=True)
if OUT:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'trousers_report.json').write_text(json.dumps(report, indent=1))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Candidate.blend'), compress=True)
result = report
